"""Rotation simulation (T3.5). Output tag: D (model); parameters tag A/E.

A sequence is S consecutive calendar-year seasons. Each season has a crop window inside a
365-day year (sowing day + Kc curve from `kc.kc_curve`); the other days are fallow with
Kc = `kc_fallow`. The root-zone depletion Dr carries over from one season (and its fallow
period) to the next, so a crop leaves the next one a drier or wetter profile. Weather year
y + i forces season i of the sequence that starts in weather year y (no wrap-around).

State arrays are shaped (options, draws, years) and stepped through days with NumPy by
`waterbal.run` (FAO-56 Eq. 82-85), so one call simulates everything for a field. "draws" are
posterior parameter draws (TAW, Kc scale). Assumptions (A, UNVERIFIED): kc_fallow = 0.3 is a
team choice, not read from FAO-56; irrigation is applied only inside crop windows; crop windows
must fit inside one calendar year (winter crops spanning New Year are not supported yet).
"""

from dataclasses import dataclass

import numpy as np

from fieldwitness.physics import waterbal
from fieldwitness.physics.season import relative_yield_index

DAYS = 365


@dataclass(frozen=True)
class SeasonSpec:
    kc: np.ndarray  # daily Kc from sowing, length = season length
    sow_day: int  # 0-based day of the calendar year
    kc_mid: float
    ky: float | None  # FAO-33 yield response factor; None -> RYI NaN


def _chunk(rain, eto, sequences, taw_mm, p, policy, kc_scale, kc_fallow, dr0, n_start):
    n_opt, n_seas = len(sequences), len(sequences[0])
    n_draw = taw_mm.shape[0]
    shape = (n_opt, n_draw, n_start)
    taw3 = taw_mm[None, :, None]
    keys = ("eta_mm", "etc_mm", "irr_mm", "irr_gross_mm", "ryi", "dp_mm")
    out = {k: np.zeros(shape + (n_seas,)) for k in keys}
    out["dr_end"] = np.zeros(shape + (n_seas,))
    dr = np.broadcast_to(np.asarray(dr0, float), shape).copy()
    for i in range(n_seas):
        kc = np.full((DAYS, n_opt), float(kc_fallow))
        win = np.zeros((DAYS, n_opt), bool)
        for o, seq in enumerate(sequences):
            s = seq[i]
            end = s.sow_day + len(s.kc)
            if s.sow_day < 0 or end > DAYS:
                raise ValueError("crop window must fit inside one calendar year")
            kc[s.sow_day : end, o] = s.kc
            win[s.sow_day : end, o] = True
        r = np.broadcast_to(rain[i : i + n_start].T[:, None, None, :], (DAYS,) + shape)
        e = eto[i : i + n_start].T[:, None, None, :]
        etc = kc[:, :, None, None] * kc_scale[None, None, :, None] * e
        win4 = win[:, :, None, None]
        wb = waterbal.run(r, etc, taw3, p, policy, dr0=dr, irr_mask=win4)
        m = np.broadcast_to(win4, etc.shape)
        eta = np.where(m, wb["eta"], 0.0).sum(0)
        etc_s = np.where(m, etc, 0.0).sum(0)
        out["eta_mm"][..., i], out["etc_mm"][..., i] = eta, etc_s
        out["irr_mm"][..., i] = wb["irr"].sum(0)
        out["irr_gross_mm"][..., i] = wb["irr_gross"].sum(0)
        out["dp_mm"][..., i] = wb["dp"].sum(0)
        ky = np.array([seq[i].ky if seq[i].ky is not None else np.nan for seq in sequences])
        ryi = relative_yield_index(eta, etc_s, 1.0)  # Ky applied per option below
        ratio_loss = 1.0 - ryi  # = 1 - ETa/ETc (clipped), so RYI = 1 - Ky * loss
        out["ryi"][..., i] = np.clip(1.0 - ky[:, None, None] * ratio_loss, 0.0, 1.0)
        dr = wb["dr"][-1]
        out["dr_end"][..., i] = dr
    return out


def simulate(
    rain,
    eto,
    sequences,
    taw_mm,
    p,
    policy: waterbal.Policy | None = None,
    kc_scale=1.0,
    kc_fallow=0.3,
    dr0=0.0,
    chunk=50,
):
    """Simulate every sequence x draw x start year in batched NumPy calls.

    rain, eto: (n_years, 365) mm/day, weather years in order. sequences: list of sequences,
    each a list of `SeasonSpec`, all with the same number of seasons S. taw_mm: scalar or
    (draws,). kc_scale: scalar or (draws,). Returns arrays shaped (options, draws, starts, S)
    with starts = n_years - S + 1: eta_mm, etc_mm (crop window only), irr_mm, irr_gross_mm
    (crop window), dp_mm (whole year incl. fallow), ryi, dr_end; plus tag "D".
    """
    rain, eto = np.asarray(rain, float), np.asarray(eto, float)
    if rain.shape != eto.shape or rain.ndim != 2 or rain.shape[1] != DAYS:
        raise ValueError("rain and eto must both be (n_years, 365)")
    lens = {len(s) for s in sequences}
    if len(lens) != 1 or 0 in lens:
        raise ValueError("all sequences need the same number of seasons >= 1")
    n_seas = lens.pop()
    n_start = rain.shape[0] - n_seas + 1
    if n_start < 1:
        raise ValueError("not enough weather years for the sequence length")
    taw_mm = np.atleast_1d(np.asarray(taw_mm, float))
    kc_scale = np.broadcast_to(np.asarray(kc_scale, float), taw_mm.shape)
    parts = [
        _chunk(
            rain,
            eto,
            sequences[a : a + chunk],
            taw_mm,
            p,
            policy,
            kc_scale,
            kc_fallow,
            dr0,
            n_start,
        )
        for a in range(0, len(sequences), chunk)
    ]
    res = {k: np.concatenate([q[k] for q in parts], axis=0) for k in parts[0]}
    res["tag"] = "D"
    return res
