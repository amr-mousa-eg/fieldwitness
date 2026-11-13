"""Asymmetric & symmetric Conformalized Quantile Regression (CQR) calibration.

Pre-registered in DECISIONS.md (2026-11-13). Output tag D (model statistics).
Does not modify stored medians (q50) or production FieldPacks; strictly calibrates
prediction bounds [lo, hi] via:
  - Symmetric CQR (Romano et al., NeurIPS 2019):
      E_i = max(q_lo_i - y_i, y_i - q_hi_i)
      calibrated interval = [q_lo - Q_{1-alpha}(E), q_hi + Q_{1-alpha}(E)]
  - Asymmetric signed CQR (tail-specific finite-sample margins):
      E_lo_i = q_lo_i - y_i,   E_hi_i = y_i - q_hi_i
      calibrated interval = [q_lo - Q_{1-alpha/2}(E_lo), q_hi + Q_{1-alpha/2}(E_hi)]
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

MIN_CAL = 30
DEFAULT_BLOCK_KM = 10.0


def assign_spatial_blocks(df: pd.DataFrame, block_km: float = DEFAULT_BLOCK_KM) -> pd.Series:
    """Assign each row to a 10 km x 10 km equirectangular spatial block from (lon, lat)."""
    if df.empty:
        return pd.Series([], dtype="object", index=df.index)
    lat = df["lat"].to_numpy(float)
    lon = df["lon"].to_numpy(float)
    lat_km = lat * 110.574
    lon_km = lon * (111.320 * np.cos(np.deg2rad(np.mean(lat))))
    bx = np.floor(lon_km / block_km).astype(int)
    by = np.floor(lat_km / block_km).astype(int)
    return pd.Series([f"{x}_{y}" for x, y in zip(bx, by, strict=True)], index=df.index)


def finite_sample_quantile(values: Iterable[float], q: float, min_n: int = MIN_CAL) -> float | None:
    """Split-conformal finite-sample quantile k = ceil((n + 1) * q)."""
    arr = np.asarray(list(values), float)
    v = np.sort(arr[np.isfinite(arr)])
    n = len(v)
    if n < min_n:
        return None
    k = math.ceil((n + 1) * q - 1e-12)
    k = max(1, min(k, n))
    return float(v[k - 1])


def cqr_scores(y, q_lo, q_hi) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (e_sym, e_lo, e_hi) signed CQR conformity scores."""
    y_a = np.asarray(y, float)
    lo_a = np.asarray(q_lo, float)
    hi_a = np.asarray(q_hi, float)
    e_lo = lo_a - y_a
    e_hi = y_a - hi_a
    e_sym = np.maximum(e_lo, e_hi)
    return e_sym, e_lo, e_hi


def fit_cqr_offsets(
    cal: pd.DataFrame,
    by: list[str],
    level: float = 0.90,
    min_n: int = MIN_CAL,
) -> dict[tuple, dict[str, float | int | None]]:
    """Compute pooled symmetric and asymmetric signed CQR margins per group."""
    tail_level = 1.0 - (1.0 - level) / 2.0
    out: dict[tuple, dict[str, float | int | None]] = {}
    for key, g in cal.groupby(by):
        k_norm = key if isinstance(key, tuple) else (key,)
        e_sym, e_lo, e_hi = cqr_scores(g["y"], g["q_lo"], g["q_hi"])
        n = int(np.isfinite(e_sym).sum())
        out[k_norm] = {
            "n": n,
            "m_sym": finite_sample_quantile(e_sym, level, min_n=min_n),
            "m_lo": finite_sample_quantile(e_lo, tail_level, min_n=min_n),
            "m_hi": finite_sample_quantile(e_hi, tail_level, min_n=min_n),
        }
    return out


def leave_block_out_cqr(
    cal: pd.DataFrame,
    by: list[str],
    blocks: Iterable[str],
    level: float = 0.90,
    min_n: int = MIN_CAL,
) -> dict[tuple[tuple, str], dict[str, float | int | None]]:
    """Leave-one-spatial-block-out CQR offsets per (group_key, block)."""
    tail_level = 1.0 - (1.0 - level) / 2.0
    block_list = sorted(set(blocks))
    out: dict[tuple[tuple, str], dict[str, float | int | None]] = {}
    for key, g in cal.groupby(by):
        k_norm = key if isinstance(key, tuple) else (key,)
        for b in block_list:
            rest = g.loc[g["block"] != b]
            e_sym, e_lo, e_hi = cqr_scores(rest["y"], rest["q_lo"], rest["q_hi"])
            n = int(np.isfinite(e_sym).sum())
            out[(k_norm, b)] = {
                "n": n,
                "m_sym": finite_sample_quantile(e_sym, level, min_n=min_n),
                "m_lo": finite_sample_quantile(e_lo, tail_level, min_n=min_n),
                "m_hi": finite_sample_quantile(e_hi, tail_level, min_n=min_n),
            }
    return out


def apply_cqr(
    q_lo,
    q_hi,
    m_lo,
    m_hi,
    lower_bound: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply (m_lo, m_hi) conformal margins without touching q50; optionally clip physical floor."""
    lo = np.asarray(q_lo, float) - np.asarray(m_lo, float)
    hi = np.asarray(q_hi, float) + np.asarray(m_hi, float)
    if lower_bound is not None:
        lo = np.maximum(lo, lower_bound)
    hi = np.maximum(hi, lo)
    return lo, hi


def interval_score(lo, hi, y, alpha: float = 0.10) -> np.ndarray:
    """Winkler interval score (lower is better; Gneiting & Raftery 2007)."""
    lo_a, hi_a, y_a = np.asarray(lo, float), np.asarray(hi, float), np.asarray(y, float)
    return (
        (hi_a - lo_a)
        + (2.0 / alpha) * np.maximum(lo_a - y_a, 0.0)
        + (2.0 / alpha) * np.maximum(y_a - hi_a, 0.0)
    )
