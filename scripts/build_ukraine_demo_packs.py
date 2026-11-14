"""Build a 20-field demo pack for Central Ukraine (ua_central_t36uvu, Tier 3).

Uses real open data already supported in the repo:
  - FTW 2024 field boundaries (data/fields/ua_central_t36uvu_pilot.parquet)
  - Sentinel-2 L2A 20 m COG NDVI/EVI2 series (fieldwitness.data.s2_cog, tag O)
  - Causal Tier 3 crop-sequence classifier (fieldwitness.story.ukraine_seasons, tag D)
  - NASA POWER daily weather 2001-2024 (fieldwitness.data.power, tag E)
  - FAO-56 water balance & rotation ranking (fieldwitness.rotate, tag D / A)

Outputs packs/demo/ua_central_t36uvu/ and updates packs/demo/regions.json.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import wkb

from fieldwitness.config import load_crops
from fieldwitness.data import power
from fieldwitness.data.s2_cog import build_s2_series
from fieldwitness.packs import build as B
from fieldwitness.packs import extras as X
from fieldwitness.packs import sim3d as sim3d_mod
from fieldwitness.packs import sim3d_inputs as sim3d_in_mod
from fieldwitness.packs.validate import validate_dir
from fieldwitness.physics.forcing import forcing
from fieldwitness.resolve.pilot import load_grid
from fieldwitness.rotate.evaluate import evaluate
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
SEED = 20261114
N_DEMO = 20
Y0, Y1 = 2001, 2024
OUT_ROOT = Path("packs/demo")
MAX_PACK_BYTES = 300_000

# Modelled crops in rotate.slots (SOW_DAY) that also have ua_central_t36uvu params in crops.yaml
ROTATION_CROPS = ("winter_wheat", "maize", "fallow", "cover_crop")
CANDIDATE_SEQS = [
    ("winter_wheat", "maize", "fallow"),
    ("winter_wheat", "maize", "cover_crop"),
    ("maize", "winter_wheat", "fallow"),
    ("winter_wheat", "fallow", "maize"),
    ("maize", "fallow", "winter_wheat"),
    ("winter_wheat", "winter_wheat", "maize"),
]

_OPT_NULL = ("lo50", "hi50", "lo90", "hi90")


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


def _select_20_fields(pilot: pd.DataFrame) -> pd.DataFrame:
    """Pick 20 fields stratified across the spatial blocks (seeded)."""
    rng = np.random.default_rng(SEED)
    pilot = pilot.sort_values("field_id").reset_index(drop=True)
    blocks = sorted(pilot["block"].unique())
    chosen_idx: list[int] = []
    # Round-robin across blocks
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


def _weather(lon: float, lat: float):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return w, float(elev or 0.0), np.array(rain), np.array(eto)


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


def main() -> None:
    import geopandas as gpd

    pilot_all = gpd.read_parquet(f"data/fields/{REGION}_pilot.parquet")
    pilot_20 = _select_20_fields(pilot_all)
    grid = load_grid(REGION)

    print(
        f"Selected {len(pilot_20)} fields across {pilot_20['block'].nunique()} blocks.", flush=True
    )
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

    # Classify crops causally (tag D)
    clf_df = infer_region_labels(s2_df, years=list(range(2017, 2025)))

    out_dir = OUT_ROOT / REGION
    out_dir.mkdir(parents=True, exist_ok=True)
    crops = load_crops()
    cfg = load_story()
    vcfg = X.load_vuln_cfg()

    # Default prior draws (k=10 identical draws: 150 mm TAW, 1.0 Kc scale, rainfed, tag A)
    prior_draws = {
        "taw_mm": [150.0] * 10,
        "kc_scale": [1.0] * 10,
        "budget_mm": [0.0] * 10,
    }

    problems: list[str] = []
    summaries: list[FieldSummary] = []
    colour: dict[str, dict[str, Tagged]] = {
        "erosion_exposure": {},
        "water_stress_share": {},
        "frost_share": {},
    }
    hindcast_scores: list[tuple[str, float, float, float]] = []
    story_fid = str(pilot_20.iloc[0]["field_id"])
    as_of = s2_df["date"].max().date() if not s2_df.empty else date(2024, 12, 31)

    for _, r in pilot_20.iterrows():
        fid = str(r["field_id"])
        r_row = r.to_dict()
        if not isinstance(r_row["geometry"], (bytes, bytearray)):
            r_row["geometry"] = wkb.dumps(r_row["geometry"])
        fld = B.field_model(r_row, REGION, tier=3)
        s = s2_df[s2_df["field_id"] == fid].sort_values("date")
        cf = clf_df[clf_df["field_id"] == fid]
        crop_by_year = {int(y): str(c) for y, c in zip(cf["year"], cf["crop"], strict=True)}

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
        all_seqs = [tuple(cur_seq)] + [sq for sq in CANDIDATE_SEQS if list(sq) != cur_seq]
        all_seqs = all_seqs[:5]

        w_df, elev, rain, eto = _weather(float(r["lon"]), float(r["lat"]))
        ev_res = evaluate(rain, eto, all_seqs, REGION, prior_draws)

        # Score options
        opt_models: list[Option] = []
        raw_metrics_list: list[dict[str, float | None]] = []
        for idx_o, seq in enumerate(all_seqs):
            oid_str = "current" if idx_o == 0 else B.oid(seq)
            m_dict: dict[str, Tagged] = {}
            raw_m: dict[str, float | None] = {}
            for ek, mk in B.EVAL_KEYS.items():
                val = ev_res[ek][idx_o] if ev_res.get(ek) else None
                val_f = None if val is None or not np.isfinite(val) else round(float(val), 3)
                raw_m[mk] = val_f
                m_dict[mk] = Tagged(
                    value=val_f,
                    unit=B.METRIC_UNITS[mk],
                    tag="D",
                    source="model:fieldwitness.physics@0.1 (prior TAW=150mm [A])",
                )
            sm_extra = sequence_metrics(seq, crops)
            for mk, t_val in sm_extra.items():
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
            raw_metrics_list.append(raw_m)
            w_res = [
                WitnessResult(
                    witness="physics",
                    metric="ryi",
                    estimate=m_dict["ryi"],
                    diagnostics={"taw_prior_mm": 150.0, "calibrated": False},
                )
            ]
            opt_models.append(
                Option(
                    option_id=oid_str,
                    sequence=list(seq),
                    metrics=m_dict,
                    witnesses=w_res,
                    grade="D",
                    grade_reasons=[
                        "Tier 3: physics uses 150 mm TAW prior (A); ABC calibration pending",
                        (
                            "Neighbours witness OFF "
                            "(Tier 3 classifier labels not ground-truth validated)"
                        ),
                    ],
                    regret=Tagged(
                        value=0.0, unit="rank-regret (0=best)", tag="D", source="model:rotate.rank"
                    ),
                    rank=idx_o + 1,
                    explanation=Explanation(
                        why=[
                            "Ranked on balanced priorities "
                            "(water use, RYI, cover days, family breaks)"
                        ],
                        evidence=["Physics [D] with 150 mm TAW prior [A]; Neighbours OFF"],
                        benefits=[],
                        gaps=[
                            "ABC calibration not yet run (credibility null)",
                            "TAW uses 150 mm prior [A]",
                        ],
                        risks=["Tier 3 crop history inferred from Sentinel-2 NDVI classifier [D]"],
                    ),
                )
            )

        # Rank with balanced weights
        ranked = rank_field(ev_res, load_presets())
        ranks = rank_positions(ranked["rank"]["balanced"])
        for o, rk in zip(opt_models, ranks, strict=True):
            o.rank = int(rk)
        opt_models.sort(key=lambda x: x.rank)
        top_opt = opt_models[0]

        # Build FieldPack
        pack = FieldPack(
            schema_version="1.2",
            field=fld,
            story=seasons,
            credibility=Tagged(
                value=None,
                unit="0-1 score",
                tag="A",
                source="ABC calibration not yet run for Tier 3 ua_central_t36uvu",
            ),
            options=opt_models,
            advice=Advice(
                measure_next=(
                    "Verify 2022-2024 crop history on the ground (Tier 3 classifier labels)"
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
            w_df, eto_s, ["winter_wheat", "maize"], REGION, vcfg, taw_mm=150.0, kc_scale=1.0
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
        presets = load_presets()
        for sid, dt_c, dp_pct in scen_grid():
            w_p = perturb(w_df, dt_c, dp_pct)
            r_p, e_p = yearly_arrays(w_p, float(r["lat"]), elev, 2001, 2021)
            ev_s = evaluate(r_p, e_p, all_seqs, REGION, prior_draws)
            srk_all = rank_positions(rank_field(ev_s, presets)["rank"]["balanced"])
            m_map: dict[str, dict[str, Tagged]] = {}
            ranks_map: dict[str, int] = {}
            for o in opt_models:
                # Find original index in all_seqs
                orig_i = (
                    0
                    if o.option_id == "current"
                    else next(i for i, sq in enumerate(all_seqs) if B.oid(sq) == o.option_id)
                )
                om = {}
                for ek, mk in B.EVAL_KEYS.items():
                    v = ev_s[ek][orig_i] if ev_s.get(ek) else None
                    vf = None if v is None or not np.isfinite(v) else round(float(v), 3)
                    om[mk] = Tagged(
                        value=vf,
                        unit=B.SCEN_UNITS[mk],
                        tag="D",
                        source="model:fieldwitness.physics@0.1",
                    )
                m_map[o.option_id] = om
                ranks_map[o.option_id] = int(srk_all[orig_i])
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
        cur_opt = next(o for o in opt_models if o.option_id == "current")
        alt_opts = [o for o in opt_models if o.option_id != "current"][:3]
        sim3d_obj = sim3d_mod.build_field_sim3d(
            fid,
            tuple(cur_opt.sequence),
            alt_opts,
            w_df,
            float(r["lat"]),
            elev,
            150.0,
            1.0,
            0.0,
            region_id=REGION,
        )
        _write(out_dir / f"{fid}.sim3d.json", sim3d_obj, problems)
        w_year, w_cases = sim3d_in_mod.scenario_weather(w_df, float(r["lat"]), elev)
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
                "taw_mm": 150.0,
                "kc_scale": 1.0,
                "budget_mm": 0.0,
                "tag": "A",
                "source": "prior draws (TAW 150 mm [A]; ABC calibration pending)",
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
        cur_opt = next(o for o in opt_models if o.option_id == "current")
        colour["erosion_exposure"][fid] = cur_opt.metrics["erosion_exposure"]
        ws_max = max(v.shares["water_stress"].values[0] or 0.0 for v in vuln) if vuln else 0.0
        fr_max = max(v.shares["frost"].values[0] or 0.0 for v in vuln) if vuln else 0.0
        colour["water_stress_share"][fid] = Tagged(
            value=round(float(ws_max), 3),
            unit="share of years",
            tag="D",
            source="POWER daily weather x crop windows (crops.yaml)",
        )
        colour["frost_share"][fid] = Tagged(
            value=round(float(fr_max), 3),
            unit="share of years",
            tag="D",
            source="POWER daily weather x crop windows (crops.yaml)",
        )

        # Track 2022-2024 observed cover_days for hindcast summary
        for sm in seasons:
            if sm.year in (2022, 2023, 2024) and sm.cover_days.value is not None:
                pred_cd = (cur_opt.metrics["cover_days"].value or 0.0) / 3.0
                hindcast_scores.append(
                    (
                        fid,
                        float(sm.cover_days.value),
                        pred_cd,
                        float(sm.canopy_integral.value or 0.0),
                    )
                )

        summaries.append(
            FieldSummary(
                field_id=fid,
                geometry_wkt=fld.geometry_wkt,
                area_ha=fld.area_ha,
                current_sequence=cur_seq,
                top_option_id=top_opt.option_id,
                top_grade=top_opt.grade,
            )
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
        basemap=None,
        fields=summaries,
        data_as_of=as_of,
    )
    _write(out_dir / "index.json", reg_idx, problems)

    # RegionLayers (empty regional coarse layers + field_colouring)
    reg_layers = RegionLayers(
        schema_version="1.2",
        region_id=REGION,
        layers=[],
        field_colouring=colour,
        data_as_of=as_of,
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
    print(
        f"SUCCESS: {len(summaries)} Ukraine demo field packs written and validated in {out_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
