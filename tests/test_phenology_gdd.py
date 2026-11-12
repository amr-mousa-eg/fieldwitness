"""Experiment 2 tests: GDD accumulation (hand-computed), the phenology switch, and proof that
calendar mode is bit-identical to the code on main (frozen copy in tests/fixtures)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from fieldwitness.infer import forward, priors
from fieldwitness.physics import phenology

ROOT = Path(__file__).resolve().parents[1]
CROPS = ROOT / "config" / "crops.yaml"


def _ref_module():
    spec = importlib.util.spec_from_file_location(
        "forward_main_ref", ROOT / "tests" / "fixtures" / "forward_main_ref.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- GDD accumulation, hand-computed -------------------------------------------------------


def test_mf3740_examples_method2_corn():
    # MF3740 worked examples for corn (Tbase 50 F, Tupper 86 F), Method 2, in degrees F:
    # Ex.1 36/48 -> 0; Ex.2 40/70 -> (50+70)/2-50 = 10; Ex.3 72/104 -> (72+86)/2-50 = 29.
    tmax_f = np.array([48.0, 70.0, 104.0])
    tmin_f = np.array([36.0, 40.0, 72.0])
    c = np.vectorize(phenology.f_to_c)
    g = phenology.daily_gdd(c(tmax_f), c(tmin_f), "mf3740_method2", 10.0, 30.0)
    np.testing.assert_allclose(g * 9 / 5, [0.0, 10.0, 29.0], atol=1e-9)


def test_mesonet_uncapped_wheat():
    # (Tmax + Tmin)/2 - 32 F: 67/33 -> 18 F (the MT200103 example); 104/72 -> 56; 20/10 -> 0
    c = np.vectorize(phenology.f_to_c)
    g = phenology.daily_gdd(
        c(np.array([67.0, 104.0, 20.0])), c(np.array([33.0, 72.0, 10.0])), "mesonet_uncapped", 0.0
    )
    np.testing.assert_allclose(g * 9 / 5, [18.0, 56.0, 0.0], atol=1e-9)


def test_stage_ends_and_lengths_by_hand():
    gdd = np.array([0, 5, 5, 10, 10, 10, 0, 20, 20, 20], float)
    # from index 1: cumulative 5, 10, 20, 30, 40, 40, 60, 80, 100
    ends = phenology.stage_ends(gdd, 1, [10, 30, 60, 500])
    # 10 reached on day 2 (index 2), 30 on day 4, 60 on day 7, 500 never -> 9 days left
    assert ends.tolist() == [[2, 4, 7, 9]]
    assert phenology.stage_lengths(ends).tolist() == [[2, 2, 3, 2]]
    assert phenology.stage_lengths(ends, lead_days=5).tolist() == [[7, 2, 3, 2]]


def test_unit_conversion():
    assert phenology.f_to_c(50) == pytest.approx(10.0)
    assert phenology.f_to_c(86) == pytest.approx(30.0)
    np.testing.assert_allclose(phenology.gdd_f_to_c([1800.0]), [1000.0])


# ---- the switch ------------------------------------------------------------------------------


def _setup(crop_name, nominal, n=40, seed=3):
    rng = np.random.default_rng(seed)
    span = 730 if nominal < 0 else 365
    t = np.arange(span)
    tmean = 12 - 14 * np.cos(2 * np.pi * (t - 15) / 365)  # smooth Kansas-like annual cycle
    tmax, tmin = tmean + 7, tmean - 7
    rain = rng.gamma(0.3, 5.0, span)
    eto = 3 + 2 * np.sin(2 * np.pi * (t - 100) / 365)
    cfg = {**forward.load_cfg(), "crop": crop_name, "nominal_sow_doy": {crop_name: nominal}}
    crop = forward.crop_params(crop_name, "ks_t14slh", CROPS)
    hidden = priors.sample(n, seed=seed)
    return rain, eto, tmax, tmin, hidden, crop, cfg


def test_gdd_mode_changes_stages_and_needs_temperatures():
    rain, eto, tmax, tmin, hid, crop, cfg = _setup("maize", 105)
    cal = forward.simulate(rain, eto, hid, crop, cfg)
    gdd = forward.simulate(rain, eto, hid, crop, {**cfg, "phenology_mode": "gdd"}, tmax, tmin)
    assert gdd["ndvi"].shape == cal["ndvi"].shape
    assert not np.array_equal(gdd["ndvi"], cal["ndvi"])
    with pytest.raises(ValueError, match="tmax"):
        forward.simulate(rain, eto, hid, crop, {**cfg, "phenology_mode": "gdd"})


def test_gdd_wheat_counts_from_jan1_and_warm_spring_is_earlier():
    rain, eto, tmax, tmin, hid, crop, cfg = _setup("winter_wheat", -78)
    sow = (-78 + np.rint(hid["sow_offset_days"]).astype(int)) + 365
    st = forward.gdd_stages(tmax, tmin, sow, 365, crop, 730)
    st_warm = forward.gdd_stages(tmax + 3, tmin + 3, sow, 365, crop, 730)
    # initial stage = sowing to 31 Dec plus the days to 600 F GDD after 1 Jan
    assert (st[:, 0] > 365 - sow).all()
    # the same sowing date reaches every later stage end sooner in a warmer spring
    assert (st_warm.cumsum(1)[:, 1:] <= st.cumsum(1)[:, 1:]).all()
    assert (st_warm.sum(1) < st.sum(1)).all()
    # winter temperatures before 1 Jan do not move any stage end
    cold_fall = tmax.copy(), tmin.copy()
    cold_fall[0][:365] -= 10
    cold_fall[1][:365] -= 10
    np.testing.assert_array_equal(forward.gdd_stages(*cold_fall, sow, 365, crop, 730), st)


def test_crop_without_cited_gdd_is_rejected():
    crop = forward.crop_params("maize", "ks_t14slh", CROPS)
    crop["gdd"] = None
    with pytest.raises(ValueError, match="no cited|cited gdd"):
        forward.gdd_stages(np.zeros(365), np.zeros(365), np.array([100]), 0, crop, 365)


# ---- calendar mode is bit-identical to main -------------------------------------------------


@pytest.mark.parametrize(
    ("crop_name", "nominal"), [("maize", 105), ("sorghum", 152), ("winter_wheat", -78)]
)
def test_calendar_mode_bit_identical_to_main(crop_name, nominal):
    ref = _ref_module()
    rain, eto, tmax, tmin, hid, crop, cfg = _setup(crop_name, nominal, n=60)
    old_crop = {k: v for k, v in crop.items() if k != "gdd"}
    old = ref.simulate(rain, eto, hid, old_crop, cfg)
    for c in (cfg, {**cfg, "phenology_mode": "calendar"}):
        new = forward.simulate(rain, eto, hid, crop, c)
        for key in ("ndvi", "eta_mm", "sow_day"):
            assert np.array_equal(new[key], old[key]), key
            assert new[key].dtype == old[key].dtype
    # unused temperatures do not change calendar output
    new = forward.simulate(rain, eto, hid, crop, cfg, tmax, tmin)
    assert np.array_equal(new["ndvi"], old["ndvi"])


def test_season_weather_unchanged_for_pairs_and_handles_four_arrays():
    ref = _ref_module()
    cfg = {"crop": "winter_wheat", "nominal_sow_doy": {"winter_wheat": -78}}
    a = tuple(np.arange(365.0) + k for k in range(4))
    b = tuple(np.arange(365.0) * 2 + k for k in range(4))
    old = ref.season_weather({2020: a[:2], 2021: b[:2]}, 2021, cfg)
    new = forward.season_weather({2020: a[:2], 2021: b[:2]}, 2021, cfg)
    assert len(new) == 2 and all(np.array_equal(x, y) for x, y in zip(new, old, strict=True))
    four = forward.season_weather({2020: a, 2021: b}, 2021, cfg)
    assert len(four) == 4 and four[3].shape == (730,)
