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

import dataclasses
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


# --- T6.2: continuous multi-year timeline (winter crops, cover crop, fallow) ------------------
#
# The sequence has S slots, one per harvest year (PLAN T2.2 season-year rule). The timeline has
# S + 1 calendar years: year 0 is a spin-up year (only the autumn sowing of a winter crop in
# slot 0 lives there); slot i has its harvest year at timeline year i + 1. A crop is placed by
# its sowing day relative to 1 Jan of its harvest year (negative = previous autumn, so a winter
# crop sown in autumn of year t is harvested in year t + 1). Dr is carried through the whole
# timeline. Between crops the soil is bare (Kc = kc_fallow, tag A, UNVERIFIED: FAO-56 Table 12
# has no fallow row and its "bare soil" row belongs to the orchard-cover group, so it is not
# used). A cover-crop slot starts the day after the previous crop ends and runs for
# min(gap to the next crop's sowing, its stage-length sum), Kc from `kc_curve` (oats proxy, A).
# If the next crop starts before the previous one ends, the earlier crop is cut at that day.
# Irrigation runs on crop days only. Accounting spans: per-slot metrics use the days a slot
# owns; per-year metrics use timeline years 1..S (the same span for every option).


@dataclass(frozen=True)
class SlotSpec:
    kind: str  # "crop" | "cover" | "fallow"
    kc: np.ndarray  # daily Kc from sowing (crop, cover); empty for fallow
    sow_day: int | None  # crop: 0-based day of its harvest year, may be < 0; else None
    kc_mid: float
    ky: float | None  # None -> RYI NaN (cover, fallow, unverified Ky)
    p: float  # depletion fraction p for this crop (FAO-56 Table 22), tag E/A


def fallow_slot() -> SlotSpec:
    return SlotSpec("fallow", np.zeros(0), None, 1.0, None, 0.55)


def _layout(slots, kc_fallow, p_fallow, cover_frac):
    """Daily Kc, p, owner slot (-1 bare), crop flag, canopy proxy and window starts."""
    S = len(slots)
    T = (S + 1) * DAYS
    kc = np.full(T, float(kc_fallow))
    p = np.full(T, float(p_fallow))
    owner = np.full(T, -1, int)
    crop = np.zeros(T, bool)
    canopy = np.zeros(T)
    starts = np.full(S, -1, int)
    crops = [i for i, s in enumerate(slots) if s.kind == "crop"]
    sow = {}
    for i in crops:
        a = DAYS * (i + 1) + int(slots[i].sow_day)
        b = a + len(slots[i].kc)
        if a < 0 or b > T:
            raise ValueError(f"slot {i}: crop window leaves the timeline")
        sow[i] = (a, b)
    prev = None
    for i in crops:
        if prev is not None and sow[i][0] <= sow[prev][0]:
            raise ValueError("crops overlap completely; sequence not placeable")
        if prev is not None and sow[i][0] < sow[prev][1]:
            sow[prev] = (sow[prev][0], sow[i][0])  # earlier crop cut at the next sowing
        prev = i
    cursor = DAYS  # 1 Jan of the harvest year of slot 0
    for i, s in enumerate(slots):
        if s.kind == "crop":
            a, b = sow[i]
            n = b - a
            kc[a:b], p[a:b], owner[a:b], crop[a:b] = s.kc[:n], s.p, i, True
            canopy[a:b] = np.clip(s.kc[:n] / s.kc_mid, 0.0, 1.0)
            starts[i] = a
            cursor = b
        elif s.kind == "cover":
            nxt = [sow[j][0] for j in crops if j > i]
            limit = nxt[0] if nxt else T
            a = max(cursor, DAYS)
            n = min(limit - a, len(s.kc))
            if n > 0:
                kc[a : a + n], p[a : a + n], owner[a : a + n] = s.kc[:n], s.p, i
                canopy[a : a + n] = np.clip(s.kc[:n] / s.kc_mid, 0.0, 1.0)
                starts[i] = a
                cursor = a + n
    return kc, p, owner, crop, canopy, starts


def _timeline_chunk(wr, we, options, taw_mm, policy, kc_scale, kc_fallow, p_fallow, dr0, cf):
    S = len(options[0])
    n_opt, n_draw, n_start = len(options), taw_mm.shape[0], wr.shape[1]
    T = (S + 1) * DAYS
    lay = [_layout(o, kc_fallow, p_fallow, cf) for o in options]
    kc = np.stack([x[0] for x in lay], 1)  # (T, opt)
    pp = np.stack([x[1] for x in lay], 1)
    owner = np.stack([x[2] for x in lay], 1)
    crop = np.stack([x[3] for x in lay], 1)
    canopy = np.stack([x[4] for x in lay], 1)
    starts = np.stack([x[5] for x in lay], 0)  # (opt, S)
    reset = np.zeros((T, n_opt), bool)
    for o in range(n_opt):
        reset[starts[o][starts[o] >= 0], o] = True
    shape = (T, n_opt, n_draw, n_start)
    rain = np.broadcast_to(wr[:, None, None, :], shape)
    etc = kc[:, :, None, None] * kc_scale[None, None, :, None] * we[:, None, None, :]
    if policy is not None and np.ndim(policy.budget_mm) == 1:  # one budget per draw
        policy = dataclasses.replace(policy, budget_mm=np.asarray(policy.budget_mm)[:, None])
    wb = waterbal.run(
        rain,
        etc,
        taw_mm[None, :, None],
        pp[:, :, None, None],
        policy,
        dr0=dr0,
        irr_mask=crop[:, :, None, None],
        budget_reset=reset[:, :, None, None],
    )
    keys = (
        "eta_mm",
        "etc_mm",
        "irr_mm",
        "irr_gross_mm",
        "ryi",
        "eta_year_mm",
        "irr_year_mm",
        "irr_gross_year_mm",
        "dp_year_mm",
    )
    out = {k: np.zeros((n_opt, n_draw, n_start, S)) for k in keys}
    ky = np.array([[s.ky if s.ky is not None else np.nan for s in o] for o in options])
    for i in range(S):
        m = (owner == i)[:, :, None, None]
        eta = np.where(m, wb["eta"], 0.0).sum(0)
        ec = np.where(m, etc, 0.0).sum(0)
        out["eta_mm"][..., i], out["etc_mm"][..., i] = eta, ec
        out["irr_mm"][..., i] = np.where(m, wb["irr"], 0.0).sum(0)
        out["irr_gross_mm"][..., i] = np.where(m, wb["irr_gross"], 0.0).sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.where(ec > 0, eta / np.where(ec > 0, ec, 1.0), np.nan)
            ryi = np.clip(1.0 - ky[:, i][:, None, None] * (1.0 - np.minimum(ratio, 1.0)), 0, 1)
        out["ryi"][..., i] = ryi
        y = slice(DAYS * (i + 1), DAYS * (i + 2))
        out["eta_year_mm"][..., i] = wb["eta"][y].sum(0)
        out["irr_year_mm"][..., i] = wb["irr"][y].sum(0)
        out["irr_gross_year_mm"][..., i] = wb["irr_gross"][y].sum(0)
        out["dp_year_mm"][..., i] = wb["dp"][y].sum(0)
    out["dr_final"] = wb["dr"][-1]
    out["cover_days"] = np.stack(
        [(canopy[DAYS * (i + 1) : DAYS * (i + 2)] >= cf).sum(0) for i in range(S)], 1
    )  # (opt, S), same for every draw / start year
    out["slot_start"] = starts
    return out


def simulate_timeline(
    rain,
    eto,
    options,
    taw_mm,
    policy: waterbal.Policy | None = None,
    kc_scale=1.0,
    kc_fallow=0.3,
    p_fallow=0.55,
    dr0=0.0,
    chunk=6,
    cover_frac=0.5,
):
    """Continuous multi-year simulation (T6.2). Output tag D.

    rain, eto: (n_years, 365) mm/day. options: list of sequences, each a list of S `SlotSpec`.
    taw_mm, kc_scale: scalar or (draws,). policy.budget_mm may be (draws,) (one seasonal
    budget per posterior draw; refilled at each crop sowing). Start year y = 0..n_years - S - 1
    forces timeline years y..y+S. Returns arrays (options, draws, starts, S): eta_mm, etc_mm,
    irr_mm, irr_gross_mm, ryi (slot-owned days), eta_year_mm, irr_year_mm, irr_gross_year_mm,
    dp_year_mm (timeline years 1..S); cover_days (options, S); dr_final (options, draws, starts);
    slot_start (options, S) timeline day index or -1; tag "D".
    """
    rain, eto = np.asarray(rain, float), np.asarray(eto, float)
    if rain.shape != eto.shape or rain.ndim != 2 or rain.shape[1] != DAYS:
        raise ValueError("rain and eto must both be (n_years, 365)")
    lens = {len(o) for o in options}
    if len(lens) != 1 or 0 in lens:
        raise ValueError("all options need the same number of slots >= 1")
    S = lens.pop()
    n_start = rain.shape[0] - S
    if n_start < 1:
        raise ValueError("not enough weather years for the sequence length")
    T = (S + 1) * DAYS
    win = np.lib.stride_tricks.sliding_window_view
    wr = win(rain.reshape(-1), T)[::DAYS][:n_start].T
    we = win(eto.reshape(-1), T)[::DAYS][:n_start].T
    taw_mm = np.atleast_1d(np.asarray(taw_mm, float))
    kc_scale = np.broadcast_to(np.asarray(kc_scale, float), taw_mm.shape)
    parts = [
        _timeline_chunk(
            wr,
            we,
            options[a : a + chunk],
            taw_mm,
            policy,
            kc_scale,
            kc_fallow,
            p_fallow,
            dr0,
            cover_frac,
        )
        for a in range(0, len(options), chunk)
    ]
    res = {k: np.concatenate([q[k] for q in parts], axis=0) for k in parts[0]}
    res["tag"] = "D"
    return res
