"""USGS/NASA Landsat 8/9 Collection 2 Level-2 Surface Temperature (ST_B10 / lwir11) client.

Public STAC + COG HTTP Range reader using Microsoft Planetary Computer anonymous SAS tokens
(zero Earthdata credentials required; verified in docs/api_notes.md).
Resolves the Earthdata auth gap when ECOSTRESS ECO_L3T_JET v003 is unavailable locally while
providing direct 30 m / 100 m TIRS field-scale thermal stress observations (CLAUDE.md Rule 5).

Radiometric conversion (USGS Landsat 8-9 Collection 2 Level-2 Science Product Guide):
  LST (Kelvin) = DN * 0.00341802 + 149.0
  LST (degC)   = LST (Kelvin) - 273.15

Clear-land QA rule (Landsat C2 QA_PIXEL uint16 bitmask):
  Drop fill (bit 0), dilated cloud (bit 1), cirrus (bit 2), cloud (bit 3), cloud shadow (bit 4),
  snow/ice (bit 5), and water (bit 7): keep only `(qa & 0b10111111) == 0` with `dn > 0`.

Provenance tag: 'O' (direct radiometric satellite thermal observation over interior pixels).
"""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from requests.adapters import HTTPAdapter

from fieldwitness.data.asof import cutoff, guard, register
from fieldwitness.data.s2_cog import (
    fetch_cog_ifd,
    fetch_cog_tile_from_ifd,
)
from fieldwitness.resolve.fields import SEED

PC_STAC_SEARCH_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_SAS_TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
CACHE_DIR = Path("data/context/landsat_lst")
LST_SCALE = 0.00341802
LST_OFFSET_K = 149.0
KELVIN_TO_C = -273.15
# Bits: 0=Fill, 1=Dilated Cloud, 2=Cirrus, 3=Cloud, 4=Cloud Shadow, 5=Snow, 7=Water
QA_CLEAR_REJECT_MASK = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 7)
RES_30M = 30.0
MAX_POINTS = 12


def fetch_sas_token(session: requests.Session | None = None, timeout: int = 20) -> str:
    """Fetch anonymous short-lived SAS token for Planetary Computer landsat-c2-l2."""
    sess = session or requests.Session()
    r = sess.get(PC_SAS_TOKEN_URL, timeout=timeout)
    r.raise_for_status()
    return str(r.json()["token"])


def search_landsat_thermal_scenes(
    bbox: tuple[float, float, float, float],
    start_date: str = "2017-04-01",
    end_date: str = "2024-10-31",
    max_cloud: float = 25.0,
    limit: int = 250,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Search Planetary Computer STAC for clear Landsat 8/9 C2 L2 scenes across all years."""
    sess = session or requests.Session()
    y0 = int(start_date[:4])
    y1 = int(end_date[:4])
    if y1 <= y0:
        payload: dict[str, Any] = {
            "collections": ["landsat-c2-l2"],
            "bbox": [float(x) for x in bbox],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "query": {
                "eo:cloud_cover": {"lt": max_cloud},
                "platform": {"in": ["landsat-8", "landsat-9"]},
            },
            "limit": limit,
        }
        r = sess.post(PC_STAC_SEARCH_URL, json=payload, timeout=30)
        r.raise_for_status()
        return list(r.json().get("features", []))

    seen_ids: set[str] = set()
    features: list[dict[str, Any]] = []
    per_yr_lim = max(20, min(60, limit // max(1, y1 - y0 + 1)))
    for yr in range(y0, y1 + 1):
        s_d = start_date if yr == y0 else f"{yr}-01-01"
        e_d = end_date if yr == y1 else f"{yr}-12-31"
        payload = {
            "collections": ["landsat-c2-l2"],
            "bbox": [float(x) for x in bbox],
            "datetime": f"{s_d}T00:00:00Z/{e_d}T23:59:59Z",
            "query": {
                "eo:cloud_cover": {"lt": max_cloud},
                "platform": {"in": ["landsat-8", "landsat-9"]},
            },
            "limit": per_yr_lim,
        }
        r = sess.post(PC_STAC_SEARCH_URL, json=payload, timeout=30)
        r.raise_for_status()
        for ft in r.json().get("features", []):
            fid = str(ft.get("id", ""))
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                features.append(ft)
    return features


def select_thermal_scenes(
    features: list[dict[str, Any]],
    months: tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10),
    max_per_year_month: int = 2,
    max_total: int = 48,
) -> list[dict[str, Any]]:
    """Select lowest-cloud Landsat 8/9 scenes balanced across growing months, years & WRS tiles."""
    by_ym_pr: dict[tuple[int, int, str], dict[str, Any]] = {}
    for ft in features:
        assets = ft.get("assets", {})
        if "lwir11" not in assets or "qa_pixel" not in assets:
            continue
        props = ft["properties"]
        if not props.get("proj:epsg") or not props.get("proj:transform"):
            continue
        d_str = props["datetime"][:10]
        yr, mo = int(d_str[:4]), int(d_str[5:7])
        if mo not in months:
            continue
        pr = f"{props.get('landsat:wrs_path', '')}_{props.get('landsat:wrs_row', '')}"
        cloud = float(props.get("eo:cloud_cover", 100.0))
        prev = by_ym_pr.get((yr, mo, pr))
        if prev is None or cloud < float(prev["properties"].get("eo:cloud_cover", 100.0)):
            by_ym_pr[(yr, mo, pr)] = ft

    # Round-robin across (year, month) in summer-first priority so byte-capped downloads still
    # span multiple years per month rather than cluster in a single year.
    priority_months = tuple(sorted(months, key=lambda m: (abs(m - 7), m)))
    by_ym: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for (yr, mo, _pr), ft in sorted(by_ym_pr.items()):
        by_ym.setdefault((yr, mo), []).append(ft)
    years = sorted({y for y, _ in by_ym})
    for ym in by_ym:
        by_ym[ym] = sorted(
            by_ym[ym], key=lambda f: float(f["properties"].get("eo:cloud_cover", 100.0))
        )[:max_per_year_month]

    balanced: list[dict[str, Any]] = []
    for k in range(max_per_year_month):
        for mo in priority_months:
            for yr in years:
                items = by_ym.get((yr, mo), [])
                if k < len(items):
                    balanced.append(items[k])
                    if len(balanced) >= max_total:
                        return balanced
    return balanced


def dn_to_lst_c(
    dn: np.ndarray,
    qa: np.ndarray,
    scale: float = LST_SCALE,
    offset_k: float = LST_OFFSET_K,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert Landsat C2 lwir11 DN + QA_PIXEL arrays to masked Celsius values and valid mask."""
    dn_u = np.asarray(dn)
    qa_u = np.asarray(qa)
    valid = (dn_u > 0) & ((qa_u & QA_CLEAR_REJECT_MASK) == 0)
    lst_k = dn_u.astype(float) * scale + offset_k
    lst_c = np.where(valid, lst_k + KELVIN_TO_C, np.nan)
    return lst_c, valid


def _sample_scene_pixels(
    fields_gdf: gpd.GeoDataFrame,
    epsg: int,
    transform: list[float],
    width: int,
    height: int,
    tile_w: int = 256,
    tile_h: int = 256,
    max_per_field: int = MAX_POINTS,
    buffer_m: float = 15.0,
    seed: int = SEED,
) -> pd.DataFrame:
    """Sample interior 30 m pixel coordinates in this Landsat scene's projection."""
    rng = np.random.default_rng(seed)
    utm = fields_gdf.to_crs(f"EPSG:{epsg}")
    px_w = abs(float(transform[0]))
    ulx = float(transform[2])
    px_h = abs(float(transform[4]))
    uly = float(transform[5])

    rows: list[dict[str, Any]] = []
    for fid, geom in zip(utm["field_id"], utm.geometry, strict=True):
        inner = geom.buffer(-buffer_m)
        if inner.is_empty:
            continue
        minx, miny, maxx, maxy = inner.bounds
        i0 = max(0, math.ceil((minx - ulx) / px_w - 0.5))
        i1 = min(width - 1, math.floor((maxx - ulx) / px_w - 0.5))
        j0 = max(0, math.ceil((uly - maxy) / px_h - 0.5))
        j1 = min(height - 1, math.floor((uly - miny) / px_h - 0.5))
        if i1 < i0 or j1 < j0:
            continue
        cols, rws = (a.ravel() for a in np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1)))
        xs = ulx + px_w * (cols + 0.5)
        ys = uly - px_h * (rws + 0.5)
        idx = np.flatnonzero(shapely.contains_xy(inner, xs, ys))
        if len(idx) == 0:
            continue
        if len(idx) > max_per_field:
            idx = np.sort(rng.choice(idx, max_per_field, replace=False))
        n_samp = int(len(idx))
        for k in idx:
            c, r = int(cols[k]), int(rws[k])
            rows.append(
                {
                    "field_id": str(fid),
                    "col": c,
                    "row": r,
                    "tx": c // tile_w,
                    "ty": r // tile_h,
                    "lc": c % tile_w,
                    "lr": r % tile_h,
                    "n_sampled": n_samp,
                }
            )
    return pd.DataFrame(rows)


def extract_landsat_scene_lst(
    scene: dict[str, Any],
    fields_gdf: gpd.GeoDataFrame,
    sas_token: str,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, int]:
    """Extract interior-pixel median clear-sky LST (degC) per field for one Landsat C2 L2 scene."""
    props = scene["properties"]
    assets = scene["assets"]
    date_str = props["datetime"][:10]
    epsg = int(props["proj:epsg"])
    transform = list(props["proj:transform"])
    height, width = [int(v) for v in props["proj:shape"]]

    lwir_asset = assets["lwir11"]
    rb = (lwir_asset.get("raster:bands") or [{}])[0]
    scale = float(rb.get("scale", LST_SCALE))
    offset_k = float(rb.get("offset", LST_OFFSET_K))

    lwir_url = f"{lwir_asset['href']}?{sas_token}"
    qa_url = f"{assets['qa_pixel']['href']}?{sas_token}"
    sess = session or requests.Session()

    # Quick intersection filter in WGS84
    sb = scene.get("bbox")
    if sb:
        scene_box = shapely.box(float(sb[0]), float(sb[1]), float(sb[2]), float(sb[3]))
        sub_fields = fields_gdf[fields_gdf.geometry.intersects(scene_box)].copy()
    else:
        sub_fields = fields_gdf

    if sub_fields.empty:
        return pd.DataFrame(
            columns=["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]
        ), 0

    bytes_used = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_lwir = pool.submit(fetch_cog_ifd, lwir_url, width, sess, 30, height)
        f_qa = pool.submit(fetch_cog_ifd, qa_url, width, sess, 30, height)
        endian_l, ifd_l, b_hl = f_lwir.result()
        endian_q, ifd_q, b_hq = f_qa.result()
    bytes_used += b_hl + b_hq

    px_df = _sample_scene_pixels(
        sub_fields,
        epsg=epsg,
        transform=transform,
        width=ifd_l.width,
        height=ifd_l.height,
        tile_w=ifd_l.tile_width,
        tile_h=ifd_l.tile_height,
    )
    if px_df.empty:
        return pd.DataFrame(
            columns=["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]
        ), bytes_used

    tiles_needed = sorted(set(zip(px_df["tx"], px_df["ty"], strict=True)))
    tile_arrays: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs: dict[tuple[str, int, int], Any] = {}
        for tx, ty in tiles_needed:
            futs[("l", tx, ty)] = pool.submit(
                fetch_cog_tile_from_ifd, lwir_url, ifd_l, endian_l, tx, ty, sess
            )
            futs[("q", tx, ty)] = pool.submit(
                fetch_cog_tile_from_ifd, qa_url, ifd_q, endian_q, tx, ty, sess
            )
        for tx, ty in tiles_needed:
            arr_l, bl = futs[("l", tx, ty)].result()
            arr_q, bq = futs[("q", tx, ty)].result()
            tile_arrays[(tx, ty)] = (arr_l, arr_q)
            bytes_used += bl + bq

    px_recs = []
    for (tx, ty), g in px_df.groupby(["tx", "ty"], sort=False):
        arr_l, arr_q = tile_arrays[(int(tx), int(ty))]
        lr = g["lr"].to_numpy()
        lc = g["lc"].to_numpy()
        lst_c_t, valid_t = dn_to_lst_c(arr_l[lr, lc], arr_q[lr, lc], scale=scale, offset_k=offset_k)
        if not valid_t.any():
            continue
        fids = g["field_id"].to_numpy()[valid_t]
        nsamp = g["n_sampled"].to_numpy()[valid_t]
        vals = lst_c_t[valid_t]
        # Plausible land surface temperature sanity bounds [-40, 80] degC
        sane = (vals >= -40.0) & (vals <= 80.0)
        if not sane.any():
            continue
        px_recs.append(
            pd.DataFrame({"field_id": fids[sane], "n_sampled": nsamp[sane], "lst_c": vals[sane]})
        )

    if not px_recs:
        return pd.DataFrame(
            columns=["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]
        ), bytes_used

    all_px = pd.concat(px_recs, ignore_index=True)
    out = (
        all_px.groupby("field_id", as_index=False)
        .agg(
            lst_c=("lst_c", "median"),
            n_clear=("lst_c", "size"),
            n_sampled=("n_sampled", "first"),
        )
        .assign(
            date=pd.Timestamp(date_str).date(),
            clear_fraction=lambda d: d["n_clear"] / d["n_sampled"],
            tag="O",
            source="USGS/NASA Landsat 8-9 C2 L2 ST_B10 (100 m TIRS / 30 m COG)",
        )
    )[["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]]
    return out, bytes_used


def build_landsat_lst_region(
    region_id: str,
    fields_gdf: gpd.GeoDataFrame,
    start_date: str = "2017-04-01",
    end_date: str = "2024-10-31",
    max_total_scenes: int = 36,
    max_bytes: int = 80_000_000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build and cache field-level Landsat 8/9 C2 L2 daytime LST series for a region."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / f"{region_id}_lst.parquet"
    meta_path = CACHE_DIR / f"{region_id}_lst_meta.json"

    bbox_arr = fields_gdf.total_bounds
    bbox = (float(bbox_arr[0]), float(bbox_arr[1]), float(bbox_arr[2]), float(bbox_arr[3]))
    with requests.Session() as sess:
        adapter = HTTPAdapter(pool_connections=12, pool_maxsize=12)
        sess.mount("https://", adapter)
        raw_scenes = search_landsat_thermal_scenes(
            bbox, start_date=start_date, end_date=end_date, session=sess
        )
        scenes = select_thermal_scenes(raw_scenes, max_total=max_total_scenes)
        token = fetch_sas_token(session=sess)

        frames: list[pd.DataFrame] = []
        total_bytes = 0
        for sc in scenes:
            if total_bytes > max_bytes:
                break
            df_sc, b = extract_landsat_scene_lst(sc, fields_gdf, token, session=sess)
            total_bytes += b
            if not df_sc.empty:
                frames.append(df_sc)

    combined = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(
            columns=["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]
        )
    )
    if not combined.empty:
        combined["date"] = pd.to_datetime(combined["date"]).dt.date
        combined = (
            combined.groupby(["field_id", "date"], as_index=False)
            .agg(
                lst_c=("lst_c", "median"),
                n_clear=("n_clear", "max"),
                clear_fraction=("clear_fraction", "max"),
                tag=("tag", "first"),
                source=("source", "first"),
            )
            .sort_values(["field_id", "date"])
            .reset_index(drop=True)
        )
    combined.to_parquet(out_path, index=False)
    meta = {
        "region_id": region_id,
        "scenes_targeted": len(scenes),
        "downloaded_bytes": int(total_bytes),
        "rows": int(len(combined)),
        "fields_with_obs": int(combined["field_id"].nunique()) if not combined.empty else 0,
        "date_min": str(combined["date"].min()) if not combined.empty else None,
        "date_max": str(combined["date"].max()) if not combined.empty else None,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return combined, meta


@register("landsat_lst", weather=False)
def read_landsat_lst(
    region_id: str = "ks_t14slh",
    field_id: str | None = None,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read cached Landsat 8/9 C2 L2 field-level LST observations respecting active as_of."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_lst.parquet"
        if not p.exists():
            return pd.DataFrame(
                columns=["field_id", "date", "lst_c", "n_clear", "clear_fraction", "tag", "source"]
            )
        df = pd.read_parquet(p)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]
    if field_id is not None:
        df = df[df["field_id"] == field_id]

    guard(df["date"], "landsat_lst", weather=False)
    return df.reset_index(drop=True)
