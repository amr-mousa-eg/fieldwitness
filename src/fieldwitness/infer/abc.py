"""ABC rejection for the hidden field variables (T4.3). Output tag D (model posterior).

Method (plain rejection ABC, Pritchard et al. style; no regression adjustment):
1. Reference table per weather year: N prior draws -> `forward.simulate` (daily NDVI).
2. For one field, the simulated NDVI is sampled on the field's own observation days, noise
   (sd from the HLS census) is added, and the sparse series is turned into summary statistics.
3. Distance = Euclidean on statistics standardised by the reference-table sd; the closest k
   draws are the posterior "worlds".
Statistics (same function for observed and simulated series): SOS, peak day, EOS, canopy
integral (the four in PLAN T4.3) plus peak NDVI (team addition, tag A; without it irrigation and
TAW have almost no handle). Seasonal ET is not available from satellite here, so not used.
Thresholds: SOS/EOS = first up- / last down-crossing of min + 0.5 (max - min) of the
linearly interpolated series (team choice, tag A, UNVERIFIED).
"""

import numpy as np

STATS = ("sos", "peak_day", "eos", "integral", "peak_ndvi")


def _interp_daily(doy: np.ndarray, v: np.ndarray, days: int) -> np.ndarray:
    """Linear interpolation of v (m, N) observed on sorted doy (m,) to days 1..days (edges held)."""
    t = np.arange(1, days + 1)
    if doy.size == 1:
        return np.broadcast_to(v[0], (days, v.shape[1])).copy()
    i1 = np.clip(np.searchsorted(doy, t), 1, doy.size - 1)
    i0 = i1 - 1
    w = np.clip((t - doy[i0]) / (doy[i1] - doy[i0]), 0.0, 1.0)[:, None]
    return v[i0] * (1.0 - w) + v[i1] * w


def summary_stats(doy, ndvi, days: int = 365) -> np.ndarray:
    """doy (m,) sorted unique days 1..days; ndvi (m,) or (m, N). Returns (N, 5) in STATS order."""
    v = np.asarray(ndvi, float)
    v = v[:, None] if v.ndim == 1 else v
    g = _interp_daily(np.asarray(doy), v, days)  # (days, N)
    lo, hi = g.min(0), g.max(0)
    thr = lo + 0.5 * (hi - lo)
    above = g >= thr[None, :]
    first = np.argmax(above, axis=0)
    last = days - 1 - np.argmax(above[::-1], axis=0)
    return np.stack(
        [first + 1, g.argmax(0) + 1, last + 1, (g - lo[None, :]).sum(0), hi], axis=1
    ).astype(float)


def reference_table(
    rain, eto, n: int, crop: dict, cfg: dict, seed: int, prior_cfg=None, tmax=None, tmin=None
) -> dict:
    """n prior draws simulated under one year's weather. Returns hidden (dict) and ndvi (365, n).

    tmax/tmin (deg C) are needed only when cfg["phenology_mode"] == "gdd" (Experiment 2).
    """
    from fieldwitness.infer import forward, priors

    hidden = priors.sample(n, seed=seed, cfg=prior_cfg)
    return {
        "hidden": hidden,
        "ndvi": forward.simulate(rain, eto, hidden, crop, cfg, tmax, tmin)["ndvi"],
    }


def posterior(
    obs_doy, obs_ndvi, ref: dict, noise_sd: float, k: int, rng: np.random.Generator
) -> dict:
    """Closest-k worlds for one field. Returns indices, distances, and the observed stats."""
    doy = np.asarray(obs_doy)
    sim = ref["ndvi"][doy - 1, :] + rng.normal(0.0, noise_sd, (doy.size, ref["ndvi"].shape[1]))
    s_sim = summary_stats(doy, np.clip(sim, -1.0, 1.0))
    s_obs = summary_stats(doy, obs_ndvi)[0]
    sd = s_sim.std(0)
    sd[sd == 0] = 1.0
    d = np.sqrt((((s_sim - s_obs) / sd) ** 2).sum(1))
    idx = np.argsort(d, kind="stable")[:k]
    return {"idx": idx, "dist": d[idx], "obs_stats": s_obs}


def interval_coverage(post: np.ndarray, truth: np.ndarray, level: float) -> float:
    """post (k, F) posterior draws per field, truth (F,). Share of fields with truth in the
    central `level` interval."""
    a = (1.0 - level) / 2.0
    lo, hi = np.quantile(post, [a, 1.0 - a], axis=0)
    return float(np.mean((truth >= lo) & (truth <= hi)))
