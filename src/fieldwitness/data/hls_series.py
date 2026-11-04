"""T1.5: HLS-VI (NDVI, EVI) + Fmask time series for pilot fields via AppEEARS point tasks.

Why point tasks (DECISIONS.md 2026-11-04): AppEEARS area tasks are limited by the number of output
files (~4 field-years per task; 200 fields x 9 years would need ~450 tasks), and direct COG reads
would be ~36 GB because HLS-VI COGs are striped and the fields span the tile. Point tasks are
limited to 1,000 coordinates per request and by the number of values (~1,600 point-years per
task with 6 layers), so each field is sampled at up to MAX_POINTS interior HLS pixel centres (all
of them when it has fewer), fields are grouped into chunks of <= 1,000 points (a field is never
split), and each task covers one year (1,000 points x 1 year was accepted). The field value
per date is the median over its clear sampled pixels.
"""

import json
import math
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from pyproj import Transformer

from fieldwitness.data import appeears as ae
from fieldwitness.resolve.fields import SEED
from fieldwitness.resolve.pixels import HLS_RES_M

OUT = Path("data/appeears")
CAP_BYTES = 1e9
MAX_POINTS = 12
MAX_COORDS = 1000  # AppEEARS: "maximum of 1,000 per request"
PERIODS = [("2015", "09-01-2015", "12-31-2015")] + [
    (str(y), f"01-01-{y}", f"12-31-{y}") for y in range(2016, 2025)
]


def registry_path(region_id: str) -> Path:
    return OUT / f"{region_id}_tasks.json"


def interior_points(
    pilot: gpd.GeoDataFrame, grid: dict, max_per_field: int | None = MAX_POINTS, buffer_m=15.0
) -> list[dict]:
    """Point coordinates at HLS 30 m pixel centres strictly inside each field after the inward
    buffer (same rule as fieldwitness.resolve.pixels). At most `max_per_field` per field, chosen
    with a seeded RNG. id = '<field_id>_<col>_<row>' (tile pixel indices), category = field_id."""
    rng = np.random.default_rng(SEED)
    to_ll = Transformer.from_crs(grid["epsg"], "EPSG:4326", always_xy=True)
    utm = pilot.to_crs(grid["epsg"])
    ulx, uly, res = grid["ulx"], grid["uly"], HLS_RES_M
    out = []
    for fid, geom in zip(utm["field_id"], utm.geometry, strict=True):
        inner = geom.buffer(-buffer_m)
        if inner.is_empty:
            continue
        minx, miny, maxx, maxy = inner.bounds
        i0, i1 = math.ceil((minx - ulx) / res - 0.5), math.floor((maxx - ulx) / res - 0.5)
        j0, j1 = math.ceil((uly - maxy) / res - 0.5), math.floor((uly - miny) / res - 0.5)
        cols, rows = (a.ravel() for a in np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1)))
        xs, ys = ulx + res * (cols + 0.5), uly - res * (rows + 0.5)
        idx = np.flatnonzero(shapely.contains_xy(inner, xs, ys))
        if max_per_field is not None and len(idx) > max_per_field:
            idx = np.sort(rng.choice(idx, max_per_field, replace=False))
        lon, lat = to_ll.transform(xs[idx], ys[idx])
        for k, lo, la in zip(idx, lon, lat, strict=True):
            out.append(
                {
                    "id": f"{fid}_{int(cols[k])}_{int(rows[k])}",
                    "category": fid,
                    "latitude": round(float(la), 7),
                    "longitude": round(float(lo), 7),
                }
            )
    return out


def chunk_by_field(coords: list[dict], max_coords: int = MAX_COORDS) -> list[list[dict]]:
    """Group points into chunks of <= max_coords without splitting a field's points."""
    chunks: list[list[dict]] = [[]]
    by_field: dict[str, list[dict]] = {}
    for c in coords:
        by_field.setdefault(c["category"], []).append(c)
    for pts in by_field.values():
        if len(chunks[-1]) + len(pts) > max_coords:
            chunks.append([])
        chunks[-1].extend(pts)
    return chunks


def point_task(name: str, coords: list[dict], start: str, end: str) -> dict:
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": ae.HLS_LAYERS,
            "coordinates": coords,
        },
    }


def submit_region(region_id: str, grid: dict) -> dict:
    pilot = gpd.read_parquet(f"data/fields/{region_id}_pilot.parquet")
    coords = interior_points(pilot, grid)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{region_id}_points.json").write_text(json.dumps(coords), encoding="utf-8")
    reg_path = registry_path(region_id)
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else {}
    reg.setdefault("tasks", {})
    reg["n_points"] = len(coords)
    reg["max_points_per_field"] = MAX_POINTS
    chunks = chunk_by_field(coords)
    reg["n_chunks"] = len(chunks)
    s = ae.login()
    try:
        for period, start, end in PERIODS:
            for k, chunk in enumerate(chunks):
                name = f"{period}_c{k}"
                if name in reg["tasks"]:
                    continue
                body = point_task(f"fieldwitness-T1.5-{region_id}-{name}", chunk, start, end)
                tid = ae.submit(s, body)
                reg["tasks"][name] = {"task_id": tid, "start": start, "end": end, "n": len(chunk)}
                ae.save_registry(reg_path, reg)  # write each ID immediately (resume path)
                print("submitted", name, tid, flush=True)
    finally:
        print("logout HTTP", ae.logout(s), flush=True)
    return reg


def wait_and_download(region_id: str, poll_s: int = 120, once: bool = False) -> None:
    """Wait for all tasks and download them; stop before further downloads if the size projected
    from the downloaded tasks exceeds the 1 GB cap (CLAUDE.md rule 11). With `once`, make a
    single pass (download what is done, report the rest) and return, so no process outlives an
    unattended run."""
    reg = json.loads(registry_path(region_id).read_text(encoding="utf-8"))
    ids = {v["task_id"]: k for k, v in reg["tasks"].items()}
    s = ae.login()
    try:
        sizes: dict[str, int] = {}
        pending = set(ids)
        while pending:
            counts: dict[str, int] = {}
            for tid in sorted(pending):
                t = ae.task(s, tid)
                counts[t.get("status", "?")] = counts.get(t.get("status", "?"), 0) + 1
                if t.get("status") == "error":
                    print("ERROR", ids[tid], tid, t.get("error"), flush=True)
                    pending.discard(tid)
                elif t.get("status") == "done":
                    files = ae.bundle(s, tid)
                    sizes[tid] = sum(f["file_size"] for f in files)
                    projected = sum(sizes.values()) / len(sizes) * len(ids)
                    if projected > CAP_BYTES:
                        print(f"STOP: projected {projected / 1e6:.0f} MB > 1 GB cap", flush=True)
                        return
                    ae.download(s, tid, files, OUT / region_id / ids[tid])
                    print(
                        f"downloaded {ids[tid]}: {len(files)} files, {sizes[tid] / 1e6:.1f} MB; "
                        f"projected total {projected / 1e6:.0f} MB",
                        flush=True,
                    )
                    pending.discard(tid)
            if pending:
                print(time.strftime("%H:%M:%S"), "status of remaining tasks:", counts, flush=True)
                if once:
                    return
                time.sleep(poll_s)
    finally:
        print("logout HTTP", ae.logout(s), flush=True)
