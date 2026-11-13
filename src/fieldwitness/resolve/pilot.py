"""Pilot-field selection for a region (PLAN.md T1.4).

Kansas (Tier 1): CSB 2024 edition polygons on the HLS tile, read once (capped bbox read) and
cached under data/fields/. Fields are annual arable on the current year (2024) and must be one of
the region's rotation crops (fallow/cover crop excluded as current crops). Sample ~200 fields
stratified by crop and 10 km block (WorldCereal irrigation layer needs a Terrascope login, so no
irrigation stratum; DECISIONS.md).
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from fieldwitness.census import tile_lonlat_bounds
from fieldwitness.config import load_crops, load_regions, rotation_options
from fieldwitness.data.geoparquet import open_source, read_bbox
from fieldwitness.data.hcat import is_annual_arable
from fieldwitness.resolve.fields import candidate_fields, select_pilot_fields

DATA = Path("data/fields")
RESULTS = Path("results/pilot_fields")
N_PILOT = 200
MIN_PER_CROP = 40
CSB_COLUMNS = ["geometry", "id", "crop:name", "hcat:code"]


def load_grid(region_id: str) -> dict:
    """Tile grid (EPSG, ULX/ULY, size) from the census result of the region."""
    res = json.loads(Path(f"docs/census/{region_id}.json").read_text(encoding="utf-8"))
    return res["grid"]


def read_tile_polygons(
    region_id: str, key: str, grid: dict, columns: list[str]
) -> gpd.GeoDataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    cache = DATA / f"{region_id}_boundaries.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    gdf, info = read_bbox(open_source(), key, tile_lonlat_bounds(grid), columns=columns)
    print(f"  read {key}: est {info['estimated_mb']} MB, {len(gdf):,} rows", flush=True)
    gdf.to_parquet(cache)
    return gdf


def crop_keys_from_labels(names: pd.Series, source: str, crop_keys: list[str]) -> pd.Series:
    """Map label names (e.g. CSB CDL names) to crop keys via crops.yaml `label_aliases`."""
    crops = load_crops().crops
    alias = {a: k for k in crop_keys for a in crops[k].label_aliases.get(source, [])}
    return names.map(alias)


def quotas(counts: pd.Series, n: int = N_PILOT, minimum: int = MIN_PER_CROP) -> dict[str, int]:
    """Per-crop sample sizes: proportional to the candidate counts, at least `minimum` each
    (capped by availability), summing to about `n`."""
    base = {c: max(minimum, round(n * k / counts.sum())) for c, k in counts.items()}
    scale = n / sum(base.values())
    return {c: min(int(counts[c]), max(minimum, round(v * scale))) for c, v in base.items()}


def build_pilot_fields(
    region_id: str,
    n_pilot: int = N_PILOT,
    cog_tile_window: tuple[tuple[int, int], tuple[int, int]] | None = None,
    min_area_ha: float = 0.0,
) -> tuple[gpd.GeoDataFrame, dict]:
    region = load_regions()[region_id]
    crops = load_crops()
    grid = load_grid(region_id)
    raw = region.model_extra or {}
    key = raw["boundary"]["key"]
    has_csb_labels = raw.get("labels", {}).get("source") == "CSB"
    cols = CSB_COLUMNS if has_csb_labels else ["geometry"]
    gdf = read_tile_polygons(region_id, key, grid, cols)

    if cog_tile_window is not None:
        import shapely

        (tx0, tx1), (ty0, ty1) = cog_tile_window
        tile_m = 512 * 20.0
        box_utm = shapely.box(
            grid["ulx"] + tx0 * tile_m,
            grid["uly"] - (ty1 + 1) * tile_m,
            grid["ulx"] + (tx1 + 1) * tile_m,
            grid["uly"] - ty0 * tile_m,
        )
        utm_tmp = gdf.to_crs(grid["epsg"])
        gdf = gdf[shapely.within(utm_tmp.geometry.values, box_utm)].copy()

    if has_csb_labels:
        current = [
            c
            for c in rotation_options(crops, region.crops or [])
            if c not in ("fallow", "cover_crop")
        ]
        gdf = gdf[gdf["hcat:code"].map(is_annual_arable)].copy()
        gdf["crop"] = crop_keys_from_labels(gdf["crop:name"], "CSB", current)
        gdf = gdf[gdf["crop"].notna()]
        cand = candidate_fields(gdf, grid)
        if min_area_ha > 0:
            cand = cand[cand["area_m2"] >= min_area_ha * 1e4].copy()
        counts = cand["crop"].value_counts()
        q = quotas(counts, n=n_pilot)
        boundary_source = "CSB"
        strat = "crop x 10 km block (no irrigation stratum; DECISIONS.md)"
    else:
        cand = candidate_fields(gdf, grid)
        cand = cand.drop_duplicates(subset=["field_id"]).reset_index(drop=True)
        if min_area_ha > 0:
            cand = cand[cand["area_m2"] >= min_area_ha * 1e4].copy()
        cand["crop"] = "unlabelled"
        counts = pd.Series({"unlabelled": len(cand)})
        q = {"unlabelled": min(n_pilot, len(cand))}
        boundary_source = "FTW"
        strat = "10 km block uniform (Tier 3 unlabelled FTW boundaries)"

    pilot = select_pilot_fields(cand, q)
    out = pilot.to_crs("EPSG:4326")
    out = out.assign(
        region_id=region_id,
        boundary_source=boundary_source,
        area_ha=(pilot["area_m2"] / 1e4).round(3).values,
        lon=out.geometry.representative_point().x.round(6).values,
        lat=out.geometry.representative_point().y.round(6).values,
    )
    if not has_csb_labels:
        out["id"] = pd.NA
        out["crop"] = None
    keep = [
        "field_id",
        "region_id",
        "boundary_source",
        "id",
        "crop",
        "block",
        "area_ha",
        "interior_px",
        "hls_scale_flag",
        "lon",
        "lat",
        "geometry",
    ]
    out = out[keep].rename(columns={"id": "csb_id", "crop": "crop_2024"}).reset_index(drop=True)
    DATA.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(DATA / f"{region_id}_pilot.parquet")
    out.drop(columns="geometry").to_csv(RESULTS / f"{region_id}.csv", index=False)
    summary = {
        "region_id": region_id,
        "candidates": int(len(cand)),
        "candidates_by_crop": {str(k): int(v) for k, v in counts.items()},
        "quotas": {str(k): int(v) for k, v in q.items()},
        "pilot_fields": int(len(out)),
        "blocks_covered": int(out["block"].nunique()),
        "blocks_with_candidates": int(cand["block"].nunique()),
        "area_ha_median": float(out["area_ha"].median()),
        "interior_px_median": float(out["interior_px"].median()),
        "hls_scale_flagged": int(out["hls_scale_flag"].sum()),
        "cog_tile_window": [list(x) for x in cog_tile_window] if cog_tile_window else None,
        "min_area_ha": min_area_ha,
        "seed": 20261114,
        "stratification": strat,
    }
    (RESULTS / f"{region_id}_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    return out, summary
