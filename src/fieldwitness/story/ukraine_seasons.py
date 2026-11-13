"""Tier 3 crop-sequence classifier for Central Ukraine (ua_central_t36uvu).

Central Ukraine has no multi-year public field-level crop labels (`labels.source == "none"` in
config/regions.yaml). For Phase 2 Neighbours Witness diagnostics, we infer annual crop states
`(field_id, year)` strictly from each field's observed Sentinel-2 L2A NDVI time series using
observations dated on or before `year-12-31` (enforcing CLAUDE.md Rule 6, zero post-year
leakage).

Method (source tag D, crop_source = "classifier"):
  1. Smooth each harvest-year trajectory `[year-1-09-01 .. year-12-31]` using Savitzky-Golay
     on the 5-day grid (config/story.yaml).
  2. Extract seasonal phenology features on `[Jan 1 .. Oct 31]` of `year`:
       - peak_ndvi, peak_doy (max smoothed NDVI in DOY 75..304)
       - spring_mean (mean NDVI in DOY 105..165, mid-Apr to mid-Jun)
       - midsummer_mean (mean NDVI in DOY 185..235, early Jul to late Aug)
       - late_summer_mean (mean NDVI in DOY 240..275, late Aug to early Oct)
  3. Require >= 5 clear observations in the growing window (DOY 60..304); else "unknown".
  4. Fallow / bare if peak_ndvi < 0.40.
  5. Winter cereal cohort (`winter_wheat`, combining winter wheat/barley per FAOSTAT region notes)
     if peak_doy <= 175 or (spring_mean - midsummer_mean >= 0.05 and peak_doy <= 185).
  6. Summer crop cohort separated into `sunflower` vs `maize` using Phase 1 Time-Weighted
     Dynamic Time Warping (`twdtw_distance`, Maus et al. 2016) against FAO-56 stage-length
     NDVI templates derived from `config/crops.yaml` (`sunflower`: [25, 35, 45, 25] days;
     `maize`: [30, 40, 50, 50] days; nominal planting DOY 115, tag A).

All inferred labels carry `crop_source = "classifier"` (tag D) and must be disclosed as weaker
than USDA CSB Tier 1 ground labels when interpreting Neighbours Witness diagnostics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fieldwitness.story.phenology_algorithms import twdtw_distance
from fieldwitness.story.smooth import load_story, smooth_series

EPOCH = pd.Timestamp("1970-01-01")
TEMPLATE_GRID = np.arange(75.0, 305.0, 10.0)


def _fao56_ndvi_template(
    sow_doy: float,
    stage_lengths: tuple[int, int, int, int],
    peak_ndvi: float = 0.78,
    base: float = 0.18,
) -> np.ndarray:
    """Piecewise-linear canopy NDVI proxy from FAO-56 Kc stage lengths (config/crops.yaml)."""
    l_ini, l_dev, l_mid, l_late = stage_lengths
    d0 = sow_doy
    d1 = d0 + l_ini
    d2 = d1 + l_dev
    d3 = d2 + l_mid
    d4 = d3 + l_late
    t = TEMPLATE_GRID
    out = np.full_like(t, base)
    ini_mask = (t >= d0) & (t < d1)
    dev_mask = (t >= d1) & (t < d2)
    mid_mask = (t >= d2) & (t < d3)
    late_mask = (t >= d3) & (t <= d4)
    out[ini_mask] = base + 0.05
    if l_dev > 0:
        out[dev_mask] = (base + 0.05) + (peak_ndvi - (base + 0.05)) * (t[dev_mask] - d1) / l_dev
    out[mid_mask] = peak_ndvi
    if l_late > 0:
        out[late_mask] = peak_ndvi - (peak_ndvi - (base + 0.05)) * (t[late_mask] - d3) / l_late
    return out


DEFAULT_TEMPLATES = {
    # config/crops.yaml ua_central_t36uvu stage lengths, nominal late-April sowing (DOY 115, tag A)
    "sunflower": _fao56_ndvi_template(115.0, (25, 35, 45, 25), peak_ndvi=0.76),
    "maize": _fao56_ndvi_template(115.0, (30, 40, 50, 50), peak_ndvi=0.80),
}


def season_features(
    dates: np.ndarray | pd.Series, ndvi: np.ndarray | pd.Series, year: int, cfg: dict | None = None
) -> dict[str, float] | None:
    """Extract causal phenology features for harvest `year` on `[year-1-09-01 .. year-12-31]`."""
    cfg = cfg or load_story()
    d = pd.DatetimeIndex(pd.to_datetime(dates))
    v = np.asarray(ndvi, dtype=float)
    start = pd.Timestamp(year=year - 1, month=9, day=1)
    end = pd.Timestamp(year=year, month=12, day=31)
    mask = (d >= start) & (d <= end) & np.isfinite(v)
    d_sub = d[mask]
    v_sub = v[mask]
    grow_obs = int(
        ((d_sub.year == year) & (d_sub.day_of_year >= 60) & (d_sub.day_of_year <= 304)).sum()
    )
    if len(d_sub) < 6 or grow_obs < 5:
        return None

    days = (d_sub - EPOCH).days.to_numpy(float)
    grid, sm = smooth_series(days, v_sub, cfg["smoothing"])
    ts = EPOCH + pd.to_timedelta(grid, unit="D")
    yr = ts.year.to_numpy()
    doy = ts.day_of_year.to_numpy()

    in_year = (yr == year) & np.isfinite(sm)
    grow = in_year & (doy >= 75) & (doy <= 304)
    if grow.sum() < 20:
        return None

    sm_grow = sm[grow]
    doy_grow = doy[grow]
    pk_idx = int(np.argmax(sm_grow))
    peak_ndvi = float(sm_grow[pk_idx])
    peak_doy = float(doy_grow[pk_idx])

    def _win_mean(a: int, b: int) -> float:
        m = in_year & (doy >= a) & (doy <= b)
        return float(np.nanmean(sm[m])) if m.any() else float("nan")

    curve = np.interp(TEMPLATE_GRID, doy_grow, sm_grow)
    return {
        "peak_ndvi": peak_ndvi,
        "peak_doy": peak_doy,
        "spring_mean": _win_mean(105, 165),
        "midsummer_mean": _win_mean(185, 235),
        "late_summer_mean": _win_mean(240, 275),
        "n_obs_growing": float(grow_obs),
        "curve": curve,
    }


def classify_season(
    feats: dict[str, float] | None,
    templates: dict[str, np.ndarray] | None = None,
) -> tuple[str, float]:
    """Classify one field-season into (crop, confidence) using causal phenology + TWDTW."""
    if feats is None:
        return "unknown", 0.0
    if feats["peak_ndvi"] < 0.40:
        conf = min(1.0, max(0.5, (0.40 - feats["peak_ndvi"]) / 0.20 + 0.5))
        return "fallow", round(float(conf), 3)

    pk_doy = feats["peak_doy"]
    spring = feats["spring_mean"]
    midsum = feats["midsummer_mean"]

    # Winter cereals (winter wheat / barley): spring/early-June peak before midsummer harvest
    if pk_doy <= 175 or (
        np.isfinite(spring) and np.isfinite(midsum) and spring - midsum >= 0.06 and pk_doy <= 185
    ):
        margin = max(0.0, (180.0 - pk_doy) / 40.0)
        conf = min(0.95, 0.65 + 0.30 * min(1.0, margin))
        return "winter_wheat", round(float(conf), 3)

    # Summer crop separation via TWDTW distance to FAO-56 templates (sunflower vs maize)
    tmpl = templates or DEFAULT_TEMPLATES
    curve = feats["curve"]
    d_sun = twdtw_distance(curve, TEMPLATE_GRID, tmpl["sunflower"], TEMPLATE_GRID)
    d_mai = twdtw_distance(curve, TEMPLATE_GRID, tmpl["maize"], TEMPLATE_GRID)
    crop = "sunflower" if d_sun <= d_mai else "maize"
    diff = abs(d_sun - d_mai) / (min(d_sun, d_mai) + 1e-6)
    conf = min(0.92, 0.55 + 0.37 * min(1.0, diff * 2.0))
    return crop, round(float(conf), 3)


def infer_region_labels(
    series: pd.DataFrame,
    years: list[int] | None = None,
    templates: dict[str, np.ndarray] | None = None,
) -> pd.DataFrame:
    """Infer causal `(field_id, year, crop, crop_conf, crop_source)` table from NDVI series."""
    cfg = load_story()
    if years is None:
        years = sorted(int(y) for y in pd.to_datetime(series["date"]).dt.year.unique())
    rows = []
    for fid, g in series.groupby("field_id", sort=True):
        dates = g["date"].to_numpy()
        ndvi = g["ndvi"].to_numpy()
        for y in years:
            feats = season_features(dates, ndvi, y, cfg=cfg)
            crop, conf = classify_season(feats, templates=templates)
            rows.append(
                {
                    "field_id": fid,
                    "year": int(y),
                    "crop": crop,
                    "crop_conf": conf,
                    "crop_source": "classifier",
                    "peak_doy": np.nan if feats is None else round(feats["peak_doy"], 1),
                    "peak_ndvi": np.nan if feats is None else round(feats["peak_ndvi"], 3),
                }
            )
    return pd.DataFrame(rows)
