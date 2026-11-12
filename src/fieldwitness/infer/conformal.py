"""Split-conformal recalibration of the stored prediction intervals (experiment, branch only).

Pre-registered in DECISIONS.md (2026-11-12, "conformal recalibration of the prediction
intervals"). Not used by packs or the app. Output tag D (model statistics).

Score per field-season: s = |y - q50| / h, with h = (q95 - q5) / 2 (half-width of the stored
90 % interval). Multiplier at level L: the k-th smallest calibration score, k = ceil((n + 1) L)
(split conformal, finite-sample rule; Lei et al. 2018, JASA 113:1094-1111, Sec. 2.2).
Calibrated interval: q50 +/- m_L * h. The median (point prediction) is never changed. Groups
with fewer than MIN_CAL scores are not calibrated.
"""

import math

import numpy as np
import pandas as pd

MIN_CAL = 30


def scores(y, q5, q50, q95) -> tuple[np.ndarray, np.ndarray]:
    """Nonconformity scores and half-widths; s is NaN where h == 0 (excluded, counted)."""
    y, q5, q50, q95 = (np.asarray(a, float) for a in (y, q5, q50, q95))
    h = (q95 - q5) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(h > 0, np.abs(y - q50) / h, np.nan)
    return s, h


def conformal_multiplier(s, level: float, min_n: int = MIN_CAL) -> float | None:
    """k-th smallest finite score, k = ceil((n + 1) * level); None if n < min_n or k > n."""
    v = np.sort(np.asarray(s, float)[np.isfinite(np.asarray(s, float))])
    n = len(v)
    if n < min_n:
        return None
    k = math.ceil((n + 1) * level - 1e-12)
    return float(v[k - 1]) if k <= n else None


def mondrian(cal: pd.DataFrame, by: list[str], level: float) -> dict:
    """Pooled multiplier per group (e.g. crop x run type): {group key: (m or None, n)}."""
    out = {}
    for key, g in cal.groupby(by):
        n = int(np.isfinite(g["s"]).sum())
        out[key] = (conformal_multiplier(g["s"], level), n)
    return out


def leave_block_out(cal: pd.DataFrame, by: list[str], level: float, blocks) -> dict:
    """Block-aware multiplier: {(group key, block): (m or None, n)} computed with that block's
    calibration scores removed. `blocks` lists the blocks needed (for example the test blocks)."""
    out = {}
    for key, g in cal.groupby(by):
        for b in blocks:
            rest = g.loc[g["block"] != b, "s"]
            out[(key, b)] = (conformal_multiplier(rest, level), int(np.isfinite(rest).sum()))
    return out


def interval(q50, h, m) -> tuple[np.ndarray, np.ndarray]:
    """Calibrated interval q50 +/- m h. The inputs are not modified."""
    q50, h, m = (np.asarray(a, float) for a in (q50, h, m))
    return q50 - m * h, q50 + m * h


def winkler(lo, hi, y, alpha: float) -> np.ndarray:
    """Interval score (Gneiting and Raftery 2007, JASA 102:359-378, Eq. 43)."""
    lo, hi, y = (np.asarray(a, float) for a in (lo, hi, y))
    return (
        (hi - lo)
        + (2.0 / alpha) * np.maximum(lo - y, 0.0)
        + (2.0 / alpha) * np.maximum(y - hi, 0.0)
    )
