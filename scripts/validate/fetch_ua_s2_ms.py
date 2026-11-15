"""Fetch Sentinel-2 L2A 20 m Red-Edge/SWIR indices (NDRE1, NDRE2, NDMI, NBR2) for ua_central_t36uvu.

Capped at <= 220 MB HTTP range reads so total data/ stays well under CLAUDE.md Rule 11 (1 GB).
Writes `data/fields/ua_central_t36uvu_s2_multispectral.parquet`.

Usage: uv run python -u scripts/validate/fetch_ua_s2_ms.py
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

from fieldwitness.data.s2_cog import build_s2_multispectral

REGION = "ua_central_t36uvu"


def main() -> int:
    pilot = gpd.read_parquet(f"data/fields/{REGION}_pilot.parquet")
    scenes = json.loads((Path("data/s2_cog") / REGION / "scenes.json").read_text("utf-8"))
    ref = scenes[0]
    epsg = int(ref["properties"]["proj:epsg"])
    tr = ref["assets"]["rededge1"]["proj:transform"]
    grid = {
        "epsg": f"EPSG:{epsg}",
        "ulx": float(tr[2]),
        "uly": float(tr[5]),
        "size_m": 109800.0,
    }
    print(
        f"Fetching S2 20 m Red-Edge/SWIR for {REGION} ({len(pilot)} fields, grid={grid})...",
        flush=True,
    )
    df, meta = build_s2_multispectral(
        REGION,
        pilot,
        grid,
        months=(5, 6, 7, 8, 9, 10),
        max_bytes=280_000_000,
    )
    print(f"Done: {meta}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
