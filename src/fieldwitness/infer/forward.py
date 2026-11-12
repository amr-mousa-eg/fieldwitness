"""Forward model for inference (T4.2/T4.3): hidden variables + weather -> daily canopy NDVI.

One calendar year, one crop, `n` parameter draws at once. Uses the FAO-56 Kc curve (`kc_curve`)
and water balance (`waterbal.run`, Eq. 82-85). Output tag D (model). The canopy fraction, the
NDVI map and the stress coupling are team choices (tag A, UNVERIFIED), see config/synthetic.yaml.
Caveat: the synthetic "truth" and the ABC forward model are the same code, so recovery tests
show identifiability under a perfect model only, not skill on real fields.
"""

from pathlib import Path

import numpy as np
import yaml

from fieldwitness.physics import phenology, waterbal
from fieldwitness.physics.kc import kc_curve

DAYS = 365
_ROOT = Path(__file__).resolve().parents[3]


def load_cfg(path: Path | str | None = None) -> dict:
    return yaml.safe_load(Path(path or _ROOT / "config" / "synthetic.yaml").read_text("utf-8"))


def crop_params(crop: str, region: str, path: Path | str | None = None) -> dict:
    """Plain numbers for one crop from config/crops.yaml (values as printed there)."""
    c = yaml.safe_load(Path(path or _ROOT / "config" / "crops.yaml").read_text("utf-8"))["crops"][
        crop
    ]
    return {
        "stages": tuple(int(x) for x in c["stage_lengths_days"][region]["value"]),
        "kc_ini": float(
            c["kc_ini"][c["kc_ini"]["by_region"][region]]["value"]
            if "by_region" in c["kc_ini"]
            else c["kc_ini"]["value"]
        ),  # winter wheat: frozen / non-frozen soils by region (crops.yaml, A)
        "kc_mid": float(c["kc_mid"]["value"]),
        "kc_end": float(c["kc_end"]["value"]),
        "p": float(c["p"]["value"]),
        # None when unverified (barley, T7.1c): such crops are prediction_only, no RYI.
        "ky": None if c["ky"]["value"] is None else float(c["ky"]["value"]),
        # Experiment 2 (thermal time); used only when cfg phenology_mode == "gdd".
        "gdd": _gdd_params(c.get("gdd_phenology")),
    }


def _gdd_params(g: dict | None) -> dict | None:
    """GDD settings converted from degrees F (crops.yaml) to degrees C; None if not cited."""
    if g is None:
        return None
    return {
        "method": g["method"],
        "count_start": g["count_start"],
        "t_base_c": phenology.f_to_c(g["t_base_f"]),
        "t_upper_c": None if g.get("t_upper_f") is None else phenology.f_to_c(g["t_upper_f"]),
        "stage_end_gdd_c": phenology.gdd_f_to_c(g["stage_end_gdd_f"]),
    }


def season_weather(wx: dict, year: int, cfg: dict):
    """Weather arrays for the season harvested in `year` (T7.1a), or None if a year is missing.

    wx: {year: (rain, eto)} with 365 days each. Winter crop (negative nominal sowing day): previous
    year + `year` concatenated (730 days); otherwise the year alone.
    """
    if int(cfg["nominal_sow_doy"][cfg["crop"]]) >= 0:
        return wx.get(year)
    if year not in wx or year - 1 not in wx:
        return None
    # every daily array of the tuple (rain, eto[, tmax, tmin]) is concatenated
    return tuple(np.concatenate([a, b]) for a, b in zip(wx[year - 1], wx[year], strict=True))


def gdd_stages(tmax, tmin, sow, off: int, crop: dict, span: int) -> np.ndarray:
    """(n, 4) FAO-56 stage lengths from thermal time (Experiment 2, physics/phenology.py).

    sow: (n,) sowing index in the span. count_start "planting": GDD summed from sowing.
    "jan1_harvest_year" (winter wheat, user choice 2026-11-12): sowing to 31 Dec stays in the
    initial stage (calendar days), GDD summed from 1 Jan of the harvest year (index `off`).
    """
    g = crop.get("gdd")
    if g is None:
        raise ValueError("phenology_mode gdd needs cited gdd_phenology for this crop")
    if tmax is None or tmin is None:
        raise ValueError("phenology_mode gdd needs daily tmax and tmin")
    tmax, tmin = np.asarray(tmax, float), np.asarray(tmin, float)
    if tmax.shape != (span,) or tmin.shape != (span,):
        raise ValueError(f"tmax and tmin must have shape ({span},)")
    daily = phenology.daily_gdd(tmax, tmin, g["method"], g["t_base_c"], g["t_upper_c"])
    sow = np.asarray(sow, int)
    if g["count_start"] == "planting":
        ends = phenology.stage_ends(daily, sow, g["stage_end_gdd_c"])
        return phenology.stage_lengths(ends)
    if np.any(sow > off):
        raise ValueError("count from 1 Jan needs sowing before 1 Jan of the harvest year")
    ends = phenology.stage_ends(daily, np.full(len(sow), off), g["stage_end_gdd_c"])
    return phenology.stage_lengths(ends, lead_days=off - sow)


def simulate(rain, eto, hidden: dict, crop: dict, cfg: dict, tmax=None, tmin=None) -> dict:
    """rain, eto: (365,) mm/day. hidden: arrays of length n (see infer.priors.VARIABLES).

    cfg["phenology_mode"] (default "calendar"): "gdd" sets each draw's stage lengths from
    thermal time (`gdd_stages`), which needs daily tmax/tmin (deg C, same span as rain).
    Returns ndvi (365, n), eta_mm (n,) crop-window ETa, sow_day (n,) 0-based, tag "D".
    """
    rain, eto = np.asarray(rain, float), np.asarray(eto, float)
    n = len(hidden["taw_scale"])
    nominal = int(cfg["nominal_sow_doy"][cfg["crop"]])
    # Winter crop (nominal < 0, T7.1a): weather = previous year + harvest year (2 * DAYS days);
    # the sowing day is then counted from 1 Jan of the previous year and the output covers the
    # harvest year only. Other crops: one calendar year, as before.
    span = 2 * DAYS if nominal < 0 else DAYS
    if rain.shape != (span,) or eto.shape != (span,):
        raise ValueError(f"rain and eto must have shape ({span},) for this crop")
    off = span - DAYS  # days before 1 Jan of the harvest year
    sow = nominal + np.rint(np.asarray(hidden["sow_offset_days"])).astype(int)
    length = sum(crop["stages"])
    gdd_mode = cfg.get("phenology_mode", "calendar") == "gdd"
    if gdd_mode:
        # each draw gets its own stage lengths; gdd_stages cuts them at the end of the span
        stage_list = [tuple(s) for s in gdd_stages(tmax, tmin, sow + off, off, crop, span)]
        if sow.min() + off < 0:
            raise ValueError("crop window must fit inside the weather span")
    else:
        stage_list = None
        if sow.min() + off < 0 or sow.max() + off + length > span:
            raise ValueError("crop window must fit inside the weather span")
    sow_h = sow  # relative to 1 Jan of the harvest year (may be negative)
    sow = sow + off
    kc = np.full((span, n), float(cfg["kc_fallow"]))
    win = np.zeros((span, n), bool)
    cf = np.zeros((span, n))
    scale = np.asarray(hidden["kc_mid_scale"], float)
    for j in range(n):
        st = crop["stages"] if stage_list is None else stage_list[j]
        length = sum(st)
        k = kc_curve(st, crop["kc_ini"], crop["kc_mid"] * scale[j], crop["kc_end"])
        kc[sow[j] : sow[j] + length, j] = k
        win[sow[j] : sow[j] + length, j] = True
        den = crop["kc_mid"] * scale[j] - crop["kc_ini"]
        cf[sow[j] : sow[j] + length, j] = np.clip((k - crop["kc_ini"]) / den, 0.0, 1.0)
    taw = float(cfg["taw_base_mm"]) * np.asarray(hidden["taw_scale"], float)
    irrigated = np.asarray(hidden["irrigated"], bool)
    budget = np.where(irrigated, np.asarray(hidden["irrigation_mm"], float), 0.0)
    pol = waterbal.Policy("fixed_seasonal_mm", 1.0, budget)
    etc = (
        kc * scale[None, :] * eto[:, None]
    )  # scale also applies on fallow days (as in rotation.py)
    wb = waterbal.run(
        np.broadcast_to(rain[:, None], (span, n)),
        etc,
        taw,
        crop["p"],
        pol,
        dr0=float(cfg["dr0_mm"]),
        irr_mask=win,
    )
    cf = cf * (1.0 - float(cfg["stress_coupling"]) * (1.0 - wb["ks"]))
    ndvi = cfg["ndvi_bare"] + (cfg["ndvi_peak"] - cfg["ndvi_bare"]) * cf
    return {
        "ndvi": ndvi[off:],
        "eta_mm": np.where(win, wb["eta"], 0.0).sum(0),
        "sow_day": sow_h,
        "tag": "D",
    }
