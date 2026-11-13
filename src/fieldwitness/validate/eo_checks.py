"""Pure validation metrics & dataset reconciliation helpers for independent NASA EO & WIMAS data.

Datasets supported (ids verified in docs/api_notes.md):
  - NASA SMAP L4 root-zone soil moisture: SPL4SMGP.008 (C3480440870-NSIDC_CPRD),
    layer Geophysical_Data_sm_rootzone (9 km grid -> context-flagged monthly z-score check).
  - NASA GPM IMERG / POWER daily precipitation extreme-rain agreement (>= 25 mm/day events).
  - NASA ECOSTRESS ETa overpasses: ECO_L3T_JET v003 (C4057232489-LPCLOUD, 70 m).
  - Kansas WIMAS point-of-diversion seasonal irrigation volumes (user-supplied CSV).

All returned summaries carry provenance tag "D" (model/derived statistics) and "E" (external ref).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

EXTREME_RAIN_THRESHOLD_MM = 25.0
ACRE_FOOT_M3 = 1233.48183754752
HECTARE_M2 = 10_000.0


def _corr_pair(x: np.ndarray, y: np.ndarray) -> tuple[float | None, float | None]:
    ok = np.isfinite(x) & np.isfinite(y)
    xv, yv = x[ok], y[ok]
    if len(xv) < 3 or np.std(xv) == 0 or np.std(yv) == 0:
        return None, None
    pearson = float(np.corrcoef(xv, yv)[0, 1])
    rx = pd.Series(xv).rank().to_numpy(float)
    ry = pd.Series(yv).rank().to_numpy(float)
    spearman = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 0 and np.std(ry) > 0 else None
    return pearson, spearman


def evaluate_smap_soil_moisture(
    sim_daily: pd.DataFrame,
    smap_series: pd.DataFrame,
) -> dict[str, Any]:
    """Compare simulated relative root-zone moisture (1 - Dr/TAW) vs SMAP L4 monthly z-scores.

    Args:
        sim_daily: Columns ["date", "dr_mm", "taw_mm"] (or ["date", "rel_sm"]).
        smap_series: Columns ["date", "sm_rootzone"] (m3/m3 from SPL4SMGP.008).
    """
    sim = sim_daily.copy()
    sim["date"] = pd.to_datetime(sim["date"])
    if "rel_sm" not in sim.columns:
        taw = np.maximum(sim["taw_mm"].to_numpy(float), 1.0)
        sim["rel_sm"] = np.clip(1.0 - sim["dr_mm"].to_numpy(float) / taw, 0.0, 1.0)
    sim["ym"] = sim["date"].dt.to_period("M")

    smap = smap_series.copy()
    smap["date"] = pd.to_datetime(smap["date"])
    smap = smap[np.isfinite(smap["sm_rootzone"]) & (smap["sm_rootzone"] >= 0.0)]
    smap["ym"] = smap["date"].dt.to_period("M")

    sim_m = sim.groupby("ym", as_index=False)["rel_sm"].mean()
    smap_m = smap.groupby("ym", as_index=False)["sm_rootzone"].mean()
    merged = sim_m.merge(smap_m, on="ym", how="inner")

    if len(merged) < 3:
        return {
            "n_months": int(len(merged)),
            "too_few_to_judge": True,
            "pearson_r": None,
            "spearman_rho": None,
            "anomaly_pearson_r": None,
            "tag": "D",
            "external_source": "NASA SMAP L4 SPL4SMGP.008 (9 km, context-flagged)",
        }

    r, rho = _corr_pair(merged["rel_sm"].to_numpy(float), merged["sm_rootzone"].to_numpy(float))
    # Monthly climatology z-score anomaly correlation
    merged["month_num"] = merged["ym"].apply(lambda p: p.month)
    for col in ("rel_sm", "sm_rootzone"):
        m_mean = merged.groupby("month_num")[col].transform("mean")
        m_std = merged.groupby("month_num")[col].transform("std").replace(0.0, np.nan)
        merged[f"{col}_z"] = ((merged[col] - m_mean) / m_std).fillna(0.0)
    anom_r, _ = _corr_pair(
        merged["rel_sm_z"].to_numpy(float),
        merged["sm_rootzone_z"].to_numpy(float),
    )
    return {
        "n_months": int(len(merged)),
        "too_few_to_judge": bool(len(merged) < 20),
        "pearson_r": round(r, 4) if r is not None else None,
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "anomaly_pearson_r": round(anom_r, 4) if anom_r is not None else None,
        "tag": "D",
        "external_source": "NASA SMAP L4 SPL4SMGP.008 (9 km, context-flagged)",
    }


def evaluate_extreme_rain_agreement(
    power_daily: pd.DataFrame,
    imerg_daily: pd.DataFrame,
    threshold_mm: float = EXTREME_RAIN_THRESHOLD_MM,
) -> dict[str, Any]:
    """Compare daily extreme-rain detection between NASA POWER and GPM IMERG."""
    p = power_daily[["date", "rain_mm"]].copy()
    g = imerg_daily[["date", "rain_mm"]].copy()
    p["date"] = pd.to_datetime(p["date"]).dt.normalize()
    g["date"] = pd.to_datetime(g["date"]).dt.normalize()
    m = p.merge(g, on="date", how="inner", suffixes=("_power", "_imerg")).dropna()

    n = len(m)
    if n == 0:
        return {"n_days": 0, "too_few_to_judge": True, "tag": "D"}

    p_hi = m["rain_mm_power"] >= threshold_mm
    g_hi = m["rain_mm_imerg"] >= threshold_mm
    hits = int((p_hi & g_hi).sum())
    misses = int((~p_hi & g_hi).sum())
    false_alarms = int((p_hi & ~g_hi).sum())
    denom_csi = hits + misses + false_alarms
    r, rho = _corr_pair(m["rain_mm_power"].to_numpy(float), m["rain_mm_imerg"].to_numpy(float))

    return {
        "n_days": int(n),
        "threshold_mm": float(threshold_mm),
        "too_few_to_judge": bool(n < 20),
        "pearson_r": round(r, 4) if r is not None else None,
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "bias_mm_per_day": round(float((m["rain_mm_power"] - m["rain_mm_imerg"]).mean()), 3),
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "hit_rate": round(hits / (hits + misses), 4) if (hits + misses) > 0 else None,
        "false_alarm_ratio": (
            round(false_alarms / (hits + false_alarms), 4) if (hits + false_alarms) > 0 else None
        ),
        "csi": round(hits / denom_csi, 4) if denom_csi > 0 else None,
        "tag": "D",
        "external_source": "NASA GPM IMERG vs NASA POWER daily precipitation",
    }


def evaluate_ecostress_eta(
    sim_daily: pd.DataFrame,
    ecostress_obs: pd.DataFrame,
) -> dict[str, Any]:
    """Compare ECOSTRESS ECO_L3T_JET v003 daytime ETa (mm/day) vs simulated FAO-56 ETa."""
    sim = sim_daily[["field_id", "date", "eta_mm"]].copy()
    eco = ecostress_obs[["field_id", "date", "eta_mm"]].copy()
    sim["date"] = pd.to_datetime(sim["date"]).dt.normalize()
    eco["date"] = pd.to_datetime(eco["date"]).dt.normalize()
    if "qc_good" in ecostress_obs.columns:
        eco = eco.loc[ecostress_obs["qc_good"].astype(bool).values]

    m = sim.merge(eco, on=["field_id", "date"], how="inner", suffixes=("_sim", "_eco")).dropna()
    n = len(m)
    if n == 0:
        return {
            "n_overpasses": 0,
            "too_few_to_judge": True,
            "tag": "D",
            "external_source": "NASA ECOSTRESS ECO_L3T_JET v003 (C4057232489-LPCLOUD, 70 m)",
        }

    err = m["eta_mm_sim"].to_numpy(float) - m["eta_mm_eco"].to_numpy(float)
    r, rho = _corr_pair(m["eta_mm_sim"].to_numpy(float), m["eta_mm_eco"].to_numpy(float))
    return {
        "n_overpasses": int(n),
        "too_few_to_judge": bool(n < 20),
        "bias_mm_day": round(float(np.mean(err)), 3),
        "mae_mm_day": round(float(np.mean(np.abs(err))), 3),
        "rmse_mm_day": round(float(np.sqrt(np.mean(err**2))), 3),
        "pearson_r": round(r, 4) if r is not None else None,
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "tag": "D",
        "external_source": "NASA ECOSTRESS ECO_L3T_JET v003 (C4057232489-LPCLOUD, 70 m)",
    }


def evaluate_wimas_irrigation(
    sim_seasons: pd.DataFrame,
    wimas_records: pd.DataFrame,
) -> dict[str, Any]:
    """T4.6 check: compare seasonal posterior irrigation (mm) vs Kansas WIMAS pumping records.

    Args:
        sim_seasons: Columns ["field_id", "year", "irrigation_mm"].
        wimas_records: Columns ["field_id", "year"] plus either "reported_mm" or
            both "af_used" (acre-feet) and "area_ha".
    """
    w = wimas_records.copy()
    if "reported_mm" not in w.columns:
        if not {"af_used", "area_ha"}.issubset(w.columns):
            raise ValueError("wimas_records needs either 'reported_mm' or ('af_used', 'area_ha')")
        area_m2 = np.maximum(w["area_ha"].to_numpy(float) * HECTARE_M2, 1.0)
        w["reported_mm"] = (w["af_used"].to_numpy(float) * ACRE_FOOT_M3 / area_m2) * 1000.0

    m = sim_seasons.merge(w[["field_id", "year", "reported_mm"]], on=["field_id", "year"]).dropna()
    n = len(m)
    if n == 0:
        return {
            "n_field_years": 0,
            "too_few_to_judge": True,
            "tag": "D",
            "external_source": "Kansas WIMAS point-of-diversion pumping records [E]",
        }

    sim_v = m["irrigation_mm"].to_numpy(float)
    obs_v = m["reported_mm"].to_numpy(float)
    err = sim_v - obs_v
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((obs_v - np.mean(obs_v)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
    r, rho = _corr_pair(sim_v, obs_v)

    return {
        "n_field_years": int(n),
        "too_few_to_judge": bool(n < 20),
        "bias_mm": round(float(np.mean(err)), 2),
        "mae_mm": round(float(np.mean(np.abs(err))), 2),
        "r2": round(float(r2), 4) if r2 is not None else None,
        "pearson_r": round(r, 4) if r is not None else None,
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "tag": "D",
        "external_source": "Kansas WIMAS point-of-diversion pumping records [E]",
    }
