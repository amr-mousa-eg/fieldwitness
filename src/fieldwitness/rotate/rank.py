"""Rank candidate rotations (PLAN T6.3). Pure functions, no randomness (so rankings are
reproducible by construction; ties break by candidate index, which is deterministic).

Input: one field's `evaluate` output (lists per candidate). Steps:
1. Orient six metrics so higher is better (water, irrigation, CVaR water are negated).
   Missing RYI (no crop slot with a Ky) is set to 0 (A, UNVERIFIED team choice).
2. Pareto filter: option i is dominated if another option is >= on every metric and > on one.
3. Weighted score: weights from config/ranking.yaml presets, metrics min-max normalised per field.
   The score ranks all options; `pareto` is a flag. A dominated option never outscores its
   dominator under non-negative weights.
4. Regret matrix over weather start years: regret[o, y] = best RYI in year y minus o's RYI.
All outputs are tag D (model on satellite-calibrated draws); weights are tag A.
"""

from pathlib import Path

import numpy as np
import yaml

METRICS = ("ryi", "cvar10_ryi", "cover_days", "water_use_mm", "irrigation_mm", "cvar10_water_mm")
DOWN = {"water_use_mm", "irrigation_mm", "cvar10_water_mm"}


def load_presets(path: Path | str = "config/ranking.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text("utf-8"))
    for name, w in cfg["presets"].items():
        if set(w) != set(METRICS) or any(v < 0 for v in w.values()):
            raise ValueError(f"preset {name}: need non-negative weights for {METRICS}")
        if abs(sum(w.values()) - 1.0) > 1e-9:
            raise ValueError(f"preset {name}: weights must sum to 1")
    return cfg


def oriented(ev: dict) -> np.ndarray:
    """(n_candidates, 6) matrix, higher = better; NaN/None -> 0 before orientation."""
    cols = []
    for m in METRICS:
        x = np.array([np.nan if v is None else v for v in ev[m]], float)
        x = np.nan_to_num(x, nan=0.0)
        cols.append(-x if m in DOWN else x)
    return np.stack(cols, axis=1)


def pareto_mask(m: np.ndarray) -> np.ndarray:
    """True where the row is not dominated by any other row (maximisation)."""
    n = len(m)
    keep = np.ones(n, bool)
    for i in range(n):
        ge = (m >= m[i]).all(axis=1)
        gt = (m > m[i]).any(axis=1)
        if (ge & gt).any():
            keep[i] = False
    return keep


def scores(m: np.ndarray, weights: dict) -> np.ndarray:
    lo, hi = m.min(0), m.max(0)
    span = np.where(hi > lo, hi - lo, 1.0)
    norm = (m - lo) / span  # constant metric -> 0 for all options, no effect on order
    w = np.array([weights[k] for k in METRICS], float)
    return norm @ w


def regret(ev: dict) -> np.ndarray | None:
    """(n_candidates, n_years) regret in RYI vs the best option of that weather year; None if
    no option has an RYI series."""
    rows = [r if r is not None else None for r in ev["ryi_by_year"]]
    if all(r is None for r in rows):
        return None
    ny = len(next(r for r in rows if r is not None))
    a = np.array([r if r is not None else [0.0] * ny for r in rows], float)
    return a.max(0, keepdims=True) - a


def rank_field(ev: dict, presets: dict) -> dict:
    """Ranking per preset + Pareto flags + regret summary for one field."""
    m = oriented(ev)
    par = pareto_mask(m)
    out = {"pareto": par.tolist(), "rank": {}, "score": {}}
    for name, w in presets["presets"].items():
        s = scores(m, w)
        order = np.lexsort((np.arange(len(s)), -s))  # score desc, index asc on ties
        out["rank"][name] = order.tolist()
        out["score"][name] = s.round(5).tolist()
    rg = regret(ev)
    if rg is not None:
        out["regret_mean"] = rg.mean(1).round(5).tolist()
        out["regret_max"] = rg.max(1).round(5).tolist()
        out["minimax_regret_best"] = int(np.argmin(rg.max(1)))
    out["tag"] = "D"
    return out
