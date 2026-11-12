"""Bias diagnosis and per-crop centre recalibration (experiment; pre-registered in DECISIONS.md,
2026-11-12 "[claude-code] PRE-REGISTRATION: bias diagnosis"). Not used by the pipeline or the app.

All functions are pure. Signed error = predicted median - observed. Quantile levels are the ones
stored by `scripts/t71_hindcast.py` (QS = 0.05, 0.25, 0.5, 0.75, 0.95).
"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

QS = np.array([0.05, 0.25, 0.5, 0.75, 0.95])
SEED = 20261114


def pinball_crps(q: np.ndarray, y: float, levels: np.ndarray = QS) -> float:
    """CRPS approximated as 2 x mean pinball loss over the stored quantile levels.

    CRPS = 2 * integral_0^1 pinball_tau(q_tau, y) d tau (quantile-score form of the CRPS;
    UNVERIFIED: reference not opened in this session); here the integral is replaced by the
    mean over the five stored levels, so it is an approximation used identically before and
    after correction.
    """
    q = np.asarray(q, float)
    d = y - q
    loss = np.maximum(levels * d, (levels - 1.0) * d)
    return float(2.0 * loss.mean())


def block_bootstrap(
    values: np.ndarray, blocks: np.ndarray, stat=np.median, n_boot: int = 1000, seed: int = SEED
) -> tuple[float, float, float]:
    """Statistic and 95% CI by resampling whole spatial blocks with replacement."""
    values = np.asarray(values, float)
    blocks = np.asarray(blocks)
    ids = np.unique(blocks)
    groups = [values[blocks == b] for b in ids]
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        boots[i] = stat(np.concatenate([groups[j] for j in pick]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(stat(values)), float(lo), float(hi)


def block_bootstrap_spearman(
    x: np.ndarray, y: np.ndarray, blocks: np.ndarray, n_boot: int = 1000, seed: int = SEED
) -> tuple[float, float, float]:
    """Spearman rho of (x, y) with a 95% block-bootstrap CI."""
    from scipy.stats import spearmanr

    x, y, blocks = np.asarray(x, float), np.asarray(y, float), np.asarray(blocks)
    ids = np.unique(blocks)
    idx = [np.flatnonzero(blocks == b) for b in ids]
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        sel = np.concatenate([idx[j] for j in rng.integers(0, len(idx), len(idx))])
        r = spearmanr(x[sel], y[sel]).statistic
        if np.isfinite(r):
            boots.append(r)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(spearmanr(x, y).statistic), float(lo), float(hi)


def summarize(err: np.ndarray, blocks: np.ndarray, min_n: int = 20) -> dict:
    """n, median signed error and MAE with block-bootstrap CIs; n < min_n -> too few to judge."""
    err = np.asarray(err, float)
    out = {"n": int(len(err))}
    if len(err) < min_n:
        out["verdict"] = "too few to judge"
        return out
    out["median"], out["median_lo"], out["median_hi"] = block_bootstrap(err, blocks, np.median)
    out["mae"], out["mae_lo"], out["mae_hi"] = block_bootstrap(np.abs(err), blocks, np.mean)
    return out


# --- the three pre-registered correction families -------------------------------------------


def fit_multiplier(pred_median: np.ndarray, observed: np.ndarray) -> float:
    """Family (1): m = median(observed / predicted median)."""
    return float(np.median(np.asarray(observed, float) / np.asarray(pred_median, float)))


def apply_multiplier(q: np.ndarray, m: float) -> np.ndarray:
    return np.asarray(q, float) * m


def fit_isotonic(pred_median: np.ndarray, observed: np.ndarray) -> IsotonicRegression:
    """Family (2): increasing isotonic map predicted median -> observed (clipped outside)."""
    return IsotonicRegression(increasing=True, out_of_bounds="clip").fit(
        np.asarray(pred_median, float), np.asarray(observed, float)
    )


def apply_isotonic(q: np.ndarray, iso: IsotonicRegression) -> np.ndarray:
    q = np.asarray(q, float)
    return np.maximum.accumulate(iso.predict(q.ravel()).reshape(q.shape), axis=-1)


def fit_shift(peak_signed_err: np.ndarray) -> float:
    """Family (3): s = -median(signed peak error), in days."""
    return float(-np.median(np.asarray(peak_signed_err, float)))


def apply_shift(q: np.ndarray, s: float) -> np.ndarray:
    return np.asarray(q, float) + s
