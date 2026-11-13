"""Unit tests for independent NASA SMAP, GPM IMERG, ECOSTRESS ETa, and Kansas WIMAS checks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fieldwitness.validate.eo_checks import (
    evaluate_ecostress_eta,
    evaluate_extreme_rain_agreement,
    evaluate_smap_soil_moisture,
    evaluate_wimas_irrigation,
)


def test_smap_monthly_correlation_recovers_seasonal_signal():
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    signal = 0.5 + 0.3 * np.sin(2 * np.pi * dates.dayofyear.to_numpy() / 365.25)
    sim = pd.DataFrame({"date": dates, "dr_mm": (1.0 - signal) * 200.0, "taw_mm": 200.0})
    smap = pd.DataFrame({"date": dates, "sm_rootzone": 0.15 + 0.2 * signal})

    res = evaluate_smap_soil_moisture(sim, smap)
    assert res["n_months"] == 48
    assert res["too_few_to_judge"] is False
    assert res["pearson_r"] > 0.99
    assert res["tag"] == "D"


def test_gpm_imerg_extreme_rain_metrics():
    dates = pd.date_range("2022-01-01", periods=30, freq="D")
    imerg_rain = np.zeros(30)
    power_rain = np.zeros(30)
    imerg_rain[[2, 5, 10]] = [30.0, 42.0, 28.0]
    power_rain[[2, 5, 15]] = [31.0, 39.0, 27.0]

    res = evaluate_extreme_rain_agreement(
        pd.DataFrame({"date": dates, "rain_mm": power_rain}),
        pd.DataFrame({"date": dates, "rain_mm": imerg_rain}),
        threshold_mm=25.0,
    )
    assert res["n_days"] == 30
    assert res["hits"] == 2
    assert res["misses"] == 1
    assert res["false_alarms"] == 1
    assert res["csi"] == pytest.approx(0.5)


def test_ecostress_eta_filters_bad_qc_and_computes_bias():
    sim = pd.DataFrame(
        {
            "field_id": ["f1", "f1", "f1"],
            "date": ["2023-06-10", "2023-06-18", "2023-06-25"],
            "eta_mm": [4.5, 5.2, 3.8],
        }
    )
    eco = pd.DataFrame(
        {
            "field_id": ["f1", "f1", "f1"],
            "date": ["2023-06-10", "2023-06-18", "2023-06-25"],
            "eta_mm": [4.0, 9.9, 3.6],
            "qc_good": [True, False, True],
        }
    )
    res = evaluate_ecostress_eta(sim, eco)
    assert res["n_overpasses"] == 2
    assert res["bias_mm_day"] == pytest.approx(0.35, abs=1e-3)
    assert res["too_few_to_judge"] is True


def test_wimas_irrigation_converts_acre_feet_and_scores_r2():
    sim = pd.DataFrame(
        {
            "field_id": ["f1", "f2", "f3"],
            "year": [2022, 2022, 2022],
            "irrigation_mm": [200.0, 300.0, 100.0],
        }
    )
    # 10 ha = 100,000 m2; 200 mm = 20,000 m3 ~ 16.2143 acre-feet
    af_factor = 100_000.0 / 1000.0 / 1233.48183754752
    wimas = pd.DataFrame(
        {
            "field_id": ["f1", "f2", "f3"],
            "year": [2022, 2022, 2022],
            "af_used": [195.0 * af_factor, 290.0 * af_factor, 110.0 * af_factor],
            "area_ha": [10.0, 10.0, 10.0],
        }
    )
    res = evaluate_wimas_irrigation(sim, wimas)
    assert res["n_field_years"] == 3
    assert res["r2"] > 0.98
    assert res["mae_mm"] == pytest.approx(8.33, abs=0.1)
