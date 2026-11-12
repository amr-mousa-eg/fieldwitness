"""Thermal-time (GDD) stage lengths for the FAO-56 Kc curve (Experiment 2). Output tag D.

Pre-registered in DECISIONS.md (2026-11-12). Used only when `phenology_mode == "gdd"`; the
calendar mode never calls this module.

Daily GDD (degrees C here; source values in degrees F are converted exactly):
- `mf3740_method2`: K-State Extension MF3740 (Soni et al. 2026), Table 2, Method 2: limit Tmin and
  Tmax to [T_lower, T_upper], average them, subtract T_base (= T_lower), set negatives to zero.
- `mesonet_uncapped`: Kansas Mesonet wheat tool: (Tmax + Tmin) / 2 - 32 F, negatives set to 0.
Stage ends: the first day on which the GDD summed from the count start reaches the cited stage
GDD (config/crops.yaml `gdd_phenology`). A stage end that is never reached inside the weather
span is cut at the end of the span (later stages then have length 0).
"""

import numpy as np


def f_to_c(t_f: float) -> float:
    """Temperature degrees F -> degrees C."""
    return (float(t_f) - 32.0) * 5.0 / 9.0


def gdd_f_to_c(g_f) -> np.ndarray:
    """Degree-days F -> degree-days C (a difference: factor 5/9, no offset)."""
    return np.asarray(g_f, float) * 5.0 / 9.0


def daily_gdd(tmax, tmin, method: str, t_base_c: float, t_upper_c: float | None = None):
    """Daily GDD (degree C days) from daily Tmax/Tmin (degrees C)."""
    tmax = np.asarray(tmax, float)
    tmin = np.asarray(tmin, float)
    if method == "mf3740_method2":
        hi = np.clip(tmax, t_base_c, t_upper_c)
        lo = np.clip(tmin, t_base_c, t_upper_c)
        return np.maximum(0.0, (hi + lo) / 2.0 - t_base_c)
    if method == "mesonet_uncapped":
        return np.maximum(0.0, (tmax + tmin) / 2.0 - t_base_c)
    raise ValueError(f"unknown GDD method {method}")


def stage_ends(gdd, start, thresholds_c) -> np.ndarray:
    """Days from `start` (inclusive) until each cumulative threshold is reached.

    gdd: daily GDD over the span; start: int or (n,) start indices; thresholds_c: 4 increasing
    cumulative GDD. Returns (n, 4) counts of days E (stage end = start + E - 1). Not reached:
    E = span - start.
    """
    g = np.asarray(gdd, float)
    c = np.cumsum(g)
    s = np.atleast_1d(np.asarray(start, int))
    base = np.where(s > 0, c[np.maximum(s - 1, 0)], 0.0)
    target = base[:, None] + np.asarray(thresholds_c, float)[None, :]
    idx = np.searchsorted(c, target, side="left")  # first day with cumulative >= target
    return np.minimum(idx, len(g)) - s[:, None] + np.where(idx < len(g), 1, 0)


def stage_lengths(ends: np.ndarray, lead_days=0) -> np.ndarray:
    """(n, 4) stage-end day counts -> (n, 4) FAO-56 stage lengths.

    lead_days (int or (n,)) is added to the initial stage (winter wheat: sowing to 1 Jan).
    """
    e = np.asarray(ends, int)
    e = np.maximum.accumulate(e, axis=1)
    out = np.diff(np.concatenate([np.zeros((len(e), 1), int), e], axis=1), axis=1)
    out[:, 0] += np.asarray(lead_days, int)
    return out
