"""ISRIC SoilGrids 2.0 soil properties per pilot field via WCS (PLAN.md T1.3).

The SoilGrids REST `properties/query` service was down on 2026-11-04 (HTTP 503 / timeouts); the
documented WCS on maps.isric.org works and is used instead (docs.isric.org/globaldata/soilgrids/
wcs.html; GetCapabilities verified). Licence: CC-BY 4.0 for SoilGrids per the ISRIC data policy
(v2024-1). Units and conversion factors from docs.isric.org SoilGrids_faqs_01 ("SoilGrids layers"):
bdod cg/cm3 /100 -> kg/dm3; clay, sand, silt g/kg /10 -> %; soc dg/kg /10 -> g/kg.

SoilGrids is 250 m: context/forcing only, never a field-level claim (CLAUDE.md rule 5); values
are tag E. The coverages declare no nil value; a cell is treated as missing where the property's
`mean` coverage at that depth is 0 (tag A assumption, DECISIONS.md), and that mask applies to all
statistics, so a genuine 0 in a lower quantile (e.g. deep SOC Q0.05) is kept.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
import shapely

WCS = "https://maps.isric.org/mapserv"
PROPERTIES = {  # name: (mapped units, divide by, conventional units)
    "bdod": ("cg/cm3", 100, "kg/dm3"),
    "clay": ("g/kg", 10, "%"),
    "sand": ("g/kg", 10, "%"),
    "silt": ("g/kg", 10, "%"),
    "soc": ("dg/kg", 10, "g/kg"),
}
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]
STATS = ["mean", "Q0.05", "Q0.5", "Q0.95"]
CACHE = Path("data/soil")


def coverage_id(prop: str, depth: str, stat: str) -> str:
    return f"{prop}_{depth}_{stat}"


def fetch_coverage(prop: str, depth: str, stat: str, bbox, out: Path, session=None) -> Path:
    """GetCoverage (WCS 2.0.1) for a lon/lat bbox (EPSG:4326 subset and output); cached GeoTIFF."""
    path = out / f"{coverage_id(prop, depth, stat)}.tif"
    if path.exists():
        return path
    w, s, e, n = bbox
    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    params = [
        ("map", f"/map/{prop}.map"),
        ("SERVICE", "WCS"),
        ("VERSION", "2.0.1"),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", coverage_id(prop, depth, stat)),
        ("FORMAT", "GEOTIFF_INT16"),
        ("SUBSET", f"X({w},{e})"),
        ("SUBSET", f"Y({s},{n})"),
        ("SUBSETTINGCRS", crs),
        ("OUTPUTCRS", crs),
    ]
    r = (session or requests).get(WCS, params=params, timeout=300)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/tiff"):
        raise RuntimeError(f"unexpected WCS response for {coverage_id(prop, depth, stat)}")
    out.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return path


def field_medians(
    tif: Path, fields_4326: gpd.GeoDataFrame, nodata_from: Path | None = None
) -> list[tuple[float | None, int]]:
    """Per field: median raw value over grid cells whose centres fall inside the field, or the cell
    under the representative point if no centre falls inside. Cells are missing where the raster
    `nodata_from` (default: `tif` itself) is 0. Returns (raw value, number of cells)."""
    with rasterio.open(nodata_from or tif) as ref:
        missing = ref.read(1) == 0
    with rasterio.open(tif) as src:
        a = src.read(1).astype(float)
        a[missing] = np.nan
        t = src.transform
        rows, cols = np.indices(a.shape)
        xs, ys = rasterio.transform.xy(t, rows.ravel(), cols.ravel())
        xs, ys, vals = np.asarray(xs), np.asarray(ys), a.ravel()
        out = []
        for geom in fields_4326.geometry:
            minx, miny, maxx, maxy = geom.bounds
            near = (xs >= minx) & (xs <= maxx) & (ys >= miny) & (ys <= maxy)
            inside = np.zeros_like(near)
            inside[near] = shapely.contains_xy(geom, xs[near], ys[near])
            v = vals[inside]
            v = v[~np.isnan(v)]
            if v.size == 0:
                p = geom.representative_point()
                r, c = src.index(p.x, p.y)
                v = np.array([a[r, c]]) if 0 <= r < a.shape[0] and 0 <= c < a.shape[1] else v
                v = v[~np.isnan(v)]
            out.append((float(np.median(v)) if v.size else None, int(v.size)))
    return out


def build(region_id: str, bbox) -> pd.DataFrame:
    pilot = gpd.read_parquet(f"data/fields/{region_id}_pilot.parquet").to_crs("EPSG:4326")
    out_dir = CACHE / region_id
    rows = []
    with requests.Session() as s:
        for prop, (_mapped, factor, units) in PROPERTIES.items():
            for depth in DEPTHS:
                for stat in STATS:
                    tif = fetch_coverage(prop, depth, stat, bbox, out_dir, session=s)
                    mean_tif = fetch_coverage(prop, depth, "mean", bbox, out_dir, session=s)
                    vals = field_medians(tif, pilot, nodata_from=mean_tif)
                    for fid, (raw, n) in zip(pilot["field_id"], vals, strict=True):
                        rows.append(
                            {
                                "field_id": fid,
                                "property": prop,
                                "depth": depth,
                                "stat": stat,
                                "value": None if raw is None else raw / factor,
                                "units": units,
                                "n_cells": n,
                                "tag": "E",
                                "source": f"SoilGrids 2.0 WCS {coverage_id(prop, depth, stat)}",
                            }
                        )
            print(f"  {prop}: {len(DEPTHS) * len(STATS)} coverages done", flush=True)
    table = pd.DataFrame(rows)
    table.to_parquet(CACHE / f"{region_id}_fields.parquet")
    return table
