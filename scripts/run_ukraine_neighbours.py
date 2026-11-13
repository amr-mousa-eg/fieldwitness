"""Phase 2 Neighbours Witness diagnostics for Central Ukraine (ua_central_t36uvu, Tier 3).

Runs three causal designs on `data/neighbours/ua_central_t36uvu_field_season.parquet`:
  1. Primary DML (`fieldwitness.neighbours.dml` + `diagnostics`)
  2. Matching-History DML (`fieldwitness.neighbours.matching`, identical `prev2_crop`)
  3. Distance-Adjusted Propensity Score Matching (`fieldwitness.neighbours.dapsm`, UTM 36N)

Both periods are evaluated:
  - `pre_cutoff_le_2021` (primary hindcast-clean run: `year <= 2021`,
    `dry_season` recomputed strictly on `<= 2021` precipitation)
  - `full_2018_2024` (full-record sensitivity run)

All crop states carry `crop_source = "classifier"` (tag D, Tier 3 causal S2 L2A phenology).
Saves:
  - results/neighbours/ua_central_t36uvu_dml.csv
  - results/neighbours/ua_central_t36uvu_matching.csv
  - results/neighbours/ua_central_t36uvu_dapsm.json
  - results/neighbours/ua_central_t36uvu_report.md

Usage: uv run python -u scripts/run_ukraine_neighbours.py [--stage all|dml_pre|mdap_pre|...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.neighbours import dapsm, diagnostics, dml
from fieldwitness.neighbours.diagnostics import (
    OVERLAP_MAX_SHARE,
    PS_HIGH,
    PS_LOW,
    SMD_MAX,
    add_lags,
)
from fieldwitness.neighbours.dml import CONFOUNDERS, MIN_BLOCKS, OUTCOMES, fit_plr
from fieldwitness.neighbours.matching import (
    MIN_ARM,
    diagnose_matching_contrast,
    fit_matching_contrast,
    matching_contrast_list,
    matching_design,
)

REGION = "ua_central_t36uvu"
EPSG = "EPSG:32636"
CUT_YEAR = 2021
TABLE = Path(f"data/neighbours/{REGION}_field_season.parquet")
PILOT = Path(f"data/fields/{REGION}_pilot.parquet")
CACHE_DIR = Path("data/neighbours")
KS_DML = Path("results/neighbours/diagnostics.csv")
KS_MATCH = Path("results/neighbours/matching_diagnostics.csv")
KS_DAPSM = Path("results/neighbours/dapsm.json")
OUT = Path("results/neighbours")
STRATA = ("all", "wet", "dry")
CHECKS = ("overlap", "balance", "placebo", "negctrl")


def prepare_period(df: pd.DataFrame, cut_year: int | None) -> pd.DataFrame:
    sub = df.copy() if cut_year is None else df[df["year"] <= cut_year].copy()
    med = sub.groupby("field_id")["season_precip_mm"].transform("median")
    sub["dry_season"] = (sub["season_precip_mm"] < med).where(sub["season_precip_mm"].notna())
    return sub.reset_index(drop=True)


def _sample(
    df: pd.DataFrame, crop: str, prev2: str, a: str, b: str, st: str, arm_col: str, y: str
) -> tuple[pd.DataFrame, np.ndarray, bool]:
    s = df[(df["crop"] == crop) & (df["prev2_crop"] == prev2) & df[arm_col].isin([a, b])]
    if st != "all":
        s = s[s["dry_season"] == (st == "dry")]
    s = s.dropna(subset=[y, *CONFOUNDERS]).reset_index(drop=True)
    d = (s[arm_col] == a).to_numpy()
    ok = (
        int(d.sum()) >= MIN_ARM
        and int((~d).sum()) >= MIN_ARM
        and int(s["block"].nunique()) >= MIN_BLOCKS
    )
    return s, d, ok


def _propensity(s: pd.DataFrame, d: np.ndarray, y: str) -> np.ndarray:
    x = matching_design(s).reset_index(drop=True)
    data = pd.concat([x, s[y].rename("y"), pd.Series(d.astype(float), name="d")], axis=1)
    plr = fit_plr(data, x.columns, s["block"].to_numpy())
    return np.asarray(plr.predictions["ml_m"])[:, 0, 0]


def _scaled_dist(s: pd.DataFrame, pos: dict[str, int], dmax: float, dist: np.ndarray) -> np.ndarray:
    i = s["field_id"].map(pos).to_numpy()
    return dist[np.ix_(i, i)] / dmax


def _counts(series: pd.Series) -> dict:
    vc = series.value_counts().to_dict()
    k = int(vc.get("pass", 0))
    n = int(k + vc.get("fail", 0))
    lo, hi = dapsm.wilson(k, n)
    return {
        "pass": k,
        "fail": int(vc.get("fail", 0)),
        "untested": int(vc.get("untested", 0)),
        "pass_share_of_tested": round(k / n, 4) if n else None,
        "wilson95": [
            round(lo, 4) if np.isfinite(lo) else None,
            round(hi, 4) if np.isfinite(hi) else None,
        ],
    }


def summarize_dml(diag_df: pd.DataFrame, period_name: str) -> dict:
    fit = diag_df[diag_df["effect"].notna()]
    return {
        "period": period_name,
        "total_rows": int(len(diag_df)),
        "fitted": int(len(fit)),
        "overlap": _counts(fit["overlap_status"]) if len(fit) else {},
        "balance": _counts(fit["balance_status"]) if len(fit) else {},
        "placebo": _counts(fit["placebo_status"]) if len(fit) else {},
        "negctrl": _counts(fit["negctrl_status"]) if len(fit) else {},
        "median_smd_raw_max": float(fit["smd_raw_max"].median()) if len(fit) else None,
        "median_smd_weighted_max": float(fit["smd_weighted_max"].median()) if len(fit) else None,
        "evidence": int(fit["show_as_evidence"].sum()) if len(fit) else 0,
    }


def run_dml_period(dfp: pd.DataFrame, pname: str) -> tuple[pd.DataFrame, dict]:
    eff = dml.run_all(dfp)
    diag = diagnostics.run_diagnostics(dfp, eff)
    diag["period"] = pname
    diag["crop_source"] = "classifier"
    diag["tag"] = "D"
    summ = summarize_dml(diag, pname)
    print(f"  Primary DML {pname}: {summ}", flush=True)
    return diag, summ


def _key_str(key: tuple[str, str, str, str, str, str]) -> str:
    return "|".join(key)


def _fit_matching_chunk(
    df: pd.DataFrame,
    lags: pd.DataFrame,
    contrasts: list[tuple[str, str, str, str]],
    pos: dict[str, int],
    dist: np.ndarray,
    dmax: float,
    period_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, list[float]]]:
    match_effect_rows, match_diag_rows = [], []
    rows, grid = [], []
    ps_cache: dict[str, list[float]] = {}

    for crop, prev2, a, b in contrasts:
        for y in OUTCOMES:
            for st in STRATA:
                key = (crop, prev2, a, b, y, st)
                base = {
                    "crop": crop,
                    "prev2_crop": prev2,
                    "treated_prev": a,
                    "reference_prev": b,
                    "outcome": y,
                    "stratum": st,
                }
                row, plr = fit_matching_contrast(df, crop, prev2, a, b, y, st)
                old = diagnose_matching_contrast(lags, row, plr=plr)
                match_effect_rows.append(row)
                match_diag_rows.append(old)

                rec = {
                    **base,
                    "n": row["n"],
                    "fitted": plr is not None,
                    "old_effect": row["effect"],
                    "old_ci_low": row["ci_low"],
                    "old_ci_high": row["ci_high"],
                    "old_smd_weighted_max": old.get("smd_weighted_max", np.nan),
                    "old_evidence": bool(old["show_as_evidence"]),
                }
                for c in CHECKS:
                    rec[f"old_{c}"] = old[f"{c}_status"]
                rows.append(rec)
                if plr is None:
                    continue

                s, d, _ = _sample(lags, crop, prev2, a, b, st, "prev_crop", y)
                ps = np.asarray(plr.predictions["ml_m"])[:, 0, 0]
                ds = _scaled_dist(s, pos, dmax, dist)
                x = matching_design(s)
                ps_cache[_key_str(key)] = ps.tolist()
                for w in dapsm.W_GRID:
                    m = dapsm.match(ps, ds, d, s["field_id"].to_numpy(), w)
                    smd = dapsm.smd_per_covariate(x, d, dapsm.match_weights(m, d))
                    grid.append(
                        {
                            **base,
                            "w": w,
                            "smd_max": float(smd.max()),
                            "worst_covariate": str(smd.idxmax()),
                            "n_pairs": int((m[d] >= 0).sum()),
                        }
                    )

    mdiag = pd.concat([pd.DataFrame(match_effect_rows), pd.DataFrame(match_diag_rows)], axis=1)
    mdiag["period"] = period_name
    mdiag["crop_source"] = "classifier"
    return mdiag, pd.DataFrame(rows), pd.DataFrame(grid), ps_cache


def _eval_dapsm_from_parts(
    df: pd.DataFrame,
    lags: pd.DataFrame,
    mdiag: pd.DataFrame,
    res_df: pd.DataFrame,
    grid_df: pd.DataFrame,
    ps_cache: dict[str, list[float]],
    pos: dict[str, int],
    dist: np.ndarray,
    dmax: float,
    period_name: str,
    n_contrasts: int,
) -> tuple[pd.DataFrame, dict, pd.DataFrame, dict]:
    msumm = summarize_dml(mdiag, period_name)
    print(f"  Matching DML {period_name}: {msumm}", flush=True)

    if grid_df.empty:
        dsumm = {
            "period": period_name,
            "rows_used": int(len(df)),
            "contrast_pairs": n_contrasts,
            "fitted": 0,
            "chosen_w": None,
            "w_grid_summary": [],
            "old_ipw": {},
            "dapsm": {},
            "dapsm_evidence": 0,
        }
        return mdiag, msumm, res_df, dsumm

    w_star = dapsm.choose_w(grid_df)
    new_rows = []
    for r in res_df.itertuples():
        key = (r.crop, r.prev2_crop, r.treated_prev, r.reference_prev, r.outcome, r.stratum)
        kstr = _key_str(key)
        out: dict[str, object] = {f"new_{c}": "untested" for c in CHECKS}
        if kstr in ps_cache:
            s, d, _ = _sample(lags, *key[:4], r.stratum, "prev_crop", r.outcome)
            ps = np.asarray(ps_cache[kstr], dtype=float)
            ds = _scaled_dist(s, pos, dmax, dist)
            share = float(np.mean((ps < PS_LOW) | (ps > PS_HIGH)))
            out["new_overlap"] = "pass" if share <= OVERLAP_MAX_SHARE else "fail"
            out["share_outside"] = share
            m = dapsm.match(ps, ds, d, s["field_id"].to_numpy(), w_star)
            smd = dapsm.smd_per_covariate(matching_design(s), d, dapsm.match_weights(m, d))
            out["new_smd_max"] = float(smd.max())
            out["new_worst_covariate"] = str(smd.idxmax())
            out["new_balance"] = "pass" if float(smd.max()) <= SMD_MAX else "fail"
            eff = dapsm.matched_effect(s[r.outcome].to_numpy(), m, d, s["block"].to_numpy())
            out.update(
                new_effect=eff["effect"],
                new_ci_low=eff["ci_low"],
                new_ci_high=eff["ci_high"],
                new_n_pairs=eff["n_pairs"],
            )
            for check, arm, yy in (
                ("placebo", "next_crop", r.outcome),
                ("negctrl", "prev_crop", f"{r.outcome}_lag2"),
            ):
                sp, dp, ok = _sample(lags, *key[:4], r.stratum, arm, yy)
                if not ok:
                    continue
                psp = _propensity(sp, dp, yy)
                mp = dapsm.match(
                    psp,
                    _scaled_dist(sp, pos, dmax, dist),
                    dp,
                    sp["field_id"].to_numpy(),
                    w_star,
                )
                e = dapsm.matched_effect(sp[yy].to_numpy(), mp, dp, sp["block"].to_numpy())
                out[f"new_{check}"] = e["status"]
                out.update(
                    {
                        f"{check}_effect": e["effect"],
                        f"{check}_ci_low": e["ci_low"],
                        f"{check}_ci_high": e["ci_high"],
                        f"{check}_n": len(sp),
                    }
                )
        new_rows.append(out)

    res_df = pd.concat([res_df, pd.DataFrame(new_rows)], axis=1)
    res_df["new_evidence"] = res_df[[f"new_{c}" for c in CHECKS]].eq("pass").all(axis=1)
    res_df["period"] = period_name
    res_df["tag"] = "D"

    fit = res_df[res_df["fitted"]]
    w_summ = (
        grid_df.groupby("w")
        .agg(
            median_smd_max=("smd_max", "median"),
            mean_smd_max=("smd_max", "mean"),
            n_pass_balance=("smd_max", lambda v: int((v <= SMD_MAX).sum())),
            n_contrasts=("smd_max", "size"),
        )
        .reset_index()
    )
    dsumm = {
        "period": period_name,
        "rows_used": int(len(df)),
        "fields_used": int(df["field_id"].nunique()),
        "blocks_used": int(df["block"].nunique()),
        "contrast_pairs": n_contrasts,
        "contrast_rows": int(len(res_df)),
        "fitted": int(len(fit)),
        "chosen_w": w_star,
        "w_grid_summary": w_summ.to_dict("records"),
        "old_ipw": {c: _counts(fit[f"old_{c}"]) for c in CHECKS},
        "old_ipw_evidence": int(fit["old_evidence"].sum()),
        "dapsm": {c: _counts(fit[f"new_{c}"]) for c in CHECKS},
        "dapsm_evidence": int(fit["new_evidence"].sum()),
        "dapsm_worst_covariates": fit["new_worst_covariate"].value_counts().to_dict(),
    }
    print(
        f"  DAPSM {period_name}: fitted={dsumm['fitted']}, w*={dsumm['chosen_w']}, "
        f"balance_pass={dsumm['dapsm'].get('balance', {}).get('pass', 0)}, "
        f"evidence={dsumm['dapsm_evidence']}",
        flush=True,
    )
    return mdiag, msumm, res_df, dsumm


def run_matching_and_dapsm_period(
    df: pd.DataFrame,
    pos: dict[str, int],
    dist: np.ndarray,
    dmax: float,
    period_name: str,
) -> tuple[pd.DataFrame, dict, pd.DataFrame, dict]:
    """Run Matching-History DML and DAPSM w-grid in one shared fit pass (zero duplicate PLRs)."""
    lags = add_lags(df)
    contrasts = matching_contrast_list(df)
    mdiag, res_df, grid_df, ps_cache = _fit_matching_chunk(
        df, lags, contrasts, pos, dist, dmax, period_name
    )
    return _eval_dapsm_from_parts(
        df, lags, mdiag, res_df, grid_df, ps_cache, pos, dist, dmax, period_name, len(contrasts)
    )


def write_outputs(
    raw_df: pd.DataFrame,
    pilot: pd.DataFrame,
    dmax: float,
    dml_frames: list[pd.DataFrame],
    match_frames: list[pd.DataFrame],
    dapsm_frames: list[pd.DataFrame],
    dml_summaries: dict[str, dict],
    match_summaries: dict[str, dict],
    dapsm_summaries: dict[str, dict],
) -> None:
    all_dml = pd.concat(dml_frames, ignore_index=True)
    all_match = pd.concat(match_frames, ignore_index=True)
    all_dapsm = pd.concat(dapsm_frames, ignore_index=True)

    all_dml.to_csv(OUT / f"{REGION}_dml.csv", index=False)
    all_match.to_csv(OUT / f"{REGION}_matching.csv", index=False)

    dapsm_doc = {
        "region_id": REGION,
        "tier": 3,
        "crop_source": "classifier (Tier 3 causal S2 L2A phenology + TWDTW, tag D)",
        "geometry": f"FTW boundaries ({len(pilot)} unique fields), centroid in {EPSG}",
        "max_pairwise_dist_km": round(dmax, 3),
        "primary_dml": dml_summaries,
        "matching_dml": match_summaries,
        "dapsm": dapsm_summaries,
        "passing_contrasts": {
            "primary_dml": all_dml[all_dml["show_as_evidence"]][
                [
                    "period",
                    "crop",
                    "treated_prev",
                    "reference_prev",
                    "outcome",
                    "stratum",
                    "effect",
                    "ci_low",
                    "ci_high",
                ]
            ].to_dict("records"),
            "matching_dml": all_match[all_match["show_as_evidence"]][
                [
                    "period",
                    "crop",
                    "prev2_crop",
                    "treated_prev",
                    "reference_prev",
                    "outcome",
                    "stratum",
                    "effect",
                    "ci_low",
                    "ci_high",
                ]
            ].to_dict("records"),
            "dapsm": all_dapsm[all_dapsm["new_evidence"]][
                [
                    "period",
                    "crop",
                    "prev2_crop",
                    "treated_prev",
                    "reference_prev",
                    "outcome",
                    "stratum",
                    "new_effect",
                    "new_ci_low",
                    "new_ci_high",
                ]
            ].to_dict("records"),
        },
    }
    (OUT / f"{REGION}_dapsm.json").write_text(json.dumps(dapsm_doc, indent=2), encoding="utf-8")

    # Side-by-side Kansas comparison numbers from repo artifacts
    ks_dml_df = pd.read_csv(KS_DML)
    ks_dml_fit = ks_dml_df[ks_dml_df["effect"].notna()]
    ks_match_df = pd.read_csv(KS_MATCH)
    ks_match_fit = ks_match_df[ks_match_df["effect"].notna()]
    ks_dap = json.loads(KS_DAPSM.read_text(encoding="utf-8"))

    pre_dml = dml_summaries["pre_cutoff_le_2021"]
    full_dml = dml_summaries["full_2018_2024"]
    pre_m = match_summaries["pre_cutoff_le_2021"]
    full_m = match_summaries["full_2018_2024"]
    pre_dap = dapsm_summaries["pre_cutoff_le_2021"]
    full_dap = dapsm_summaries["full_2018_2024"]

    total_pre_ev = pre_dml["evidence"] + pre_m["evidence"] + pre_dap["dapsm_evidence"]
    total_full_ev = full_dml["evidence"] + full_m["evidence"] + full_dap["dapsm_evidence"]

    def _ratio(d: dict, k: str) -> str:
        b = d[k]
        return f"{b['pass']}/{b['pass'] + b['fail']}"

    ok_ww_prev = int(
        (raw_df["canopy_integral"].notna() & (raw_df["prev_crop"] == "winter_wheat")).sum()
    )
    ok_ww_prev2 = int(
        (raw_df["canopy_integral"].notna() & (raw_df["prev2_crop"] == "winter_wheat")).sum()
    )
    pre_ww_prev = int(
        (
            (raw_df["year"] <= CUT_YEAR)
            & raw_df["canopy_integral"].notna()
            & (raw_df["prev_crop"] == "winter_wheat")
        ).sum()
    )

    lines = [
        (
            "# Neighbours Witness Evaluation — Central Ukraine (`ua_central_t36uvu`) "
            "vs Kansas (`ks_t14slh`)"
        ),
        "",
        "Executed with `scripts/run_ukraine_neighbours.py`.",
        "",
        "## Provenance & Tier 3 Caveat",
        "",
        (
            f"- **Region:** `{REGION}` (Central Ukraine, Kirovohrad oblast area, "
            f"HLS/S2 tile `{EPSG}`, Tier 3)."
        ),
        (
            f"- **Sample:** {len(pilot)} unique FTW pilot fields inside 2×2 Sentinel-2 L2A 20 m "
            f"COG window `tx in {{1,2}}, ty in {{7,8}}` spanning {raw_df['block'].nunique()} "
            f"10 km spatial blocks (area ≥ 5 ha, 0 scale-flagged)."
        ),
        (
            '- **Labels (`crop_source = "classifier"`, tag D):** Zero public multi-year ground '
            'labels exist (`labels.source == "none"`). Annual crop sequences '
            "(`winter_wheat`, `sunflower`, `maize`, `fallow`) were inferred strictly causally "
            "(`<= year-12-31`) from Sentinel-2 L2A 20 m NDVI via Savitzky–Golay phenology + "
            "Phase 1 TWDTW."
        ),
        (
            "- **Winter Wheat Outcome Coverage Note:** Under frozen `table.py`'s window rule "
            '(`WINDOWS["winter_wheat"] = (1, 196)` requiring ≥ 80% coverage across Jan 1–Jul 15), '
            '`crop == "winter_wheat"` outcome rows have `n = 0` in Central Ukraine because '
            "snow/winter cloud at `48.2°N` leaves Dec–Feb clear S2 observations sparse until "
            "~Mar 1 (DOY 60). Rather than loosening frozen thresholds, `winter_wheat` is "
            f"tested extensively as a preceding treatment (`prev_crop == winter_wheat`: "
            f"`n = {ok_ww_prev}` across 2018–2024, `n = {pre_ww_prev}` pre-cutoff `<= 2021`; "
            f"`prev2_crop == winter_wheat`: `n = {ok_ww_prev2}`)."
        ),
        (
            "- **Kansas baseline (`ks_t14slh`, Tier 1):** 200 CSB fields across 30 spatial blocks "
            'with USDA CSB ground labels (`crop_source = "label"`, tag E).'
        ),
        "",
        "## Headline Summary (Pre-cutoff `year <= 2021` vs Full `2018–2024` & Kansas)",
        "",
        (
            "| Design | Region & Period | Fitted rows | Overlap pass | Balance pass | "
            "Placebo pass | NegCtrl pass | **Evidence (all 4 pass)** |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| Primary DML (`dml.py`) | Kansas `ks_t14slh` (2018–2024) | {len(ks_dml_fit)} | "
            f"{(ks_dml_fit['overlap_status'] == 'pass').sum()}/{len(ks_dml_fit)} | "
            f"{(ks_dml_fit['balance_status'] == 'pass').sum()}/{len(ks_dml_fit)} | "
            f"{(ks_dml_fit['placebo_status'] == 'pass').sum()}/"
            f"{(ks_dml_fit['placebo_status'].isin(['pass', 'fail'])).sum()} | "
            f"{(ks_dml_fit['negctrl_status'] == 'pass').sum()}/"
            f"{(ks_dml_fit['negctrl_status'].isin(['pass', 'fail'])).sum()} | "
            f"**{(ks_dml_fit['show_as_evidence']).sum()}** |"
        ),
        (
            f"| Primary DML (`dml.py`) | Ukraine `{REGION}` (`<=2021`) | {pre_dml['fitted']} | "
            f"{pre_dml['overlap']['pass']}/{pre_dml['fitted']} | "
            f"{pre_dml['balance']['pass']}/{pre_dml['fitted']} | "
            f"{_ratio(pre_dml, 'placebo')} | {_ratio(pre_dml, 'negctrl')} | "
            f"**{pre_dml['evidence']}** |"
        ),
        (
            f"| Primary DML (`dml.py`) | Ukraine `{REGION}` (2018–2024) | {full_dml['fitted']} | "
            f"{full_dml['overlap']['pass']}/{full_dml['fitted']} | "
            f"{full_dml['balance']['pass']}/{full_dml['fitted']} | "
            f"{_ratio(full_dml, 'placebo')} | {_ratio(full_dml, 'negctrl')} | "
            f"**{full_dml['evidence']}** |"
        ),
        (
            f"| Matching DML (`matching.py`) | Kansas `ks_t14slh` (2018–2024) | "
            f"{len(ks_match_fit)} | "
            f"{(ks_match_fit['overlap_status'] == 'pass').sum()}/{len(ks_match_fit)} | "
            f"{(ks_match_fit['balance_status'] == 'pass').sum()}/{len(ks_match_fit)} | "
            f"{(ks_match_fit['placebo_status'] == 'pass').sum()}/"
            f"{(ks_match_fit['placebo_status'].isin(['pass', 'fail'])).sum()} | "
            f"{(ks_match_fit['negctrl_status'] == 'pass').sum()}/"
            f"{(ks_match_fit['negctrl_status'].isin(['pass', 'fail'])).sum()} | "
            f"**{(ks_match_fit['show_as_evidence']).sum()}** |"
        ),
        (
            f"| Matching DML (`matching.py`) | Ukraine `{REGION}` (`<=2021`) | "
            f"{pre_m['fitted']} | "
            f"{pre_m['overlap']['pass']}/{pre_m['fitted']} | "
            f"{pre_m['balance']['pass']}/{pre_m['fitted']} | "
            f"{_ratio(pre_m, 'placebo')} | {_ratio(pre_m, 'negctrl')} | "
            f"**{pre_m['evidence']}** |"
        ),
        (
            f"| Matching DML (`matching.py`) | Ukraine `{REGION}` (2018–2024) | "
            f"{full_m['fitted']} | "
            f"{full_m['overlap']['pass']}/{full_m['fitted']} | "
            f"{full_m['balance']['pass']}/{full_m['fitted']} | "
            f"{_ratio(full_m, 'placebo')} | {_ratio(full_m, 'negctrl')} | "
            f"**{full_m['evidence']}** |"
        ),
        (
            f"| DAPSM (`dapsm.py`) | Kansas `ks_t14slh` (`<=2021`, `w*={ks_dap['chosen_w']}`) | "
            f"{ks_dap['fitted']} | {ks_dap['dapsm']['overlap']['pass']}/{ks_dap['fitted']} | "
            f"{ks_dap['dapsm']['balance']['pass']}/{ks_dap['fitted']} | "
            f"0/0 ({ks_dap['dapsm']['placebo']['untested']} untested) | "
            f"0/0 ({ks_dap['dapsm']['negctrl']['untested']} untested) | "
            f"**{ks_dap['dapsm_evidence']}** |"
        ),
        (
            f"| DAPSM (`dapsm.py`) | Ukraine `{REGION}` (`<=2021`, `w*={pre_dap['chosen_w']}`) | "
            f"{pre_dap['fitted']} | {pre_dap['dapsm']['overlap']['pass']}/{pre_dap['fitted']} | "
            f"{pre_dap['dapsm']['balance']['pass']}/{pre_dap['fitted']} | "
            f"{_ratio(pre_dap['dapsm'], 'placebo')} | {_ratio(pre_dap['dapsm'], 'negctrl')} | "
            f"**{pre_dap['dapsm_evidence']}** |"
        ),
        (
            f"| DAPSM (`dapsm.py`) | Ukraine `{REGION}` (2018–2024, `w*={full_dap['chosen_w']}`) | "
            f"{full_dap['fitted']} | "
            f"{full_dap['dapsm']['overlap']['pass']}/{full_dap['fitted']} | "
            f"{full_dap['dapsm']['balance']['pass']}/{full_dap['fitted']} | "
            f"{_ratio(full_dap['dapsm'], 'placebo')} | {_ratio(full_dap['dapsm'], 'negctrl')} | "
            f"**{full_dap['dapsm_evidence']}** |"
        ),
        "",
        "## DAPSM w-Grid (`ua_central_t36uvu`, pre-cutoff `<= 2021`)",
        "",
        "| w | Median max \\|SMD\\| | Mean max \\|SMD\\| | Balance pass (≤ 0.25) |",
        "|---:|---:|---:|---:|",
    ]
    for row_w in pre_dap["w_grid_summary"]:
        lines.append(
            f"| {row_w['w']:.1f} | {row_w['median_smd_max']:.3f} | {row_w['mean_smd_max']:.3f} | "
            f"{row_w['n_pass_balance']}/{row_w['n_contrasts']} |"
        )

    lines.extend(["", "## Witness Status Verdict", ""])
    if total_pre_ev == 0 and total_full_ev == 0:
        lines.append(
            "- **Neighbours Witness remains OFF:** Zero contrasts across Primary DML, "
            "Matching DML, and DAPSM cleared all four pre-registered causal gates in Central "
            "Ukraine."
        )
    else:
        lines.append(
            f"- **Pre-registered gates cleared in Ukraine:** {total_pre_ev} pre-cutoff "
            f"(`<= 2021`) and {total_full_ev} full-period (`2018–2024`) contrast-outcome-stratum "
            "rows passed all four checks (overlap, balance, placebo, negative control)."
        )
        lines.append(
            "- **Critical Tier 3 Disclosure:** Because Ukraine crop states are inferred by an "
            'unvalidated NDVI classifier (`crop_source = "classifier"`, tag `D`) rather than '
            "ground labels, and `config/grading.yaml` + production Kansas packs "
            "(`app/public/packs/ks_t14slh/`) are locked, Neighbours stays OFF in grading until "
            "cross-validated against ground truth and explicitly approved."
        )
    lines.extend(["", "### Contrasts Passing All Four Gates", ""])
    any_pass = False
    for label, recs in dapsm_doc["passing_contrasts"].items():
        if recs:
            any_pass = True
            lines.append(f"#### {label} ({len(recs)} rows)")
            for rec in recs[:30]:
                eff_k = "new_effect" if "new_effect" in rec else "effect"
                lo_k = "new_ci_low" if "new_ci_low" in rec else "ci_low"
                hi_k = "new_ci_high" if "new_ci_high" in rec else "ci_high"
                prev2 = f" [prev2={rec['prev2_crop']}]" if "prev2_crop" in rec else ""
                lines.append(
                    f"- `{rec['period']}` | `{rec['crop']}`{prev2}: "
                    f"`{rec['treated_prev']}` vs `{rec['reference_prev']}` on "
                    f"`{rec['outcome']}` (`{rec['stratum']}`): "
                    f"**{rec[eff_k]:+.3f}** (95% CI [{rec[lo_k]:+.3f}, {rec[hi_k]:+.3f}])"
                )
            if len(recs) > 30:
                lines.append(f"- ... ({len(recs) - 30} more rows in CSV/JSON)")
            lines.append("")
    if not any_pass:
        lines.append("None (0 rows cleared all 4 gates across all 3 designs).")

    (OUT / f"{REGION}_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"\nWrote {REGION}_dml.csv, {REGION}_matching.csv, {REGION}_dapsm.json, {REGION}_report.md"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=(
            "all",
            "dml_pre",
            "mdap_pre",
            "dml_full",
            "mdap_full",
            "mdap_full_a",
            "mdap_full_b",
            "mdap_full_eval",
            "report",
        ),
        default="all",
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw_df = pd.read_parquet(TABLE)
    pilot = pd.read_parquet(PILOT).drop_duplicates("field_id").reset_index(drop=True)
    cen = dapsm.centroids(pilot, epsg=EPSG)
    dist = dapsm.haversine_km(cen["lat"].to_numpy(), cen["lon"].to_numpy())
    dmax = float(dist.max())
    pos = {f: k for k, f in enumerate(cen["field_id"])}

    def _p(name: str) -> Path:
        return CACHE_DIR / f"_cache_{REGION}_{name}.parquet"

    def _j(name: str) -> Path:
        return CACHE_DIR / f"_cache_{REGION}_{name}.json"

    if args.stage in ("all", "dml_pre"):
        print(f"=== Running {REGION} dml_pre ===", flush=True)
        dfp = prepare_period(raw_df, CUT_YEAR)
        diag, summ = run_dml_period(dfp, "pre_cutoff_le_2021")
        diag.to_parquet(_p("dml_pre"), index=False)
        _j("dml_pre").write_text(json.dumps(summ), encoding="utf-8")

    if args.stage in ("all", "mdap_pre"):
        print(f"=== Running {REGION} mdap_pre ===", flush=True)
        dfp = prepare_period(raw_df, CUT_YEAR)
        mdiag, msumm, dap_df, dsumm = run_matching_and_dapsm_period(
            dfp, pos, dist, dmax, "pre_cutoff_le_2021"
        )
        mdiag.to_parquet(_p("match_pre"), index=False)
        _j("match_pre").write_text(json.dumps(msumm), encoding="utf-8")
        dap_df.to_parquet(_p("dapsm_pre"), index=False)
        _j("dapsm_pre").write_text(json.dumps(dsumm), encoding="utf-8")

    if args.stage in ("all", "dml_full"):
        print(f"=== Running {REGION} dml_full ===", flush=True)
        dfp = prepare_period(raw_df, None)
        diag, summ = run_dml_period(dfp, "full_2018_2024")
        diag.to_parquet(_p("dml_full"), index=False)
        _j("dml_full").write_text(json.dumps(summ), encoding="utf-8")

    if args.stage in ("all", "mdap_full"):
        print(f"=== Running {REGION} mdap_full ===", flush=True)
        dfp = prepare_period(raw_df, None)
        mdiag, msumm, dap_df, dsumm = run_matching_and_dapsm_period(
            dfp, pos, dist, dmax, "full_2018_2024"
        )
        mdiag.to_parquet(_p("match_full"), index=False)
        _j("match_full").write_text(json.dumps(msumm), encoding="utf-8")
        dap_df.to_parquet(_p("dapsm_full"), index=False)
        _j("dapsm_full").write_text(json.dumps(dsumm), encoding="utf-8")

    if args.stage in ("mdap_full_a", "mdap_full_b"):
        print(f"=== Running {REGION} {args.stage} ===", flush=True)
        dfp = prepare_period(raw_df, None)
        lags = add_lags(dfp)
        contrasts = matching_contrast_list(dfp)
        mid = len(contrasts) // 2
        sub_c = contrasts[:mid] if args.stage == "mdap_full_a" else contrasts[mid:]
        tag = "a" if args.stage == "mdap_full_a" else "b"
        md_c, r_c, g_c, ps_c = _fit_matching_chunk(
            dfp, lags, sub_c, pos, dist, dmax, "full_2018_2024"
        )
        md_c.to_parquet(_p(f"mf_md_{tag}"), index=False)
        r_c.to_parquet(_p(f"mf_res_{tag}"), index=False)
        g_c.to_parquet(_p(f"mf_grid_{tag}"), index=False)
        _j(f"mf_ps_{tag}").write_text(json.dumps(ps_c), encoding="utf-8")
        print(f"  Finished {args.stage}: {len(sub_c)} contrasts, {len(md_c)} rows", flush=True)

    if args.stage == "mdap_full_eval":
        print(f"=== Running {REGION} mdap_full_eval ===", flush=True)
        dfp = prepare_period(raw_df, None)
        lags = add_lags(dfp)
        contrasts = matching_contrast_list(dfp)
        mdiag = pd.concat(
            [pd.read_parquet(_p("mf_md_a")), pd.read_parquet(_p("mf_md_b"))], ignore_index=True
        )
        res_df = pd.concat(
            [pd.read_parquet(_p("mf_res_a")), pd.read_parquet(_p("mf_res_b"))], ignore_index=True
        )
        grid_df = pd.concat(
            [pd.read_parquet(_p("mf_grid_a")), pd.read_parquet(_p("mf_grid_b"))], ignore_index=True
        )
        ps_cache = {
            **json.loads(_j("mf_ps_a").read_text(encoding="utf-8")),
            **json.loads(_j("mf_ps_b").read_text(encoding="utf-8")),
        }
        mdiag, msumm, dap_df, dsumm = _eval_dapsm_from_parts(
            dfp,
            lags,
            mdiag,
            res_df,
            grid_df,
            ps_cache,
            pos,
            dist,
            dmax,
            "full_2018_2024",
            len(contrasts),
        )
        mdiag.to_parquet(_p("match_full"), index=False)
        _j("match_full").write_text(json.dumps(msumm), encoding="utf-8")
        dap_df.to_parquet(_p("dapsm_full"), index=False)
        _j("dapsm_full").write_text(json.dumps(dsumm), encoding="utf-8")

    if args.stage in ("all", "report"):
        dml_frames = [pd.read_parquet(_p("dml_pre")), pd.read_parquet(_p("dml_full"))]
        match_frames = [pd.read_parquet(_p("match_pre")), pd.read_parquet(_p("match_full"))]
        dapsm_frames = [pd.read_parquet(_p("dapsm_pre")), pd.read_parquet(_p("dapsm_full"))]
        dml_summaries = {
            "pre_cutoff_le_2021": json.loads(_j("dml_pre").read_text(encoding="utf-8")),
            "full_2018_2024": json.loads(_j("dml_full").read_text(encoding="utf-8")),
        }
        match_summaries = {
            "pre_cutoff_le_2021": json.loads(_j("match_pre").read_text(encoding="utf-8")),
            "full_2018_2024": json.loads(_j("match_full").read_text(encoding="utf-8")),
        }
        dapsm_summaries = {
            "pre_cutoff_le_2021": json.loads(_j("dapsm_pre").read_text(encoding="utf-8")),
            "full_2018_2024": json.loads(_j("dapsm_full").read_text(encoding="utf-8")),
        }
        write_outputs(
            raw_df,
            pilot,
            dmax,
            dml_frames,
            match_frames,
            dapsm_frames,
            dml_summaries,
            match_summaries,
            dapsm_summaries,
        )


if __name__ == "__main__":
    main()
