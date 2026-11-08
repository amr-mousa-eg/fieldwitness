import numpy as np
import pandas as pd

from fieldwitness.neighbours.dml import SEED
from fieldwitness.neighbours.matching import (
    diagnose_matching_contrast,
    fit_matching_contrast,
    matching_contrast_list,
)


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


def test_matching_contrast_list():
    df = _synthetic(n=100)
    contrasts = matching_contrast_list(df, min_arm=15)
    assert contrasts == [("maize", "maize", "maize", "winter_wheat")]


def test_fit_matching_contrast_recovers_known_effect():
    df = _synthetic(n=300, effect=5.0)
    row, plr = fit_matching_contrast(
        df, "maize", "maize", "winter_wheat", "maize", "canopy_integral", "all"
    )
    assert plr is not None
    assert row["ci_low"] < 5.0 < row["ci_high"]
    assert row["n"] == 300
    assert row["prev2_crop"] == "maize"


def test_matching_small_arm_is_skipped():
    df = _synthetic(n=20)
    row, plr = fit_matching_contrast(
        df, "maize", "maize", "winter_wheat", "maize", "canopy_integral", "all", min_arm=15
    )
    assert plr is None
    assert np.isnan(row["effect"])
    assert row["note"] == "too few rows or blocks"


def test_diagnose_matching_unfitted():
    df = _synthetic(n=100)
    unfitted_row = {
        "crop": "maize",
        "prev2_crop": "maize",
        "treated_prev": "winter_wheat",
        "reference_prev": "maize",
        "outcome": "canopy_integral",
        "stratum": "all",
        "effect": np.nan,
    }
    diag = diagnose_matching_contrast(df, unfitted_row)
    assert not diag["show_as_evidence"]
    assert diag["n_untested"] == 4
