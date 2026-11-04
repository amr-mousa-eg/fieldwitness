"""Per field-year crop labels (PLAN.md T1.6).

Kansas (Tier 1): USDA CSB 2017-2024 edition, one GeoParquet file per year on Source Cooperative.
CSB field ids do not persist between the per-year files (2023 vs 2024: 5 of 200 pilot ids found,
none with identical geometry; DECISIONS.md), so each year's crop is taken from the polygon that
contains the pilot field's representative point (spatial join).

Names: CSB `crop:name` -> crop key via crops.yaml `label_aliases`; otherwise the HCAT3 code is
mapped to a history state (fallow, temporary_grass, perennial_forage, other_arable, unknown),
"other_annual" for an annual crop without a crop key, or "non_arable" for groups 3302-3308.
CDL double-crop names ("Dbl Crop WinWht/Sorghum") give the first crop plus `double_crop_second`.
Labels for season year Y are dated Y-12-31 for the `as_of` guard.
"""

import datetime as dt
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from fieldwitness.census import tile_lonlat_bounds
from fieldwitness.config import load_crops
from fieldwitness.data.asof import cutoff, guard, register
from fieldwitness.data.geoparquet import open_source, read_bbox
from fieldwitness.data.hcat import history_state

CSB_KEY = "ftw/harmonized-field-data/us_usda_cropland/year={y}/us_usda_cropland-{y}.parquet"
CSB_YEARS = range(2017, 2025)
DATA = Path("data/fields")
TABLE = Path("data/labels")
RESULTS = Path("results/labels")


def csb_year(region_id: str, year: int, grid: dict, src=None) -> gpd.GeoDataFrame:
    cache = DATA / f"{region_id}_csb{year}.parquet"
    if year == 2024 and not cache.exists():
        cache = DATA / f"{region_id}_boundaries.parquet"  # read by T1.4
    if cache.exists():
        return gpd.read_parquet(cache)
    gdf, info = read_bbox(
        src or open_source(),
        CSB_KEY.format(y=year),
        tile_lonlat_bounds(grid),
        columns=["geometry", "id", "crop:name", "hcat:code"],
    )
    print(f"  CSB {year}: est {info['estimated_mb']} MB, {len(gdf):,} rows", flush=True)
    gdf.to_parquet(cache)
    return gdf


# Parts of CDL double-crop names ("Dbl Crop WinWht/Sorghum") as observed in the Kansas CSB files,
# mapped to crop keys; the first part is the earlier (winter) crop, the second the summer crop.
DOUBLE_PARTS = {
    "WinWht": "winter_wheat",
    "Corn": "maize",
    "Sorghum": "sorghum",
    "Soybeans": "soybean",
}


def label_of(crop_name, hcat_code, aliases: dict[str, str]) -> tuple[str, str | None]:
    """(crop key or history state, second crop of a double-crop year or None).

    Order: CSB alias -> crop key; "Dbl Crop A/B" -> (A, B); else the HCAT3 history state, where an
    annual arable code without a crop key becomes "other_annual" and groups 3302-3308 "non_arable".
    """
    if isinstance(crop_name, str):
        if crop_name in aliases:
            return aliases[crop_name], None
        if crop_name.startswith("Dbl Crop "):
            a, _, b = crop_name.removeprefix("Dbl Crop ").partition("/")
            if a in DOUBLE_PARTS and b in DOUBLE_PARTS:
                return DOUBLE_PARTS[a], DOUBLE_PARTS[b]
    state = history_state(hcat_code)
    if state is None:
        return "non_arable", None
    return ("other_annual" if state.isdigit() else state), None


def build_labels(region_id: str, grid: dict) -> pd.DataFrame:
    pilot = gpd.read_parquet(DATA / f"{region_id}_pilot.parquet")
    crops = load_crops().crops
    aliases = {a: k for k, c in crops.items() for a in c.label_aliases.get("CSB", [])}
    pts = gpd.GeoDataFrame(
        pilot[["field_id"]], geometry=pilot.geometry.representative_point(), crs=pilot.crs
    )
    src = open_source()
    rows = []
    for y in CSB_YEARS:
        g = csb_year(region_id, y, grid, src)
        j = gpd.sjoin(pts.to_crs(g.crs), g[["geometry", "crop:name", "hcat:code"]], how="left")
        j = j[~j.index.duplicated(keep="first")]
        for fid, name, code in zip(j["field_id"], j["crop:name"], j["hcat:code"], strict=True):
            crop, second = label_of(name, code, aliases)
            rows.append(
                {
                    "field_id": fid,
                    "year": y,
                    "crop": crop,
                    "double_crop_second": second,
                    "crop_name_raw": name if isinstance(name, str) else None,
                    "hcat_code": None if pd.isna(code) else str(int(code)).zfill(10),
                    "crop_source": "label",
                }
            )
    table = pd.DataFrame(rows)
    TABLE.mkdir(parents=True, exist_ok=True)
    table.to_parquet(TABLE / f"{region_id}.parquet")
    return table


def coverage(table: pd.DataFrame) -> dict:
    crop_keys = set(load_crops().crops)
    per_field = table.groupby("field_id")["crop"].apply(lambda s: (s != "unknown").sum())
    raw_unmapped = table.loc[~table["crop"].isin(crop_keys), "crop_name_raw"].value_counts()
    return {
        "fields": int(table["field_id"].nunique()),
        "years": sorted(int(y) for y in table["year"].unique()),
        "field_years": int(len(table)),
        "labelled_share": round(float((table["crop"] != "unknown").mean()), 4),
        "fields_with_all_years": int((per_field == table["year"].nunique()).sum()),
        "crop_mix": {k: int(v) for k, v in table["crop"].value_counts().items()},
        "not_a_crop_key_by_raw_name": {str(k): int(v) for k, v in raw_unmapped.items()},
    }


def write_coverage(region_id: str, table: pd.DataFrame) -> dict:
    rep = coverage(table)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{region_id}_coverage.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


@register("labels")
def read(region_id: str = "ks_t14slh", table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Label table limited to season years whose end (Y-12-31) is on or before the cut-off."""
    t = table if table is not None else pd.read_parquet(TABLE / f"{region_id}.parquet")
    c = cutoff()
    if c is not None:
        t = t[t["year"].map(lambda y: dt.date(int(y), 12, 31) <= c)]
    guard((dt.date(int(y), 12, 31) for y in t["year"]), "labels")
    return t
