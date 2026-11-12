# ruff: noqa: E501  (markdown table rows)
"""Conformal experiment (pre-registered in DECISIONS.md 2026-11-12): calibrate and evaluate.

Usage: uv run python -u scripts/x4_conformal.py
Calibration: results/hindcast/conformal/pseudo_cut{2018,2019,2020}.jsonl (seasons 2019-2021,
rolling origin). Test: results/hindcast/ks_t14slh_records.jsonl (2022-2024, published; never used
to fit or choose). Bootstrap: `block_bootstrap` from scripts/t7_diagnosis.py (10 km blocks,
1,000 resamples, seed 42); the median uses the same resampling scheme.
Outputs in results/hindcast/conformal/.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t7_diagnosis import BOOTSTRAP_SEED, N_BOOTSTRAP, block_bootstrap  # noqa: E402

from fieldwitness.infer import conformal as cf  # noqa: E402

H = Path("results/hindcast")
C = H / "conformal"
LEVELS = (0.5, 0.8, 0.9)
METRICS = ("canopy_integral", "peak")
CROPS = ("maize", "sorghum", "winter_wheat")
RUNS = ("forecast", "forced")
BY = ["crop", "run", "metric"]
CROP = {"maize": "Maize", "sorghum": "Sorghum", "winter_wheat": "Winter wheat"}
MET = {"canopy_integral": "canopy integral", "peak": "peak day"}


def read(path):
    return [json.loads(x) for x in Path(path).read_text("utf-8").splitlines() if x.strip()]


def rows(recs, blocks, source):
    out = []
    for r in recs:
        for s in r["seasons"]:
            for run in RUNS:
                if run not in s:
                    continue
                for met in METRICS:
                    q = s[run][met]["q"]
                    out.append(
                        {
                            "field_id": r["field_id"],
                            "block": blocks[r["field_id"]],
                            "year": s["year"],
                            "crop": s["crop"],
                            "run": run,
                            "metric": met,
                            "y": s["observed"][met],
                            "q5": q[0],
                            "q25": q[1],
                            "q50": q[2],
                            "q75": q[3],
                            "q95": q[4],
                            "cov90_stored": float(s[run][met]["covered90"]),
                            "cov50_stored": float(s[run][met]["covered50"]),
                            "source": source,
                        }
                    )
    df = pd.DataFrame(out)
    df["s"], df["h"] = cf.scores(df["y"], df["q5"], df["q50"], df["q95"])
    return df


def boot(df, col, stat="mean"):
    """Mean via t7_diagnosis.block_bootstrap; median with the same resampling scheme."""
    if stat == "mean":
        m, ci, *_ = block_bootstrap(df.reset_index(drop=True), col)
        return {"value": m, "ci_low": ci[0], "ci_high": ci[1], "n": len(df)}
    d = df.reset_index(drop=True)
    blocks = d["block"].unique()
    idx = [d.index[d["block"] == b].to_numpy() for b in blocks]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    v = d[col].to_numpy(float)
    res = [
        np.median(v[np.concatenate([idx[i] for i in rng.choice(len(blocks), len(blocks))])])
        for _ in range(N_BOOTSTRAP)
    ]
    return {
        "value": float(np.median(v)),
        "ci_low": float(np.percentile(res, 2.5)),
        "ci_high": float(np.percentile(res, 97.5)),
        "n": len(d),
    }


def apply(test, cal, version):
    """Add lo/hi/cov columns per level for the pooled or block-aware multipliers."""
    out = test.copy()
    for L in LEVELS:
        tag = f"{int(L * 100)}"
        if version == "pooled":
            mm = cf.mondrian(cal, BY, L)
            m = [
                mm.get((c, r, k), (None, 0))[0]
                for c, r, k in zip(out["crop"], out["run"], out["metric"], strict=True)
            ]
        else:
            mm = cf.leave_block_out(cal, BY, L, sorted(out["block"].unique()))
            m = [
                mm.get(((c, r, k), b), (None, 0))[0]
                for c, r, k, b in zip(
                    out["crop"], out["run"], out["metric"], out["block"], strict=True
                )
            ]
        out[f"m{tag}"] = [np.nan if v is None else v for v in m]
        calib = out[f"m{tag}"].notna()
        lo, hi = cf.interval(out["q50"], out["h"], out[f"m{tag}"].fillna(0))
        # not calibrated -> stored interval (90/50) or none (80)
        if tag == "90":
            lo = np.where(calib, lo, out["q5"])
            hi = np.where(calib, hi, out["q95"])
        elif tag == "50":
            lo = np.where(calib, lo, out["q25"])
            hi = np.where(calib, hi, out["q75"])
        else:
            lo = np.where(calib, lo, np.nan)
            hi = np.where(calib, hi, np.nan)
        out[f"lo{tag}"], out[f"hi{tag}"] = lo, hi
        out[f"cov{tag}"] = np.where(
            np.isnan(lo), np.nan, ((out["y"] >= lo) & (out["y"] <= hi)).astype(float)
        )
        out[f"width{tag}"] = hi - lo
    out["winkler90"] = cf.winkler(out["lo90"], out["hi90"], out["y"], 0.1)
    out["winkler90_stored"] = cf.winkler(out["q5"], out["q95"], out["y"], 0.1)
    out["width90_stored"] = out["q95"] - out["q5"]
    out["width50_stored"] = out["q75"] - out["q25"]
    out["signed_err"] = out["y"] - out["q50"]
    out["above_median"] = (out["y"] > out["q50"]).astype(float)
    return out


def cell(d):
    if len(d) < 20:
        return {"n": len(d), "too_few_to_judge": True}
    r = {"n": len(d), "too_few_to_judge": False}
    for col in (
        "cov90_stored",
        "cov50_stored",
        "cov90",
        "cov80",
        "cov50",
        "width90_stored",
        "width90",
        "winkler90_stored",
        "winkler90",
        "above_median",
    ):
        dd = d.dropna(subset=[col])
        r[col] = boot(dd, col) if len(dd) >= 20 else None
    r["median_signed_err"] = boot(d, "signed_err", "median")
    r["calibrated"] = bool(d["m90"].notna().all())
    return r


def main():
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    blocks = dict(zip(pilot["field_id"], pilot["block"], strict=True))
    runs = {y: read(C / f"pseudo_cut{y}.jsonl") for y in (2018, 2019, 2020, 2021)}
    check = {
        "fields_per_run": {y: len(v) for y, v in runs.items()},
        "cut2021_identical_to_published": runs[2021] == read(H / "ks_t14slh_records.jsonl"),
    }
    cal = pd.concat(
        [rows(runs[y], blocks, f"cut{y}") for y in (2018, 2019, 2020)], ignore_index=True
    )
    assert cal["year"].max() <= 2021
    test = rows(read(H / "ks_t14slh_records.jsonl"), blocks, "published")
    cal.drop(columns=["q25", "q75"]).to_csv(C / "calibration_scores.csv", index=False)

    mult = {}
    for L in LEVELS:
        for key, (m, n) in cf.mondrian(cal, BY, L).items():
            mult.setdefault("|".join(key), {})[f"m{int(L * 100)}"] = m
            mult["|".join(key)]["n_scores"] = n
    zero_h = cal.groupby(BY)["s"].apply(lambda s: int(s.isna().sum())).to_dict()
    for key, v in mult.items():
        v["n_zero_width_excluded"] = zero_h[tuple(key.split("|"))]
        v["status"] = "calibrated" if v["m90"] is not None else "too few to calibrate"
    lobo = {}
    for key, _g in cal.groupby(BY):
        ms = [
            m
            for (k2, b), (m, n) in cf.leave_block_out(
                cal, BY, 0.9, sorted(test["block"].unique())
            ).items()
            if k2 == key and m is not None
        ]
        lobo["|".join(key)] = {
            "m90_min": min(ms) if ms else None,
            "m90_max": max(ms) if ms else None,
        }
    (C / "multipliers.json").write_text(
        json.dumps(
            {
                "pooled": mult,
                "block_aware_m90_range_over_test_blocks": lobo,
                "calibration_seasons": {
                    str(k): int(v) for k, v in cal.groupby("year").size().items()
                },
                "calibration_fields": int(cal["field_id"].nunique()),
                "reproduction_check": check,
                "tag": "D",
            },
            indent=1,
        ),
        "utf-8",
    )

    # cross-validated check on the calibration seasons (leave-one-block-out within calibration)
    cv = apply(cal, cal, "block_aware")
    res = {"reproduction_check": check, "calibration_cv": {}, "test": {}}
    for (c, r, k), g in cv.groupby(BY):
        res["calibration_cv"][f"{c}|{r}|{k}"] = {
            "n": len(g),
            "cov90": float(g["cov90"].mean()),
            "cov50": float(g["cov50"].mean()),
        }
    table = []
    for version in ("block_aware", "pooled"):
        t = apply(test, cal, version)
        if version == "block_aware":
            t.to_csv(C / "test_intervals_block_aware.csv", index=False)
            primary = t
        for (c, r, k), g in t.groupby(BY):
            for y in ("all", 2022, 2023, 2024):
                d = g if y == "all" else g[g["year"] == y]
                e = cell(d)
                res["test"][f"{version}|{c}|{r}|{k}|{y}"] = e
                table.append(
                    {
                        "version": version,
                        "crop": c,
                        "run": r,
                        "metric": k,
                        "year": y,
                        **{
                            kk: (vv["value"] if isinstance(vv, dict) else vv)
                            for kk, vv in e.items()
                        },
                    }
                )
    pd.DataFrame(table).to_csv(C / "before_after.csv", index=False)

    gate = {}
    for c in CROPS:
        e = res["test"][f"block_aware|{c}|forecast|canopy_integral|all"]
        if e["too_few_to_judge"]:
            gate[c] = {"result": "too few to judge"}
            continue
        cov = e["cov90"]["value"]
        bias = (not 0.4 <= e["above_median"]["value"] <= 0.6) or (
            e["median_signed_err"]["ci_low"] > 0 or e["median_signed_err"]["ci_high"] < 0
        )
        gate[c] = {
            "calibrated": e["calibrated"],
            "coverage_after": e["cov90"],
            "coverage_before": e["cov90_stored"],
            "mean_width_before": e["width90_stored"]["value"],
            "mean_width_after": e["width90"]["value"],
            "width_ratio": e["width90"]["value"] / e["width90_stored"]["value"],
            "winkler_before": e["winkler90_stored"]["value"],
            "winkler_after": e["winkler90"]["value"],
            "biased_centre": bool(bias),
            "result": "pass" if (e["calibrated"] and 0.85 <= cov <= 0.95) else "fail",
        }
    res["gate_forecast_canopy_integral_block_aware"] = gate
    (C / "results.json").write_text(json.dumps(res, indent=1, default=float), "utf-8")

    # reliability plots (forecast and forced, both metrics), block-aware
    for c in CROPS:
        fig, ax = plt.subplots(2, 2, figsize=(8, 7), constrained_layout=True)
        for i, k in enumerate(METRICS):
            for j, r in enumerate(RUNS):
                a = ax[i, j]
                g = primary[
                    (primary["crop"] == c) & (primary["run"] == r) & (primary["metric"] == k)
                ]
                before = [g["cov50_stored"].mean(), np.nan, g["cov90_stored"].mean()]
                after = [g["cov50"].mean(), g["cov80"].mean(), g["cov90"].mean()]
                a.plot([0, 1], [0, 1], color="#999999", lw=1, ls=":", label="perfect")
                a.plot(
                    [0.5, 0.9],
                    [before[0], before[2]],
                    "o-",
                    color="#0072B2",
                    label="before (stored)",
                )
                a.plot(LEVELS, after, "s--", color="#D55E00", label="after (conformal)")
                a.set_xlim(0.4, 1)
                a.set_ylim(0, 1)
                a.set_title(f"{MET[k]}, {r} (n = {len(g)})", fontsize=9)
                a.set_xlabel("Stated coverage")
                a.set_ylabel("Observed coverage 2022-2024")
                if i == 0 and j == 0:
                    a.legend(fontsize=7, frameon=False)
        fig.suptitle(f"{CROP[c]}: reliability of the prediction intervals (block-aware)")
        fig.savefig(C / f"reliability_{c}.png", dpi=100)
        plt.close(fig)

    # markdown
    def f(e, pct=True, nd=1):
        if not isinstance(e, dict):
            return "n/a"
        k = 100 if pct else 1
        return f"{e['value'] * k:.{nd}f}{'%' if pct else ''} [{e['ci_low'] * k:.{nd}f}, {e['ci_high'] * k:.{nd}f}]"

    L = [
        "# Conformal recalibration of the prediction intervals: results",
        "",
        "Pre-registered in `DECISIONS.md` (commit `1c7a9e7`). Calibration: rolling-origin pseudo-forecasts for seasons 2019-2021 (cut-offs 2018-2020). Test: published 2022-2024 records, unchanged medians. 95 % CI: spatial block bootstrap (10 km, 1,000, seed 42). Tag D (model) vs O (HLS).",
        "",
        f"Reproduction check: cut-off 2021 re-run identical to the published records: **{check['cut2021_identical_to_published']}**; fields per run {check['fields_per_run']}.",
        "",
        "## Multipliers (pooled; block-aware values vary by left-out block, see `multipliers.json`)",
        "",
        "| Crop | Run | Quantity | n scores | m50 | m80 | m90 | status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, v in mult.items():
        c, r, k = key.split("|")
        fm = lambda x: "-" if x is None else f"{x:.2f}"  # noqa: E731
        L.append(
            f"| {CROP[c]} | {r} | {MET[k]} | {v['n_scores']} | {fm(v['m50'])} | {fm(v['m80'])} | {fm(v['m90'])} | {v['status']} |"
        )
    L += [
        "",
        "## Gate (forecast, canopy integral, block-aware, 2022-2024 pooled; pass = coverage in 85-95 %)",
        "",
        "| Crop | n | 90 % coverage before | after | mean width before -> after | Winkler before -> after | biased centre | gate |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c, g in gate.items():
        e = res["test"][f"block_aware|{c}|forecast|canopy_integral|all"]
        if g["result"] == "too few to judge":
            L.append(f"| {CROP[c]} | {e['n']} | too few to judge | | | | | |")
            continue
        L.append(
            f"| {CROP[c]} | {e['n']} | {f(g['coverage_before'])} | {f(g['coverage_after'])} | {g['mean_width_before']:.1f} -> {g['mean_width_after']:.1f} (x{g['width_ratio']:.2f}) | {g['winkler_before']:.1f} -> {g['winkler_after']:.1f} | {'yes' if g['biased_centre'] else 'no'} | **{g['result']}** |"
        )
    L += [
        "",
        "## All cells (block-aware; pooled version in `before_after.csv`)",
        "",
        "| Crop | Run | Quantity | Year | n | 90 % before | 90 % after | 80 % after | 50 % before | 50 % after | above median | median signed error |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, e in res["test"].items():
        v, c, r, k, y = key.split("|")
        if v != "block_aware":
            continue
        if e["too_few_to_judge"]:
            L.append(
                f"| {CROP[c]} | {r} | {MET[k]} | {y} | {e['n']} | too few to judge | | | | | | |"
            )
            continue
        L.append(
            f"| {CROP[c]} | {r} | {MET[k]} | {y} | {e['n']} | {f(e['cov90_stored'])} | {f(e['cov90'])} | {f(e['cov80'])} | {f(e['cov50_stored'])} | {f(e['cov50'])} | {f(e['above_median'])} | {f(e['median_signed_err'], pct=False)} |"
        )
    L += [
        "",
        "## Cross-validated coverage on the calibration seasons (leave-one-block-out)",
        "",
        "| Group | n | 90 % | 50 % |",
        "|---|---|---|---|",
    ]
    for key, e in res["calibration_cv"].items():
        L.append(f"| {key} | {e['n']} | {e['cov90'] * 100:.1f}% | {e['cov50'] * 100:.1f}% |")
    (C / "before_after.md").write_text("\n".join(L), "utf-8")
    print(
        json.dumps(
            {
                "check": check,
                "gate": {
                    c: (
                        g["result"],
                        g.get("coverage_after", {}).get("value")
                        if isinstance(g.get("coverage_after"), dict)
                        else None,
                    )
                    for c, g in gate.items()
                },
            },
            default=float,
        )
    )


if __name__ == "__main__":
    main()
