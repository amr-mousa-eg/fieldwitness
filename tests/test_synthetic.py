from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldwitness.infer import forward, priors, synthetic

CFG = forward.load_cfg()
CROP = forward.crop_params(CFG["crop"], CFG["region"])


def _wx(seed=0):
    rng = np.random.default_rng(seed)
    rain = np.where(rng.random(365) < 0.2, rng.gamma(2.0, 4.0, 365), 0.0)
    eto = 3.0 + 3.0 * np.sin(np.linspace(-1.2, 4.3, 365)).clip(0)
    return rain, eto


def _hidden(**kw):
    h = {
        "sow_offset_days": np.array([0.0]),
        "taw_scale": np.array([1.0]),
        "irrigated": np.array([False]),
        "irrigation_mm": np.array([0.0]),
        "kc_mid_scale": np.array([1.0]),
    }
    h.update({k: np.atleast_1d(v) for k, v in kw.items()})
    n = max(len(v) for v in h.values())
    return {k: np.repeat(v, n) if len(v) == 1 else v for k, v in h.items()}


def test_canopy_shape_and_bounds():
    r = forward.simulate(np.full(365, 10.0), _wx()[1], _hidden(), CROP, CFG)  # wet: no stress
    nd = r["ndvi"][:, 0]
    assert nd.min() >= CFG["ndvi_bare"] - 1e-9 and nd.max() <= CFG["ndvi_peak"] + 1e-9
    assert nd[:100].max() == pytest.approx(CFG["ndvi_bare"])  # bare before sowing (day 105)
    peak = int(np.argmax(nd))
    sow = CFG["nominal_sow_doy"]["maize"]
    ini, dev, mid, _ = CROP["stages"]
    assert sow + ini + dev - 1 <= peak <= sow + ini + dev + mid


def test_sow_offset_shifts_season():
    r = forward.simulate(*_wx(), _hidden(sow_offset_days=[-10, 10]), CROP, CFG)
    assert r["sow_day"][1] - r["sow_day"][0] == 20
    assert np.argmax(r["ndvi"][:, 1]) > np.argmax(r["ndvi"][:, 0])


def test_irrigation_helps_in_dry_year():
    rain, eto = _wx()
    dry = np.zeros(365)
    h = _hidden(
        irrigated=[False, True],
        irrigation_mm=[0, 400],
        taw_scale=[0.5, 0.5],
        sow_offset_days=[0, 0],
        kc_mid_scale=[1, 1],
    )
    r = forward.simulate(dry, eto, h, CROP, CFG)
    assert r["eta_mm"][1] > r["eta_mm"][0]
    assert r["ndvi"].max(0)[1] > r["ndvi"].max(0)[0]


def test_bad_inputs():
    with pytest.raises(ValueError):
        forward.simulate(np.zeros(10), np.zeros(10), _hidden(), CROP, CFG)
    with pytest.raises(ValueError):
        forward.simulate(*_wx(), _hidden(sow_offset_days=[200]), CROP, CFG)


def _series():
    rng = np.random.default_rng(3)
    rows = []
    for f in range(4):
        days = np.sort(rng.choice(np.arange(1, 360), 40, replace=False))
        for d in days:
            rows.append((f"f{f}", pd.Timestamp("2020-01-01") + pd.Timedelta(days=int(d) - 1)))
    df = pd.DataFrame(rows, columns=["field_id", "date"])
    df["ndvi"] = 0.5 + rng.normal(0, 0.03, len(df))
    return df


def test_census_noise_recovers_known_sd():
    c = synthetic.census(_series())
    assert c["n_templates"] == 4
    assert c["noise_sd"] == pytest.approx(0.03, rel=0.35)


def test_make_fields_seeded_and_shapes():
    cen = synthetic.census(_series())
    wx = {2020: _wx(1), 2021: _wx(2)}
    a = synthetic.make_fields(20, cen, wx, seed=5)
    b = synthetic.make_fields(20, cen, wx, seed=5)
    c = synthetic.make_fields(20, cen, wx, seed=6)
    assert np.array_equal(a["true_ndvi"], b["true_ndvi"])
    assert not np.array_equal(a["true_ndvi"], c["true_ndvi"])
    assert a["true_ndvi"].shape == (365, 20) and len(a["obs_doy"]) == 20
    for d, v in zip(a["obs_doy"], a["obs_ndvi"], strict=True):
        assert len(d) == len(v) >= synthetic.MIN_OBS and d.min() >= 1 and d.max() <= 365
    assert set(a["truth"]) == set(priors.VARIABLES)


def test_observations_follow_truth_within_noise():
    cen = {"gap_templates": [np.arange(1, 366, 5)], "noise_sd": 0.02}
    f = synthetic.make_fields(10, cen, {2020: _wx(1)}, seed=2)
    res = np.concatenate(
        [
            v - f["true_ndvi"][d - 1, j]
            for j, (d, v) in enumerate(zip(f["obs_doy"], f["obs_ndvi"], strict=True))
        ]
    )
    assert abs(res.mean()) < 0.01 and res.std() == pytest.approx(0.02, rel=0.2)


@pytest.mark.skipif(
    not Path("data/fields/ks_t14slh_hls_series.parquet").exists(), reason="HLS series not on disk"
)
def test_real_census_smoke():
    s = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    c = synthetic.census(s)
    assert c["n_templates"] > 100 and 0.0 < c["noise_sd"] < 0.2
