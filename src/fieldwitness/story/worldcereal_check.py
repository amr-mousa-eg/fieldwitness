"""T2.4 WorldCereal / OGH-GHLC10 independent cross-check for Tier 3 Ukraine classifier.

Evaluates the causal Sentinel-2 L2A + TWDTW classifier (`story.ukraine_seasons`) against
OpenGeoHub Global Harmonized Land Cover (`ogh-ghlc10`, Doi: 10.5194/egusphere-2026-5540,
CC BY 4.0) 30 m annual COGs (2020-2024), where class 3 (`2.2 Annual crops - maize`) is
directly assigned from ESA WorldCereal 10 m main-season maize (`README.md`), class 2 is
soybean, and class 5 is other annual crops (winter wheat, sunflower, barley, etc.).

Downloads only the exact 2048x2048 BigTIFF ZSTD tiles intersecting the region bounding box
via HTTP Range requests (~0.7 MB per year; zero login required) and samples interior pixels
using the 15 m inward field buffer (CLAUDE.md Rule 5). Spatial-block bootstrap (10 km blocks)
quantifies precision, recall, F1, Cohen's kappa, and accuracy with 95% confidence intervals.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from rasterio.io import MemoryFile

BASE_URL = (
    "https://data.source.coop/opengeohub/ogh-ghlc10/"
    "land.cover_ifad.mcdt_c_30m_s_{year}0101_{year}1231_go_epsg.4326_v1.2.tif"
)
MAIZE_CLASS = 3
SOYBEAN_CLASS = 2
OTHER_CROP_CLASS = 5
ANNUAL_CROP_CLASSES = (2, 3, 4, 5)
CACHE_DIR = Path("data/worldcereal_ogh")
SEED = 20261114
N_BOOT = 1000


def _parse_bigtiff_grid(sess: requests.Session, url: str) -> dict[str, Any]:
    hdr = sess.get(url, headers={"Range": "bytes=0-16383"}, timeout=30)
    hdr.raise_for_status()
    b = hdr.content
    magic, ver, _, _ = struct.unpack_from("<HHHH", b, 0)
    if magic != 18761 or ver != 43:
        raise ValueError(f"Expected little-endian BigTIFF, got magic={magic} ver={ver}")
    ifd0 = struct.unpack_from("<Q", b, 8)[0]
    n_tags = struct.unpack_from("<Q", b, ifd0)[0]
    tags: dict[int, tuple[int, int, int]] = {}
    pos = ifd0 + 8
    for _ in range(n_tags):
        tag, typ, cnt, val = struct.unpack_from("<HHQQ", b, pos)
        tags[tag] = (typ, cnt, val)
        pos += 20
    scale = struct.unpack_from("<3d", b, tags[33550][2])
    tie = struct.unpack_from("<6d", b, tags[33922][2])
    return {
        "width": int(tags[256][2]),
        "height": int(tags[257][2]),
        "tile_w": int(tags[322][2]),
        "tile_h": int(tags[323][2]),
        "off_table": int(tags[324][2]),
        "bc_table": int(tags[325][2]),
        "dlon": float(scale[0]),
        "dlat": float(scale[1]),
        "lon0": float(tie[3]),
        "lat0": float(tie[4]),
    }


def _decode_zstd_tile_u8(tile_bytes: bytes, w: int, h: int) -> np.ndarray:
    """Wrap one BigTIFF 2048x2048 ZSTD+Predictor-2 byte tile in a minimal Classic TIFF."""
    hdr_size = 8 + 2 + 10 * 12 + 4
    entries = [
        (256, 4, 1, w),
        (257, 4, 1, h),
        (258, 3, 1, 8),
        (259, 3, 1, 50000),
        (273, 4, 1, hdr_size),
        (277, 3, 1, 1),
        (278, 4, 1, h),
        (279, 4, 1, len(tile_bytes)),
        (317, 3, 1, 2),
        (339, 3, 1, 1),
    ]
    buf = bytearray(b"II*\x00" + struct.pack("<IH", 8, len(entries)))
    for t, tp, c, v in entries:
        buf += struct.pack("<HHII", t, tp, c, v)
    buf += struct.pack("<I", 0) + tile_bytes
    with MemoryFile(bytes(buf)) as mem, mem.open() as ds:
        return ds.read(1)


def fetch_ghlc_bbox(
    year: int,
    bbox_4326: tuple[float, float, float, float],
    cache_dir: Path = CACHE_DIR,
    session: requests.Session | None = None,
) -> tuple[np.ndarray, dict[str, Any], int]:
    """Fetch and assemble the OGH-GHLC10 class array covering `bbox_4326 = (w, s, e, n)`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    npz_path = cache_dir / f"ogh_ghlc30_{year}.npz"
    meta_path = cache_dir / f"ogh_ghlc30_{year}.json"
    if npz_path.exists() and meta_path.exists():
        arr = np.load(npz_path)["data"]
        meta = json.loads(meta_path.read_text("utf-8"))
        return arr, meta, 0

    w, s, e, n = bbox_4326
    url = BASE_URL.format(year=year)
    sess = session or requests.Session()
    info = _parse_bigtiff_grid(sess, url)
    tw, th = info["tile_w"], info["tile_h"]
    tiles_x = (info["width"] + tw - 1) // tw

    c0 = max(0, int((w - info["lon0"]) / info["dlon"]))
    c1 = min(info["width"] - 1, int((e - info["lon0"]) / info["dlon"]))
    r0 = max(0, int((info["lat0"] - n) / info["dlat"]))
    r1 = min(info["height"] - 1, int((info["lat0"] - s) / info["dlat"]))

    tx0, tx1 = c0 // tw, c1 // tw
    ty0, ty1 = r0 // th, r1 // th
    canvas = np.zeros(((ty1 - ty0 + 1) * th, (tx1 - tx0 + 1) * tw), dtype=np.uint8)
    bytes_transferred = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            idx = ty * tiles_x + tx
            off_b0 = info["off_table"] + idx * 8
            r_off = sess.get(
                url,
                headers={"Range": f"bytes={off_b0}-{off_b0 + 7}"},
                timeout=30,
            )
            bc_b0 = info["bc_table"] + idx * 4
            r_bc = sess.get(
                url,
                headers={"Range": f"bytes={bc_b0}-{bc_b0 + 3}"},
                timeout=30,
            )
            r_off.raise_for_status()
            r_bc.raise_for_status()
            off = struct.unpack("<Q", r_off.content)[0]
            bc = struct.unpack("<I", r_bc.content)[0]
            if bc == 0 or off == 0:
                continue
            r_tile = sess.get(url, headers={"Range": f"bytes={off}-{off + bc - 1}"}, timeout=60)
            r_tile.raise_for_status()
            bytes_transferred += len(r_tile.content) + 16384
            tile = _decode_zstd_tile_u8(r_tile.content, tw, th)
            oy, ox = (ty - ty0) * th, (tx - tx0) * tw
            canvas[oy : oy + th, ox : ox + tw] = tile

    # Crop tightly to requested pixel box
    y_start = r0 - ty0 * th
    y_end = r1 - ty0 * th + 1
    x_start = c0 - tx0 * tw
    x_end = c1 - tx0 * tw + 1
    cropped = canvas[y_start:y_end, x_start:x_end].copy()
    meta = {
        "year": year,
        "lon0": info["lon0"] + c0 * info["dlon"],
        "lat0": info["lat0"] - r0 * info["dlat"],
        "dlon": info["dlon"],
        "dlat": info["dlat"],
        "shape": list(cropped.shape),
        "bytes_downloaded": int(bytes_transferred),
    }
    np.savez_compressed(npz_path, data=cropped)
    meta_path.write_text(json.dumps(meta, indent=2), "utf-8")
    return cropped, meta, bytes_transferred


def sample_fields_ghlc(
    pilot_4326: gpd.GeoDataFrame,
    arr: np.ndarray,
    meta: dict[str, Any],
    buffer_m: float = 15.0,
) -> pd.DataFrame:
    """Sample interior pixels (after 15 m inward buffer) per pilot field on GHLC 30 m grid."""
    utm_crs = pilot_4326.estimate_utm_crs()
    inner_utm = pilot_4326.to_crs(utm_crs).geometry.buffer(-buffer_m)
    inner_4326 = gpd.GeoSeries(inner_utm, crs=utm_crs).to_crs("EPSG:4326")

    h, w = arr.shape
    lon0, lat0 = float(meta["lon0"]), float(meta["lat0"])
    dlon, dlat = float(meta["dlon"]), float(meta["dlat"])

    rows = []
    for fid, block, geom in zip(
        pilot_4326["field_id"], pilot_4326["block"], inner_4326, strict=True
    ):
        if geom is None or geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        c0 = max(0, int(np.floor((minx - lon0) / dlon)))
        c1 = min(w - 1, int(np.ceil((maxx - lon0) / dlon)))
        r0 = max(0, int(np.floor((lat0 - maxy) / dlat)))
        r1 = min(h - 1, int(np.ceil((lat0 - miny) / dlat)))
        if c1 < c0 or r1 < r0:
            continue
        cc, rr = np.meshgrid(np.arange(c0, c1 + 1), np.arange(r0, r1 + 1))
        xs = lon0 + (cc.ravel() + 0.5) * dlon
        ys = lat0 - (rr.ravel() + 0.5) * dlat
        inside = shapely.contains_xy(geom, xs, ys)
        vals = arr[rr.ravel()[inside], cc.ravel()[inside]]
        if len(vals) == 0:
            p = geom.representative_point()
            c_idx = int(np.clip((p.x - lon0) / dlon, 0, w - 1))
            r_idx = int(np.clip((lat0 - p.y) / dlat, 0, h - 1))
            vals = np.array([arr[r_idx, c_idx]])
        n_px = int(len(vals))
        n_maize = int((vals == MAIZE_CLASS).sum())
        n_soy = int((vals == SOYBEAN_CLASS).sum())
        n_other_crop = int((vals == OTHER_CROP_CLASS).sum())
        n_annual = int(np.isin(vals, ANNUAL_CROP_CLASSES).sum())
        u, cnt = np.unique(vals, return_counts=True)
        maj_cls = int(u[np.argmax(cnt)])
        rows.append(
            {
                "field_id": str(fid),
                "block": str(block),
                "year": int(meta["year"]),
                "ghlc_n_px": n_px,
                "ghlc_majority_class": maj_cls,
                "ghlc_maize_share": round(n_maize / n_px, 4),
                "ghlc_soy_share": round(n_soy / n_px, 4),
                "ghlc_other_crop_share": round(n_other_crop / n_px, 4),
                "ghlc_annual_crop_share": round(n_annual / n_px, 4),
                "ghlc_is_maize": bool(maj_cls == MAIZE_CLASS or n_maize / n_px >= 0.5),
                "ghlc_is_cropland": bool(n_annual / n_px >= 0.5),
            }
        )
    return pd.DataFrame(rows)


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    yt = np.asarray(y_true, bool)
    yp = np.asarray(y_pred, bool)
    tp = int((yt & yp).sum())
    fp = int((~yt & yp).sum())
    fn = int((yt & ~yp).sum())
    tn = int((~yt & ~yp).sum())
    n = len(yt)
    acc = (tp + tn) / n if n else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    pe = (((tp + fp) * (tp + fn)) + ((fn + tn) * (fp + tn))) / (n * n) if n else 1.0
    kappa = (acc - pe) / (1.0 - pe) if pe < 1.0 else 0.0
    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "kappa": round(float(kappa), 4),
    }


def evaluate_agreement(
    clf_df: pd.DataFrame,
    ghlc_df: pd.DataFrame,
    conf_threshold: float = 0.0,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    """Compare Tier 3 classifier labels against OGH-GHLC10 / WorldCereal labels."""
    m = clf_df.merge(ghlc_df, on=["field_id", "year"], how="inner")
    m = m[m["crop"] != "unknown"].copy()
    if conf_threshold > 0:
        m = m[m["crop_conf"] >= conf_threshold].copy()
    if m.empty:
        return {"n": 0}

    m["clf_is_maize"] = m["crop"] == "maize"
    m["clf_is_cropland"] = m["crop"].isin(["winter_wheat", "sunflower", "maize"])

    maize_metrics = _binary_metrics(m["ghlc_is_maize"].to_numpy(), m["clf_is_maize"].to_numpy())
    cropland_acc = float(m["ghlc_is_cropland"].mean())
    ghlc_cropland_mask = m["ghlc_is_cropland"].to_numpy()

    # Among WorldCereal-confirmed non-maize annual crops (class 5), share classified as non-maize
    other_crop_mask = m["ghlc_majority_class"] == OTHER_CROP_CLASS
    non_maize_specificity = (
        float((m.loc[other_crop_mask, "crop"].isin(["winter_wheat", "sunflower"])).mean())
        if other_crop_mask.any()
        else float("nan")
    )

    # Spatial-block bootstrap 95% CI across 10 km blocks for F1 and Overall Accuracy
    rng = np.random.default_rng(seed)
    blocks = sorted(m["block"].unique())
    by_b = {b: m[m["block"] == b] for b in blocks}
    boot_acc, boot_f1 = [], []
    if len(blocks) >= 2:
        for _ in range(n_boot):
            pick = rng.choice(blocks, size=len(blocks), replace=True)
            sub = pd.concat([by_b[b] for b in pick], ignore_index=True)
            bm = _binary_metrics(sub["ghlc_is_maize"].to_numpy(), sub["clf_is_maize"].to_numpy())
            boot_acc.append(bm["accuracy"])
            boot_f1.append(bm["f1"])
    else:
        boot_acc, boot_f1 = [maize_metrics["accuracy"]], [maize_metrics["f1"]]

    by_clf_crop = {}
    for c, g in m.groupby("crop"):
        is_other = g["ghlc_majority_class"] == OTHER_CROP_CLASS
        by_clf_crop[str(c)] = {
            "n": int(len(g)),
            "ghlc_maize_frac": round(float(g["ghlc_is_maize"].mean()), 4),
            "ghlc_other_crop_frac": round(float(is_other.mean()), 4),
            "ghlc_cropland_frac": round(float(g["ghlc_is_cropland"].mean()), 4),
        }

    return {
        "n": int(len(m)),
        "n_fields": int(m["field_id"].nunique()),
        "n_blocks": int(m["block"].nunique()),
        "conf_threshold": conf_threshold,
        "cropland_rate_on_ghlc": round(float(ghlc_cropland_mask.mean()), 4),
        "clf_cropland_agreement": round(float(cropland_acc), 4),
        "non_maize_other_crop_agreement": (
            round(non_maize_specificity, 4) if np.isfinite(non_maize_specificity) else None
        ),
        "maize_vs_non_maize": {
            **maize_metrics,
            "accuracy_ci95": [
                round(float(np.quantile(boot_acc, 0.025)), 4),
                round(float(np.quantile(boot_acc, 0.975)), 4),
            ],
            "f1_ci95": [
                round(float(np.quantile(boot_f1, 0.025)), 4),
                round(float(np.quantile(boot_f1, 0.975)), 4),
            ],
        },
        "by_classified_crop": by_clf_crop,
    }
