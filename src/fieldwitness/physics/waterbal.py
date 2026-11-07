"""Daily root-zone water balance (T3.3). Output tag: D (model); parameters tag A/E.

FAO-56 Eq. 82 (TAW), Eq. 83 (RAW), Eq. 84 (Ks), Eq. 85 (Dr); see docs/fao56_equations.md.
Eq. 85 with CR = 0 (no capillary rise, tag A). Deep percolation DP = water above field
capacity (Dr would be < 0); ETa is cut so Dr never exceeds TAW. Runoff is a simple fraction
of rain, RO = ro_frac * P (tag A, UNVERIFIED; default 0). Pure NumPy; all inputs broadcast, so
one call can step (options, draws, years) arrays.

Irrigation policies (net depth I, applied on the day Dr(prev) > RAW, refilling to field capacity):
  rainfed                     I = 0
  trigger_at_RAW(efficiency)  gross = I / efficiency (reported as `irr_gross`)
  fixed_seasonal_mm(budget)   same trigger, events stop when the seasonal budget is used up
"""

from dataclasses import dataclass

import numpy as np


def taw(theta_fc, theta_wp, zr_m):
    """FAO-56 Eq. 82, mm."""
    return 1000.0 * (np.asarray(theta_fc) - np.asarray(theta_wp)) * np.asarray(zr_m)


def raw(taw_mm, p):
    """FAO-56 Eq. 83, mm."""
    return np.asarray(p) * np.asarray(taw_mm)


def ks(dr, taw_mm, raw_mm):
    """FAO-56 Eq. 84; 1 while Dr <= RAW, linear to 0 at Dr = TAW. Clipped to [0, 1]."""
    dr, taw_mm, raw_mm = np.broadcast_arrays(dr, taw_mm, raw_mm)
    denom = np.where(taw_mm > raw_mm, taw_mm - raw_mm, 1.0)
    k = np.where(dr > raw_mm, (taw_mm - dr) / denom, 1.0)
    return np.clip(k, 0.0, 1.0)


@dataclass(frozen=True)
class Policy:
    kind: str = "rainfed"  # rainfed | trigger_at_raw | fixed_seasonal_mm
    efficiency: float = 1.0  # application efficiency (0, 1]
    budget_mm: float = 0.0  # net seasonal budget for fixed_seasonal_mm


def rainfed() -> Policy:
    return Policy("rainfed")


def trigger_at_raw(efficiency: float) -> Policy:
    if not 0 < efficiency <= 1:
        raise ValueError("efficiency must be in (0, 1]")
    return Policy("trigger_at_raw", efficiency)


def fixed_seasonal_mm(budget_mm: float, efficiency: float = 1.0) -> Policy:
    if np.any(np.asarray(budget_mm) < 0) or not 0 < efficiency <= 1:
        raise ValueError("bad budget or efficiency")
    return Policy("fixed_seasonal_mm", efficiency, budget_mm)


def run(
    rain,
    etc,
    taw_mm,
    p,
    policy: Policy | None = None,
    dr0=0.0,
    ro_frac=0.0,
    irr_mask=None,
    budget_reset=None,
):
    """Step the balance over days (axis 0 of `rain`/`etc`; other axes broadcast).

    irr_mask (optional bool, broadcastable to rain): irrigation only where True (T3.5: no
    irrigation on fallow days).

    p may vary by day (T6.2): an array with the same ndim as `rain` and a leading axis of 1 or
    T is read per day (p[t]); lower-dimensional p is constant in time as before.
    budget_reset (optional bool, broadcastable to rain): where True the seasonal budget of
    `fixed_seasonal_mm` is refilled to `policy.budget_mm` (start of a new season). The budget
    may be an array broadcastable to the trailing axes (one budget per draw).

    rain, etc: mm/day (etc = Kc * ETo, unstressed). Returns dict of arrays:
    dr (end of day), ks, eta, irr (net), irr_gross, dp, ro; each shaped like rain.
    Daily mass: dr_prev - dr = (P-RO) + I - ETa - DP.
    """
    policy = policy or rainfed()
    rain = np.asarray(rain, float)
    etc = np.broadcast_to(np.asarray(etc, float), rain.shape)
    taw_mm = np.asarray(taw_mm, float)
    shape = rain.shape
    p = np.asarray(p, float)
    p_t = p.ndim == rain.ndim
    if p_t and p.shape[0] not in (1, shape[0]):
        raise ValueError("time-varying p needs a leading axis of 1 or T")
    raw_mm = None if p_t else raw(taw_mm, p)
    if budget_reset is not None:
        budget_reset = np.broadcast_to(np.asarray(budget_reset, bool), shape)
    if irr_mask is not None:
        irr_mask = np.broadcast_to(np.asarray(irr_mask, bool), shape)
    out = {k: np.zeros(shape) for k in ("dr", "ks", "eta", "irr", "irr_gross", "dp", "ro")}
    dr = np.broadcast_to(np.asarray(dr0, float), shape[1:]).copy()
    dr = np.clip(dr, 0.0, np.broadcast_to(taw_mm, shape[1:]))
    budget = np.broadcast_to(np.asarray(policy.budget_mm, float), shape[1:])
    left = budget.copy()
    for t in range(shape[0]):
        if p_t:
            raw_mm = raw(taw_mm, p[min(t, p.shape[0] - 1)])
        if budget_reset is not None:
            left = np.where(budget_reset[t], budget, left)
        ro = ro_frac * rain[t]
        pe = rain[t] - ro
        irr = np.zeros(shape[1:])
        if policy.kind != "rainfed":
            need = np.where(dr > raw_mm, dr, 0.0)
            if irr_mask is not None:
                need = np.where(irr_mask[t], need, 0.0)
            irr = np.minimum(need, left) if policy.kind == "fixed_seasonal_mm" else need
            if policy.kind == "fixed_seasonal_mm":
                left = left - irr
        k = ks(dr, taw_mm, raw_mm)
        eta = k * etc[t]
        new = dr - pe - irr + eta
        dp = np.where(new < 0.0, -new, 0.0)
        new = np.maximum(new, 0.0)
        excess = np.where(new > taw_mm, new - taw_mm, 0.0)  # ETa cut so Dr <= TAW
        eta = eta - excess
        new = new - excess
        out["dr"][t], out["ks"][t], out["eta"][t] = new, k, eta
        out["irr"][t], out["irr_gross"][t] = irr, irr / policy.efficiency
        out["dp"][t], out["ro"][t] = dp, ro
        dr = new
    return out
