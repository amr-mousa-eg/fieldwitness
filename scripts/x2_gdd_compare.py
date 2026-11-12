"""Experiment 2 (pre-registered in DECISIONS.md 2026-11-12): calendar vs gdd phenology.

Usage: uv run python -u scripts/x2_gdd_compare.py
Inputs : results/hindcast/gdd/records_{calendar,gdd}.jsonl (scripts/x2_gdd_hindcast.py),
         results/hindcast/gdd/baselines_{calendar,gdd}.jsonl (scripts/x2_gdd_baselines.py),
         results/hindcast/ks_t14slh_records.jsonl and ks_t14slh_baselines.jsonl (published).
Outputs: results/hindcast/gdd_experiment.json (the .md is written by hand from it).

Same scoring as `scripts/t7_diagnosis.py`: per field-season CRPS of the canopy integral, peak
timing absolute error = |median predicted peak day - observed peak day|, 50/90 % interval
coverage; 95 % CI = spatial block bootstrap over 10 km blocks, 1,000 resamples, seed 42.
Paired difference = gdd - calendar on the same field-seasons (negative = gdd better for errors).
Verdict rule fixed in the pre-registration (forecast mode only).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

N_BOOT = 1000
SEED = 42
H = Path("results/hindcast")
G = H / "gdd"
CROPS = ("maize", "sorghum", "winter_wheat")
MODES = ("forecast", "forced")


def read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]


def identical(a: Path, b: Path, key) -> dict:
    ra = {key(r): r for r in read(a)}
    rb = {key(r): r for r in read(b)}
    same = sum(ra[k] == rb.get(k) for k in ra)
    return {
        "n_a": len(ra),
        "n_b": len(rb),
        "n_identical": same,
        "all_identical": same == len(ra) == len(rb),
    }


def rows(recs: list[dict], blocks: dict) -> pd.DataFrame:
    out = []
    for r in recs:
        for s in r["seasons"]:
            for mode in MODES:
                if mode not in s:
                    continue
                m = s[mode]
                out.append(
                    {
                        "field_id": r["field_id"],
                        "block": blocks[r["field_id"]],
                        "year": s["year"],
                        "crop": s["crop"],
                        "mode": mode,
                        "ci_crps": m["canopy_integral"]["crps"],
                        "ci_cov50": float(m["canopy_integral"]["covered50"]),
                        "ci_cov90": float(m["canopy_integral"]["covered90"]),
                        "peak_abs_err": abs(m["peak"]["err_median"]),
                        "peak_signed_err": m["peak"]["err_median"],
                        "peak_crps": m["peak"]["crps"],
                        "peak_cov50": float(m["peak"]["covered50"]),
                        "peak_cov90": float(m["peak"]["covered90"]),
                    }
                )
    return pd.DataFrame(out)


def boot(df: pd.DataFrame, col: str) -> dict:
    """Block-bootstrap mean and 95 % CI of `col` (as in t7_diagnosis.block_bootstrap)."""
    df = df.reset_index(drop=True)
    blocks = df["block"].unique()
    idx = [df.index[df["block"] == b].to_numpy() for b in blocks]
    rng = np.random.default_rng(SEED)
    v = df[col].to_numpy(float)
    means = []
    for _ in range(N_BOOT):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        means.append(v[np.concatenate([idx[i] for i in pick])].mean())
    return {
        "mean": float(v.mean()),
        "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
        "n": len(df),
    }


METRICS = (
    "ci_crps",
    "peak_abs_err",
    "peak_signed_err",
    "peak_crps",
    "ci_cov50",
    "ci_cov90",
    "peak_cov50",
    "peak_cov90",
)


def compare(cal: pd.DataFrame, gdd: pd.DataFrame) -> dict:
    keys = ["field_id", "year", "crop", "mode"]
    m = cal.merge(gdd, on=[*keys, "block"], suffixes=("_cal", "_gdd"), validate="one_to_one")
    res = {}
    for mode in MODES:
        for crop in (*CROPS, "all"):
            sub = m[m["mode"] == mode]
            if crop != "all":
                sub = sub[sub["crop"] == crop]
            if sub.empty:
                continue
            cell = {"n": len(sub)}
            for met in METRICS:
                d = sub.assign(diff=sub[f"{met}_gdd"] - sub[f"{met}_cal"])
                cell[met] = {
                    "calendar": boot(sub, f"{met}_cal"),
                    "gdd": boot(sub, f"{met}_gdd"),
                    "diff_gdd_minus_calendar": boot(d, "diff"),
                }
            res[f"{mode}/{crop}"] = cell
    return res


def verdict(res: dict) -> dict:
    def above(c, met):
        return res[c][met]["diff_gdd_minus_calendar"]["ci95"][0] > 0

    def below(c, met):
        return res[c][met]["diff_gdd_minus_calendar"]["ci95"][1] < 0

    wheat = below("forecast/winter_wheat", "peak_abs_err")
    worse = {
        c: {met: above(f"forecast/{c}", met) for met in ("ci_crps", "peak_abs_err")}
        for c in ("maize", "sorghum")
    }
    any_worse = any(v for d in worse.values() for v in d.values())
    better = {
        c: {met: below(f"forecast/{c}", met) for met in ("ci_crps", "peak_abs_err")} for c in CROPS
    }
    return {
        "winter_wheat_peak_timing_improves": wheat,
        "maize_sorghum_worse": worse,
        "any_maize_sorghum_worse": any_worse,
        "ci_excludes_zero_in_gdd_favour": better,
        "h2_holds": wheat and not any_worse,
        "rule": "pre-registered: wheat improves if forecast peak_abs_err diff CI < 0; "
        "maize/sorghum "
        "worse if forecast canopy-integral CRPS or peak_abs_err diff CI > 0; H2 = improves and "
        "none worse",
    }


def baselines(blocks: dict) -> dict:
    out = {}
    for mode in ("calendar", "gdd"):
        b = read(G / f"baselines_{mode}.jsonl")
        recs = {
            (r["field_id"], s["year"]): s
            for r in read(G / f"records_{mode}.jsonl")
            for s in r["seasons"]
        }
        rows_ = []
        for e in b:
            s = recs[(e["field_id"], e["year"])]
            rows_.append(
                {
                    "block": blocks[e["field_id"]],
                    "crop": e["crop"],
                    "fw": s["forecast"]["canopy_integral"]["crps"],
                    **{k: e[k]["canopy_integral"]["crps"] for k in ("B0", "B1", "B2")},
                }
            )
        df = pd.DataFrame(rows_)
        cell = {}
        for crop in ("maize", "sorghum", "all"):
            sub = df if crop == "all" else df[df["crop"] == crop]
            c = {"n": len(sub), "fieldwitness": boot(sub, "fw")}
            for k in ("B0", "B1", "B2"):
                c[k] = boot(sub, k)
                c[f"{k}_minus_fw"] = boot(sub.assign(d=sub[k] - sub["fw"]), "d")
            cell[crop] = c
        out[mode] = cell
    return out


def main() -> None:
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    blocks = dict(zip(pilot["field_id"], pilot["block"], strict=True))
    checks = {
        "calendar_records_vs_published": identical(
            G / "records_calendar.jsonl", H / "ks_t14slh_records.jsonl", lambda r: r["field_id"]
        ),
        "calendar_baselines_vs_published": identical(
            G / "baselines_calendar.jsonl",
            H / "ks_t14slh_baselines.jsonl",
            lambda r: (r["field_id"], r["year"]),
        ),
    }
    cal = rows(read(G / "records_calendar.jsonl"), blocks)
    gdd = rows(read(G / "records_gdd.jsonl"), blocks)
    res = compare(cal, gdd)
    doc = {
        "experiment": "Experiment 2: thermal-time (GDD) phenology",
        "preregistration": "DECISIONS.md 2026-11-12 (commit c6b82f7), amendment (commit 17bc5cd)",
        "cutoff": "2021-12-31",
        "scored_years": [2022, 2023, 2024],
        "bootstrap": {"blocks": "10 km", "resamples": N_BOOT, "seed": SEED},
        "reproduction_checks": checks,
        "by_mode_crop": res,
        "verdict": verdict(res),
        "baselines_forecast_canopy_crps": baselines(blocks),
        "tag": "D (model) vs O (HLS) statistics; labels E",
    }
    (H / "gdd_experiment.json").write_text(json.dumps(doc, indent=1), "utf-8")
    print(json.dumps(checks, indent=1))
    print(json.dumps(doc["verdict"], indent=1))


if __name__ == "__main__":
    main()
