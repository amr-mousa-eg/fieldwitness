"""Reliability tiers: leakage guard, frozen tiers, ordering and bootstrap on hand-checked cases."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldwitness.agree import reliability as rl


def _series_labels():
    rows = []
    for y, n in ((2018, 12), (2019, 9), (2020, 15), (2021, 30)):
        for d in range(n):
            rows.append(
                {
                    "field_id": "f",
                    "date": pd.Timestamp(y, 3, 1) + pd.Timedelta(days=3 * d),
                    "ndvi": 0.5,
                }
            )
    rows.append({"field_id": "f", "date": pd.Timestamp(2020, 3, 1), "ndvi": 0.6})  # duplicate day
    rows.append({"field_id": "f", "date": pd.Timestamp(2020, 3, 4), "ndvi": np.nan})  # not clear
    s = pd.DataFrame(rows)
    lab = pd.DataFrame(
        {
            "field_id": "f",
            "year": [2018, 2019, 2020, 2021],
            "crop": ["maize", "sorghum", "fallow", "winter_wheat"],
        }
    )
    return s, lab


def test_n_clear_fit_hand_example():
    s, lab = _series_labels()
    # cut 2020: 2018 maize 12 (>=10), 2019 sorghum 9 (<10), 2020 fallow (not a modelled crop)
    assert rl.n_clear_fit(s, lab, "f", 2020) == 12
    assert rl.n_clear_fit(s, lab, "f", 2021) == 12 + 30


def test_features_unchanged_when_future_data_removed():
    s, lab = _series_labels()
    for cut in (2018, 2019, 2020):
        full = rl.n_clear_fit(s, lab, "f", cut)
        past = rl.n_clear_fit(s[s["date"].dt.year <= cut], lab[lab["year"] <= cut], "f", cut)
        assert full == past
    # rel_spread and grade use only the forecast and the cut-off fit/credibility
    assert rl.rel_spread([10.0, 0, 20.0, 0, 30.0]) == 1.0
    assert rl.grade_number("prior", 0.9) == 3
    assert rl.grade_number("own_crop_posterior", 0.6) == 1
    assert rl.grade_number("own_crop_posterior", None) == 2


@pytest.mark.needs_data("data/fields/ks_t14slh_hls_series.parquet")
def test_real_features_leakage_guard():
    series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    lab = pd.read_parquet("data/labels/ks_t14slh.parquet")
    for fid in sorted(series["field_id"].unique())[:5]:
        for cut in (2018, 2019, 2020, 2021):
            past = series[series["date"].dt.year <= cut]
            assert rl.n_clear_fit(series, lab, fid, cut) == rl.n_clear_fit(
                past, lab[lab["year"] <= cut], fid, cut
            )


@pytest.mark.needs_data("data/fields/ks_t14slh_hls_series.parquet")
def test_credibility_unchanged_when_future_data_removed():
    import datetime as dt
    import sys

    sys.path.insert(0, str(Path("scripts").resolve()))
    import t7_grade_validity as gv

    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").head(3)
    series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    series["year"] = series["date"].dt.year
    series["doy"] = series["date"].dt.day_of_year
    old = gv.CUT
    try:
        gv.CUT = dt.date(2019, 12, 31)
        full = gv.compute_cutoff_credibility(pilot, series)
        past = gv.compute_cutoff_credibility(pilot, series[series["year"] <= 2019])
    finally:
        gv.CUT = old
    assert full == past


@pytest.mark.needs_data("results/hindcast/reliability/credibility_cut2021.json")
def test_credibility_files_record_their_cutoff():
    for cut in (2018, 2019, 2020, 2021):
        d = json.loads(Path(f"results/hindcast/reliability/credibility_cut{cut}.json").read_text())
        assert d["cutoff"] == f"{cut}-12-31"


def test_target_field_scale():
    df = pd.DataFrame(
        {
            "field_id": ["a", "a", "b"],
            "crop": ["maize"] * 3,
            "obs_ci": [10.0, 30.0, 0.5],
            "crps_ci": [5.0, 5.0, 2.0],
        }
    )
    y = rl.add_target(df)
    assert y["scale"].tolist() == [20.0, 20.0, 1.0]  # median; floor 1
    assert y["y"].iloc[0] == pytest.approx(np.log(0.25))


def test_tiers_frozen_and_applied_unchanged():
    train_pred = np.arange(1, 101, dtype=float)
    b = rl.tier_bounds(train_pred)
    assert b == pytest.approx([25.75, 50.5, 75.25])
    frozen = list(b)
    t = rl.assign_tiers([0.0, 25.75, 26.0, 50.5, 60.0, 99.0, 1e9], b)
    assert t.tolist() == [1, 1, 2, 2, 3, 4, 4]  # ties go to the lower tier
    assert b == frozen  # assigning does not move the boundaries


def test_choose_simplest_within_one_se():
    cv = pd.DataFrame(
        {
            "model": list(rl.MODELS),
            "loss": [1.0, 0.80, 0.85, 0.90, 0.75],
            "se": [0.1, 0.1, 0.1, 0.1, 0.06],
        }
    )
    assert rl.choose(cv) == "crop"  # best 0.75 + 0.06 = 0.81 -> crop (0.80) is simplest within
    cv.loc[cv["model"] == "gbm", "se"] = 0.01
    assert rl.choose(cv) == "gbm"


def test_ordering_and_bootstrap_hand_example():
    assert (
        rl.ordered([1, 2, 3, 4])
        and not rl.ordered([1, 3, 2, 4])
        and not rl.ordered([1, None, 3, 4])
    )
    v = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0])
    t = np.array([1, 1, 2, 2, 3, 3, 4, 4])
    blocks = np.array(["a", "b"] * 4)  # each block holds one row of every tier
    out = rl.boot_tier_means(v, t, blocks)
    assert out["R1"]["mean"] == 1.0 and out["R4"]["mean"] == 4.0
    assert out["R4_minus_R1"]["mean"] == 3.0 and out["R4_minus_R1"]["ci"] == [3.0, 3.0]
    s = rl.boot_spearman(v, v, blocks, pred2=np.zeros(8))
    assert s["rho"] == pytest.approx(1.0) and s["diff"] == pytest.approx(1.0)
