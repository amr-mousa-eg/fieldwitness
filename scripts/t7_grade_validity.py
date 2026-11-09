"""T7: Grade and credibility empirical validity check on Kansas hindcast.

Pre-registered in DECISIONS.md (2026-11-09) before execution:
  - No circularity: credibility scores and evidence grades are evaluated strictly at the
    hindcast cut-off (as_of 2021-12-31). No 2022-2024 data enters credibility or grades.
  - Which grade: grade of the field's Current option (crops observed in scored seasons).
  - Primary test: forecast-mode canopy integral CRPS, Grade B vs Grade D.
    Success: Grade B's mean CRPS is lower than Grade D's, and the 95% spatial block
    bootstrap CI of (CRPS_D - CRPS_B) strictly excludes 0.
  - Secondary (exploratory): timing error, coverage, Grade C, credibility rank correlation,
    and forced mode.
  - Sample size rule: any grade group with n < 20 is reported as 'too few to judge'.
  - Spatial block bootstrap: 1,000 iterations blocking by the 10 km grid cells from T1.4,
    seed=42.

Outputs:
  - results/hindcast/grade_validity.json
  - results/hindcast/grade_validity.md
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from fieldwitness.data import labels, power
from fieldwitness.data.asof import as_of
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.physics.forcing import forcing

CUT = dt.date(2021, 12, 31)
SEED = priors.SEED
CROPS = ("maize", "sorghum")
MIN_OBS = 10
N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 42

OUT_DIR = Path("results/hindcast")
OUT_JSON = OUT_DIR / "grade_validity.json"
OUT_MD = OUT_DIR / "grade_validity.md"


def compute_cutoff_credibility(pilot: pd.DataFrame, series: pd.DataFrame) -> dict[str, dict]:
    """Compute in-sample physics credibility at cut-off (as_of 2021-12-31)."""
    grading = yaml.safe_load(Path("config/grading.yaml").read_text("utf-8"))["credibility"]
    w_spearman = float(grading["weight_spearman"])
    scale_days = float(grading["timing_error_scale_days"])

    cfg0 = forward.load_cfg()
    region = cfg0["region"]
    series_cut = series[series["year"] <= CUT.year].copy()
    cen = synthetic.census(series_cut)
    noise = cen["noise_sd"]
    rng = np.random.default_rng(SEED + 45)
    crop_p = {c: forward.crop_params(c, region) for c in CROPS}
    cfgs = {c: {**cfg0, "crop": c} for c in CROPS}

    def rank_corr(a: np.ndarray, b: np.ndarray) -> float:
        if len(a) < 3:
            return float("nan")
        ra = pd.Series(a).rank().to_numpy()
        rb = pd.Series(b).rank().to_numpy()
        if ra.std() == 0 or rb.std() == 0:
            return float("nan")
        return float(np.corrcoef(ra, rb)[0, 1])

    def get_weather(
        lon: float, lat: float, years: list[int]
    ) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31))
        _, elev = power.cached(lon, lat)
        f = forcing(w, lat, float(elev or 0.0))
        out = {}
        for y in years:
            fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
            if len(fy) == 365 and not fy.isna().any().any():
                out[y] = (fy["rain"].to_numpy(float), fy["eto"].to_numpy(float))
        return out

    by_field = {fid: g for fid, g in series_cut.groupby("field_id")}
    pos = pilot.set_index("field_id")
    results: dict[str, dict] = {}

    with as_of(CUT):
        lab = labels.read(region)
        lab = lab[lab["crop"].isin(CROPS)]

        for fid in pilot["field_id"]:
            lf = lab[lab["field_id"] == fid]
            seasons = {c: [] for c in CROPS}
            if len(lf):
                r = pos.loc[fid]
                wx = get_weather(r["lon"], r["lat"], sorted(set(lf["year"])))
                for rec in lf.itertuples():
                    if fid not in by_field:
                        continue
                    g = by_field[fid]
                    g = g[g["year"] == rec.year].dropna(subset=["ndvi"]).drop_duplicates("doy")
                    g = g[(g["doy"] >= 1) & (g["doy"] <= 365)].sort_values("doy")
                    if len(g) < MIN_OBS or rec.year not in wx:
                        continue
                    ref = abc.reference_table(
                        *wx[rec.year],
                        1000,
                        crop_p[rec.crop],
                        cfgs[rec.crop],
                        seed=SEED + 1000 + rec.year,
                    )
                    doy, nd = g["doy"].to_numpy(int), g["ndvi"].to_numpy(float)
                    p = abc.posterior(doy, nd, ref, noise, 50, rng)
                    sim = abc.summary_stats(doy, ref["ndvi"][doy - 1][:, p["idx"]])
                    pred = np.median(sim, axis=0)
                    seasons[rec.crop].append((rec.year, p["obs_stats"], pred))

            best = max(CROPS, key=lambda c: len(seasons[c]))
            s = seasons[best]
            if not s:
                results[fid] = {
                    "credibility": None,
                    "mode": "not_assessable",
                    "n_seasons": 0,
                    "crop": None,
                }
            else:
                obs = np.array([x[1] for x in s])
                pr = np.array([x[2] for x in s])
                err = np.abs(obs[:, [0, 1, 2]] - pr[:, [0, 1, 2]]).mean(1)
                med_err = float(np.median(err))
                t_score = max(0.0, 1 - med_err / scale_days)
                rho = rank_corr(obs[:, 3], pr[:, 3])
                if np.isnan(rho):
                    cred, mode = t_score, "timing_only"
                else:
                    cred, mode = w_spearman * max(0.0, rho) + (1 - w_spearman) * t_score, "full"

                results[fid] = {
                    "credibility": round(float(cred), 4),
                    "mode": mode,
                    "spearman": None if np.isnan(rho) else round(float(rho), 4),
                    "median_timing_error_days": round(med_err, 2),
                    "n_seasons": len(s),
                    "crop": best,
                }

    return results


def run_grade_validity() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    series["year"] = series["date"].dt.year
    series["doy"] = series["date"].dt.dayofyear

    print("Step 1: Computing cut-off credibility scores (as_of 2021-12-31)...")
    cred_cutoff = compute_cutoff_credibility(pilot, series)

    # Step 2: Read hindcast records
    rec_path = OUT_DIR / "ks_t14slh_records.jsonl"
    if not rec_path.exists():
        raise FileNotFoundError(f"Hindcast records missing: {rec_path}")

    field_blocks = dict(zip(pilot["field_id"], pilot["block"], strict=True))

    rows = []
    with open(rec_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            fid = r["field_id"]
            block = field_blocks.get(fid, "unknown")
            c_info = cred_cutoff.get(fid, {"credibility": None})
            cred_val = c_info.get("credibility")

            for s in r["seasons"]:
                fit_src = s["fit_source"]
                # Determine grade under as_of(2021-12-31)
                # Prior fitting -> D (assumptions >= 50%)
                # Posterior fitting -> B if credibility >= 0.6 else C
                if fit_src == "prior":
                    grade = "D"
                elif cred_val is not None and cred_val >= 0.6:
                    grade = "B"
                else:
                    grade = "C"

                # Extract forecast and forced metrics
                fc = s["forecast"]
                fc_ci = fc["canopy_integral"]
                fc_peak = fc["peak"]
                fc_sos = fc["sos"]
                fc_cover = fc["cover_days"]

                fd = s.get("forced", {})
                fd_ci = fd.get("canopy_integral", {})
                fd_peak = fd.get("peak", {})

                rows.append(
                    {
                        "field_id": fid,
                        "block": block,
                        "year": s["year"],
                        "crop": s["crop"],
                        "fit_source": fit_src,
                        "grade": grade,
                        "credibility": cred_val,
                        # Forecast metrics
                        "forecast_ci_crps": fc_ci["crps"],
                        "forecast_ci_covered90": fc_ci["covered90"],
                        "forecast_ci_abs_err": abs(fc_ci["err_median"]),
                        "forecast_peak_crps": fc_peak["crps"],
                        "forecast_peak_abs_err": abs(fc_peak["err_median"]),
                        "forecast_peak_covered90": fc_peak["covered90"],
                        "forecast_sos_crps": fc_sos["crps"],
                        "forecast_sos_abs_err": abs(fc_sos["err_median"]),
                        "forecast_sos_covered90": fc_sos["covered90"],
                        "forecast_cover_crps": fc_cover["crps"],
                        # Forced metrics
                        "forced_ci_crps": fd_ci.get("crps"),
                        "forced_peak_abs_err": abs(fd_peak.get("err_median", 0.0))
                        if fd_peak
                        else None,
                    }
                )

    df = pd.DataFrame(rows)
    print(f"Total scored field-seasons: {len(df)}")
    print("Counts by grade:", df["grade"].value_counts().to_dict())

    # Step 3: Spatial block bootstrap
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    unique_blocks = df["block"].unique()

    grades_list = ["B", "C", "D"]
    stats_by_grade = {}

    for g in grades_list:
        sub = df[df["grade"] == g]
        n_g = len(sub)
        too_few = n_g < 20
        mean_crps = float(sub["forecast_ci_crps"].mean()) if n_g else float("nan")
        mean_peak_err = float(sub["forecast_peak_abs_err"].mean()) if n_g else float("nan")
        cov90_ci = float(sub["forecast_ci_covered90"].mean()) if n_g else float("nan")
        cov90_peak = float(sub["forecast_peak_covered90"].mean()) if n_g else float("nan")

        stats_by_grade[g] = {
            "n": n_g,
            "too_few_to_judge": too_few,
            "forecast_ci_crps_mean": round(mean_crps, 4) if not np.isnan(mean_crps) else None,
            "forecast_peak_abs_err_mean": round(mean_peak_err, 2)
            if not np.isnan(mean_peak_err)
            else None,
            "forecast_ci_covered90_share": round(cov90_ci, 4) if not np.isnan(cov90_ci) else None,
            "forecast_peak_covered90_share": round(cov90_peak, 4)
            if not np.isnan(cov90_peak)
            else None,
        }

    # Block bootstrap resamples
    boot_diff_d_b = []
    boot_diff_c_b = []
    boot_means = {g: [] for g in grades_list}

    for _ in range(N_BOOTSTRAP):
        resampled_blocks = rng.choice(unique_blocks, size=len(unique_blocks), replace=True)
        # Gather rows belonging to chosen blocks
        # Use pandas merge or indexing for speed
        block_counts = pd.Series(resampled_blocks).value_counts()
        boot_sub_list = []
        for blk, count in block_counts.items():
            b_rows = df[df["block"] == blk]
            if len(b_rows):
                boot_sub_list.append(pd.concat([b_rows] * count, ignore_index=True))

        boot_df = pd.concat(boot_sub_list, ignore_index=True)

        m_b = boot_df[boot_df["grade"] == "B"]["forecast_ci_crps"].mean()
        m_c = boot_df[boot_df["grade"] == "C"]["forecast_ci_crps"].mean()
        m_d = boot_df[boot_df["grade"] == "D"]["forecast_ci_crps"].mean()

        boot_means["B"].append(m_b)
        boot_means["C"].append(m_c)
        boot_means["D"].append(m_d)

        if not np.isnan(m_d) and not np.isnan(m_b):
            boot_diff_d_b.append(m_d - m_b)
        if not np.isnan(m_c) and not np.isnan(m_b):
            boot_diff_c_b.append(m_c - m_b)

    for g in grades_list:
        arr = [x for x in boot_means[g] if not np.isnan(x)]
        if arr:
            stats_by_grade[g]["forecast_ci_crps_ci95"] = [
                round(float(np.percentile(arr, 2.5)), 4),
                round(float(np.percentile(arr, 97.5)), 4),
            ]
        else:
            stats_by_grade[g]["forecast_ci_crps_ci95"] = None

    diff_d_b_ci95 = (
        [
            round(float(np.percentile(boot_diff_d_b, 2.5)), 4),
            round(float(np.percentile(boot_diff_d_b, 97.5)), 4),
        ]
        if boot_diff_d_b
        else None
    )
    diff_d_b_mean = (
        round(
            float(
                stats_by_grade["D"]["forecast_ci_crps_mean"]
                - stats_by_grade["B"]["forecast_ci_crps_mean"]
            ),
            4,
        )
        if stats_by_grade["D"]["forecast_ci_crps_mean"] is not None
        and stats_by_grade["B"]["forecast_ci_crps_mean"] is not None
        else None
    )

    # Primary Decision Rule Check:
    # Success iff Grade B's mean CRPS < Grade D's mean CRPS (diff_d_b_mean > 0)
    # AND 95% CI strictly excludes 0 (> 0).
    is_success = False
    if diff_d_b_mean is not None and diff_d_b_ci95 is not None:
        if diff_d_b_mean > 0 and diff_d_b_ci95[0] > 0:
            is_success = True

    # Continuous credibility correlation (Spearman rho across fields with non-null credibility)
    sub_cred = df.dropna(subset=["credibility"])
    if len(sub_cred) >= 10:
        rho_crps, p_crps = stats.spearmanr(sub_cred["credibility"], sub_cred["forecast_ci_crps"])
        rho_peak, p_peak = stats.spearmanr(
            sub_cred["credibility"], sub_cred["forecast_peak_abs_err"]
        )
        cred_corr = {
            "n_field_seasons": len(sub_cred),
            "spearman_rho_crps": round(float(rho_crps), 4),
            "p_value_crps": round(float(p_crps), 4),
            "spearman_rho_peak_timing_error": round(float(rho_peak), 4),
            "p_value_peak_timing_error": round(float(p_peak), 4),
            "note": "Negative rho means higher credibility predicts lower error (better skill).",
        }
    else:
        cred_corr = {
            "n_field_seasons": len(sub_cred),
            "error": "Too few fields with cut-off credibility",
        }

    verdict_str = (
        "PASS: Grade B has strictly lower canopy integral CRPS than Grade D with 95% confidence."
        if is_success
        else "DID NOT PASS: Evidence grades did not show a statistically significant difference "
        "in predictive accuracy."
    )

    summary = {
        "analysis": "Grade & Credibility Empirical Validity Check (Kansas Pilot)",
        "as_of_cutoff": "2021-12-31",
        "scored_seasons": "2022-2024",
        "total_scored_field_seasons": len(df),
        "primary_test": {
            "target": "forecast_ci_crps (canopy integral)",
            "comparison": "Grade B vs Grade D",
            "decision_rule": "Success iff B mean < D mean and 95% CI of (D - B) strictly > 0",
            "diff_d_minus_b_mean": diff_d_b_mean,
            "diff_d_minus_b_ci95": diff_d_b_ci95,
            "passed": is_success,
            "verdict": verdict_str,
        },
        "grades": stats_by_grade,
        "credibility_rank_correlation": cred_corr,
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Generate Markdown report
    b_stat = stats_by_grade["B"]
    d_stat = stats_by_grade["D"]
    lines = [
        "# Grade & Credibility Empirical Validity Report (Kansas Pilot)",
        "",
        "**Cut-off Date:** 2021-12-31 (Strict `as_of` guard; pre-registered in `DECISIONS.md`).  ",
        "**Scored Seasons:** 2022–2024 maize, sorghum, and winter wheat field-seasons.  ",
        f"**Total Sample Size:** {len(df)} field-seasons across {pilot['field_id'].nunique()} "
        "pilot fields.  ",
        f"**Bootstrap:** {N_BOOTSTRAP} resamples clustered by 10 km spatial grid blocks "
        f"(seed={BOOTSTRAP_SEED}).",
        "",
        "## 1. Primary Pre-registered Test (Grade B vs Grade D)",
        "",
        "- **Primary Metric:** Forecast-mode canopy integral CRPS.",
        f"- **Grade B Mean CRPS:** {b_stat['forecast_ci_crps_mean']} "
        f"(95% CI: {b_stat['forecast_ci_crps_ci95']}, n = {b_stat['n']})",
        f"- **Grade D Mean CRPS:** {d_stat['forecast_ci_crps_mean']} "
        f"(95% CI: {d_stat['forecast_ci_crps_ci95']}, n = {d_stat['n']})",
        f"- **Difference (D − B):** {diff_d_b_mean} (95% CI: {diff_d_b_ci95})",
        f"- **Primary Test Result:** **{summary['primary_test']['verdict']}**",
        "",
        "## 2. Full Performance by Evidence Grade",
        "",
        "| Evidence Grade | n | Mean Canopy Integral CRPS (95% CI) | "
        "Mean Peak Timing Error (days) | 90% Canopy Coverage | 90% Peak Coverage | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for g in grades_list:
        st = stats_by_grade[g]
        status_txt = "Too few to judge (<20)" if st["too_few_to_judge"] else "Sufficient sample"
        ci_str = (
            f"{st['forecast_ci_crps_ci95'][0]} – {st['forecast_ci_crps_ci95'][1]}"
            if st["forecast_ci_crps_ci95"]
            else "N/A"
        )
        cov_ci = round(st["forecast_ci_covered90_share"] * 100, 1)
        cov_pk = round(st["forecast_peak_covered90_share"] * 100, 1)
        lines.append(
            f"| **Grade {g}** | {st['n']} | {st['forecast_ci_crps_mean']} ({ci_str}) | "
            f"{st['forecast_peak_abs_err_mean']} d | {cov_ci}% | {cov_pk}% | {status_txt} |"
        )

    lines.extend(
        [
            "",
            "## 3. Continuous Credibility Score Rank Correlation (Exploratory)",
            "",
            f"- **Sample size:** {cred_corr.get('n_field_seasons')} field-seasons with "
            "pre-cutoff credibility assessment.",
            f"- **Spearman $\\rho$ vs Canopy Integral CRPS:** {cred_corr.get('spearman_rho_crps')} "
            f"(p = {cred_corr.get('p_value_crps')})",
            f"- **Spearman $\\rho$ vs Peak Timing Error:** "
            f"{cred_corr.get('spearman_rho_peak_timing_error')} "
            f"(p = {cred_corr.get('p_value_peak_timing_error')})",
            "- *Interpretation:* A negative correlation indicates that higher physics "
            "credibility is associated with lower prediction errors.",
            "",
            "## 4. Integrity and Model Invariance Statement",
            "",
            "As pre-registered, FieldWitness evidence grades and threshold rules are "
            "**not altered** based on this check. The findings are reported transparently "
            "on the public Scoreboard and Methods pages to let reviewers and users judge "
            "the evidence system on empirical grounds.",
        ]
    )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {OUT_MD}")
    print(f"JSON written to {OUT_JSON}")
    return summary


if __name__ == "__main__":
    run_grade_validity()
