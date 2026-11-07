import time

import numpy as np

from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.evaluate import cvar, evaluate, subsample_draws
from fieldwitness.rotate.slots import slot_spec

REGION = "ks_t14slh"


def weather(n=14, seed=3):
    rng = np.random.default_rng(seed)
    rain = rng.gamma(0.3, 4.0, (n, 365)) * (rng.random((n, 365)) < 0.3)
    eto = 1.0 + 4.0 * np.sin(np.linspace(0, np.pi, 365)) ** 2 + rng.normal(0, 0.2, (n, 365))
    return rain, np.clip(eto, 0.2, None)


def draws(n=30, budget=0.0):
    return {
        "taw_mm": np.full(n, 150.0),
        "kc_scale": np.ones(n),
        "budget_mm": np.full(n, budget),
    }


def test_cvar_tails():
    x = np.arange(1.0, 11.0)
    assert cvar(x) == 1.0 and cvar(x, upper=True) == 10.0
    assert np.isnan(cvar([np.nan]))


def test_slot_specs_from_config():
    assert slot_spec("winter_wheat", REGION).sow_day < 0
    assert slot_spec("cover_crop", REGION).kind == "cover"
    assert slot_spec("fallow", REGION).kind == "fallow"


def test_subsample_seeded():
    d = {"taw_mm": np.arange(100.0), "budget_mm": np.arange(100.0)}
    a, b = subsample_draws(d, 30), subsample_draws(d, 30)
    assert np.array_equal(a["taw_mm"], b["taw_mm"]) and len(a["taw_mm"]) == 30


def test_irrigation_helps_and_fallow_has_no_ryi():
    rain, eto = weather()
    cands = [("maize", "maize", "maize"), ("fallow", "fallow", "fallow")]
    dry = evaluate(rain, eto, cands, REGION, draws(budget=0.0))
    wet = evaluate(rain, eto, cands, REGION, draws(budget=400.0))
    assert wet["ryi"][0] >= dry["ryi"][0] and wet["irrigation_mm"][0] > 0
    assert dry["irrigation_mm"][0] == 0 and dry["ryi"][1] is None
    assert dry["cvar10_ryi"][0] <= dry["ryi"][0] + 1e-9
    assert dry["cvar10_water_mm"][0] >= dry["water_use_mm"][0] - 1e-9


def test_runtime_all_kansas_candidates():
    rain, eto = weather(24)  # 2001-2024
    cands = enumerate_candidates(REGION)
    t0 = time.time()
    out = evaluate(rain, eto, cands, REGION, draws(30, budget=200.0))
    assert time.time() - t0 < 60
    assert len(out["water_use_mm"]) == len(cands) == 36  # 61 before the non-crop constraints
    assert out["n_samples"] == 30 * (24 - 3)
