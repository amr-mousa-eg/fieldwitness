"""What to measure next + counterfactual flip (PLAN T6.4). Output tag: D (posterior worlds).

A world = one posterior draw (taw_mm, kc_scale, budget_mm). The sowing offset is NOT an input of
the rotation worlds (sow days are fixed in `rotate/slots.py`), so it is not analysed here.
Per world, metrics are means over weather start years (CVaR10 over those years), oriented so that
higher is better, min-max normalised over options within that world and scored with a preset
(`rotate.rank`). Rank 1 = highest score, ties to the lowest candidate index.
- flip_share[x]: share of posterior worlds whose rank 1 changes when input x is fixed at its
  posterior median (other inputs keep the world's own value). High share = measuring x matters.
- counterfactual[x]: start from the median world; change x alone along a grid (taw, kc: relative
  steps; budget: absolute mm steps, clipped at 0); report the smallest step, either sign, after
  which rank 1 differs from the median world's rank 1.
"""

import numpy as np

from fieldwitness.physics import waterbal
from fieldwitness.physics.rotation import simulate_timeline
from fieldwitness.rotate.rank import METRICS
from fieldwitness.rotate.slots import option_slots
from fieldwitness.schemas import Advice, Tagged

INPUTS = ("taw_mm", "kc_scale", "budget_mm")
REL_STEPS = (0.10, 0.20, 0.30, 0.40)  # taw_mm, kc_scale (fraction of the median)
ABS_STEPS_MM = (25.0, 50.0, 100.0, 200.0)  # budget_mm
CVAR_LEVEL = 0.10


def _tail(x: np.ndarray, upper: bool) -> np.ndarray:
    """Mean of the worst CVAR_LEVEL share along the last axis (lowest, or highest if upper)."""
    k = max(1, int(np.ceil(CVAR_LEVEL * x.shape[-1])))
    s = np.sort(x, axis=-1)
    return s[..., -k:].mean(-1) if upper else s[..., :k].mean(-1)


def world_metrics(rain, eto, candidates, region_id: str, worlds: dict, cover_frac: float = 0.5):
    """(n_candidates, n_worlds, 6) oriented metrics in `rank.METRICS` order, higher = better."""
    options = [option_slots(c, region_id) for c in candidates]
    r = simulate_timeline(
        rain,
        eto,
        options,
        worlds["taw_mm"],
        policy=waterbal.fixed_seasonal_mm(np.asarray(worlds["budget_mm"], float)),
        kc_scale=worlds["kc_scale"],
        cover_frac=cover_frac,
    )
    n, nw = len(candidates), len(worlds["taw_mm"])
    water = r["eta_year_mm"].sum(-1).reshape(n, nw, -1)
    irr = r["irr_year_mm"].sum(-1).reshape(n, nw, -1)
    ok = ~np.isnan(r["ryi"])
    tot = np.where(ok, r["ryi"], 0.0).sum(-1)
    ryi = (tot / r["ryi"].shape[-1]).reshape(n, nw, -1)  # no crop -> 0 (as rank.oriented)
    # cover days are identical in every world and year (evaluate.py): shape (n,) -> (n, nw)
    cover = np.broadcast_to(r["cover_days"].sum(-1).reshape(n, 1), (n, nw))
    cols = {
        "ryi": ryi.mean(-1),
        "cvar10_ryi": _tail(ryi, upper=False),
        "cover_days": cover,
        "water_use_mm": -water.mean(-1),
        "irrigation_mm": -irr.mean(-1),
        "cvar10_water_mm": -_tail(water, upper=True),
    }
    return np.stack([cols[m] for m in METRICS], axis=-1)


def top1_per_world(m: np.ndarray, weights: dict) -> np.ndarray:
    """Index of rank 1 per world. m: (n_candidates, n_worlds, 6) oriented metrics."""
    lo, hi = m.min(0), m.max(0)
    span = np.where(hi > lo, hi - lo, 1.0)
    w = np.array([weights[k] for k in METRICS], float)
    return np.argmax(((m - lo) / span) @ w, axis=0)  # first max = lowest index on ties


def smallest_flip(top: dict, base: int, steps: dict) -> dict | None:
    """top[(sign, step)] = rank-1 index after that change; steps in increasing size.
    Returns the smallest {sign, step, new_top} with a rank-1 change, or None."""
    for step in steps:
        for sign in (-1, 1):
            t = top.get((sign, step))
            if t is not None and t != base:
                return {"sign": sign, "step": step, "new_top": int(t)}
    return None


LABEL = {
    "taw_mm": "soil water holding capacity (TAW)",
    "kc_scale": "crop water-use scale (Kc)",
    "budget_mm": "seasonal irrigation amount",
}


def advice(res: dict, preset: str) -> Advice:
    """Build the schema `Advice` from one field's `analyse` result for one preset."""
    p = res["presets"][preset]
    share = p["flip_share"]
    best = max(INPUTS, key=lambda x: (share[x], -INPUTS.index(x)))
    if share[best] == 0.0:
        measure = "No uncertain input changes rank 1 in the posterior worlds."
    else:
        measure = f"Measure the {LABEL[best]}: it changes rank 1 in {share[best]:.0%} of worlds."
    parts = []
    for x in INPUTS:
        f = p["counterfactual"][x]
        if f is None:
            parts.append(f"{LABEL[x]}: no flip in the tested range")
        else:
            unit = " mm" if x == "budget_mm" else ""
            amount = f"{f['step']:g}{unit}" if x == "budget_mm" else f"{f['step']:.0%}"
            sign = "+" if f["sign"] > 0 else "-"
            parts.append(f"{LABEL[x]}: rank 1 changes at {sign}{amount}")
    return Advice(
        measure_next=measure,
        flip_probability=Tagged(
            value=share[best],
            unit="share of posterior worlds",
            tag="D",
            source="rotate.flip over posterior worlds (in-sample)",
        ),
        counterfactual_flip="; ".join(parts),
    )


def _grid_worlds(med: dict) -> tuple[dict, list]:
    """Worlds for the counterfactual grid: one input changed at a time from the median world."""
    rows, keys = [], []
    for x in INPUTS:
        steps = ABS_STEPS_MM if x == "budget_mm" else REL_STEPS
        for s in steps:
            for sign in (-1, 1):
                w = dict(med)
                w[x] = max(0.0, med[x] + sign * s) if x == "budget_mm" else med[x] * (1 + sign * s)
                rows.append(w)
                keys.append((x, sign, s))
    return {k: np.array([r[k] for r in rows], float) for k in INPUTS}, keys


def analyse(rain, eto, candidates, region_id: str, worlds: dict, presets: dict) -> dict:
    """Flip analysis for one field, every preset. `worlds`: equal-length arrays of INPUTS."""
    w0 = {k: np.asarray(worlds[k], float) for k in INPUTS}
    nw = len(w0["taw_mm"])
    med = {k: float(np.median(w0[k])) for k in INPUTS}
    parts = [w0]  # own worlds
    for x in INPUTS:  # input x fixed at its median
        p = {k: v.copy() for k, v in w0.items()}
        p[x] = np.full(nw, med[x])
        parts.append(p)
    parts.append({k: np.array([med[k]]) for k in INPUTS})  # median world
    grid, keys = _grid_worlds(med)
    parts.append(grid)
    allw = {k: np.concatenate([p[k] for p in parts]) for k in INPUTS}
    m = world_metrics(rain, eto, candidates, region_id, allw)
    i_fix = 1 + np.arange(len(INPUTS))
    i_med = nw * (1 + len(INPUTS))
    out = {"median_world": med, "n_worlds": nw, "presets": {}, "tag": "D"}
    for name, wts in presets["presets"].items():
        top = top1_per_world(m, wts)
        own = top[:nw]
        share = {
            x: float(np.mean(top[nw * i : nw * (i + 1)] != own))
            for x, i in zip(INPUTS, i_fix, strict=True)
        }
        base = int(top[i_med])
        grid_top = top[i_med + 1 :]
        cf = {}
        for x in INPUTS:
            steps = ABS_STEPS_MM if x == "budget_mm" else REL_STEPS
            tt = {(sg, s): int(grid_top[j]) for j, (xx, sg, s) in enumerate(keys) if xx == x}
            cf[x] = smallest_flip(tt, base, steps)
        out["presets"][name] = {
            "rank1_own_worlds": own.tolist(),
            "rank1_median_world": base,
            "flip_share": share,
            "counterfactual": cf,
        }
    return out
