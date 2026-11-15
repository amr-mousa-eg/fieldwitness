"""Fetch real open Phase P2 Earth observations & run E1.3 EO cross-checks.

Downloads within CLAUDE.md Rule 11 (< 1 GB budget):
  1. Landsat 8/9 C2 L2 ST_B10/lwir11 daytime LST (30 m COG / 100 m TIRS) for:
     - ks_t14slh (200 fields from packs/demo/ks_t14slh/index.json)
     - ua_central_t36uvu (400 pilot fields from data/fields/ua_central_t36uvu_pilot.parquet)
  2. ECMWF ERA5 daily precipitation/temperature/ETo (2001-2024, Open-Meteo Archive, tag E)
     for ks_t14slh and ua_central_t36uvu centroids.
  3. Runs scripts/validate/check_ecostress.py and scripts/validate/check_smap_gpm.py.

Usage: uv run python -u scripts/validate/fetch_p2_obs.py
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from fieldwitness.data import era5
from fieldwitness.data.landsat_lst import build_landsat_lst_region


def _ks_fields() -> gpd.GeoDataFrame:
    idx = json.loads(Path("packs/demo/ks_t14slh/index.json").read_text("utf-8"))
    rows = [
        {"field_id": f["field_id"], "geometry": shapely.from_wkt(f["geometry_wkt"])}
        for f in idx["fields"]
    ]
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def _ua_fields() -> gpd.GeoDataFrame:
    return gpd.read_parquet("data/fields/ua_central_t36uvu_pilot.parquet")[
        ["field_id", "geometry"]
    ].to_crs("EPSG:4326")


def main() -> int:
    # 1. ECMWF ERA5 daily series (2001-2024)
    era5_dir = Path("data/weather/era5")
    era5_dir.mkdir(parents=True, exist_ok=True)
    centroids = {
        "ks_t14slh": (-101.08, 38.28),
        "ua_central_t36uvu": (30.56, 48.20),
    }
    for region_id, (lon, lat) in centroids.items():
        out_p = era5_dir / f"{region_id}_era5_daily.parquet"
        if not out_p.exists():
            print(f"Fetching ERA5 2001-2024 for {region_id} ({lat}, {lon})...", flush=True)
            payload = era5.fetch_era5_point(lat, lon, dt.date(2001, 1, 1), dt.date(2024, 12, 31))
            df_e = era5.parse_era5_payload(payload)
            df_e.to_parquet(out_p, index=False)
            kb = out_p.stat().st_size / 1024
            print(f"  -> {out_p} ({len(df_e)} rows, {kb:.1f} KB)", flush=True)
        else:
            print(f"ERA5 cached: {out_p}", flush=True)

    # 2. Landsat 8/9 C2 L2 ST_B10 LST (max 48 scenes, <= 60 MB/region)
    for region_id, loader in (("ks_t14slh", _ks_fields), ("ua_central_t36uvu", _ua_fields)):
        lst_p = Path(f"data/context/landsat_lst/{region_id}_lst.parquet")
        if lst_p.exists():
            df_existing = pd.read_parquet(lst_p)
            print(
                f"Landsat LST cached for {region_id}: {len(df_existing)} rows, "
                f"{df_existing['field_id'].nunique()} fields",
                flush=True,
            )
            continue
        gdf = loader()
        print(f"Fetching Landsat 8/9 C2 L2 LST for {region_id} ({len(gdf)} fields)...", flush=True)
        df_lst, meta = build_landsat_lst_region(
            region_id,
            gdf,
            start_date="2017-04-01",
            end_date="2024-10-31",
            max_total_scenes=48,
            max_bytes=60_000_000,
        )
        print(
            f"  -> {region_id}: {meta['rows']} rows, {meta['fields_with_obs']} fields, "
            f"{meta['downloaded_bytes'] / 1e6:.2f} MB",
            flush=True,
        )

    # 3. Run validation checks
    subprocess.run([sys.executable, "scripts/validate/check_ecostress.py"], check=True)
    subprocess.run([sys.executable, "scripts/validate/check_smap_gpm.py"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
