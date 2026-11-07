"""T5.1 field-season table for the neighbour witness (PLAN.md T5.1).

One row per (field, year) with a crop label and the previous year's label. Outcomes come from the
HLS NDVI series smoothed by T2.1 inside a fixed per-crop window (T2.2 failed its acceptance test, so
observed SOS/EOS are not used). Windows are team choices (tag A, UNVERIFIED): summer crops
1 Apr-31 Oct (day of year 91-304), winter wheat 1 Jan-15 Jul (1-196).
Outcomes (tag D, from satellite data):
  canopy_integral  sum of smoothed NDVI over the window days (NDVI-days)
  peak_ndvi        maximum smoothed NDVI in the window
  cover_days       window days with NDVI >= the cover threshold of config/story.yaml
  season_length    days from first to last covered day in the window
  canopy_drop      largest fall of NDVI below its running maximum inside the window
                   ("drought-season canopy drop" is this value for dry seasons, see `dry_season`)
ET outcomes are not included (no ECOSTRESS data yet). Confounders: POWER season precipitation and
mean Tmax (tag D scale-flagged, 0.5 deg-like coarse forcing), SoilGrids 5-15 cm mean clay/sand/SOC
(tag E, 250 m), field area, lon/lat, earlier crop (two years back), `dry_season` = season rain below
the field's own median over all labelled years. Irrigation proxy: NOT AVAILABLE (WorldCereal needs a
login, T1.4), column absent. All reads go through the `as_of` readers.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import hls_qa, labels, power
from fieldwitness.story.smooth import load_story, smooth_series

REGION = "ks_t14slh"
OUT = Path("data/neighbours")
RESULTS = Path("results/neighbours")
WINDOWS = {  # crop key -> (first, last) day of the season year, tag A
    "maize": (91, 304),
    "sorghum": (91, 304),
    "soybean": (91, 304),
    "sunflower": (91, 304),
    "winter_wheat": (1, 196),
}
SOIL_PROPS = ("clay", "sand", "soc")
SOIL_DEPTH = "5-15cm"
TAGS = {
    "canopy_integral": "D",
    "peak_ndvi": "D",
    "cover_days": "D",
    "season_length": "D",
    "canopy_drop": "D",
    "season_precip_mm": "D",
    "season_tmax_c": "D",
    "clay_pct": "E",
    "sand_pct": "E",
    "soc_g_kg": "E",
    "area_ha": "E",
    "crop": "E",
    "prev_crop": "E",
    "prev2_crop": "E",
    "dry_season": "A",
}
EPOCH = pd.Timestamp("1970-01-01")


def season_outcomes(
    dates: np.ndarray, ndvi: np.ndarray, year: int, window: tuple[int, int], cfg: dict
) -> dict | None:
    """Outcomes of one season from raw clear NDVI observations of the year; None if too sparse."""
    if len(dates) < 10:
        return None
    days = (pd.to_datetime(dates) - EPOCH).days.to_numpy(float)
    grid, sm = smooth_series(days, np.asarray(ndvi, float), cfg["smoothing"])
    doy = (EPOCH + pd.to_timedelta(grid, unit="D")).day_of_year.to_numpy()
    yr = (EPOCH + pd.to_timedelta(grid, unit="D")).year.to_numpy()
    inside = (yr == year) & (doy >= window[0]) & (doy <= window[1]) & np.isfinite(sm)
    if inside.sum() < 0.8 * (window[1] - window[0] + 1) / (grid[1] - grid[0]):
        return None  # smoothed series does not cover the window (gaps too long)
    step = float(grid[1] - grid[0])
    v = sm[inside]
    covered = v >= cfg["cover"]["ndvi_threshold"]
    idx = np.flatnonzero(covered)
    return {
        "canopy_integral": float(v.sum() * step),
        "peak_ndvi": float(v.max()),
        "cover_days": float(covered.sum() * step),
        "season_length": float((idx[-1] - idx[0] + 1) * step) if len(idx) else 0.0,
        "canopy_drop": float((np.maximum.accumulate(v) - v).max()),
    }


def build(region_id: str = REGION) -> pd.DataFrame:
    cfg = load_story()
    lab = labels.read(region_id)
    series = hls_qa.read(region_id)
    series = series.dropna(subset=["ndvi"])
    pilot = pd.read_parquet(f"data/fields/{region_id}_pilot.parquet").set_index("field_id")
    soil = pd.read_parquet(f"data/soil/{region_id}_fields.parquet")
    soil = soil[(soil["depth"] == SOIL_DEPTH) & (soil["stat"] == "mean")]
    soil = soil.pivot(index="field_id", columns="property", values="value")
    crop_of = lab.set_index(["field_id", "year"])["crop"].to_dict()
    by_field = {fid: g for fid, g in series.groupby("field_id")}
    rows = []
    for fid, g in by_field.items():
        if fid not in pilot.index:
            continue
        r = pilot.loc[fid]
        wx = power.read(r["lon"], r["lat"])
        g = g.assign(year=g["date"].dt.year)
        for year in sorted(set(lab.loc[lab["field_id"] == fid, "year"])):
            crop = crop_of.get((fid, year))
            prev = crop_of.get((fid, year - 1))
            if crop is None or prev is None:
                continue
            row = {
                "field_id": fid,
                "year": int(year),
                "crop": crop,
                "prev_crop": prev,
                "prev2_crop": crop_of.get((fid, year - 2)),
                "area_ha": float(r["area_ha"]),
                "lon": float(r["lon"]),
                "lat": float(r["lat"]),
                "block": r["block"],
            }
            for p in SOIL_PROPS:
                row[{"clay": "clay_pct", "sand": "sand_pct", "soc": "soc_g_kg"}[p]] = (
                    float(soil.loc[fid, p]) if fid in soil.index else np.nan
                )
            if crop in WINDOWS:
                a, b = WINDOWS[crop]
                gy = g[g["year"] == year]
                out = season_outcomes(
                    gy["date"].to_numpy(), gy["ndvi"].to_numpy(), year, (a, b), cfg
                )
                s = wx[
                    (wx.index.year == year) & (wx.index.dayofyear >= a) & (wx.index.dayofyear <= b)
                ]
                row["season_precip_mm"] = float(s["PRECTOTCORR"].sum()) if len(s) else np.nan
                row["season_tmax_c"] = float(s["T2M_MAX"].mean()) if len(s) else np.nan
                if out:
                    row.update(out)
            rows.append(row)
    df = pd.DataFrame(rows)
    # dry season: season rain below the field's own median over its labelled seasons (A)
    med = df.groupby("field_id")["season_precip_mm"].transform("median")
    df["dry_season"] = (df["season_precip_mm"] < med).where(df["season_precip_mm"].notna())
    return df


def contrast_counts(df: pd.DataFrame, min_n: int = 1) -> pd.DataFrame:
    """Row counts per (current crop, previous crop) with a computed outcome."""
    ok = df.dropna(subset=["canopy_integral"])
    c = ok.groupby(["crop", "prev_crop"]).agg(
        n=("field_id", "size"), n_fields=("field_id", "nunique")
    )
    return c[c["n"] >= min_n].reset_index().sort_values(["crop", "n"], ascending=[True, False])


def write(df: pd.DataFrame, region_id: str = REGION) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / f"{region_id}_field_season.parquet", index=False)
    cc = contrast_counts(df)
    summary = {
        "rows": len(df),
        "rows_with_outcome": int(df["canopy_integral"].notna().sum()),
        "fields": int(df["field_id"].nunique()),
        "tags": TAGS,
        "windows_tag_A": WINDOWS,
        "contrast_counts": cc.to_dict("records"),
        "irrigation_proxy": "not available (WorldCereal needs a login, T1.4)",
        "et_outcome": "not available (no ECOSTRESS data)",
    }
    (RESULTS / "field_season_summary.json").write_text(json.dumps(summary, indent=2), "utf-8")
    cc.to_csv(RESULTS / "precrop_contrast_counts.csv", index=False)
    return summary
