"""T1.4 acceptance: 20 points across regions -> polygon or "no field"; interior pixels on 3 fields.

Usage:  uv run python -u scripts/check_resolver.py

Uses only cached boundary files (no network): Kansas CSB tile (data/fields), Toulouse RPG 2024
20 km box and Ukraine FTW 2024 10 km box (data/census). Points: per region, the representative
points of seeded random fields (expected: a field) plus seeded random points in the cached
extent (either result). Writes results/resolver_check.json.
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from fieldwitness.resolve.fields import (
    SEED,
    field_id,
    interior_pixel_counts_raster,
    resolve_point,
)
from fieldwitness.resolve.pilot import load_grid
from fieldwitness.resolve.pixels import interior_pixel_counts

SOURCES = {  # region: (cached file, n field points, n random points)
    "ks_t14slh": ("data/fields/ks_t14slh_boundaries.parquet", 5, 3),
    "fr_toulouse_t31tcj": ("data/census/fr_t31tcj_box20km_2024.parquet", 3, 3),
    "ua_central_t36uvu": ("data/census/ua_t36uvu_box10km_ftw.parquet", 3, 3),
}


def load(region: str, path: str) -> gpd.GeoDataFrame:
    g = gpd.read_parquet(path)
    if "determination:datetime" in g.columns:  # FTW: 2024 layer only
        g = g[pd.to_datetime(g["determination:datetime"]).dt.year == 2024]
    return g.to_crs("EPSG:4326").reset_index(drop=True)


def main() -> None:
    rng = np.random.default_rng(SEED)
    points = []
    for region, (path, n_field, n_rand) in SOURCES.items():
        g = load(region, path)
        for i in rng.choice(len(g), n_field, replace=False):
            p = g.geometry.iloc[i].representative_point()
            points.append((region, "field_point", p.x, p.y, g))
        x0, y0, x1, y1 = g.total_bounds
        for _ in range(n_rand):
            points.append((region, "random_point", rng.uniform(x0, x1), rng.uniform(y0, y1), g))
    rows = []
    for region, kind, lon, lat, g in points:
        hit = resolve_point(lon, lat, g)
        rows.append(
            {
                "region": region,
                "kind": kind,
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "result": "no field" if hit is None else "polygon",
                "field_id": None if hit is None else field_id(hit.geometry),
            }
        )

    # Interior pixels on 3 pilot fields: vector rule vs GDAL rasterisation (independent check)
    grid = load_grid("ks_t14slh")
    pilot = gpd.read_parquet("data/fields/ks_t14slh_pilot.parquet").to_crs(grid["epsg"])
    three = pilot.sample(3, random_state=SEED)
    geoms = list(three.geometry)
    v = interior_pixel_counts(geoms, grid["ulx"], grid["uly"], buffer_m=15)
    r = interior_pixel_counts_raster(geoms, grid["ulx"], grid["uly"], buffer_m=15)
    checks = [
        {
            "field_id": f,
            "stored": int(s),
            "vector": int(a),
            "raster_gdal": int(b),
            "match": bool(a == b == s),
        }
        for f, s, a, b in zip(three["field_id"], three["interior_px"], v, r, strict=True)
    ]
    out = {
        "points": rows,
        "n_points": len(rows),
        "n_polygon": sum(r["result"] == "polygon" for r in rows),
        "n_no_field": sum(r["result"] == "no field" for r in rows),
        "field_points_resolved": all(
            r["result"] == "polygon" for r in rows if r["kind"] == "field_point"
        ),
        "interior_pixel_checks": checks,
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/resolver_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "points"}, indent=1))


if __name__ == "__main__":
    main()
