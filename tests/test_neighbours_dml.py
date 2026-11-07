import numpy as np
import pandas as pd

from fieldwitness.neighbours.dml import SEED, contrast_list, fit_contrast


def _synthetic(n=300, effect=5.0):
    rng = np.random.default_rng(SEED)
    df = pd.DataFrame(
        {
            "crop": "maize",
            "year": rng.integers(2018, 2025, n),
            "area_ha": rng.uniform(10, 80, n),
            "lon": rng.uniform(-100.9, -100.5, n),
            "lat": rng.uniform(38.6, 39.0, n),
            "clay_pct": rng.uniform(15, 35, n),
            "sand_pct": rng.uniform(10, 40, n),
            "soc_g_kg": rng.uniform(8, 20, n),
            "season_precip_mm": rng.uniform(300, 700, n),
            "season_tmax_c": rng.uniform(24, 30, n),
            "prev2_crop": "maize",
            "dry_season": rng.random(n) < 0.5,
        }
    )
    df["block"] = (df["lon"] * 10).round().astype(int).astype(str) + (
        df["lat"] * 10
    ).round().astype(int).astype(str)
    treated = rng.random(n) < 0.5
    df["prev_crop"] = np.where(treated, "winter_wheat", "maize")
    df["canopy_integral"] = effect * treated + 0.05 * df["season_precip_mm"] + rng.normal(0, 1, n)
    return df


def test_recovers_known_effect():
    df = _synthetic()
    row = fit_contrast(df, "maize", "winter_wheat", "maize", "canopy_integral", "all")
    assert row["ci_low"] < 5.0 < row["ci_high"]
    assert row["n"] == 300


def test_small_arm_is_skipped():
    df = _synthetic(n=40)
    row = fit_contrast(df, "maize", "winter_wheat", "maize", "canopy_integral", "all")
    assert np.isnan(row["effect"]) and row["note"]


def test_contrast_list_needs_both_arms():
    df = _synthetic()
    assert contrast_list(df) == [("maize", "maize", "winter_wheat")]
