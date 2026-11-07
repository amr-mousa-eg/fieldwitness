"""Evaluate candidate rotations (PLAN T6.2). Output tag: D (model on satellite-calibrated draws).

One batched call of `physics.rotation.simulate_timeline` over posterior worlds x weather start
years. A "world" is one posterior draw: TAW (mm), Kc scale, seasonal irrigation budget (mm; 0 =
rainfed). Samples = worlds x start years; metrics are taken over all samples of an option:
- water_use_mm: ETa of the S timeline years 1..S (crops, cover, bare soil), summed over years;
- irrigation_mm: net irrigation applied in those years, summed;
- ryi: mean Relative Yield Index over the slots that have one (crops with a Ky); NaN if none;
- cover_days: days with canopy proxy >= `cover_frac` over the S years (same in every sample);
- cvar10_water_mm: mean of the highest 10 % of water-use samples; cvar10_ryi: mean of the lowest
  10 % of RYI samples (tail = bad outcome; CVaR level 0.10, PLAN T6.2).
Weather years: pass only years up to the cut-off (use `power.read`, which honours `as_of`).
"""

import numpy as np

from fieldwitness.physics import waterbal
from fieldwitness.physics.rotation import simulate_timeline
from fieldwitness.rotate.slots import option_slots

SEED = 20261114
N_WORLDS = 30
CVAR_LEVEL = 0.10


def subsample_draws(draws: dict, n: int = N_WORLDS, seed: int = SEED) -> dict:
    """Seeded subsample (without replacement when possible) of equal-length draw arrays."""
    m = len(draws["taw_mm"])
    idx = np.random.default_rng(seed).choice(m, size=n, replace=m < n)
    return {k: np.asarray(v)[idx] for k, v in draws.items()}


def cvar(x: np.ndarray, level: float = CVAR_LEVEL, upper: bool = False) -> float:
    """Mean of the worst `level` share of x (lowest values, or highest if upper). NaN-safe."""
    x = np.asarray(x, float).ravel()
    x = x[~np.isnan(x)]
    if x.size == 0:
        return float("nan")
    k = max(1, int(np.ceil(level * x.size)))
    s = np.sort(x)
    return float(s[-k:].mean() if upper else s[:k].mean())


def evaluate(rain, eto, candidates, region_id: str, draws: dict, cover_frac: float = 0.5) -> dict:
    """Metrics per candidate. rain, eto: (n_years, 365); candidates: tuples of crop keys;
    draws: taw_mm, kc_scale, budget_mm (equal length). Returns dict of lists + tag "D"."""
    options = [option_slots(c, region_id) for c in candidates]
    policy = waterbal.fixed_seasonal_mm(np.asarray(draws["budget_mm"], float))
    r = simulate_timeline(
        rain,
        eto,
        options,
        draws["taw_mm"],
        policy=policy,
        kc_scale=draws["kc_scale"],
        cover_frac=cover_frac,
    )
    n = len(candidates)
    water = r["eta_year_mm"].sum(-1).reshape(n, -1)
    irr = r["irr_year_mm"].sum(-1).reshape(n, -1)
    ok = ~np.isnan(r["ryi"])
    cnt = ok.sum(-1)
    tot = np.where(ok, r["ryi"], 0.0).sum(-1)
    ryi = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan).reshape(n, -1)  # NaN: no slot RYI
    return {
        "candidates": [list(c) for c in candidates],
        "water_use_mm": water.mean(1).tolist(),
        "irrigation_mm": irr.mean(1).tolist(),
        "ryi": [float(np.nanmean(x)) if not np.all(np.isnan(x)) else None for x in ryi],
        "cover_days": r["cover_days"].sum(-1).astype(int).tolist(),
        "cvar10_water_mm": [cvar(x, upper=True) for x in water],
        "cvar10_ryi": [None if np.all(np.isnan(x)) else cvar(x) for x in ryi],
        # per weather start year, mean over worlds (axis 1); feeds the T6.3 regret matrix
        "ryi_by_year": [
            None if np.all(np.isnan(x)) else np.nanmean(x, axis=0).round(4).tolist()
            for x in ryi.reshape(n, len(draws["taw_mm"]), -1)
        ],
        "water_by_year": water.reshape(n, len(draws["taw_mm"]), -1).mean(1).round(1).tolist(),
        "p_by_slot": [[s.p for s in o] for o in options],
        "n_samples": int(water.shape[1]),
        "tag": "D",
    }
