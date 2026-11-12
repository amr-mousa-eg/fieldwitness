"""Experiment 1 (pre-registered in DECISIONS.md 2026-11-12): DAPSM for the neighbour witness.

Usage: uv run python -u scripts/x1_dapsm.py
Inputs : data/neighbours/ks_t14slh_field_season.parquet, data/fields/ks_t14slh_pilot.parquet
Outputs: results/neighbours/field_centroids.csv, field_distance_km.npy, dapsm_w_grid.csv,
         dapsm_contrasts.csv, dapsm.json, dapsm.md

Only seasons <= 2021 are used (cut-off 2021-12-31): `next_crop` of 2021 rows is missing,
`dry_season` is recomputed from each field's seasons <= 2021. The old T5.xa IPW double-ML
diagnostics are re-run on the same rows for a like-for-like comparison.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.neighbours import dapsm
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

CUT_YEAR = 2021
TABLE = Path("data/neighbours/ks_t14slh_field_season.parquet")
PILOT = Path("data/fields/ks_t14slh_pilot.parquet")
OUT = Path("results/neighbours")
OLD_DIAG = OUT / "matching_diagnostics.csv"
STRATA = ("all", "wet", "dry")
CHECKS = ("overlap", "balance", "placebo", "negctrl")


def load() -> pd.DataFrame:
    df = pd.read_parquet(TABLE)
    df = df[df["year"] <= CUT_YEAR].copy()
    med = df.groupby("field_id")["season_precip_mm"].transform("median")
    df["dry_season"] = (df["season_precip_mm"] < med).where(df["season_precip_mm"].notna())
    return df.reset_index(drop=True)


def sample(df, crop, prev2, a, b, st, arm_col, y):
    s = df[(df["crop"] == crop) & (df["prev2_crop"] == prev2) & df[arm_col].isin([a, b])]
    if st != "all":
        s = s[s["dry_season"] == (st == "dry")]
    s = s.dropna(subset=[y, *CONFOUNDERS]).reset_index(drop=True)
    d = (s[arm_col] == a).to_numpy()
    ok = d.sum() >= MIN_ARM and (~d).sum() >= MIN_ARM and s["block"].nunique() >= MIN_BLOCKS
    return s, d, ok


def propensity(s, d, y):
    x = matching_design(s).reset_index(drop=True)
    data = pd.concat([x, s[y].rename("y"), pd.Series(d.astype(float), name="d")], axis=1)
    plr = fit_plr(data, x.columns, s["block"].to_numpy())
    return np.asarray(plr.predictions["ml_m"])[:, 0, 0]


def scaled(s, pos, dmax, dist):
    i = s["field_id"].map(pos).to_numpy()
    return dist[np.ix_(i, i)] / dmax


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_parquet(PILOT)
    cen = dapsm.centroids(pilot)
    dist = dapsm.haversine_km(cen["lat"].to_numpy(), cen["lon"].to_numpy())
    dmax = float(dist.max())
    cen.assign(tag="D").to_csv(OUT / "field_centroids.csv", index=False)
    np.save(OUT / "field_distance_km.npy", dist)
    pos = {f: k for k, f in enumerate(cen["field_id"])}

    df = load()
    lags = add_lags(df)
    contrasts = matching_contrast_list(df)
    print(f"{len(df)} rows <= {CUT_YEAR}; {len(contrasts)} contrast pairs", flush=True)

    rows, grid, cache = [], [], {}
    for crop, prev2, a, b in contrasts:
        for y in OUTCOMES:
            for st in STRATA:
                key = (crop, prev2, a, b, y, st)
                base = dict(
                    zip(
                        (
                            "crop",
                            "prev2_crop",
                            "treated_prev",
                            "reference_prev",
                            "outcome",
                            "stratum",
                        ),
                        key,
                        strict=True,
                    )
                )
                row, plr = fit_matching_contrast(df, crop, prev2, a, b, y, st)
                old = diagnose_matching_contrast(lags, row, plr=plr)
                rec = {
                    **base,
                    "n": row["n"],
                    "fitted": plr is not None,
                    "old_effect": row["effect"],
                    "old_ci_low": row["ci_low"],
                    "old_ci_high": row["ci_high"],
                }
                for c in CHECKS:
                    rec[f"old_{c}"] = old[f"{c}_status"]
                rec["old_smd_weighted_max"] = old.get("smd_weighted_max", np.nan)
                rec["old_evidence"] = bool(old["show_as_evidence"])
                rows.append(rec)
                if plr is None:
                    continue
                s, d, _ = sample(lags, crop, prev2, a, b, st, "prev_crop", y)
                ps = np.asarray(plr.predictions["ml_m"])[:, 0, 0]
                assert len(ps) == len(s) and d.sum() == row["n_treated"]
                ds = scaled(s, pos, dmax, dist)
                x = matching_design(s)
                cache[key] = (s, d, ps, ds)
                for w in dapsm.W_GRID:
                    m = dapsm.match(ps, ds, d, s["field_id"].to_numpy(), w)
                    smd = dapsm.smd_per_covariate(x, d, dapsm.match_weights(m, d))
                    grid.append(
                        {
                            **base,
                            "w": w,
                            "smd_max": float(smd.max()),
                            "worst_covariate": smd.idxmax(),
                            "n_pairs": int((m[d] >= 0).sum()),
                        }
                    )
        print("done", crop, prev2, a, b, flush=True)

    grid = pd.DataFrame(grid)
    w_star = dapsm.choose_w(grid)
    grid.to_csv(OUT / "dapsm_w_grid.csv", index=False)
    print("chosen w", w_star, flush=True)

    res = pd.DataFrame(rows)
    new = []
    for r in res.itertuples():
        key = (r.crop, r.prev2_crop, r.treated_prev, r.reference_prev, r.outcome, r.stratum)
        out = dict.fromkeys((f"new_{c}" for c in CHECKS), "untested")
        if key in cache:
            s, d, ps, ds = cache[key]
            share = float(np.mean((ps < PS_LOW) | (ps > PS_HIGH)))
            out["new_overlap"] = "pass" if share <= OVERLAP_MAX_SHARE else "fail"
            out["share_outside"] = share
            m = dapsm.match(ps, ds, d, s["field_id"].to_numpy(), w_star)
            smd = dapsm.smd_per_covariate(matching_design(s), d, dapsm.match_weights(m, d))
            out["new_smd_max"] = float(smd.max())
            out["new_worst_covariate"] = smd.idxmax()
            out["new_balance"] = "pass" if smd.max() <= SMD_MAX else "fail"
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
                sp, dp, ok = sample(lags, *key[:4], r.stratum, arm, yy)
                if not ok:
                    continue
                psp = propensity(sp, dp, yy)
                mp = dapsm.match(
                    psp, scaled(sp, pos, dmax, dist), dp, sp["field_id"].to_numpy(), w_star
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
        new.append(out)
    res = pd.concat([res, pd.DataFrame(new)], axis=1)
    res["new_evidence"] = res[[f"new_{c}" for c in CHECKS]].eq("pass").all(axis=1)
    res["tag"] = "D"
    res.to_csv(OUT / "dapsm_contrasts.csv", index=False)
    write_report(res, grid, w_star, dmax, len(df))


def counts(series: pd.Series) -> dict:
    vc = series.value_counts().to_dict()
    k, n = int(vc.get("pass", 0)), int(vc.get("pass", 0) + vc.get("fail", 0))
    lo, hi = dapsm.wilson(k, n)
    return {
        "pass": k,
        "fail": int(vc.get("fail", 0)),
        "untested": int(vc.get("untested", 0)),
        "pass_share_of_tested": (k / n) if n else None,
        "wilson95": [lo, hi],
    }


def write_report(res, grid, w_star, dmax, n_rows) -> None:
    fit = res[res["fitted"]]
    old_pub = pd.read_csv(OLD_DIAG)
    old_pub = old_pub.dropna(subset=["effect"])
    both = fit[
        fit["old_balance"].isin(["pass", "fail"]) & fit["new_balance"].isin(["pass", "fail"])
    ]
    n_old_bal = int((both["old_balance"] == "pass").sum())
    n_new_bal = int((both["new_balance"] == "pass").sum())
    summ = (
        grid.groupby("w")
        .agg(
            median_smd_max=("smd_max", "median"),
            mean_smd_max=("smd_max", "mean"),
            n_pass_balance=("smd_max", lambda v: int((v <= SMD_MAX).sum())),
            n_contrasts=("smd_max", "size"),
        )
        .reset_index()
    )
    worst = fit["new_worst_covariate"].value_counts().to_dict()
    doc = {
        "experiment": "Experiment 1: distance-adjusted propensity score matching (DAPSM)",
        "preregistration": "DECISIONS.md 2026-11-12 'Pre-registration: two algorithm experiments'",
        "cutoff_year": CUT_YEAR,
        "rows_used": n_rows,
        "geometry_source": "data/fields/ks_t14slh_pilot.parquet (CSB polygons, WGS 84); "
        "centroid in EPSG:32614",
        "distance_scaling": f"dist_km / {dmax:.4f} km (max pairwise centroid distance, 200 fields)",
        "w_grid_summary": summ.to_dict("records"),
        "chosen_w": w_star,
        "contrast_rows": len(res),
        "fitted": len(fit),
        "old_ipw_same_rows": {c: counts(fit[f"old_{c}"]) for c in CHECKS},
        "old_ipw_same_rows_evidence": int(fit["old_evidence"].sum()),
        "dapsm": {c: counts(fit[f"new_{c}"]) for c in CHECKS},
        "dapsm_evidence": int(fit["new_evidence"].sum()),
        "old_published_all_years": {
            "fitted": len(old_pub),
            **{c: counts(old_pub[f"{c}_status"]) for c in CHECKS},
            "evidence": int(old_pub["show_as_evidence"].sum()),
        },
        "h1_balance_tested_both": len(both),
        "h1_balance_pass_old": n_old_bal,
        "h1_balance_pass_dapsm": n_new_bal,
        "h1_holds": n_new_bal > n_old_bal,
        "dapsm_worst_covariate_counts": worst,
        "thresholds_tag_A": {
            "ps_range": [PS_LOW, PS_HIGH],
            "overlap_max_share": OVERLAP_MAX_SHARE,
            "smd_max": SMD_MAX,
        },
        "witness_status": "OFF (unchanged; grading and app not modified)",
        "tag": "D",
    }
    (OUT / "dapsm.json").write_text(json.dumps(doc, indent=2, default=float), "utf-8")
    print(
        json.dumps(
            {
                k: doc[k]
                for k in (
                    "chosen_w",
                    "fitted",
                    "dapsm",
                    "dapsm_evidence",
                    "h1_balance_pass_old",
                    "h1_balance_pass_dapsm",
                )
            },
            indent=1,
            default=float,
        )
    )


if __name__ == "__main__":
    main()
