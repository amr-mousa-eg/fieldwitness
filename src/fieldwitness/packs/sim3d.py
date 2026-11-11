"""Build <field_id>.sim3d.json for the Field in 3D tab.

Generates 156-week series for Current + top 3 default alternatives across 12 what-if
weather scenarios forced with the historical median-rain year weather. Fully vectorized.
"""

from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd

from fieldwitness.packs import build as B
from fieldwitness.physics import waterbal
from fieldwitness.physics.forcing import forcing
from fieldwitness.physics.rotation import _layout
from fieldwitness.rotate.scenarios import grid, perturb
from fieldwitness.rotate.slots import _crops, option_slots
from fieldwitness.schemas import (
    FieldSim3D,
    Sim3DOption,
    Sim3DScenario,
    Sim3DWeek,
)

DAYS = 365
T_DAYS = 1460
N_WEEKS = 156
MONTH_NAMES = [
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def find_median_gs_rain_year(
    weather: pd.DataFrame, lat: float, elev: float, y0: int = 2001, y1: int = 2021
) -> int:
    """Find the historical year whose growing-season rain (Apr-Sep) is closest to the median."""
    f = forcing(weather, lat, elev)
    gs_rain = {}
    for y in range(y0, y1 + 1):
        fy = f[(f.index.year == y) & (f.index.month >= 4) & (f.index.month <= 9)]
        if len(fy) > 0 and not fy["rain"].isna().all():
            gs_rain[y] = float(fy["rain"].sum())
    if not gs_rain:
        return 2018  # fallback
    s = pd.Series(gs_rain).sort_values()
    med_year = int(s.index[len(s) // 2])
    return med_year


def build_weekly_calendar(start_year: int = 2022, n_seasons: int = 3) -> list[Sim3DWeek]:
    """156 weeks (52 weeks per season) starting Jan 1 of start_year."""
    weeks: list[Sim3DWeek] = []
    base_date = datetime.date(start_year, 1, 1)
    for w in range(n_seasons * 52):
        s_year = start_year + w // 52
        w_in_year = (w % 52) + 1
        cur_date = base_date + datetime.timedelta(days=w * 7)
        month = cur_date.month
        month_str = MONTH_NAMES[month]
        label = f"Week {w_in_year} ({month_str} {s_year})"
        weeks.append(
            Sim3DWeek(
                week=w,
                year=s_year,
                week_in_year=w_in_year,
                week_start=cur_date.isoformat(),
                month=month,
                label=label,
            )
        )
    return weeks


def _crop_root_depth_max(crop_name: str) -> float:
    """Return max root depth in meters for a crop from crops.yaml (or default)."""
    cfg = _crops().crops
    if crop_name in cfg and cfg[crop_name].root_depth_m:
        rng = cfg[crop_name].root_depth_m.range
        return float(np.mean(rng))
    if crop_name == "winter_wheat":
        return 1.65
    if crop_name == "sorghum":
        return 1.50
    if crop_name == "maize":
        return 1.35
    if crop_name == "cover_crop":
        return 1.25
    return 1.20


def precompute_scenario_weather(
    weather_med_year: pd.DataFrame, lat: float, elev: float
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Precompute (sids, rain_12, eto_12) shaped (1460, 1, 12)."""
    scen_list = grid()
    sids = [sid for sid, _, _ in scen_list]
    rain_cols, eto_cols = [], []

    for _, dt, dp in scen_list:
        w_pert = perturb(weather_med_year, dt, dp)
        f = forcing(w_pert, lat, elev)
        rain_day = f["rain"].to_numpy(float)
        eto_day = f["eto"].to_numpy(float)
        if len(rain_day) < DAYS:
            rain_day = np.pad(rain_day, (0, DAYS - len(rain_day)), mode="edge")
            eto_day = np.pad(eto_day, (0, DAYS - len(eto_day)), mode="edge")
        else:
            rain_day = rain_day[:DAYS]
            eto_day = eto_day[:DAYS]
        rain_cols.append(np.tile(rain_day, 4)[:T_DAYS])
        eto_cols.append(np.tile(eto_day, 4)[:T_DAYS])

    rain_12 = np.stack(rain_cols, axis=-1)[:, None, :]  # (T, 1, 12)
    eto_12 = np.stack(eto_cols, axis=-1)[:, None, :]  # (T, 1, 12)
    return sids, rain_12, eto_12


def safe_slot_spec(crop: str, region_id: str) -> Any:
    """Return slot_spec for crop, falling back to cover_crop proxy or fallow if unmodelled."""
    try:
        return option_slots((crop,), region_id)[0]
    except KeyError:
        try:
            return option_slots(("cover_crop",), region_id)[0]
        except Exception:
            from fieldwitness.physics.rotation import fallow_slot

            return fallow_slot()


def _compute_option_metadata(
    seq: tuple[str, ...], region_id: str
) -> tuple[
    list[str], list[str], list[float], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    """Compute weekly crops, stages, roots, and daily layout arrays for one sequence."""
    slots = [safe_slot_spec(c, region_id) for c in seq]
    kc, p, owner, crop, canopy, starts = _layout(slots, 0.3, 0.55, 0.5)
    crops_cfg = _crops().crops

    weekly_crops: list[str] = []
    weekly_stages: list[str] = []
    weekly_roots: list[float] = []

    for w in range(N_WEEKS):
        d = 365 + w * 7 + 3
        if d >= T_DAYS:
            d = T_DAYS - 1
        slot_idx = owner[d]
        is_crop = crop[d]
        if slot_idx >= 0 and is_crop and slot_idx < len(seq):
            cname = seq[slot_idx]
            weekly_crops.append(cname)
            s_day = starts[slot_idx]
            ds = max(0, d - s_day)
            zr_max = _crop_root_depth_max(cname)
            zr_ini = 0.20
            if cname in crops_cfg and region_id in crops_cfg[cname].stage_lengths_days:
                stg = [int(x) for x in crops_cfg[cname].stage_lengths_days[region_id].value]
            else:
                stg = [20, 30, 40, 20]
            l_ini, l_dev, l_mid, _ = stg[0], stg[1], stg[2], stg[3]

            if ds < l_ini:
                weekly_stages.append("initial")
                frac = ds / max(1, l_ini)
                rd = zr_ini + frac * 0.1 * (zr_max - zr_ini)
            elif ds < l_ini + l_dev:
                weekly_stages.append("development")
                frac = (ds - l_ini) / max(1, l_dev)
                rd = zr_ini + 0.1 * (zr_max - zr_ini) + frac * 0.9 * (zr_max - zr_ini)
            elif ds < l_ini + l_dev + l_mid:
                weekly_stages.append("mid")
                rd = zr_max
            else:
                weekly_stages.append("late")
                rd = zr_max
            weekly_roots.append(round(float(rd), 2))
        else:
            weekly_crops.append("fallow")
            weekly_stages.append("fallow")
            weekly_roots.append(0.0)

    reset = np.zeros(T_DAYS, bool)
    for st in starts:
        if 0 <= st < T_DAYS:
            reset[st] = True

    return weekly_crops, weekly_stages, weekly_roots, kc, p, crop, reset, canopy


def simulate_weekly(
    seqs: list[tuple[str, ...]],
    rain_t: np.ndarray,
    eto_t: np.ndarray,
    taw_mm: float,
    kc_scale: float,
    budget_mm: float,
    region_id: str,
) -> dict[str, Any]:
    """Weekly 3D series (unrounded) for several sequences and weather cases. Output tag D.

    rain_t, eto_t: (1460, n_scen) mm/day, the median weather year tiled 4x
    (`precompute_scenario_weather`). Days 0-364 are spin-up; weeks cover days 365..1456.
    Water balance FAO-56 Eq. 82-85 (`waterbal.run`); Kc curve FAO-56 Fig. 34 (`rotate.slots`).
    Returns metas [(crops, stages, roots)] and arrays soil_water_mm, ks, irrigation_mm, rain_mm
    (156, n_opt, n_scen) and canopy_cover (156, n_opt). The browser port
    (app/src/field3d/physics.ts) must reproduce this function (parity test).
    """
    n_opt, n_scen = len(seqs), rain_t.shape[1]
    kc_all = np.zeros((T_DAYS, n_opt, 1))
    p_all = np.zeros((T_DAYS, n_opt, 1))
    crop_all = np.zeros((T_DAYS, n_opt, 1), bool)
    reset_all = np.zeros((T_DAYS, n_opt, 1), bool)
    canopy_all = np.zeros((T_DAYS, n_opt))
    metas = []
    for o, seq in enumerate(seqs):
        w_crops, w_stages, w_roots, kc, p, crop, reset, canopy = _compute_option_metadata(
            seq, region_id
        )
        kc_all[:, o, 0] = kc
        p_all[:, o, 0] = p
        crop_all[:, o, 0] = crop
        reset_all[:, o, 0] = reset
        canopy_all[:, o] = canopy
        metas.append((w_crops, w_stages, w_roots))
    shape = (T_DAYS, n_opt, n_scen)
    rain = np.broadcast_to(rain_t[:, None, :], shape)
    etc = kc_all * kc_scale * eto_t[:, None, :]
    wb = waterbal.run(
        rain,
        etc,
        taw_mm,
        np.broadcast_to(p_all, shape),
        waterbal.fixed_seasonal_mm(budget_mm),
        dr0=0.0,
        irr_mask=np.broadcast_to(crop_all, shape),
        budget_reset=np.broadcast_to(reset_all, shape),
    )
    # rotation days 365..1456 (1092 = 156 weeks x 7) as weekly slices (156, 7, n_opt, n_scen)
    span = slice(365, 365 + N_WEEKS * 7)
    wk = (N_WEEKS, 7, n_opt, n_scen)
    return {
        "metas": metas,
        "soil_water_mm": np.maximum(0.0, taw_mm - wb["dr"][span].reshape(wk)).mean(axis=1),
        "ks": wb["ks"][span].reshape(wk).mean(axis=1),
        "irrigation_mm": wb["irr"][span].reshape(wk).sum(axis=1),
        "rain_mm": rain[span].reshape(wk).sum(axis=1),
        "canopy_cover": canopy_all[span].reshape(N_WEEKS, 7, n_opt).mean(axis=1),
    }


def build_field_sim3d(
    fid: str,
    cur_seq: tuple[str, ...],
    top_alts: list[Any],
    weather_full: pd.DataFrame,
    lat: float,
    elev: float,
    taw_mm: float,
    kc_scale: float,
    budget_mm: float,
    region_id: str = "ks_t14slh",
    start_year: int = 2022,
    scen_weather: tuple[list[str], np.ndarray, np.ndarray] | None = None,
    weather_year: int | None = None,
) -> FieldSim3D:
    """Build complete FieldSim3D model for one field using batched water balance."""
    med_year = (
        weather_year
        if weather_year is not None
        else find_median_gs_rain_year(weather_full, lat, elev, y0=2001, y1=2021)
    )
    if scen_weather is None:
        weather_med = weather_full[weather_full.index.year == med_year]
        scen_weather = precompute_scenario_weather(weather_med, lat, elev)

    sids, rain_12, eto_12 = scen_weather

    # Prepare options
    opt_specs = [(cur_seq, 0, "Current rotation", "current")]
    for i, a in enumerate(top_alts[:3]):
        if hasattr(a, "sequence"):
            seq = tuple(a.sequence)
            rank = a.rank
        elif isinstance(a, dict):
            seq = tuple(a["sequence"])
            rank = a.get("rank", i + 1)
        else:
            seq = tuple(a)
            rank = i + 1
        label = f"Alternative {i + 1}: {' – '.join(seq).replace('_', ' ').title()}"
        oid = B.oid(seq)
        opt_specs.append((seq, rank, label, oid))

    sim = simulate_weekly(
        [seq for seq, _, _, _ in opt_specs],
        rain_12[:, 0, :],
        eto_12[:, 0, :],
        taw_mm,
        kc_scale,
        budget_mm,
        region_id,
    )
    opt_metas = sim["metas"]
    sw_weekly, ks_weekly, irr_weekly = sim["soil_water_mm"], sim["ks"], sim["irrigation_mm"]
    rain_weekly, canopy_weekly = sim["rain_mm"], sim["canopy_cover"]

    # Build Sim3DOption models
    sim_options: list[Sim3DOption] = []
    for o, (seq, rank, label, oid) in enumerate(opt_specs):
        w_crops, w_stages, w_roots = opt_metas[o]
        scens_dict: dict[str, Sim3DScenario] = {}
        for s, sid in enumerate(sids):
            scens_dict[sid] = Sim3DScenario(
                soil_water_mm=[round(float(v), 1) for v in sw_weekly[:, o, s]],
                taw_mm=[round(float(taw_mm), 1)] * N_WEEKS,
                canopy_cover=[round(float(v), 2) for v in canopy_weekly[:, o]],
                ks=[round(float(v), 2) for v in ks_weekly[:, o, s]],
                rain_mm=[round(float(v), 1) for v in rain_weekly[:, o, s]],
                irrigation_mm=[round(float(v), 1) for v in irr_weekly[:, o, s]],
            )
        sim_options.append(
            Sim3DOption(
                option_id=oid,
                sequence=list(seq),
                rank=rank,
                label=label,
                crops=w_crops,
                stages=w_stages,
                root_depth_m=w_roots,
                scenarios=scens_dict,
            )
        )

    weeks = build_weekly_calendar(start_year=start_year, n_seasons=3)

    return FieldSim3D(
        schema_version="1.0",
        field_id=fid,
        weather_year=med_year,
        weather_label=f"Weather of {med_year} (median-rain year)",
        tag="D",
        source="FAO-56 daily water balance on median-rain weather year",
        weeks=weeks,
        current=sim_options[0],
        alternatives=sim_options[1:],
    )
