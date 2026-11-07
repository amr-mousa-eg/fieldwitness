import numpy as np
import pandas as pd

from fieldwitness.neighbours.diagnostics import add_lags, balance_smd, run_diagnostics


def test_balance_smd_detects_shift_and_weights_fix_it():
    rng = np.random.default_rng(1)
    d = np.r_[np.ones(200), np.zeros(200)]
    v = np.r_[rng.normal(1.0, 1, 200), rng.normal(0.0, 1, 200)]
    x = pd.DataFrame({"v": v})
    assert balance_smd(x, d) > 0.7
    w = np.where(d == 1, np.exp(-v), np.exp(v))  # down-weights the extremes, shrinks the gap
    assert balance_smd(x, d, w) < balance_smd(x, d)


def test_add_lags_uses_same_field_and_exact_year_offsets():
    df = pd.DataFrame(
        {
            "field_id": ["a", "a", "a", "b"],
            "year": [2018, 2019, 2020, 2019],
            "crop": ["maize", "sorghum", "winter_wheat", "maize"],
            "canopy_integral": [1.0, 2.0, 3.0, 9.0],
            "peak_ndvi": [0.1, 0.2, 0.3, 0.9],
            "cover_days": [10, 20, 30, 90],
            "canopy_drop": [0.0, 0.1, 0.2, 0.3],
        }
    )
    out = add_lags(df)
    assert out.loc[0, "next_crop"] == "sorghum"
    assert pd.isna(out.loc[2, "next_crop"])  # no 2021 row
    assert out.loc[2, "canopy_integral_lag2"] == 1.0  # 2020 -> 2018, field a
    assert pd.isna(out.loc[3, "canopy_integral_lag2"])  # field b has no 2017


def test_unfitted_rows_are_never_evidence():
    eff = pd.DataFrame(
        {
            "crop": ["maize"],
            "treated_prev": ["a"],
            "reference_prev": ["b"],
            "outcome": ["peak_ndvi"],
            "stratum": ["all"],
            "effect": [np.nan],
            "ci_low": [np.nan],
            "ci_high": [np.nan],
        }
    )
    df = pd.DataFrame(
        {
            "field_id": ["a"],
            "year": [2019],
            "crop": ["maize"],
            "canopy_integral": [1.0],
            "peak_ndvi": [0.1],
            "cover_days": [10],
            "canopy_drop": [0.0],
        }
    )
    res = run_diagnostics(df, eff)
    assert not res.loc[0, "show_as_evidence"]
    assert res.loc[0, "n_untested"] == 4
