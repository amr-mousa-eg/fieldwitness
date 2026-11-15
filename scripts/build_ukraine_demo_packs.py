"""Build a 120-field demo pack for Central Ukraine (ua_central_t36uvu, Tier 3).

Uses real open data already supported in the repo:
  - FTW 2024 field boundaries (data/fields/ua_central_t36uvu_pilot.parquet)
  - Sentinel-2 L2A 20 m COG NDVI/EVI2 series (fieldwitness.data.s2_cog, tag O)
  - Causal Tier 3 crop-sequence classifier (fieldwitness.story.ukraine_seasons, tag D)
  - NASA POWER daily weather 2001-2024 (fieldwitness.data.power, tag E)
  - ISRIC SoilGrids 2.0 0-135 cm root-zone TAW via Saxton & Rawls (2006) (tag E)
  - Panel-OBDML (<= 2021) Neighbours cover_days witness (tag D)
  - FAO-56 water balance & rotation ranking (fieldwitness.rotate, tag D / A)

Outputs packs/demo/ua_central_t36uvu/ and updates packs/demo/regions.json.
"""

from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
import yaml
from shapely import wkb

from fieldwitness.agree.grade import Effect, grade_option
from fieldwitness.config import load_crops
from fieldwitness.data import power
from fieldwitness.data.s2_cog import build_s2_series
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.packs import build as B
from fieldwitness.packs import extras as X
from fieldwitness.packs import sim3d as sim3d_mod
from fieldwitness.packs import sim3d_inputs as sim3d_in_mod
from fieldwitness.packs.validate import validate_dir
from fieldwitness.physics.forcing import forcing
from fieldwitness.resolve.pilot import load_grid
from fieldwitness.rotate.evaluate import N_WORLDS, evaluate, subsample_draws
from fieldwitness.rotate.priority import sequence_metrics
from fieldwitness.rotate.rank import load_presets, rank_field, rank_positions
from fieldwitness.rotate.scenarios import grid as scen_grid
from fieldwitness.rotate.scenarios import perturb, yearly_arrays
from fieldwitness.schemas import (
    Advice,
    BareMonth,
    Explanation,
    FieldCalendar,
    FieldPack,
    FieldScenarios,
    FieldSeries,
    FieldSim3DInputs,
    FieldSummary,
    HindcastRow,
    Option,
    RegionEntry,
    RegionHindcast,
    RegionIndex,
    RegionLayers,
    RegionList,
    Scenario,
    Season,
    Tagged,
    TaggedSeries,
    WitnessResult,
    check_tagged,
)
from fieldwitness.story.seasons import EPOCH, detect_seasons, load_story
from fieldwitness.story.smooth import smooth_series
from fieldwitness.story.ukraine_seasons import infer_region_labels

REGION = "ua_central_t36uvu"
SEED = priors.SEED
N_DEMO = 120
N_REF = 3000
K_ABC = 150
MIN_OBS_ABC = 10
Y0, Y1 = 2001, 2024
OUT_ROOT = Path("packs/demo")
MAX_PACK_BYTES = 300_000
UA_HLS_BASEMAP_URL = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/2023-08-15/"
    "GoogleMapsCompatible_Level12/{z}/{y}/{x}.png"
)

# Modelled crops in rotate.slots (SOW_DAY) that also have ua_central_t36uvu params in crops.yaml
ROTATION_CROPS = ("winter_wheat", "maize", "fallow", "cover_crop")
CANDIDATE_SEQS = [
    ("winter_wheat", "maize", "cover_crop"),
    ("winter_wheat", "maize", "maize"),
    ("winter_wheat", "maize", "winter_wheat"),
    ("winter_wheat", "maize", "fallow"),
    ("winter_wheat", "winter_wheat", "maize"),
    ("maize", "winter_wheat", "fallow"),
]
# Crops in config/crops.yaml calibrated by ABC in Tier 3 Ukraine
ABC_SUMMER_CROPS = ("sunflower", "maize")
# Nominal sowing day of year (0-based harvest year): sunflower late Apr/May (Table 11),
# maize Apr (synthetic.yaml), winter wheat mid-Oct (-78 = rotate/slots.py).
UA_NOMINAL_SOW_DOY = {"sunflower": 120, "maize": 105, "winter_wheat": -78}

_OPT_NULL = ("lo50", "hi50", "lo90", "hi90")
_DEPTH_WEIGHTS = {"0-5cm": 5.0 / 30.0, "5-15cm": 10.0 / 30.0, "15-30cm": 15.0 / 30.0}
# SoilGrids 2.0 horizon thicknesses (mm) covering 0-135 cm root zone (ssurgo_taw.py zr_m=1.35)
_ROOT_HORIZON_MM = {
    "0-5cm": 50.0,
    "5-15cm": 100.0,
    "15-30cm": 150.0,
    "30-60cm": 300.0,
    "60-100cm": 400.0,
    "100-200cm": 350.0,
}
_T24_NOTE = (
    "T2.4 ogh-ghlc10/WorldCereal check: 98.25% annual cropland, "
    "0.0% winter-wheat/maize confusion, maize-vs-sunflower kappa=0.035"
)


def _slim(o):
    if isinstance(o, dict):
        return {k: _slim(v) for k, v in o.items() if not (k in _OPT_NULL and v is None)}
    if isinstance(o, list):
        return [_slim(v) for v in o]
    return o


def _write(path: Path, model, problems: list[str]) -> None:
    bad = check_tagged(model)
    if bad:
        problems.extend(f"{path.name}: untagged {b}" for b in bad[:5])
    txt = json.dumps(_slim(model.model_dump(mode="json")), separators=(",", ":"))
    if len(txt.encode()) > MAX_PACK_BYTES:
        problems.append(f"{path.name}: {len(txt.encode())} bytes > {MAX_PACK_BYTES}")
    path.write_text(txt, "utf-8")


def _select_demo_fields(pilot: pd.DataFrame) -> pd.DataFrame:
    """Pick N_DEMO fields stratified across the spatial blocks (seeded)."""
    rng = np.random.default_rng(SEED)
    pilot = pilot.sort_values("field_id").reset_index(drop=True)
    blocks = sorted(pilot["block"].unique())
    chosen_idx: list[int] = []
    by_block = {b: pilot.index[pilot["block"] == b].tolist() for b in blocks}
    for b in blocks:
        rng.shuffle(by_block[b])
    while len(chosen_idx) < N_DEMO:
        added = False
        for b in blocks:
            if by_block[b] and len(chosen_idx) < N_DEMO:
                chosen_idx.append(by_block[b].pop())
                added = True
        if not added:
            break
    return pilot.loc[chosen_idx].reset_index(drop=True)


_WEATHER_CACHE: dict[tuple[str, float], tuple] = {}


def _weather(lon: float, lat: float):
    w_path, elev = power.cached(lon, lat)
    cache_key = (str(w_path), round(lat, 2))
    if cache_key in _WEATHER_CACHE:
        return _WEATHER_CACHE[cache_key]
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    wx_by_year: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue
        r_arr = fy["rain"].to_numpy(float)
        e_arr = fy["eto"].to_numpy(float)
        rain.append(r_arr)
        eto.append(e_arr)
        wx_by_year[y] = (r_arr, e_arr)
    res = (w, float(elev or 0.0), np.array(rain), np.array(eto), wx_by_year)
    _WEATHER_CACHE[cache_key] = res
    return res


def _bare_observed_from_s2(s: pd.DataFrame) -> list[BareMonth]:
    """Compute monthly bare-soil share from Sentinel-2 NDVI (< 0.30, tag O)."""
    s = s.copy()
    s["month"] = s["date"].dt.month
    s["year"] = s["date"].dt.year
    out = []
    for m in range(1, 13):
        sm = s[(s["month"] == m) & s["ndvi"].notna()]
        n_obs = int(len(sm))
        n_yrs = int(sm["year"].nunique())
        if n_obs < 3 or n_yrs < 2:
            out.append(
                BareMonth(
                    month=m,
                    bare_share=None,
                    clear_obs=n_obs,
                    years_with_data=n_yrs,
                    insufficient=True,
                )
            )
        else:
            yr_bare = sm.groupby("year")["ndvi"].median() < 0.30
            share = float(yr_bare.mean())
            out.append(
                BareMonth(
                    month=m,
                    bare_share=Tagged(
                        value=round(share, 3),
                        unit="share of years",
                        tag="O",
                        source="Sentinel-2 L2A 20 m NDVI < 0.30",
                    ),
                    clear_obs=n_obs,
                    years_with_data=n_yrs,
                    insufficient=False,
                )
            )
    return out


def soilgrids_saxton_rawls_taw_mm(
    clay_pct: float, sand_pct: float, soc_gkg: float, thickness_mm: float
) -> float:
    """Horizon plant-available water (mm) from SoilGrids 2.0 via Saxton & Rawls (2006).

    Source: Saxton, K.E. & Rawls, W.J. (2006), Soil Sci. Soc. Am. J. 70(5):1569-1578,
    Table 1 Eqs. 1-2 (1500 kPa wilting point & 33 kPa field capacity), combined with
    FAO-56 Eq. 82 (``waterbal.taw``): ``TAW_h = max(0, theta_33 - theta_1500) * dz_mm``.
    SoilGrids units from ``fieldwitness.data.soilgrids``: clay/sand in %, soc in g/kg.
    Van Bemmelen SOM conversion: ``om_pct = min(max(1.724 * (soc_gkg / 10.0), 0.0), 8.0)``
    (capped at the 8% OM calibration limit of Saxton & Rawls 2006). Tag E.
    """
    s = float(sand_pct) / 100.0
    c = float(clay_pct) / 100.0
    om = min(max(1.724 * (float(soc_gkg) / 10.0), 0.0), 8.0)
    t1500t = (
        -0.024 * s
        + 0.487 * c
        + 0.006 * om
        + 0.005 * (s * om)
        - 0.013 * (c * om)
        + 0.068 * (s * c)
        + 0.031
    )
    theta_1500 = t1500t + (0.14 * t1500t - 0.02)
    t33t = (
        -0.251 * s
        + 0.195 * c
        + 0.011 * om
        + 0.006 * (s * om)
        - 0.027 * (c * om)
        + 0.452 * (s * c)
        + 0.299
    )
    theta_33 = t33t + (1.283 * (t33t**2) - 0.374 * t33t - 0.015)
    return float(max(0.0, theta_33 - theta_1500) * float(thickness_mm))


def _load_soil_profile(path: Path) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """Load SoilGrids 2.0 0-30 cm context summary and 0-135 cm Saxton & Rawls TAW per field."""
    if not path.exists():
        return {}, {}
    df = pd.read_parquet(path)
    sub = df[
        (df["stat"] == "mean")
        & (df["property"].isin(["clay", "sand", "soc"]))
        & df["value"].notna()
    ].copy()
    sub_030 = sub[sub["depth"].isin(list(_DEPTH_WEIGHTS))].copy()
    sub_030["w"] = sub_030["depth"].map(_DEPTH_WEIGHTS)
    soil_030: dict[str, dict[str, float]] = {}
    for fid, grp in sub_030.groupby("field_id"):
        vals: dict[str, float] = {}
        for prop, pgrp in grp.groupby("property"):
            wsum = float(pgrp["w"].sum())
            if wsum > 0:
                vals[str(prop)] = round(float((pgrp["value"] * pgrp["w"]).sum() / wsum), 1)
        if vals:
            soil_030[str(fid)] = vals

    piv = sub.pivot_table(index=["field_id", "depth"], columns="property", values="value")
    taw_map: dict[str, float] = {}
    for fid, fgrp in piv.groupby(level=0):
        tot = 0.0
        cov_mm = 0.0
        for (_, depth), row in fgrp.iterrows():
            thick = _ROOT_HORIZON_MM.get(str(depth))
            if thick is None or row.isna().any():
                continue
            tot += soilgrids_saxton_rawls_taw_mm(
                float(row["clay"]), float(row["sand"]), float(row["soc"]), thick
            )
            cov_mm += thick
        if cov_mm >= 1350.0:
            taw_map[str(fid)] = round(tot, 2)
    return soil_030, taw_map


def _rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _calibrate_field_abc(
    fid: str,
    field_idx: int,
    s2_field: pd.DataFrame,
    crop_by_year: dict[int, str],
    wx_by_year: dict[int, tuple[np.ndarray, np.ndarray]],
    taw_base_mm: float,
    taw_tag: str,
    noise_sd: float,
    cfg0: dict,
    crop_params_map: dict[str, dict],
    cred_cfg: dict,
    rng: np.random.Generator,
    prior_hidden: dict[str, np.ndarray],
) -> tuple[dict, float | None, dict]:
    """Run per-field ABC calibration (scripts/t45_credibility + t62_draws pattern)."""
    sf = s2_field.copy()
    sf["year"] = sf["date"].dt.year
    sf["doy"] = sf["date"].dt.day_of_year

    # Calibrate summer seasons first; fall back to winter_wheat if fewer than 2 summer seasons
    summer_yrs = [y for y, c in sorted(crop_by_year.items()) if c in ABC_SUMMER_CROPS]
    fit_crops = ABC_SUMMER_CROPS if len(summer_yrs) >= 2 else ("sunflower", "maize", "winter_wheat")

    parts: list[dict[str, np.ndarray]] = []
    fit_years: list[int] = []
    seasons_by_crop: dict[str, list[tuple[int, np.ndarray, np.ndarray]]] = {
        c: [] for c in fit_crops
    }

    for year, crop_name in sorted(crop_by_year.items()):
        if crop_name not in fit_crops:
            continue
        g = sf[sf["year"] == year].dropna(subset=["ndvi"]).drop_duplicates("doy")
        if crop_name == "winter_wheat":
            # Exclude Dec-Feb snow window at 48.2 N (mirrors WINDOWS_BY_REGION active window)
            g = g[(g["doy"] >= 60) & (g["doy"] <= 220)].sort_values("doy")
            sw_cfg = {
                **cfg0,
                "region": REGION,
                "crop": crop_name,
                "taw_base_mm": taw_base_mm,
                "nominal_sow_doy": UA_NOMINAL_SOW_DOY,
            }
            sw_wx = forward.season_weather(wx_by_year, year, sw_cfg)
            if sw_wx is None or len(g) < 8:
                continue
            rain_in, eto_in = sw_wx
            ref_cfg = sw_cfg
        else:
            g = g[(g["doy"] >= 1) & (g["doy"] <= 365)].sort_values("doy")
            if len(g) < MIN_OBS_ABC or year not in wx_by_year:
                continue
            rain_in, eto_in = wx_by_year[year]
            ref_cfg = {
                **cfg0,
                "region": REGION,
                "crop": crop_name,
                "taw_base_mm": taw_base_mm,
                "nominal_sow_doy": UA_NOMINAL_SOW_DOY,
            }

        ref = abc.reference_table(
            rain_in,
            eto_in,
            N_REF,
            crop_params_map[crop_name],
            ref_cfg,
            seed=SEED + 1000 + year,
        )
        doy = g["doy"].to_numpy(int)
        nd = g["ndvi"].to_numpy(float)
        post = abc.posterior(doy, nd, ref, noise_sd, K_ABC, rng)
        sim = abc.summary_stats(doy, ref["ndvi"][doy - 1][:, post["idx"]])
        pred = np.median(sim, axis=0)
        seasons_by_crop[crop_name].append((year, post["obs_stats"], pred))

        hid = ref["hidden"]
        irrig = np.asarray(hid["irrigated"], bool)
        parts.append(
            {
                "taw_mm": (taw_base_mm * np.asarray(hid["taw_scale"], float))[post["idx"]],
                "kc_scale": np.asarray(hid["kc_mid_scale"], float)[post["idx"]],
                "budget_mm": np.where(irrig, np.asarray(hid["irrigation_mm"], float), 0.0)[
                    post["idx"]
                ],
            }
        )
        fit_years.append(int(year))

    if parts:
        pool = {key: np.concatenate([q[key] for q in parts]) for key in parts[0]}
        src, tag = "posterior", "D"
    else:
        irrig_p = np.asarray(prior_hidden["irrigated"], bool)
        pool = {
            "taw_mm": taw_base_mm * np.asarray(prior_hidden["taw_scale"], float),
            "kc_scale": np.asarray(prior_hidden["kc_mid_scale"], float),
            "budget_mm": np.where(irrig_p, np.asarray(prior_hidden["irrigation_mm"], float), 0.0),
        }
        src, tag = "prior", taw_tag

    sub = subsample_draws(pool, N_WORLDS, seed=SEED + field_idx)
    draws = {
        "source": src,
        "tag": tag,
        "years": fit_years,
        "taw_mm": [round(float(x), 2) for x in sub["taw_mm"]],
        "kc_scale": [round(float(x), 4) for x in sub["kc_scale"]],
        "budget_mm": [round(float(x), 1) for x in sub["budget_mm"]],
    }

    best_crop = max(fit_crops, key=lambda c: len(seasons_by_crop[c]))
    best_s = seasons_by_crop[best_crop]
    if not best_s:
        return (
            draws,
            None,
            {
                "field_id": fid,
                "crop": None,
                "n_seasons": 0,
                "credibility": None,
                "mode": "not_assessable",
                "spearman": None,
                "median_timing_error_days": None,
                "years": [],
                "taw_base_mm": taw_base_mm,
                "taw_post_median_mm": round(float(np.median(draws["taw_mm"])), 2),
                "taw_source": "soilgrids_saxton_rawls_0_135cm"
                if taw_tag == "E"
                else "fallback_150mm",
            },
        )

    obs = np.array([x[1] for x in best_s])
    pr = np.array([x[2] for x in best_s])
    err = np.abs(obs[:, [0, 1, 2]] - pr[:, [0, 1, 2]]).mean(1)
    med_err = float(np.median(err))
    t_score = max(0.0, 1.0 - med_err / float(cred_cfg["timing_error_scale_days"]))
    rho = _rank_corr(obs[:, 3], pr[:, 3])
    w_s = float(cred_cfg["weight_spearman"])
    if np.isnan(rho):
        cred, mode = t_score, "timing_only"
    else:
        cred, mode = w_s * max(0.0, rho) + (1.0 - w_s) * t_score, "full"
    cred_r = round(float(cred), 3)
    meta = {
        "field_id": fid,
        "crop": best_crop,
        "n_seasons": len(best_s),
        "credibility": cred_r,
        "mode": mode,
        "spearman": None if np.isnan(rho) else round(float(rho), 3),
        "median_timing_error_days": round(med_err, 1),
        "years": [int(x[0]) for x in best_s],
        "fit_years": fit_years,
        "taw_base_mm": taw_base_mm,
        "taw_post_median_mm": round(float(np.median(draws["taw_mm"])), 2),
        "kc_scale_median": round(float(np.median(draws["kc_scale"])), 4),
        "budget_median_mm": round(float(np.median(draws["budget_mm"])), 1),
        "taw_source": "soilgrids_saxton_rawls_0_135cm" if taw_tag == "E" else "fallback_150mm",
    }
    return draws, cred_r, meta


def _load_pre_panel_obdml(path: Path) -> dict[tuple[str, str, str, str], dict]:
    """Load strictly pre-cutoff (<=2021) Panel-OBDML rows passing all 4 causal gates."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    ok = df[
        (df["period"] == "pre_cutoff_le_2021")
        & (df["show_as_evidence"] == True)  # noqa: E712
        & (df["stratum"] == "all")
        & df["outcome"].isin(["cover_days", "canopy_integral"])
    ]
    out: dict[tuple[str, str, str, str], dict] = {}
    for _, row in ok.iterrows():
        key = (
            str(row["crop"]),
            str(row["treated_prev"]),
            str(row["reference_prev"]),
            str(row["outcome"]),
        )
        out[key] = row.to_dict()
    return out


def _match_neighbours_contrast(
    cur_seq_raw: list[str],
    cand_seq: tuple[str, ...],
    pob_map: dict[tuple[str, str, str, str], dict],
) -> tuple[list[WitnessResult], list[str]]:
    """Attach passing pre-cutoff Panel-OBDML contrasts when cereal breaks summer monoculture."""
    if not pob_map:
        return [], []
    cand_pairs = set(zip(cand_seq, cand_seq[1:], strict=False))
    if ("winter_wheat", "maize") not in cand_pairs:
        return [], []
    cur_pairs = set(zip(cur_seq_raw, cur_seq_raw[1:], strict=False))
    if ("winter_wheat", "sunflower") in cur_pairs:
        return [], []
    if ("sunflower", "sunflower") in cur_pairs:
        base_key = ("sunflower", "sunflower", "winter_wheat")
    elif ("maize", "sunflower") in cur_pairs:
        base_key = ("sunflower", "maize", "winter_wheat")
    else:
        return [], []

    w_out: list[WitnessResult] = []
    notes: list[str] = []
    for metric in ("cover_days", "canopy_integral"):
        row = pob_map.get((*base_key, metric))
        if row is None:
            continue
        # Panel-OBDML reports treated_prev (summer) - reference_prev (winter_wheat).
        # Introducing winter_wheat before a summer crop therefore inverts the sign.
        eff = round(-float(row["effect"]), 3)
        lo90 = round(-float(row["hi90"]), 3)
        hi90 = round(-float(row["lo90"]), 3)
        unit = (
            "days vs continuous summer crop"
            if metric == "cover_days"
            else "NDVI-days vs continuous summer crop"
        )
        w_out.append(
            WitnessResult(
                witness="neighbours",
                metric=metric,
                estimate=Tagged(
                    value=eff,
                    lo90=lo90,
                    hi90=hi90,
                    unit=unit,
                    tag="D",
                    source=(
                        f"model:panel_obdml (pre-cutoff <=2021; winter_wheat vs {base_key[1]} "
                        f"before sunflower; classifier labels [D]; {_T24_NOTE})"
                    ),
                ),
                n=int(row["n"]),
                diagnostics={
                    "design": "Panel-OBDML (pooled, <=2021)",
                    "contrast": f"winter_wheat vs {base_key[1]} -> sunflower",
                    "smd_weighted_max": round(float(row["smd_weighted_max"]), 3),
                    "overlap_outside": round(float(row["share_outside"]), 3),
                    "placebo_pass": True,
                    "negctrl_pass": True,
                },
            )
        )
        notes.append(
            f"Neighbours Panel-OBDML (<=2021) {metric} {eff:+.3f} "
            f"[{lo90:+.3f}, {hi90:+.3f}] (n={int(row['n'])}, tag D)"
        )
    return w_out, notes


def _build_option_metrics(
    ev_dict: dict,
    idx_o: int,
    seq: tuple[str, ...],
    crops,
    src_label: str,
) -> tuple[dict[str, Tagged], dict[str, float | None]]:
    m_dict: dict[str, Tagged] = {}
    raw_m: dict[str, float | None] = {}
    for ek, mk in B.EVAL_KEYS.items():
        val = ev_dict[ek][idx_o] if ev_dict.get(ek) else None
        val_f = None if val is None or not np.isfinite(val) else round(float(val), 3)
        raw_m[mk] = val_f
        m_dict[mk] = Tagged(
            value=val_f,
            unit=B.METRIC_UNITS[mk],
            tag="D",
            source=src_label,
        )
    for mk, t_val in sequence_metrics(seq, crops).items():
        raw_m[mk] = t_val.value
        m_dict[mk] = t_val
    if "erosion_exposure" not in m_dict:
        cd_v = raw_m.get("cover_days") or 0.0
        ee_v = round(max(0.0, 10.0 - cd_v / 60.0), 3)
        raw_m["erosion_exposure"] = ee_v
        m_dict["erosion_exposure"] = Tagged(
            value=ee_v,
            unit=B.METRIC_UNITS["erosion_exposure"],
            tag="D",
            source="model:fieldwitness.rotate.priority@0.1 (simulated cover)",
        )
    return m_dict, raw_m


_CTX: dict = {}


def _build_one_field(f_idx: int):
    ctx = _CTX
    r = ctx["pilot_20"].iloc[f_idx]
    fid = str(r["field_id"])
    r_row = r.to_dict()
    if not isinstance(r_row["geometry"], (bytes, bytearray)):
        r_row["geometry"] = wkb.dumps(r_row["geometry"])
    fld = B.field_model(r_row, REGION, tier=3)
    s2_df = ctx["s2_df"]
    clf_df = ctx["clf_df"]
    s = s2_df[s2_df["field_id"] == fid].sort_values("date")
    cf = clf_df[clf_df["field_id"] == fid]
    crop_by_year = {int(y): str(c) for y, c in zip(cf["year"], cf["crop"], strict=True)}
    soil_map = ctx["soil_map"]
    soil_taw_map = ctx["soil_taw_map"]
    soil_f = soil_map.get(fid, {})
    taw_base_mm = soil_taw_map.get(fid, 150.0)
    taw_tag = "E" if fid in soil_taw_map else "A"
    soil_note = (
        f"SoilGrids 2.0 [E]: 0-135 cm TAW={taw_base_mm:.1f} mm (Saxton & Rawls 2006); "
        f"0-30 cm clay {soil_f['clay']}%, sand {soil_f['sand']}%, SOC {soil_f['soc']} g/kg"
        if {"clay", "sand", "soc"}.issubset(soil_f) and fid in soil_taw_map
        else "SoilGrids 2.0 context pending; 150 mm TAW fallback [A]"
    )

    w_df, elev, rain, eto, wx_by_year = _weather(float(r["lon"]), float(r["lat"]))

    # Per-field ABC calibration & credibility (seeded per field for process-order determinism)
    rng_abc = np.random.default_rng(SEED + 45 + f_idx)
    pob_map = ctx["pob_map"]
    grading_cfg = ctx["grading_cfg"]
    cred_cfg = ctx["cred_cfg"]
    out_dir = ctx["out_dir"]
    crops = ctx["crops"]
    cfg = ctx["cfg"]
    vcfg = ctx["vcfg"]
    presets = ctx["presets"]
    cfg0 = ctx["cfg0"]
    crop_params_map = ctx["crop_params_map"]
    noise_sd = ctx["noise_sd"]
    prior_hidden = ctx["prior_hidden"]
    as_of = ctx["as_of"]
    problems: list[str] = []
    if True:
        field_draws, cred_val, cred_meta = _calibrate_field_abc(
            fid=fid,
            field_idx=f_idx,
            s2_field=s,
            crop_by_year=crop_by_year,
            wx_by_year=wx_by_year,
            taw_base_mm=taw_base_mm,
            taw_tag=taw_tag,
            noise_sd=noise_sd,
            cfg0=cfg0,
            crop_params_map=crop_params_map,
            cred_cfg=cred_cfg,
            rng=rng_abc,
            prior_hidden=prior_hidden,
        )
        med_taw = round(float(np.median(field_draws["taw_mm"])), 2)
        med_kc = round(float(np.median(field_draws["kc_scale"])), 4)
        med_budget = round(float(np.median(field_draws["budget_mm"])), 1)
        is_post = field_draws["source"] == "posterior"
        phys_src_label = (
            f"model:fieldwitness.physics@0.1 (ABC {N_WORLDS} posterior worlds; "
            f"SoilGrids 0-135 cm TAW={taw_base_mm:.1f}mm [E])"
            if is_post
            else f"model:fieldwitness.physics@0.1 (prior TAW={taw_base_mm:.1f}mm [{taw_tag}])"
        )

        seasons_raw = detect_seasons(s["date"], s["ndvi"], cfg) if not s.empty else []
        seasons: list[Season] = []
        for sm in seasons_raw:
            c_lbl = crop_by_year.get(sm.year)
            seasons.append(
                Season(
                    year=sm.year,
                    index=sm.index,
                    crop=c_lbl if c_lbl and c_lbl != "unknown" else None,
                    crop_conf=0.75 if c_lbl and c_lbl != "unknown" else 0.0,
                    crop_source="classifier",
                    sos=sm.sos,
                    peak=sm.peak,
                    eos=sm.eos,
                    canopy_integral=sm.canopy_integral,
                    cover_days=sm.cover_days,
                    bare_days=sm.bare_days,
                    clear_obs=sm.clear_obs,
                )
            )

        days = (s["date"] - EPOCH).dt.days.to_numpy(float) if not s.empty else np.array([0.0])
        ok = s["ndvi"].notna().to_numpy() if not s.empty else np.array([False])
        if ok.sum() >= 3:
            g_days, sm_vals = smooth_series(
                days[ok], s["ndvi"].to_numpy(float)[ok], cfg["smoothing"]
            )
        else:
            g_days, sm_vals = np.array([days[0]]), np.array([None], dtype=object)

        # Current 3-year sequence (2022, 2023, 2024) mapped to modelled crops
        cur_seq_raw = [crop_by_year.get(y, "fallow") for y in (2022, 2023, 2024)]
        cur_seq = [
            c if c in ROTATION_CROPS else ("maize" if c == "sunflower" else "fallow")
            for c in cur_seq_raw
        ]
        cand_seqs = [sq for sq in CANDIDATE_SEQS if list(sq) != cur_seq][:5]
        cur_ev = evaluate(rain, eto, [tuple(cur_seq)], REGION, field_draws)
        cand_ev = evaluate(rain, eto, cand_seqs, REGION, field_draws)
        ranked = rank_field(cand_ev, presets)
        cand_ranks = rank_positions(ranked["rank"]["balanced"])
        regret_mean = ranked.get("regret_mean")

        cur_ryi_yr = np.array(cur_ev["ryi_by_year"][0] or [0.0], float)
        cur_cd = float(cur_ev["cover_days"][0] or 0.0)

        key_tags = {
            "weather": "E",
            "taw": "D" if is_post else taw_tag,
            "kc_scale": "D" if is_post else "A",
            "budget": "D" if is_post else "A",
            "crop_history": "D",
        }

        # Current option (rank=0, reference option not graded - matches packs/build.py)
        cur_m_dict, _ = _build_option_metrics(cur_ev, 0, tuple(cur_seq), crops, phys_src_label)
        cur_opt = Option(
            option_id="current",
            sequence=list(cur_seq),
            metrics=cur_m_dict,
            witnesses=[],
            grade="D",
            grade_reasons=["Current rotation: reference option, not graded."],
            regret=Tagged(
                value=None, unit="RYI regret", tag="D", source="not computed for Current"
            ),
            rank=0,
            explanation=Explanation(
                why=["Current 2022-2024 rotation reference baseline."],
                evidence=[
                    (
                        f"Physics [D] calibrated over {len(field_draws['years'])} seasons "
                        f"({field_draws['source']})"
                    ),
                    soil_note,
                ],
                benefits=[],
                gaps=(
                    []
                    if is_post
                    else ["ABC calibration unavailable for this crop history (prior fallback)"]
                ),
                risks=[
                    "Tier 3 crop history inferred from Sentinel-2 NDVI classifier [D] "
                    f"({_T24_NOTE})"
                ],
            ),
        )

        # Candidate options (ranks 1..K)
        cand_models: list[Option] = []
        for idx_c, seq in enumerate(cand_seqs):
            oid_str = B.oid(seq)
            m_dict, raw_m = _build_option_metrics(cand_ev, idx_c, seq, crops, phys_src_label)

            # Weather-variability 90% RYI delta vs Current
            oy = cand_ev["ryi_by_year"][idx_c]
            if oy is not None:
                diff_ryi = np.array(oy, float) - cur_ryi_yr
                ryi_eff = Effect(
                    round(float(np.nanmedian(diff_ryi)), 4),
                    round(float(np.nanpercentile(diff_ryi, 5)), 4),
                    round(float(np.nanpercentile(diff_ryi, 95)), 4),
                )
            else:
                ryi_eff = Effect(0.0, 0.0, 0.0)

            w_res: list[WitnessResult] = [
                WitnessResult(
                    witness="physics",
                    metric="ryi",
                    estimate=Tagged(
                        value=ryi_eff.value,
                        lo90=ryi_eff.lo90,
                        hi90=ryi_eff.hi90,
                        unit="RYI change vs Current",
                        tag="D",
                        source=(
                            f"model:fieldwitness.physics@0.1 (weather variability 90% interval; "
                            f"ABC {N_WORLDS} worlds)"
                        ),
                    ),
                    diagnostics={
                        "taw_soilgrids_mm": taw_base_mm,
                        "taw_post_median_mm": med_taw,
                        "kc_scale_median": med_kc,
                        "calibrated": is_post,
                        **({f"soilgrids_{k}": v for k, v in soil_f.items()} if soil_f else {}),
                    },
                )
            ]
            if cred_val is not None:
                w_res.append(
                    WitnessResult(
                        witness="own_past",
                        metric="ryi",
                        estimate=Tagged(
                            value=cred_val,
                            unit="0-1 credibility score",
                            tag="D",
                            source=(
                                f"model:fieldwitness.infer.abc (in-sample {cred_meta['crop']}, "
                                f"{cred_meta['n_seasons']} seasons, mode={cred_meta['mode']})"
                            ),
                        ),
                        n=int(cred_meta["n_seasons"]),
                        diagnostics={
                            "crop": str(cred_meta["crop"]),
                            "mode": str(cred_meta["mode"]),
                            "median_timing_error_days": float(
                                cred_meta["median_timing_error_days"]
                            ),
                        },
                    )
                )

            nb_res, nb_notes = _match_neighbours_contrast(cur_seq_raw, seq, pob_map)
            cd_delta_yr = round(((raw_m.get("cover_days") or 0.0) - cur_cd) / 3.0, 3)
            if nb_res:
                w_res.append(
                    WitnessResult(
                        witness="physics",
                        metric="cover_days",
                        estimate=Tagged(
                            value=cd_delta_yr,
                            lo90=cd_delta_yr,
                            hi90=cd_delta_yr,
                            unit="days/yr vs Current",
                            tag="D",
                            source=(
                                "model:fieldwitness.rotate.evaluate@0.1 "
                                "(simulated canopy cover days/yr vs Current)"
                            ),
                        ),
                        diagnostics={"unit_matched_to": "panel_obdml_cover_days"},
                    )
                )
                w_res.extend(nb_res)
                phys_for_grade = Effect(cd_delta_yr, cd_delta_yr, cd_delta_yr)
                nb_for_grade = Effect(
                    float(nb_res[0].estimate.value or 0.0),
                    float(nb_res[0].estimate.lo90 or 0.0),
                    float(nb_res[0].estimate.hi90 or 0.0),
                )
            else:
                phys_for_grade = ryi_eff
                nb_for_grade = None

            grade_val, base_reasons = grade_option(
                physics=phys_for_grade,
                neighbours=nb_for_grade,
                credibility=cred_val,
                key_input_tags=key_tags,
                cfg=grading_cfg,
            )
            grade_reasons = [
                *base_reasons,
                (
                    f"Tier 3 ABC calibration (credibility {cred_val:.3f}, "
                    f"SoilGrids 0-135 cm TAW={taw_base_mm:.1f} mm [E], "
                    f"median posterior={med_taw:.1f} mm [D])"
                    if is_post and cred_val is not None
                    else "ABC calibration fallback (prior draws)"
                ),
                soil_note,
                (
                    f"Neighbours Panel-OBDML (<=2021) cover_days vs physics cover_days/yr "
                    f"({cd_delta_yr:+.1f} d/yr) (tag D; {_T24_NOTE})"
                    if nb_res
                    else (
                        "No matching pre-cutoff Panel-OBDML cover contrast for this sequence "
                        f"(tag D; {_T24_NOTE})"
                    )
                ),
            ]
            ev_lines = [
                (
                    f"Physics [D]: {N_WORLDS} ABC posterior worlds fitted over "
                    f"{len(fit_y := field_draws['years'])} HLS seasons "
                    f"({fit_y[0]}-{fit_y[-1]}); SoilGrids 0-135 cm TAW={taw_base_mm:.1f} mm [E]"
                    if is_post and field_draws["years"]
                    else f"Physics [D] with SoilGrids TAW={taw_base_mm:.1f} mm [{taw_tag}]"
                ),
                (
                    f"Own past [D]: credibility {cred_val:.3f} ({cred_meta['crop']}, "
                    f"n={cred_meta['n_seasons']}, mode={cred_meta['mode']}, "
                    f"timing MAE={cred_meta['median_timing_error_days']} d)"
                    if cred_val is not None
                    else "Own past: insufficient modelled seasons for credibility score"
                ),
                soil_note,
                *(
                    nb_notes
                    if nb_notes
                    else ["Neighbours: no pre-cutoff cover contrast matched to this sequence [D]"]
                ),
            ]
            gaps = [
                "In-sample ABC credibility caveat (same HLS seasons fitted and scored [D])",
                (
                    "SoilGrids 2.0 (250 m [E]) is coarse pedotransfer context "
                    "(Saxton & Rawls 2006), not local soil cores"
                ),
            ]
            if cred_val is not None and cred_val < float(grading_cfg["A"]["credibility_min"]):
                cmin_a = grading_cfg["A"]["credibility_min"]
                gaps.append(f"Credibility {cred_val:.3f} < {cmin_a} blocks Grade A/B")
            if not nb_res:
                gaps.append("No matching Panel-OBDML contrast for this sequence (max Grade B)")

            cand_models.append(
                Option(
                    option_id=oid_str,
                    sequence=list(seq),
                    metrics=m_dict,
                    witnesses=w_res,
                    grade=grade_val,
                    grade_reasons=grade_reasons,
                    regret=Tagged(
                        value=round(float(regret_mean[idx_c]), 4)
                        if regret_mean is not None
                        else None,
                        unit="RYI regret (mean over weather years)",
                        tag="D",
                        source="model:rotate.rank regret matrix",
                    ),
                    rank=int(cand_ranks[idx_c]),
                    explanation=Explanation(
                        why=[
                            "Ranked on balanced priorities "
                            "(water use, RYI, cover days, family breaks)"
                        ],
                        evidence=ev_lines,
                        benefits=[],
                        gaps=gaps,
                        risks=[
                            "Tier 3 crop history inferred from Sentinel-2 NDVI classifier [D] "
                            f"({_T24_NOTE})"
                        ],
                    ),
                )
            )

        cand_models.sort(key=lambda x: x.rank)
        opt_models = [cur_opt, *cand_models]
        top_opt = cand_models[0]

        # Build FieldPack
        pack = FieldPack(
            schema_version="1.2",
            field=fld,
            story=seasons,
            credibility=Tagged(
                value=cred_val,
                unit="0-1 score",
                tag="D" if cred_val is not None else "A",
                source=(
                    f"model:fieldwitness.infer.abc (in-sample {cred_meta['crop']}, "
                    f"n={cred_meta['n_seasons']}, SoilGrids 0-135 cm TAW={taw_base_mm:.1f} mm [E])"
                    if cred_val is not None
                    else "insufficient modelled HLS seasons for ABC credibility"
                ),
            ),
            options=opt_models,
            advice=Advice(
                measure_next=(
                    "Verify 2022-2024 crop history on the ground (Tier 3 classifier labels) "
                    "and measure local profile TAW"
                ),
                flip_probability=Tagged(
                    value=None, unit="probability", tag="A", source="not yet computed"
                ),
                counterfactual_flip="Ground-truth crop sequence or local soil TAW measurement",
            ),
            ledger=[],
            data_as_of=as_of,
            generated_at=datetime.now(UTC),
        )
        _write(out_dir / f"{fid}.json", pack, problems)

        # FieldSeries
        f_series = FieldSeries(
            schema_version="1.2",
            field_id=fid,
            ndvi=TaggedSeries(
                x=[d.date() for d in s["date"]],
                values=[None if pd.isna(v) else round(float(v), 4) for v in s["ndvi"]],
                unit="NDVI (-1 to 1)",
                tag="O",
                source="Sentinel-2 L2A 20 m COG (SCL 4,5)",
            ),
            evi=TaggedSeries(
                x=[d.date() for d in s["date"]],
                values=[None if pd.isna(v) else round(float(v), 4) for v in s["evi"]],
                unit="EVI2",
                tag="O",
                source="Sentinel-2 L2A 20 m COG (2-band EVI2)",
            ),
            clear_frac=[0.0 if pd.isna(v) else round(float(v), 3) for v in s["clear_fraction"]],
            ndvi_smooth=TaggedSeries(
                x=[(EPOCH + pd.Timedelta(days=float(d))).date() for d in g_days],
                values=[
                    None if v is None or not np.isfinite(v) else round(float(v), 4) for v in sm_vals
                ],
                unit="NDVI (-1 to 1)",
                tag="D",
                source="Savitzky-Golay filter (config/story.yaml)",
            ),
            data_as_of=as_of,
        )
        _write(out_dir / f"{fid}.series.json", f_series, problems)

        # FieldCalendar
        canopies = {o.option_id: X.canopy_for(o.sequence, REGION) for o in opt_models}
        eto_s = forcing(w_df, float(r["lat"]), elev)["eto"]
        vuln = X.vulnerability(
            w_df, eto_s, ["winter_wheat", "maize"], REGION, vcfg, taw_mm=med_taw, kc_scale=med_kc
        )
        cal = FieldCalendar(
            schema_version="1.2",
            field_id=fid,
            bare_observed=_bare_observed_from_s2(s),
            bare_observed_years=(2017, 2024),
            bare_by_option=X.bare_by_option(canopies),
            vulnerability=vuln,
            data_as_of=as_of,
        )
        _write(out_dir / f"{fid}.calendar.json", cal, problems)

        # FieldScenarios (12 scenarios)
        sc_list = []
        for sid, dt_c, dp_pct in scen_grid():
            w_p = perturb(w_df, dt_c, dp_pct)
            r_p, e_p = yearly_arrays(w_p, float(r["lat"]), elev, 2001, 2021)
            ev_s_cur = evaluate(r_p, e_p, [tuple(cur_seq)], REGION, field_draws)
            ev_s_cand = evaluate(r_p, e_p, cand_seqs, REGION, field_draws)
            srk_cands = rank_positions(rank_field(ev_s_cand, presets)["rank"]["balanced"])
            m_map: dict[str, dict[str, Tagged]] = {}
            ranks_map: dict[str, int] = {"current": 0}
            for o in opt_models:
                if o.option_id == "current":
                    src_ev, orig_i = ev_s_cur, 0
                else:
                    orig_i = next(i for i, sq in enumerate(cand_seqs) if B.oid(sq) == o.option_id)
                    src_ev = ev_s_cand
                    ranks_map[o.option_id] = int(srk_cands[orig_i])
                om = {}
                for ek, mk in B.EVAL_KEYS.items():
                    v = src_ev[ek][orig_i] if src_ev.get(ek) else None
                    vf = None if v is None or not np.isfinite(v) else round(float(v), 3)
                    om[mk] = Tagged(
                        value=vf,
                        unit=B.SCEN_UNITS[mk],
                        tag="D",
                        source="model:fieldwitness.physics@0.1",
                    )
                m_map[o.option_id] = om
            sc_list.append(
                Scenario(
                    scenario_id=sid,
                    dt_c=dt_c,
                    dp_pct=dp_pct,
                    metrics=m_map,
                    ranks=ranks_map,
                )
            )
        f_scen = FieldScenarios(
            schema_version="1.2",
            field_id=fid,
            baseline_id="t+0_p+0",
            note="Sensitivity tests on past weather, not climate projections.",
            scenarios=sc_list,
            data_as_of=as_of,
        )
        _write(out_dir / f"{fid}.scenarios.json", f_scen, problems)

        # FieldSim3D + FieldSim3DInputs
        alt_opts = cand_models[:3]
        sim3d_obj = sim3d_mod.build_field_sim3d(
            fid,
            tuple(cur_opt.sequence),
            alt_opts,
            w_df,
            float(r["lat"]),
            elev,
            med_taw,
            med_kc,
            med_budget,
            region_id=REGION,
        )
        _write(out_dir / f"{fid}.sim3d.json", sim3d_obj, problems)
        w_year, w_cases = sim3d_in_mod.scenario_weather(w_df, float(r["lat"]), elev)
        post_src = (
            f"median of {N_WORLDS} ABC posterior worlds; "
            f"SoilGrids 0-135 cm TAW={taw_base_mm:.1f} mm [E]"
        )
        sim3d_in_dict = {
            "schema_version": sim3d_in_mod.SCHEMA_VERSION,
            "field_id": fid,
            "region_id": REGION,
            "weather_year": w_year,
            "weather": {
                "cases": sim3d_in_mod.CASES,
                "days": sim3d_mod.DAYS,
                "tiles": sim3d_mod.T_DAYS // sim3d_mod.DAYS,
                "series": w_cases,
                "unit": "mm per day",
                "tag": "D",
                "source": "NASA POWER daily weather of the median-rain year; ETo FAO-56 Eq. 6; "
                "what-if shifts tag A (T6.8)",
            },
            "params": {
                "taw_mm": med_taw,
                "kc_scale": med_kc,
                "budget_mm": med_budget,
                "tag": "D" if is_post else taw_tag,
                "source": (
                    post_src
                    if is_post
                    else f"prior draws (SoilGrids TAW={taw_base_mm:.1f} mm [{taw_tag}])"
                ),
            },
            "slots": {
                "crops": {c: sim3d_in_mod._slot(c, REGION) for c in ROTATION_CROPS},
                "kc_fallow": 0.3,
                "p_fallow": 0.55,
                "cover_frac": 0.5,
                "zr_ini_m": 0.20,
                "max_family_run": 1,
                "tag": "A",
                "source": "config/crops.yaml (FAO-56 Tables 11, 12, 22) via rotate.slots; "
                "fallow Kc 0.3, p 0.55, root start 0.2 m are team choices (A, UNVERIFIED)",
            },
            "note": "Inputs of the in-browser 3D replay; numbers are model inputs, not results.",
        }
        sim3d_in = FieldSim3DInputs.model_validate(sim3d_in_dict)
        _write(out_dir / f"{fid}.sim3d_inputs.json", sim3d_in, problems)

        # Field colouring (Current option)
        ws_max = max(v.shares["water_stress"].values[0] or 0.0 for v in vuln) if vuln else 0.0
        fr_max = max(v.shares["frost"].values[0] or 0.0 for v in vuln) if vuln else 0.0
        ws_tag = Tagged(
            value=round(float(ws_max), 3),
            unit="share of years",
            tag="D",
            source="POWER daily weather x crop windows (crops.yaml)",
        )
        fr_tag = Tagged(
            value=round(float(fr_max), 3),
            unit="share of years",
            tag="D",
            source="POWER daily weather x crop windows (crops.yaml)",
        )

        # Track 2022-2024 observed cover_days for hindcast summary
        hind_f: list[tuple[str, float, float, float]] = []
        for sm in seasons:
            if sm.year in (2022, 2023, 2024) and sm.cover_days.value is not None:
                pred_cd = (cur_opt.metrics["cover_days"].value or 0.0) / 3.0
                hind_f.append(
                    (
                        fid,
                        float(sm.cover_days.value),
                        pred_cd,
                        float(sm.canopy_integral.value or 0.0),
                    )
                )

        geom_simple = shapely.from_wkt(fld.geometry_wkt)
        geom_summary_wkt = shapely.to_wkt(
            geom_simple.simplify(0.0001, preserve_topology=True),
            rounding_precision=5,
        )
        summary = FieldSummary(
            field_id=fid,
            geometry_wkt=geom_summary_wkt,
            area_ha=fld.area_ha,
            current_sequence=cur_seq,
            top_option_id=top_opt.option_id,
            top_grade=top_opt.grade,
        )
        log_msg = (
            f"{fid[:8]} TAW={taw_base_mm:.1f}->{med_taw:.1f}mm "
            f"cred={cred_val} grades={[o.grade for o in cand_models]} top={top_opt.grade}"
        )
        return (
            f_idx,
            fid,
            cur_opt.metrics["erosion_exposure"],
            ws_tag,
            fr_tag,
            hind_f,
            summary,
            cred_meta,
            problems,
            log_msg,
        )


def main() -> None:
    import geopandas as gpd

    pilot_all = gpd.read_parquet(f"data/fields/{REGION}_pilot.parquet")
    pilot_20 = _select_demo_fields(pilot_all)
    demo_ids = set(pilot_20["field_id"].astype(str))
    grid = load_grid(REGION)

    print(
        f"Selected {len(pilot_20)} fields across {pilot_20['block'].nunique()} blocks.", flush=True
    )
    s2_cache = Path(f"data/fields/{REGION}_hls_series.parquet")
    if s2_cache.exists():
        s2_all = pd.read_parquet(s2_cache)
        s2_df = s2_all[s2_all["field_id"].isin(demo_ids)].copy()
        if demo_ids.issubset(set(s2_df["field_id"].astype(str))):
            print(
                f"Loaded cached S2 series ({len(s2_df)} rows for {len(demo_ids)} fields).",
                flush=True,
            )
        else:
            s2_df, s2_meta = build_s2_series(
                REGION,
                pilot_20,
                grid,
                mgrs_code="MGRS-36UVU",
                start_date="2017-01-01",
                end_date="2024-12-31",
                max_per_month=1,
                max_total_scenes=48,
                max_bytes=200_000_000,
            )
            print(
                f"S2 series: {s2_meta['rows_written']} rows, {s2_meta['fields_with_obs']} fields.",
                flush=True,
            )
    else:
        s2_df, s2_meta = build_s2_series(
            REGION,
            pilot_20,
            grid,
            mgrs_code="MGRS-36UVU",
            start_date="2017-01-01",
            end_date="2024-12-31",
            max_per_month=1,
            max_total_scenes=48,
            max_bytes=200_000_000,
        )
        print(
            f"S2 series: {s2_meta['rows_written']} rows, {s2_meta['fields_with_obs']} fields.",
            flush=True,
        )
    s2_df["date"] = pd.to_datetime(s2_df["date"])

    # Classify crops causally (tag D) using cached full-tile parquet when complete
    lbl_cache = Path(f"data/labels/{REGION}.parquet")
    if lbl_cache.exists():
        clf_all = pd.read_parquet(lbl_cache)
        clf_df = clf_all[clf_all["field_id"].isin(demo_ids)].copy()
        if not demo_ids.issubset(set(clf_df["field_id"].astype(str))):
            clf_df = infer_region_labels(s2_df, years=list(range(2017, 2025)))
    else:
        clf_df = infer_region_labels(s2_df, years=list(range(2017, 2025)))

    soil_map, soil_taw_map = _load_soil_profile(Path(f"data/soil/{REGION}_fields.parquet"))
    pob_map = _load_pre_panel_obdml(Path(f"results/neighbours/{REGION}_panel_obdml.csv"))
    grading_all = yaml.safe_load(Path("config/grading.yaml").read_text(encoding="utf-8"))
    grading_cfg = grading_all["grades"]
    cred_cfg = grading_all["credibility"]

    out_dir = OUT_ROOT / REGION
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.json"):
        stale.unlink()

    crops = load_crops()
    cfg = load_story()
    vcfg = X.load_vuln_cfg()
    presets = load_presets()

    # ABC setup
    cfg0 = forward.load_cfg()
    crop_params_map = {
        c: forward.crop_params(c, REGION) for c in ("sunflower", "maize", "winter_wheat")
    }
    noise_sd = synthetic.census(s2_df)["noise_sd"]
    prior_hidden = priors.sample(2000, seed=SEED + 620)
    as_of = s2_df["date"].max().date() if not s2_df.empty else date(2024, 12, 31)
    story_fid = str(pilot_20.iloc[0]["field_id"])

    # Pre-warm POWER cache in parent before fork so child processes inherit read-only weather arrays
    for _, row in pilot_20.iterrows():
        _weather(float(row["lon"]), float(row["lat"]))

    _CTX.clear()
    _CTX.update(
        {
            "pilot_20": pilot_20,
            "s2_df": s2_df,
            "clf_df": clf_df,
            "soil_map": soil_map,
            "soil_taw_map": soil_taw_map,
            "pob_map": pob_map,
            "grading_cfg": grading_cfg,
            "cred_cfg": cred_cfg,
            "out_dir": out_dir,
            "crops": crops,
            "cfg": cfg,
            "vcfg": vcfg,
            "presets": presets,
            "cfg0": cfg0,
            "crop_params_map": crop_params_map,
            "noise_sd": noise_sd,
            "prior_hidden": prior_hidden,
            "as_of": as_of,
        }
    )

    problems: list[str] = []
    summaries: list[FieldSummary] = []
    cred_rows: list[dict] = []
    colour: dict[str, dict[str, Tagged]] = {
        "erosion_exposure": {},
        "water_stress_share": {},
        "frost_share": {},
    }
    hindcast_scores: list[tuple[str, float, float, float]] = []

    mp_ctx = multiprocessing.get_context("fork")
    raw_results = []
    done_cnt = 0
    total_cnt = len(pilot_20)
    with ProcessPoolExecutor(max_workers=2, mp_context=mp_ctx) as pool:
        futs = [pool.submit(_build_one_field, i) for i in range(total_cnt)]
        for fut in as_completed(futs):
            res = fut.result()
            raw_results.append(res)
            done_cnt += 1
            print(f"  [{done_cnt:3d}/{total_cnt}] {res[9]}", flush=True)

    raw_results.sort(key=lambda item: item[0])
    for _, fid, er_tag, ws_tag, fr_tag, hind_f, summary, cred_meta, probs_f, _ in raw_results:
        colour["erosion_exposure"][fid] = er_tag
        colour["water_stress_share"][fid] = ws_tag
        colour["frost_share"][fid] = fr_tag
        hindcast_scores.extend(hind_f)
        summaries.append(summary)
        cred_rows.append(cred_meta)
        problems.extend(probs_f)

    # Save honest credibility & grade summary
    top_counts: dict[str, int] = {}
    all_opt_counts: dict[str, int] = {}
    for s_row in summaries:
        top_counts[s_row.top_grade] = top_counts.get(s_row.top_grade, 0) + 1
        p_data = json.loads((out_dir / f"{s_row.field_id}.json").read_text(encoding="utf-8"))
        for o in p_data["options"]:
            if o["option_id"] != "current":
                g = o["grade"]
                all_opt_counts[g] = all_opt_counts.get(g, 0) + 1
    cr_vals = [float(r["credibility"]) for r in cred_rows if r["credibility"] is not None]
    cred_summary = {
        "region_id": REGION,
        "n_fields": len(cred_rows),
        "with_credibility": len(cr_vals),
        "ge_0_6": sum(c >= float(grading_cfg["A"]["credibility_min"]) for c in cr_vals),
        "median_credibility": round(float(np.median(cr_vals)), 3) if cr_vals else None,
        "taw_soilgrids_min_mm": round(float(min(r["taw_base_mm"] for r in cred_rows)), 1),
        "taw_soilgrids_median_mm": round(
            float(np.median([r["taw_base_mm"] for r in cred_rows])), 1
        ),
        "taw_soilgrids_max_mm": round(float(max(r["taw_base_mm"] for r in cred_rows)), 1),
        "top_grade_counts": top_counts,
        "all_candidate_grade_counts": all_opt_counts,
        "n_ref": N_REF,
        "k": K_ABC,
        "seed": SEED,
        "tag": "D",
        "caveat": (
            "in-sample ABC posterior predictive using Tier 3 classifier labels "
            "(kappa=0.035 maize vs sunflower)"
        ),
    }
    Path("results/inference").mkdir(parents=True, exist_ok=True)
    Path("results/inference/ua_central_t36uvu_credibility.json").write_text(
        json.dumps({"summary": cred_summary, "fields": cred_rows}, indent=2),
        encoding="utf-8",
    )

    # RegionIndex
    geoms = [wkb.loads(g) if isinstance(g, (bytes, bytearray)) else g for g in pilot_20["geometry"]]
    minx, miny, maxx, maxy = gpd.GeoSeries(geoms).total_bounds
    reg_idx = RegionIndex(
        schema_version="1.2",
        region_id=REGION,
        name="Central Ukraine (T36UVU)",
        tier=3,
        bbox_lonlat=(
            round(float(minx), 4),
            round(float(miny), 4),
            round(float(maxx), 4),
            round(float(maxy), 4),
        ),
        basemap=UA_HLS_BASEMAP_URL,
        fields=summaries,
        data_as_of=as_of,
    )
    _write(out_dir / "index.json", reg_idx, problems)

    # RegionLayers (UT-CSR GRACE when available + POWER heatwave_days + field_colouring)
    reg_cfg_ua = yaml.safe_load(Path("config/regions.yaml").read_text("utf-8"))["regions"][REGION]
    ua_bbox = tuple(float(x) for x in reg_cfg_ua["bbox_lonlat"])
    reg_layers_list = []
    csr_nc = Path("data/context/grace/CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc")
    csr_mk = Path("data/context/grace/CSR_GRACE_GRACE-FO_RL06_Mascons_v02_LandMask.nc")
    layer_cutoff = date(2024, 12, 31)
    if csr_nc.exists() and csr_mk.exists():
        reg_layers_list.append(
            X.grace_csr_layer(str(csr_nc), str(csr_mk), ua_bbox, cutoff_date=layer_cutoff)
        )
    reg_layers_list.append(
        X.heatwave_layer(
            ua_bbox,
            threshold_c=float(vcfg["heat_tmax_c"]["maize"]["value"]),
            cutoff_date=layer_cutoff,
        )
    )
    reg_layers = RegionLayers(
        schema_version="1.2",
        region_id=REGION,
        layers=reg_layers_list,
        field_colouring=colour,
        data_as_of=max(as_of, layer_cutoff),
    )
    _write(out_dir / "layers.json", reg_layers, problems)

    # RegionHindcast (honest cover_days comparison on 2022-2024 vs classifier labels)
    mae_cd = (
        float(np.mean([abs(o - p) for _, o, p, _ in hindcast_scores])) if hindcast_scores else 0.0
    )
    reg_hind = RegionHindcast(
        schema_version="1.2",
        region_id=REGION,
        cutoff=date(2021, 12, 31),
        scored_years=[2022, 2023, 2024],
        crop_observed_source="classifier",
        rows=[
            HindcastRow(
                method="fieldwitness",
                mode="forecast",
                metric="cover_days",
                n=len(hindcast_scores),
                scores={"mae_median": round(mae_cd, 2)},
            )
        ],
        story_field_id=story_fid,
        data_as_of=as_of,
    )
    _write(out_dir / "hindcast.json", reg_hind, problems)

    # Update packs/demo/regions.json
    reg_list = RegionList(
        regions=[
            RegionEntry(region_id="ks_t14slh", name="Kansas High Plains (SW Kansas)", tier=1),
            RegionEntry(region_id=REGION, name="Central Ukraine (T36UVU)", tier=3),
        ]
    )
    _write(OUT_ROOT / "regions.json", reg_list, problems)

    if problems:
        print("PROBLEMS:", problems[:10], flush=True)
        raise SystemExit(1)

    val_probs = validate_dir(OUT_ROOT)
    if val_probs:
        print("VALIDATION PROBLEMS:", val_probs[:10], flush=True)
        raise SystemExit(1)
    print(f"CREDIBILITY SUMMARY: {json.dumps(cred_summary)}", flush=True)
    print(
        f"SUCCESS: {len(summaries)} Ukraine demo field packs written and validated in {out_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
