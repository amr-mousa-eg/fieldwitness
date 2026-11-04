"""Compare the old and new `stays_arable` rules on Toulouse (T31TCJ) crop histories.

Usage:  uv run python -u scripts/check_history_rule.py

Fields = annual arable parcels of the 2024 France RPG file in the census 20 km box (selection on the
most recent year). History = the `hcat:code` of the parcel containing each field's representative
point in 2015-2023. Each year is a capped bbox read (geometry + hcat:code only), cached under
data/census/ (gitignored).
"""

import geopandas as gpd

from fieldwitness.census import CACHE, box_around
from fieldwitness.data.geoparquet import open_source, read_bbox
from fieldwitness.data.hcat import history_state, is_annual_arable, normalise, stays_arable

POINT = (1.75, 43.45)  # config/regions.yaml fr_toulouse_t31tcj
BOX = box_around(*POINT, 20)
FR = "ftw/harmonized-field-data/fr/year={y}/fr-{y}.parquet"
YEARS = range(2015, 2025)
COLS = ["geometry", "hcat:code"]


def old_history_state(code):
    """Rule in commit 2d1f351: any code outside 3301 (incl. 3399) meant 'left arable use'."""
    c = normalise(code)
    if c is None:
        return "unknown"
    return None if not c.startswith("3301") else "arable-or-state"


def year_parcels(src, y: int) -> gpd.GeoDataFrame:
    cache = CACHE / f"fr_t31tcj_box20km_{y}.parquet"
    if cache.exists():
        return gpd.read_parquet(cache)
    gdf, info = read_bbox(src, FR.format(y=y), BOX, columns=COLS)
    print(f"  read {y}: est {info['estimated_mb']} MB, {len(gdf):,} parcels", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(cache)
    return gdf


def main() -> None:
    src = open_source()
    by_year = {y: year_parcels(src, y).to_crs("EPSG:2154") for y in YEARS}
    cur = by_year[2024]
    fields = cur[cur["hcat:code"].map(is_annual_arable)].copy()
    fields["pt"] = fields.geometry.representative_point()
    pts = gpd.GeoDataFrame(fields[["hcat:code"]], geometry=fields["pt"], crs=fields.crs)
    hist = {2024: list(fields["hcat:code"])}
    for y in YEARS:
        if y == 2024:
            continue
        j = gpd.sjoin(pts, by_year[y][["geometry", "hcat:code"]], how="left", predicate="within")
        j = j[~j.index.duplicated(keep="first")]  # overlapping parcels: first match
        hist[y] = list(j["hcat:code_right"])
    rows = list(zip(*[hist[y] for y in YEARS], strict=True))
    n = len(rows)
    old_removed = sum(any(old_history_state(c) is None for c in r) for r in rows)
    new_removed = sum(not stays_arable(r) for r in rows)
    unknown_years = sum(history_state(c) == "unknown" for r in rows for c in r)
    print(f"fields (2024 annual arable, 20 km box): {n:,}")
    print(f"removed from history analysis, old rule (outside 3301): {old_removed:,}")
    print(f"removed from history analysis, new rule (3302-3308 only): {new_removed:,}")
    print(f"field-years in 'unknown' state (missing, 3399, generic): {unknown_years:,}")


if __name__ == "__main__":
    main()
