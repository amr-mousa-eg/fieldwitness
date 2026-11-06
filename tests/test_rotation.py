import time

import numpy as np
import pytest

from fieldwitness.physics import waterbal
from fieldwitness.physics.kc import kc_curve
from fieldwitness.physics.rotation import DAYS, SeasonSpec, simulate


def _spec(sow=120, ky=1.0, kc_mid=1.15):
    kc = kc_curve((20, 30, 40, 20), 0.3, kc_mid, 0.4)
    return SeasonSpec(kc, sow, kc_mid, ky)


def _weather(n, seed=1, rain_scale=2.0):
    rng = np.random.default_rng(seed)
    rain = rng.exponential(rain_scale, (n, DAYS)) * (rng.random((n, DAYS)) < 0.3)
    eto = np.full((n, DAYS), 4.0)
    return rain, eto


def test_matches_single_waterbal_run():
    rain, eto = _weather(2)
    spec = _spec()
    res = simulate(rain, eto, [[spec]], 100.0, 0.5)
    kc = np.full(DAYS, 0.3)
    kc[spec.sow_day : spec.sow_day + len(spec.kc)] = spec.kc
    wb = waterbal.run(rain[0], kc * eto[0], 100.0, 0.5)
    sl = slice(spec.sow_day, spec.sow_day + len(spec.kc))
    assert res["eta_mm"][0, 0, 0, 0] == pytest.approx(wb["eta"][sl].sum())
    assert res["dr_end"][0, 0, 0, 0] == pytest.approx(wb["dr"][-1])


def test_carry_over_between_seasons():
    # Dry weather: depletion left by season 1 is the start of season 2 (not reset).
    rain, eto = _weather(3, rain_scale=0.0)
    res = simulate(rain, eto, [[_spec(), _spec()]], 100.0, 0.5)
    assert res["dr_end"][0, 0, 0, 0] > 0
    assert res["eta_mm"][0, 0, 0, 1] < res["eta_mm"][0, 0, 0, 0] + 1e-9
    wet = simulate(rain + 5.0, eto, [[_spec(), _spec()]], 100.0, 0.5)
    assert wet["eta_mm"][0, 0, 0, 1] > res["eta_mm"][0, 0, 0, 1]


def test_irrigation_only_in_crop_window_and_ryi_bounds():
    rain, eto = _weather(3, rain_scale=0.0)
    seq = [_spec(), _spec(sow=150)]
    res = simulate(rain, eto, [seq], 100.0, 0.5, policy=waterbal.trigger_at_raw(0.7))
    assert (res["irr_mm"] > 0).all()
    assert (res["irr_gross_mm"] >= res["irr_mm"]).all()
    assert ((res["ryi"] >= 0) & (res["ryi"] <= 1)).all()
    rf = simulate(rain, eto, [seq], 100.0, 0.5)
    assert (res["ryi"] >= rf["ryi"]).all()


def test_bad_inputs():
    rain, eto = _weather(1)
    with pytest.raises(ValueError):
        simulate(rain, eto, [[_spec(), _spec()]], 100.0, 0.5)  # too few years
    with pytest.raises(ValueError):
        simulate(rain, eto, [[_spec(sow=300)]], 100.0, 0.5)  # window past year end


def test_benchmark_200_seq_30_draws_20_years():
    n_years, n_seas = 22, 3
    rain, eto = _weather(n_years)
    rng = np.random.default_rng(20261114)
    seqs = [
        [_spec(sow=int(rng.integers(60, 200)), ky=1.0) for _ in range(n_seas)] for _ in range(200)
    ]
    taw = rng.uniform(80, 200, 30)
    t0 = time.perf_counter()
    res = simulate(rain, eto, seqs, taw, 0.5, kc_scale=rng.uniform(0.9, 1.1, 30))
    dt = time.perf_counter() - t0
    assert res["ryi"].shape == (200, 30, 20, 3)
    assert dt < 60, f"{dt:.1f}s"
