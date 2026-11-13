"""Open Sentinel-2 L2A Collection 1 COG time-series client over HTTP Range requests.

Used for Tier 3 regions (such as ua_central_t36uvu) where NASA AppEEARS requires Earthdata
login or regional GeoTIFF extraction. Reads Earth Search v1 STAC metadata and fetches only the
targeted 20 m (512x512) COG tiles of red (B04 IFD 1), nir (B08 IFD 1), and scl (SCL IFD 0) over
HTTPS with requests (verifying TLS via the system CA bundle).

Radiometric offset & scale are read per scene from STAC `raster:bands` (Collection 1 baseline
03.xx has offset 0.0; baseline 05.xx has offset -0.1) so reflectance = dn * scale + offset.
Clear-land QA rule (ESA Sentinel-2 L2A Scene Classification Layer, SCL):
  keep only SCL in {4 (Vegetation), 5 (Bare / Not-vegetated)} with non-nodata reflectance.
NDVI = (NIR - RED) / (NIR + RED) for (NIR + RED) > 0.01.
EVI column uses 2-band EVI2 = 2.5 * (NIR - RED) / (NIR + 2.4 * RED + 1.0)
(Jiang et al. 2008, Remote Sensing of Environment 112(10):3833-3845) to avoid downloading a
fourth band while preserving schema compatibility with `fieldwitness.data.hls_qa.read`.

Output table schema matches `hls_qa.read()`:
  field_id, date, ndvi, evi, n_clear, clear_fraction, source_tag ("O").
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from requests.adapters import HTTPAdapter

from fieldwitness.resolve.fields import SEED

STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
CLEAR_SCL_CLASSES = (4, 5)  # 4 = Vegetation, 5 = Not-vegetated / Bare soil
RES_20M = 20.0
TILE_PX = 512
MAX_POINTS = 12
S2_CACHE_DIR = Path("data/s2_cog")


@dataclass(frozen=True)
class CogIfd:
    width: int
    height: int
    tile_width: int
    tile_height: int
    bits_per_sample: int
    compression: int
    predictor: int
    tile_offsets: tuple[int, ...]
    tile_byte_counts: tuple[int, ...]


def _read_tag_array(
    hdr: bytes, endian: str, tag_entry: tuple[int, int, int], hdr_offset: int = 0
) -> tuple[int, ...]:
    typ, cnt, val_or_off = tag_entry
    type_info = {
        1: ("B", 1),
        3: ("H", 2),
        4: ("I", 4),
        16: ("Q", 8),
    }
    if typ not in type_info:
        raise ValueError(f"Unsupported TIFF tag type {typ}")
    fmt_char, elem_size = type_info[typ]
    total = cnt * elem_size
    if total <= 4:
        raw = struct.pack(endian + "I", val_or_off)[:total]
        return struct.unpack(endian + f"{cnt}{fmt_char}", raw)
    rel = val_or_off - hdr_offset
    if rel < 0 or rel + total > len(hdr):
        raise ValueError(f"TIFF tag array out of header buffer bounds: {rel}..{rel + total}")
    return struct.unpack_from(endian + f"{cnt}{fmt_char}", hdr, rel)


def parse_cog_ifds(hdr: bytes) -> tuple[str, list[CogIfd]]:
    """Parse all IFDs in a Classic TIFF COG header buffer (first 16-32 KB)."""
    if len(hdr) < 8:
        raise ValueError("Truncated TIFF header")
    if hdr[:2] == b"II":
        endian = "<"
    elif hdr[:2] == b"MM":
        endian = ">"
    else:
        raise ValueError(f"Invalid TIFF byte order: {hdr[:2]!r}")
    magic = struct.unpack_from(endian + "H", hdr, 2)[0]
    if magic != 42:
        raise ValueError(f"Expected Classic TIFF magic 42, got {magic}")
    ifd_off = struct.unpack_from(endian + "I", hdr, 4)[0]
    ifds: list[CogIfd] = []
    while ifd_off:
        if ifd_off + 2 > len(hdr):
            raise ValueError(f"IFD offset {ifd_off} exceeds header buffer {len(hdr)}")
        n_entries = struct.unpack_from(endian + "H", hdr, ifd_off)[0]
        tags: dict[int, tuple[int, int, int]] = {}
        pos = ifd_off + 2
        for _ in range(n_entries):
            tag, typ, cnt, val = struct.unpack_from(endian + "HHII", hdr, pos)
            tags[tag] = (typ, cnt, val)
            pos += 12
        next_ifd = struct.unpack_from(endian + "I", hdr, pos)[0]
        if 324 in tags and 325 in tags:
            ifds.append(
                CogIfd(
                    width=tags[256][2],
                    height=tags[257][2],
                    tile_width=tags[322][2],
                    tile_height=tags[323][2],
                    bits_per_sample=tags[258][2],
                    compression=tags.get(259, (3, 1, 1))[2],
                    predictor=tags.get(317, (3, 1, 1))[2],
                    tile_offsets=_read_tag_array(hdr, endian, tags[324]),
                    tile_byte_counts=_read_tag_array(hdr, endian, tags[325]),
                )
            )
        ifd_off = next_ifd
    return endian, ifds


def decode_tiff_tile(
    raw: bytes,
    tile_w: int,
    tile_h: int,
    bps: int,
    compression: int,
    predictor: int,
    endian: str,
) -> np.ndarray:
    """Decode one compressed/uncompressed TIFF tile into a 2D NumPy array."""
    dt = np.dtype(endian + ("u2" if bps == 16 else "u1"))
    if not raw:
        return np.zeros((tile_h, tile_w), dtype=dt)
    if compression in (8, 32946):
        payload = zlib.decompress(raw)
    elif compression == 1:
        payload = raw
    else:
        raise ValueError(f"Unsupported TIFF compression code {compression}")
    arr = np.frombuffer(payload, dtype=dt).reshape((tile_h, tile_w)).copy()
    if predictor == 2:
        arr = np.cumsum(arr, axis=1, dtype=dt)
    elif predictor not in (1, 0):
        raise ValueError(f"Unsupported TIFF predictor {predictor}")
    return arr


def fetch_cog_ifd(
    url: str,
    target_dim: int,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[str, CogIfd, int]:
    """Fetch COG header (first 32 KB) once and return `(endian, matching_ifd, header_bytes)`."""
    sess = session or requests.Session()
    r_hdr = sess.get(url, headers={"Range": "bytes=0-32767"}, timeout=timeout)
    r_hdr.raise_for_status()
    hdr = r_hdr.content
    endian, ifds = parse_cog_ifds(hdr)
    matching = [d for d in ifds if d.width == target_dim and d.height == target_dim]
    if not matching:
        raise ValueError(f"No {target_dim}x{target_dim} IFD in {url}")
    return endian, matching[0], len(hdr)


def fetch_cog_tile_from_ifd(
    url: str,
    ifd: CogIfd,
    endian: str,
    tx: int,
    ty: int,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[np.ndarray, int]:
    """Fetch and decode one `(tx, ty)` tile using a pre-parsed `CogIfd`."""
    tiles_x = (ifd.width + ifd.tile_width - 1) // ifd.tile_width
    idx = ty * tiles_x + tx
    if idx < 0 or idx >= len(ifd.tile_offsets):
        raise IndexError(f"Tile ({tx}, {ty}) index {idx} out of range {len(ifd.tile_offsets)}")
    off = ifd.tile_offsets[idx]
    bc = ifd.tile_byte_counts[idx]
    if bc == 0 or off == 0:
        dt = np.dtype(endian + ("u2" if ifd.bits_per_sample == 16 else "u1"))
        return np.zeros((ifd.tile_height, ifd.tile_width), dtype=dt), 0
    sess = session or requests.Session()
    r_tile = sess.get(url, headers={"Range": f"bytes={off}-{off + bc - 1}"}, timeout=timeout)
    r_tile.raise_for_status()
    raw = r_tile.content
    arr = decode_tiff_tile(
        raw,
        ifd.tile_width,
        ifd.tile_height,
        ifd.bits_per_sample,
        ifd.compression,
        ifd.predictor,
        endian,
    )
    return arr, len(raw)


def fetch_cog_tile(
    url: str,
    target_dim: int,
    tx: int,
    ty: int,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[np.ndarray, int]:
    """Fetch and decode one (tx, ty) tile at `target_dim` resolution from a COG URL.

    Returns `(tile_array, bytes_transferred)`.
    """
    endian, ifd, b_hdr = fetch_cog_ifd(url, target_dim, session=session, timeout=timeout)
    arr, b_tile = fetch_cog_tile_from_ifd(
        url, ifd, endian, tx, ty, session=session, timeout=timeout
    )
    return arr, b_hdr + b_tile


def search_scenes(
    mgrs_code: str = "MGRS-36UVU",
    start_date: str = "2017-01-01",
    end_date: str = "2024-12-31",
    max_cloud: float = 35.0,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Query Earth Search v1 STAC for Sentinel-2 L2A scenes over an MGRS tile."""
    sess = session or requests.Session()
    payload: dict[str, Any] = {
        "collections": ["sentinel-2-l2a"],
        "query": {
            "grid:code": {"eq": mgrs_code},
            "eo:cloud_cover": {"lt": max_cloud},
        },
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 200,
    }
    features: list[dict[str, Any]] = []
    while True:
        r = sess.post(STAC_SEARCH_URL, json=payload, timeout=45)
        r.raise_for_status()
        body = r.json()
        features.extend(body.get("features", []))
        nxt = next((lk for lk in body.get("links", []) if lk.get("rel") == "next"), None)
        if nxt is None:
            break
        if isinstance(nxt.get("body"), dict):
            payload = nxt["body"]
        else:
            break
    return features


def select_balanced_scenes(
    features: list[dict[str, Any]],
    max_per_month: int = 2,
    max_total: int = 128,
) -> list[dict[str, Any]]:
    """Pick the clearest unique-date scenes balanced evenly across (year, month)."""
    by_date: dict[str, dict[str, Any]] = {}
    for ft in features:
        props = ft["properties"]
        assets = ft.get("assets", {})
        if not all(k in assets for k in ("red", "nir", "scl")):
            continue
        date_str = props["datetime"][:10]
        cloud = float(props.get("eo:cloud_cover", 100.0))
        prev = by_date.get(date_str)
        if prev is None or cloud < float(prev["properties"].get("eo:cloud_cover", 100.0)):
            by_date[date_str] = ft

    by_ym: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for date_str, ft in sorted(by_date.items()):
        yr, mo = int(date_str[:4]), int(date_str[5:7])
        by_ym.setdefault((yr, mo), []).append(ft)

    chosen: list[dict[str, Any]] = []
    # Growing season priority inside each year, then round-robin across months
    for _ym, items in sorted(by_ym.items()):
        ranked = sorted(items, key=lambda x: float(x["properties"].get("eo:cloud_cover", 100.0)))
        chosen.extend(ranked[:max_per_month])

    if len(chosen) > max_total:
        # Prioritize Mar-Nov (months 3..11) first, then lowest cloud across remaining
        chosen.sort(
            key=lambda x: (
                0 if 3 <= int(x["properties"]["datetime"][5:7]) <= 11 else 1,
                float(x["properties"].get("eo:cloud_cover", 100.0)),
            )
        )
        chosen = chosen[:max_total]
    return sorted(chosen, key=lambda x: x["properties"]["datetime"][:10])


def sample_interior_pixels_20m(
    pilot: gpd.GeoDataFrame,
    grid: dict[str, Any],
    max_per_field: int = MAX_POINTS,
    buffer_m: float = 15.0,
    seed: int = SEED,
) -> pd.DataFrame:
    """Sample up to `max_per_field` 20 m pixel centres inside each field's inward buffer.

    Returns DataFrame with columns:
      field_id, col, row, tx, ty, lc, lr, n_sampled
    where (col, row) index the 5490x5490 20 m grid and (tx, ty, lc, lr) index 512x512 COG tiles.
    """
    rng = np.random.default_rng(seed)
    utm = pilot.to_crs(grid["epsg"])
    ulx, uly = float(grid["ulx"]), float(grid["uly"])
    max_px = int(round(float(grid["size_m"]) / RES_20M))
    rows: list[dict[str, Any]] = []
    for fid, geom in zip(utm["field_id"], utm.geometry, strict=True):
        inner = geom.buffer(-buffer_m)
        if inner.is_empty:
            continue
        minx, miny, maxx, maxy = inner.bounds
        i0 = max(0, math.ceil((minx - ulx) / RES_20M - 0.5))
        i1 = min(max_px - 1, math.floor((maxx - ulx) / RES_20M - 0.5))
        j0 = max(0, math.ceil((uly - maxy) / RES_20M - 0.5))
        j1 = min(max_px - 1, math.floor((uly - miny) / RES_20M - 0.5))
        if i1 < i0 or j1 < j0:
            continue
        cols, rws = (a.ravel() for a in np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1)))
        xs, ys = ulx + RES_20M * (cols + 0.5), uly - RES_20M * (rws + 0.5)
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
                    "field_id": fid,
                    "col": c,
                    "row": r,
                    "tx": c // TILE_PX,
                    "ty": r // TILE_PX,
                    "lc": c % TILE_PX,
                    "lr": r % TILE_PX,
                    "n_sampled": n_samp,
                }
            )
    return pd.DataFrame(rows)


def _scale_offset(
    asset: dict[str, Any], boa_offset_applied: bool = False
) -> tuple[float, float, int]:
    rb = (asset.get("raster:bands") or [{}])[0]
    scale = float(rb.get("scale", 0.0001))
    offset = 0.0 if boa_offset_applied else float(rb.get("offset", 0.0))
    nodata = int(rb.get("nodata", 0))
    return scale, offset, nodata


def extract_scene_table(
    scene: dict[str, Any],
    px_df: pd.DataFrame,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, int]:
    """Extract clear-land NDVI & EVI2 per field for one STAC scene. Returns `(df, bytes)`."""
    assets = scene["assets"]
    props = scene["properties"]
    date_str = props["datetime"][:10]
    boa_applied = bool(props.get("earthsearch:boa_offset_applied", False))
    r_scale, r_off, r_nd = _scale_offset(assets["red"], boa_offset_applied=boa_applied)
    n_scale, n_off, n_nd = _scale_offset(assets["nir"], boa_offset_applied=boa_applied)
    _, _, s_nd = _scale_offset(assets["scl"], boa_offset_applied=False)
    target_dim = round(109800.0 / RES_20M)  # 5490
    tiles_needed = sorted(set(zip(px_df["tx"], px_df["ty"], strict=True)))

    sess = session or requests.Session()
    bytes_used = 0
    tile_arrays: dict[tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    if session is None and len(tiles_needed) == 1:
        # Backwards-compatible path for monkeypatched `fetch_cog_tile` in tests
        for tx, ty in tiles_needed:
            red_arr, b_r = fetch_cog_tile(assets["red"]["href"], target_dim, tx, ty, session=sess)
            nir_arr, b_n = fetch_cog_tile(assets["nir"]["href"], target_dim, tx, ty, session=sess)
            scl_arr, b_s = fetch_cog_tile(assets["scl"]["href"], target_dim, tx, ty, session=sess)
            tile_arrays[(tx, ty)] = (red_arr, nir_arr, scl_arr)
            bytes_used += b_r + b_n + b_s
    else:
        band_ifds: dict[str, tuple[str, CogIfd]] = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            hdr_futs = {
                b: pool.submit(fetch_cog_ifd, assets[b]["href"], target_dim, sess)
                for b in ("red", "nir", "scl")
            }
            for b, fut in hdr_futs.items():
                endian, ifd, b_hdr = fut.result()
                band_ifds[b] = (endian, ifd)
                bytes_used += b_hdr

            tile_futs: dict[tuple[str, int, int], Any] = {}
            for tx, ty in tiles_needed:
                for b in ("red", "nir", "scl"):
                    endian, ifd = band_ifds[b]
                    tile_futs[(b, tx, ty)] = pool.submit(
                        fetch_cog_tile_from_ifd,
                        assets[b]["href"],
                        ifd,
                        endian,
                        tx,
                        ty,
                        sess,
                    )
            for tx, ty in tiles_needed:
                red_arr, b_r = tile_futs[("red", tx, ty)].result()
                nir_arr, b_n = tile_futs[("nir", tx, ty)].result()
                scl_arr, b_s = tile_futs[("scl", tx, ty)].result()
                tile_arrays[(tx, ty)] = (red_arr, nir_arr, scl_arr)
                bytes_used += b_r + b_n + b_s

    px_recs = []
    for (tx, ty), g in px_df.groupby(["tx", "ty"], sort=False):
        red_t, nir_t, scl_t = tile_arrays[(int(tx), int(ty))]
        lr = g["lr"].to_numpy()
        lc = g["lc"].to_numpy()
        r_dn = red_t[lr, lc]
        n_dn = nir_t[lr, lc]
        s_v = scl_t[lr, lc]
        ok = np.isin(s_v, CLEAR_SCL_CLASSES) & (r_dn != r_nd) & (n_dn != n_nd) & (s_v != s_nd)
        if not ok.any():
            continue
        r_fl = np.clip(r_dn[ok].astype(float) * r_scale + r_off, 0.0, 1.0)
        n_fl = np.clip(n_dn[ok].astype(float) * n_scale + n_off, 0.0, 1.0)
        denom = n_fl + r_fl
        valid_d = denom > 0.01
        if not valid_d.any():
            continue
        fids = g["field_id"].to_numpy()[ok][valid_d]
        nsamp = g["n_sampled"].to_numpy()[ok][valid_d]
        r_v, n_v, d_v = r_fl[valid_d], n_fl[valid_d], denom[valid_d]
        ndvi = np.clip((n_v - r_v) / d_v, -1.0, 1.0)
        evi2 = np.clip(2.5 * (n_v - r_v) / (n_v + 2.4 * r_v + 1.0), -1.0, 1.0)
        px_recs.append(
            pd.DataFrame(
                {
                    "field_id": fids,
                    "n_sampled": nsamp,
                    "ndvi": ndvi,
                    "evi": evi2,
                }
            )
        )
    if not px_recs:
        empty = pd.DataFrame(
            columns=["field_id", "date", "ndvi", "evi", "n_clear", "clear_fraction", "source_tag"]
        )
        return empty, bytes_used

    all_px = pd.concat(px_recs, ignore_index=True)
    out = (
        all_px.groupby("field_id", as_index=False)
        .agg(
            ndvi=("ndvi", "median"),
            evi=("evi", "median"),
            n_clear=("ndvi", "size"),
            n_sampled=("n_sampled", "first"),
        )
        .assign(
            date=pd.Timestamp(date_str),
            clear_fraction=lambda d: d["n_clear"] / d["n_sampled"],
            source_tag="O",
        )
    )[["field_id", "date", "ndvi", "evi", "n_clear", "clear_fraction", "source_tag"]]
    return out, bytes_used


def build_s2_series(
    region_id: str,
    pilot: gpd.GeoDataFrame,
    grid: dict[str, Any],
    mgrs_code: str = "MGRS-36UVU",
    start_date: str = "2017-01-01",
    end_date: str = "2024-12-31",
    max_per_month: int = 2,
    max_total_scenes: int = 128,
    max_bytes: int = 550_000_000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build or resume the Sentinel-2 L2A 20 m NDVI/EVI2 series for `pilot` fields.

    Caches per-scene extractions under `data/s2_cog/<region_id>/` and stops cleanly before
    crossing `max_bytes` (default 550 MB so total project downloads remain < 1 GB).
    Writes `data/fields/<region_id>_hls_series.parquet` for `hls_qa.read(region_id)`.
    """
    cache_dir = S2_CACHE_DIR / region_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path("data/fields") / f"{region_id}_hls_series.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    px_df = sample_interior_pixels_20m(pilot, grid)
    tiles = sorted(set(zip(px_df["tx"], px_df["ty"], strict=True)))
    manifest_file = cache_dir / "scenes.json"
    with requests.Session() as sess:
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16)
        sess.mount("https://", adapter)
        if manifest_file.exists():
            scenes = json.loads(manifest_file.read_text(encoding="utf-8"))
        else:
            raw = search_scenes(
                mgrs_code=mgrs_code, start_date=start_date, end_date=end_date, session=sess
            )
            scenes = select_balanced_scenes(
                raw, max_per_month=max_per_month, max_total=max_total_scenes
            )
            manifest_file.write_text(json.dumps(scenes), encoding="utf-8")

        frames: list[pd.DataFrame] = []
        total_bytes = 0
        downloaded_scenes = 0
        for idx, sc in enumerate(scenes, 1):
            sid = sc["id"]
            sc_file = cache_dir / f"{sid}.parquet"
            if sc_file.exists():
                df_sc = pd.read_parquet(sc_file)
                frames.append(df_sc)
                continue
            # Check byte cap before next download (~0.8 MB * n_tiles per scene)
            if total_bytes + len(tiles) * 900_000 > max_bytes:
                print(
                    f"Reached byte cap {total_bytes / 1e6:.1f} MB at scene "
                    f"{idx}/{len(scenes)}; stopping.",
                    flush=True,
                )
                break
            df_sc, b = extract_scene_table(sc, px_df, session=sess)
            df_sc.to_parquet(sc_file, index=False)
            frames.append(df_sc)
            total_bytes += b
            downloaded_scenes += 1
            if downloaded_scenes % 15 == 0 or idx == len(scenes):
                print(
                    f"  S2 scene {idx}/{len(scenes)} ({sc['properties']['datetime'][:10]}): "
                    f"+{downloaded_scenes} downloaded, {total_bytes / 1e6:.1f} MB",
                    flush=True,
                )

    combined = (
        pd.concat([f for f in frames if not f.empty], ignore_index=True)
        if any(not f.empty for f in frames)
        else pd.DataFrame(
            columns=["field_id", "date", "ndvi", "evi", "n_clear", "clear_fraction", "source_tag"]
        )
    )
    if not combined.empty:
        combined["date"] = pd.to_datetime(combined["date"])
        combined = combined.sort_values(["field_id", "date"]).reset_index(drop=True)
    combined.to_parquet(out_path, index=False)
    meta = {
        "region_id": region_id,
        "mgrs_code": mgrs_code,
        "cog_tiles_20m": [list(t) for t in tiles],
        "fields_sampled": int(px_df["field_id"].nunique()),
        "pixels_sampled": int(len(px_df)),
        "scenes_targeted": len(scenes),
        "downloaded_bytes_this_run": total_bytes,
        "rows_written": int(len(combined)),
        "fields_with_obs": int(combined["field_id"].nunique()) if not combined.empty else 0,
        "date_min": str(combined["date"].min().date()) if not combined.empty else None,
        "date_max": str(combined["date"].max().date()) if not combined.empty else None,
    }
    (cache_dir / "summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return combined, meta
