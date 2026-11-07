"""T8.1 pack builder: pure functions that turn pipeline results into schema models.

Inputs are the result files of T2.x-T6.x (dicts already loaded); nothing here reads data/ or the
network, so the functions are unit-testable. Every number goes into `Tagged` / `TaggedSeries`
(CLAUDE.md rule 3); `check_tagged` is run by the caller.
Units and tags below are team choices (A, UNVERIFIED) where noted.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import shapely
from shapely import wkb

from fieldwitness.rotate.explain import Delta, ExplainInput, explain
from fieldwitness.rotate.flip import advice
from fieldwitness.schemas import (
    SEQUENCE_ONLY_METRICS,
    Field,
    FieldPack,
    FieldScenarios,
    FieldSeries,
    FieldSummary,
    Option,
    Scenario,
    Season,
    Tagged,
    TaggedSeries,
    WitnessResult,
)
from fieldwitness.story.seasons import EPOCH, SeasonMetrics

SCHEMA_VERSION = "1.2"
PRESET = "balanced"  # default weights (T6.3); regret and rank in the pack use this preset
MODEL_VERSION = "fieldwitness-0.1"

# unit per Option metric (evaluate.py docstring; priority.py for the last six)
METRIC_UNITS = {
    "water_use_mm": "mm per rotation",
    "irrigation_mm": "mm per rotation",
    "ryi": "relative index per rotation year (0-1)",
    "cover_days": "days per rotation",
    "bad_year_water_mm": "mm per rotation (CVaR10, upper tail)",
    "bad_year_ryi": "relative index per rotation year (CVaR10, lower tail)",
    "legume_share": "share of seasons",
    "family_breaks": "count",
    "deep_root_share": "share of seasons",
    "forage_value": "relative (0-1)",
    "erosion_exposure": "relative, within-field comparison only",
    "residue_proxy": "relative (0-1)",
}
SCEN_UNITS = {
    "water_use_mm": "mm",
    "irrigation_mm": "mm",
    "ryi": "RYI",
    "cover_days": "d",
    "bad_year_water_mm": "mm",
    "bad_year_ryi": "RYI",
}
# evaluation.json key -> Option metric name
EVAL_KEYS = {
    "water_use_mm": "water_use_mm",
    "irrigation_mm": "irrigation_mm",
    "ryi": "ryi",
    "cover_days": "cover_days",
    "cvar10_water_mm": "bad_year_water_mm",
    "cvar10_ryi": "bad_year_ryi",
}


def oid(seq: list[str] | tuple[str, ...]) -> str:
    return "|".join(seq)


def _nan_none(v) -> float | None:
    return None if v is None or not np.isfinite(v) else float(v)


def field_model(row: pd.Series, region_id: str, tier: int = 1) -> Field:
    """`Field` from a pilot-table row (geometry is WKB bytes)."""
    geom = wkb.loads(row["geometry"])
    return Field(
        field_id=str(row["field_id"]),
        geometry_wkt=shapely.to_wkt(geom, rounding_precision=6),
        area_ha=float(row["area_ha"]),
        region_id=region_id,
        tier=tier,
        boundary_source=row["boundary_source"],
        scale_flags={"HLS": bool(row["hls_scale_flag"]), "POWER": True, "SoilGrids": True},
        interior_pixels=int(row["interior_px"]),
    )


def story(seasons: list[SeasonMetrics], crop_by_year: dict[int, str]) -> list[Season]:
    """Detected seasons with the CSB label of their harvest year (tag E, a label, conf 1.0)."""
    out = []
    for s in seasons:
        crop = crop_by_year.get(s.year)
        out.append(
            Season(
                year=s.year,
                index=s.index,
                crop=crop,
                crop_conf=1.0 if crop else 0.0,
                crop_source="label",
                sos=s.sos,
                peak=s.peak,
                eos=s.eos,
                canopy_integral=s.canopy_integral,
                cover_days=s.cover_days,
                bare_days=s.bare_days,
                clear_obs=s.clear_obs,
            )
        )
    return out


def credibility_tagged(c: float | None) -> Tagged:
    return Tagged(
        value=c,
        unit="score 0-1 (0 = no agreement)",
        tag="D",
        source="infer credibility (in-sample, ABC posterior vs HLS history); null = not assessable",
    )


def field_series(
    field_id: str, obs: pd.DataFrame, grid_days: np.ndarray, smooth: np.ndarray, as_of: date
) -> FieldSeries:
    """`<field_id>.series.json`: observed NDVI/EVI (tag O) and the smoothed curve (tag D)."""
    obs = obs.sort_values("date")
    x = [d.date() for d in pd.to_datetime(obs["date"])]
    src = "HLS L30+S30 via AppEEARS, median over interior pixels"

    def ts(vals, unit: str) -> TaggedSeries:
        return TaggedSeries(
            x=x, values=[_nan_none(v) for v in vals], unit=unit, tag="O", source=src
        )

    sx = [(EPOCH + pd.Timedelta(days=int(d))).date() for d in grid_days]
    return FieldSeries(
        schema_version=SCHEMA_VERSION,
        field_id=field_id,
        ndvi=ts(obs["ndvi"], "NDVI"),
        evi=ts(obs["evi"], "EVI"),
        clear_frac=[round(float(v), 3) for v in obs["clear_fraction"]],
        ndvi_smooth=TaggedSeries(
            x=sx,
            values=[_nan_none(v) for v in smooth],
            unit="NDVI",
            tag="D",
            source="Savitzky-Golay smoothing of observed NDVI (story.smooth)",
        ),
        data_as_of=as_of,
    )


def options(
    fid: str,
    ev: dict,
    rk: dict,
    gr: dict | None,
    cur_seq: list[str],
    cur_metrics: dict[str, float] | None,
    cred: float | None,
    pri: dict,
    fam: dict[str, str | None],
    ky_ok: dict[str, bool],
    scale_flag: bool,
) -> list[Option]:
    """Current option first (rank 0), then every candidate. `gr` None = field not graded."""
    tag = ev["tag"]
    src = f"rotate.evaluate over {ev['n_samples']} samples ({ev['source']})"
    key_tags = (gr or {}).get("tags", {})
    gmap = {oid(g["option"]): g for g in (gr or {}).get("options", [])}
    cur_id = oid(cur_seq)
    out: list[Option] = []

    def tagged(name: str, v: float | None, t: str, s: str) -> Tagged:
        return Tagged(value=_nan_none(v), unit=METRIC_UNITS[name], tag=t, source=s)

    # --- Current ---
    cm = {}
    if cur_metrics:
        cm = {
            n: tagged(n, cur_metrics[k], tag, src) for k, n in EVAL_KEYS.items() if k in cur_metrics
        }
    cp = pri.get(cur_id, {})
    for n, m in cp.items():
        cm[n] = tagged(n, m["value"], m["tag"], "rotate.priority (sequence-only / simulated cover)")
    ex = explain(
        ExplainInput(
            sequence=tuple(cur_seq),
            current=tuple(cur_seq),
            grade="D",
            grade_reasons=("Current rotation: reference option, not graded.",),
            credibility=cred,
            key_input_tags=key_tags,
            family=fam,
            ky_verified=ky_ok,
            scale_flag=scale_flag,
            is_current=True,
        )
    )
    out.append(
        Option(
            option_id="current",
            sequence=list(cur_seq),
            metrics=cm,
            witnesses=[],
            grade="D",
            grade_reasons=["Current rotation: reference option, not graded."],
            regret=Tagged(
                value=None, unit="RYI regret", tag="D", source="not computed for Current"
            ),
            rank=0,
            explanation=ex,
        )
    )
    # --- candidates ---
    ranks = rk["rank"][PRESET]
    regret_mean = rk.get("regret_mean")
    pareto = rk["pareto"]
    for i, cand in enumerate(ev["candidates"]):
        o = oid(cand)
        g = gmap.get(o)
        metrics = {
            n: tagged(n, ev[k][i], tag, src) for k, n in EVAL_KEYS.items() if ev[k][i] is not None
        }
        for n, m in pri.get(o, {}).items():
            metrics[n] = tagged(n, m["value"], m["tag"], "rotate.priority")
        witnesses, deltas = [], {}
        grade, reasons = "D", ["Field not graded: Current rotation cannot be simulated."]
        if g:
            grade, reasons = g["grade"], g["reasons"]
            v, lo, hi = g["physics_ryi_effect"]
            eff = Tagged(
                value=v,
                lo90=lo,
                hi90=hi,
                unit="RYI change vs Current",
                tag=tag,
                source="physics witness, weather variability 90 % interval (A, UNVERIFIED)",
            )
            witnesses.append(
                WitnessResult(witness="physics", metric="ryi", estimate=eff, diagnostics={})
            )
            deltas["ryi"] = Delta(v, lo, hi, "RYI change per rotation year", tag)
        if cred is not None:
            witnesses.append(
                WitnessResult(
                    witness="own_past",
                    metric="ryi",
                    estimate=credibility_tagged(cred),
                    diagnostics={"role": "credibility of the physics for this field"},
                )
            )
        ex = explain(
            ExplainInput(
                sequence=tuple(cand),
                current=tuple(cur_seq),
                grade=grade,
                grade_reasons=tuple(reasons),
                credibility=cred,
                key_input_tags=key_tags,
                deltas=deltas,
                profile=PRESET,
                rank=int(ranks[i]),
                pareto=bool(pareto[i]),
                family=fam,
                ky_verified=ky_ok,
                scale_flag=scale_flag,
                has_neighbours=False,
            )
        )
        out.append(
            Option(
                option_id=o,
                sequence=list(cand),
                metrics=metrics,
                witnesses=witnesses,
                grade=grade,
                grade_reasons=list(reasons),
                regret=Tagged(
                    value=regret_mean[i] if regret_mean else None,
                    unit="RYI regret (mean over weather years)",
                    tag=tag,
                    source="rotate.rank regret matrix",
                ),
                rank=int(ranks[i]),
                explanation=ex,
            )
        )
    return out


def field_pack(
    fld: Field,
    seasons: list[Season],
    cred: float | None,
    opts: list[Option],
    flip_res: dict,
    as_of: date,
    now: datetime | None = None,
) -> FieldPack:
    return FieldPack(
        schema_version=SCHEMA_VERSION,
        field=fld,
        story=seasons,
        credibility=credibility_tagged(cred),
        options=opts,
        advice=advice(flip_res, PRESET),
        ledger=[],  # Phase 7 (hindcast ledger) not built yet
        data_as_of=as_of,
        generated_at=now or datetime.now(UTC),
    )


def field_scenarios(
    fid: str, sc: dict, cands: list[list[str]], tag: str, as_of: date
) -> FieldScenarios:
    """`sc` = scenarios.json entry: scenario_id -> metric -> per-candidate list (+ 'rank')."""
    out = []
    for sid, mets in sc.items():
        dt = float(sid.split("_")[0][1:])
        dp = float(sid.split("_")[1][1:])
        metrics: dict[str, dict[str, Tagged]] = {}
        for i, c in enumerate(cands):
            m = {}
            for k, v in mets.items():
                if k not in EVAL_KEYS:  # skips rank_balanced
                    continue
                name = EVAL_KEYS[k]
                if name in SEQUENCE_ONLY_METRICS or v[i] is None:
                    continue
                # short unit/source and rounded values on purpose: 12 x 36 x 6 values per file
                # must stay < 300 KB (full units are on the baseline Option metrics)
                val = _nan_none(v[i])
                m[name] = Tagged(
                    value=None if val is None else round(val, 4),
                    unit=SCEN_UNITS[name],
                    tag=tag,
                    source="scenarios",
                )
            metrics[oid(c)] = m
        ranks = mets.get("rank_balanced") or []
        out.append(
            Scenario(
                scenario_id=sid,
                dt_c=dt,
                dp_pct=dp,
                metrics=metrics,
                ranks={oid(c): int(r) for c, r in zip(cands, ranks, strict=False)} if ranks else {},
            )
        )
    return FieldScenarios(
        schema_version=SCHEMA_VERSION,
        field_id=fid,
        baseline_id="t+0_p+0",
        note="Sensitivity tests on past weather, not climate projections.",
        scenarios=out,
        data_as_of=as_of,
    )


def field_summary(fld: Field, cur_seq: list[str], top: Option) -> FieldSummary:
    return FieldSummary(
        field_id=fld.field_id,
        geometry_wkt=fld.geometry_wkt,
        area_ha=fld.area_ha,
        current_sequence=cur_seq,
        top_option_id=top.option_id,
        top_grade=top.grade,
    )
