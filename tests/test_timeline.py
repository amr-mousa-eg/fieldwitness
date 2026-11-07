import time

import numpy as np
import pytest

from fieldwitness.physics import waterbal
from fieldwitness.physics.kc import kc_curve
from fieldwitness.physics.rotation import DAYS, SlotSpec, fallow_slot, simulate_timeline


def crop(sow, stages=(20, 30, 40, 20), kc_mid=1.15, ky=1.0, p=0.5):
    return SlotSpec("crop", kc_curve(stages, 0.3, kc_mid, 0.4), sow, kc_mid, ky, p)


def cover(stages=(20, 25, 60, 30)):
    return SlotSpec("cover", kc_curve(stages, 0.3, 1.15, 0.25), None, 1.15, None, 0.55)


def weather(n, rain_scale=2.0, seed=1):
    rng = np.random.default_rng(seed)
    rain = rng.exponential(rain_scale, (n, DAYS)) * (rng.random((n, DAYS)) < 0.3)
    return rain, np.full((n, DAYS), 4.0)


def test_winter_crop_spans_new_year_and_matches_direct_run():
    rain, eto = weather(3)
    wheat = crop(-92, stages=(160, 75, 75, 25), kc_mid=1.15)  # sown 1 Oct, harvest ~end Aug
    res = simulate_timeline(rain, eto, [[wheat]], 100.0, kc_fallow=0.3, p_fallow=0.5)
    a = DAYS - 92
    assert res["slot_start"][0, 0] == a
    kc = np.full(2 * DAYS, 0.3)
    kc[a : a + len(wheat.kc)] = wheat.kc
    r = rain[:2].reshape(-1)
    e = eto[:2].reshape(-1)
    wb = waterbal.run(r, kc * e, 100.0, 0.5)
    sl = slice(a, a + len(wheat.kc))
    assert res["eta_mm"][0, 0, 0, 0] == pytest.approx(wb["eta"][sl].sum())
    assert res["dr_final"][0, 0, 0] == pytest.approx(wb["dr"][-1])
    # the season crosses New Year: part of its ETa is in timeline year 0
    assert wb["eta"][a:DAYS].sum() > 0


def test_dr_carried_across_new_year_in_dry_weather():
    rain, eto = weather(4, rain_scale=0.0)
    res = simulate_timeline(rain, eto, [[crop(100), crop(100)]], 100.0)
    assert res["dr_final"][0, 0, 0] > 0
    assert res["eta_mm"][0, 0, 0, 1] < res["eta_mm"][0, 0, 0, 0] + 1e-9


def test_cover_fills_gap_and_is_capped():
    rain, eto = weather(4)
    first, last = crop(60), crop(120)  # first crop: 110 days
    res = simulate_timeline(rain, eto, [[first, cover(), last]], 100.0, kc_fallow=0.0)
    assert res["slot_start"][0, 1] == DAYS + 60 + 110  # starts the day crop 1 ends
    kc_cov = kc_curve((20, 25, 60, 30), 0.3, 1.15, 0.25)
    assert res["etc_mm"][0, 0, 0, 1] == pytest.approx(kc_cov.sum() * 4.0)  # capped at 135 d
    assert np.isnan(res["ryi"][0, 0, 0, 1])
    # next crop starts 40 days after crop 1 ends: cover is cut there
    near = crop(-(2 * DAYS - 170 - 40))
    cut = simulate_timeline(rain, eto, [[first, cover(), near]], 100.0, kc_fallow=0.0)
    assert cut["etc_mm"][0, 0, 0, 1] == pytest.approx(kc_cov[:40].sum() * 4.0)


def test_overlap_cuts_earlier_crop():
    rain, eto = weather(4)
    a = crop(250, stages=(40, 40, 60, 40))  # 180 days from day 250 runs past New Year
    b = crop(-92, stages=(160, 75, 75, 25))  # winter crop sown 1 Oct of the same year
    res = simulate_timeline(rain, eto, [[a, b]], 100.0, kc_fallow=0.0)
    full = len(a.kc)
    kept = DAYS * 2 - 92 - (DAYS + 250)
    assert kept < full
    assert res["etc_mm"][0, 0, 0, 0] == pytest.approx(a.kc[:kept].sum() * 4.0)


def test_p_per_crop_changes_stress():
    rain, eto = weather(3, rain_scale=0.0)
    lo, hi = crop(100, p=0.2), crop(100, p=0.8)
    res = simulate_timeline(rain, eto, [[lo], [hi]], 80.0)
    assert res["eta_mm"][0, 0, 0, 0] < res["eta_mm"][1, 0, 0, 0]


def test_fixed_budget_per_draw_and_refill_each_season():
    rain, eto = weather(4, rain_scale=0.0)
    pol = waterbal.fixed_seasonal_mm(np.array([0.0, 60.0, 120.0]))
    res = simulate_timeline(rain, eto, [[crop(100), crop(100)]], np.full(3, 100.0), policy=pol)
    irr = res["irr_mm"][0, :, 0, :]
    assert irr[0].sum() == 0
    assert np.all(irr[1] <= 60.0 + 1e-9) and np.all(irr[2] <= 120.0 + 1e-9)
    assert np.all(irr[1] > 0)  # budget refilled for the second season
    assert irr[2, 0] > irr[1, 0]
    fallow_irr = simulate_timeline(
        rain, eto, [[fallow_slot(), crop(100)]], 100.0, policy=waterbal.fixed_seasonal_mm(60.0)
    )
    assert fallow_irr["irr_mm"][0, 0, 0, 0] == 0.0  # fallow slot owns no days


def test_bad_inputs():
    rain, eto = weather(3)
    with pytest.raises(ValueError):
        simulate_timeline(rain, eto, [[crop(100)] * 3], 100.0)  # needs >= 4 weather years
    with pytest.raises(ValueError):
        simulate_timeline(rain, eto, [[crop(-DAYS - 5)]], 100.0)  # leaves timeline


def test_runtime_all_candidates_one_field():
    rain, eto = weather(24)
    pool = [
        crop(100),
        crop(150, ky=0.9),
        crop(-92, stages=(160, 75, 75, 25), ky=1.05),
        fallow_slot(),
    ]
    opts = [[a, b, c] for a in pool for b in pool + [cover()] for c in pool]
    t0 = time.time()
    res = simulate_timeline(rain, eto, opts, np.linspace(80, 200, 30), kc_scale=np.ones(30))
    assert time.time() - t0 < 60
    assert res["eta_year_mm"].shape == (len(opts), 30, 21, 3)
    assert np.isfinite(res["eta_year_mm"]).all()
