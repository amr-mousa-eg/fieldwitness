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
CAP_BYTES = 1e9  # CLAUDE.md rule 11: ask before downloading more than 1 GB

# One-time exception approved by the user on 2026-11-04 (DECISIONS.md, "User approval: T1.5 HLS
# download over the 1 GB cap"): the 30 Kansas T1.5 point tasks below, 1,317 MB in total from the
# AppEEARS bundle listings. The cap is 1,317.5 MB, the largest total the approved "1,317 MB" can
# denote; no other margin. It applies only when every task being downloaded is one of these IDs.
APPROVED_OVER_CAP: dict[str, tuple[frozenset[str], float]] = {
    "ks_t14slh": (
        frozenset(
            {
                "f8c665a6-2a8f-4e1d-a131-886e96ae0daa",
                "ae736313-dd01-4a81-87de-844b622f3516",
                "88a1ef5a-f935-44a9-9b48-4dbff0d5b9dd",
                "6a5e2bf9-9d1d-4cab-a047-176605ae0551",
                "a5d9e797-23e5-42d7-a2f9-4dc514b98949",
                "83e1b307-c3d6-4812-b3e9-dc28598cf4f8",
                "74ef5285-4843-42bc-9364-bfb4b7678139",
                "fee5b585-b517-4e6c-a33f-a273bd55ee17",
                "7b42e912-f5b9-436a-aa97-e9229987758f",
                "0d854682-f827-4fc5-84d7-6dfcfb3991a7",
                "4bd9bb18-80b6-49b4-895b-c07727ba5c33",
                "dec79915-d4a6-488b-9e4b-d829230e1557",
                "93c4bf46-966f-4de6-93dd-510338e58518",
                "24030ae6-cfc1-4987-b427-c19a0e05e4e0",
                "a1c02f72-da9b-45b1-b0a9-a399996d2e42",
                "dccdbe3f-61a6-4c7b-a951-9868339b82e4",
                "5c9160d1-8e0b-45ff-b2fb-67d6ff85bca0",
                "95958354-0dd4-45a3-847c-858c7e5704bc",
                "5bd0ec8a-8530-4182-9ca9-8ce974a5a8e7",
                "33605d4a-1fd5-490b-aa1d-a09724852301",
                "bf8e4a17-9232-46a3-afa0-f524a89728b8",
                "2e6530aa-b946-40da-9423-c75d8eef5a95",
                "c5a1e1bd-aaaa-4304-863f-bf689de5b215",
                "d541d0dd-7c1f-43dd-b593-ca21a77a541c",
                "260dcaa7-e0c6-4315-91b6-8bb7b2eda79a",
                "7678c27c-75d0-43a5-beab-276355148cff",
                "ec590ff0-c310-4bbb-843b-7c8bc942e689",
                "7219687a-961a-4eba-82c8-11a13189759a",
                "8d47e76e-4aa8-41d6-a88f-d53f594172fb",
                "cf441cd4-721a-49db-8850-5a24ef9c9faa",
            }
        ),
        1_317.5e6,
    ),
}
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


def download_cap(region_id: str, task_ids) -> float:
    """Byte cap for downloading `task_ids`: 1 GB (CLAUDE.md rule 11), unless every ID is in the
    user-approved exception for this region (APPROVED_OVER_CAP)."""
    approved, cap = APPROVED_OVER_CAP.get(region_id, (frozenset(), CAP_BYTES))
    return cap if set(task_ids) <= approved else CAP_BYTES


def projected_bytes(sizes: dict[str, int], n_tasks: int) -> float:
    """Total bundle size: exact listed sizes, plus their mean for each task not yet listed."""
    if not sizes:
        return 0.0
    return sum(sizes.values()) + sum(sizes.values()) / len(sizes) * (n_tasks - len(sizes))


def wait_and_download(region_id: str, poll_s: int = 120, once: bool = False) -> None:
    """Wait for all tasks and download them. Each pass lists every finished bundle first and
    stops before downloading anything if the projected total of all tasks exceeds the cap
    (`download_cap`). With `once`, make a single pass (download what is done, report the rest)
    and return, so no process outlives an unattended run."""
    reg = json.loads(registry_path(region_id).read_text(encoding="utf-8"))
    ids = {v["task_id"]: k for k, v in reg["tasks"].items()}
    cap = download_cap(region_id, ids)
    s = ae.login()
    try:
        sizes: dict[str, int] = {}
        pending = set(ids)
        while pending:
            counts: dict[str, int] = {}
            done: dict[str, list[dict]] = {}
            for tid in sorted(pending):
                t = ae.task(s, tid)
                counts[t.get("status", "?")] = counts.get(t.get("status", "?"), 0) + 1
                if t.get("status") == "error":
                    print("ERROR", ids[tid], tid, t.get("error"), flush=True)
                    pending.discard(tid)
                elif t.get("status") == "done":
                    done[tid] = ae.bundle(s, tid)
                    sizes[tid] = sum(f["file_size"] for f in done[tid])
            projected = projected_bytes(sizes, len(ids))
            print(
                f"bundles listed {len(sizes)}/{len(ids)}: {sum(sizes.values()) / 1e6:.1f} MB; "
                f"projected total {projected / 1e6:.1f} MB; cap {cap / 1e6:.1f} MB",
                flush=True,
            )
            if projected > cap:
                print(
                    f"STOP: projected {projected / 1e6:.1f} MB > cap {cap / 1e6:.1f} MB", flush=True
                )
                return
            for tid, files in done.items():
                ae.download(s, tid, files, OUT / region_id / ids[tid])
                print(
                    f"downloaded {ids[tid]}: {len(files)} files, {sizes[tid] / 1e6:.1f} MB",
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
