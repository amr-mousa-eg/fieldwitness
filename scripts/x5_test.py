# ruff: noqa: E501
"""Reliability tiers, step 2 of 2: the one test on 2022-2024 (DECISIONS.md 2026-11-12).

Usage: uv run python -u scripts/x5_test.py
Reads the frozen model choice and tier boundaries (model_and_tiers.json, written by x5_train.py
from training data only), refits the models on the same training table, and scores the published
2022-2024 records once. Writes test_by_tier.csv/.md, breakdowns.json, results.json and
tiers_vs_grades.png under results/hindcast/reliability/.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fieldwitness.agree import reliability as rl  # noqa: E402

R = Path("results/hindcast/reliability")
CROP = {"maize": "Maize", "sorghum": "Sorghum", "winter_wheat": "Winter wheat"}


def read(p):
    return [json.loads(x) for x in Path(p).read_text("utf-8").splitlines() if x.strip()]


def main():
    frozen = json.loads((R / "model_and_tiers.json").read_text("utf-8"))
    bounds, chosen = frozen["tier_bounds_log_scaled_crps"], frozen["chosen_model"]
    train = pd.read_csv(R / "training_table.csv")
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    labels = pd.read_parquet("data/labels/ks_t14slh.parquet")
    cred = json.loads((R / "credibility_cut2021.json").read_text("utf-8"))
    cred = {k: v["credibility"] for k, v in cred["fields"].items()}
    test = rl.build_rows(
        read("results/hindcast/ks_t14slh_records.jsonl"), 2021, series, labels, pilot, cred
    )
    test = rl.add_target(test)
    grade_check = {
        "B": int((test["grade"] == 1).sum()),
        "C": int((test["grade"] == 2).sum()),
        "D": int((test["grade"] == 3).sum()),
    }

    pred = {m: rl.fit_predict(m, train, test) for m in rl.MODELS}
    test["pred"] = pred[chosen]
    test["tier"] = rl.assign_tiers(test["pred"], bounds)
    test["tier_crop_only"] = rl.assign_tiers(
        pred["crop"], rl.tier_bounds(rl.fit_predict("crop", train, train))
    )
    test.to_csv(R / "test_table.csv", index=False)

    def evaluate(d, tier_col="tier", p=None):
        p = d["pred"] if p is None else p
        tm = rl.boot_tier_means(d["crps_ci"], d[tier_col], d["block"])
        means = [tm[f"R{k}"]["mean"] for k in (1, 2, 3, 4)]
        for k in (1, 2, 3, 4):
            if tm[f"R{k}"]["n"] < 20:
                tm[f"R{k}"]["too_few_to_judge"] = True
        return tm, means, rl.boot_spearman(p, d["y"], d["block"])

    tm, means, sp = evaluate(test)
    sp_e_b = rl.boot_spearman(pred["gbm"], test["y"], test["block"], pred2=pred["crop"])
    sp_e_c = rl.boot_spearman(pred["gbm"], test["y"], test["block"], pred2=pred["grade"])
    gate = {
        "i_ordered_R1_lt_R2_lt_R3_lt_R4": rl.ordered(means),
        "ii_R4_minus_R1_ci_excludes_0": bool(
            tm["R4_minus_R1"]["ci"] is not None
            and (tm["R4_minus_R1"]["ci"][0] > 0 or tm["R4_minus_R1"]["ci"][1] < 0)
        ),
        "iii_spearman_ci_excludes_0": bool(sp["ci"][0] > 0 or sp["ci"][1] < 0),
        "iv_gbm_beats_crop_and_grade": bool(sp_e_b["diff_ci"][0] > 0 and sp_e_c["diff_ci"][0] > 0),
    }
    gate["verdict"] = "shown" if all(gate.values()) else "not shown"

    # all models' test Spearman (information)
    sp_all = {m: rl.boot_spearman(pred[m], test["y"], test["block"]) for m in rl.MODELS}
    # breakdowns
    brk = {"by_crop": {}, "by_year": {}}
    for c, d in test.groupby("crop"):
        t2, m2, s2 = evaluate(d)
        brk["by_crop"][c] = {
            "tiers": t2,
            "ordered": rl.ordered(m2),
            "spearman_chosen": s2,
            "spearman_gbm": rl.boot_spearman(pred["gbm"][d.index], d["y"], d["block"]),
        }
    for y, d in test.groupby("year"):
        t2, m2, s2 = evaluate(d)
        brk["by_year"][str(y)] = {
            "tiers": t2,
            "ordered": rl.ordered(m2),
            "spearman_chosen": s2,
            "spearman_gbm": rl.boot_spearman(pred["gbm"][d.index], d["y"], d["block"]),
        }
    # honesty: crop-only tiers, current grades, train vs test level, secondary target
    crop_only = rl.boot_tier_means(test["crps_ci"], test["tier_crop_only"], test["block"])
    grades = rl.boot_tier_means(test["crps_ci"], test["grade"], test["block"])  # R1..R3 = B, C, D
    peak = rl.boot_tier_means(test["peak_abs_err"], test["tier"], test["block"])
    tier_crop = test.groupby(["tier", "crop"]).size().unstack(fill_value=0).to_dict()
    level = {
        "train_mean_crps": float(train["crps_ci"].mean()),
        "test_mean_crps": float(test["crps_ci"].mean()),
        "train_by_crop": train.groupby("crop")["crps_ci"].mean().to_dict(),
        "test_by_crop": test.groupby("crop")["crps_ci"].mean().to_dict(),
    }
    res = {
        "preregistration": frozen["preregistration"],
        "chosen_model": chosen,
        "tier_bounds": bounds,
        "test_n": len(test),
        "grade_reproduction_check": grade_check,
        "by_tier": tm,
        "spearman_chosen": sp,
        "spearman_all_models": sp_all,
        "gbm_minus_crop": sp_e_b,
        "gbm_minus_grade": sp_e_c,
        "gate": gate,
        "crop_only_tiers": crop_only,
        "current_grades_B_C_D_as_R1_R3": grades,
        "peak_abs_err_by_tier": peak,
        "tier_crop_composition": tier_crop,
        "error_level_train_vs_test": level,
        "tag": "D (model) vs O (HLS) statistics; labels E",
    }
    (R / "results.json").write_text(json.dumps(res, indent=1, default=float), "utf-8")
    (R / "breakdowns.json").write_text(json.dumps(brk, indent=1, default=float), "utf-8")

    rows = []
    for k in (1, 2, 3, 4):
        t = tm[f"R{k}"]
        rows.append(
            {
                "tier": f"R{k}",
                "n": t["n"],
                "mean_crps": t["mean"],
                "ci_low": t["ci"][0] if t["ci"] else None,
                "ci_high": t["ci"][1] if t["ci"] else None,
            }
        )
    pd.DataFrame(rows).to_csv(R / "test_by_tier.csv", index=False)

    # plot
    fig, ax = plt.subplots(figsize=(8, 4.2), constrained_layout=True)
    xs, labs = [], []
    for i, k in enumerate((1, 2, 3, 4)):
        t = tm[f"R{k}"]
        if t["mean"] is not None:
            ax.errorbar(
                i,
                t["mean"],
                yerr=[[t["mean"] - t["ci"][0]], [t["ci"][1] - t["mean"]]],
                fmt="o",
                color="#0072B2",
                capsize=4,
            )
        xs.append(i)
        labs.append(f"R{k}\nn={t['n']}")
    for j, (g, k) in enumerate((("B", 1), ("C", 2), ("D", 3))):
        t = grades[f"R{k}"]
        x = 5 + j
        ax.errorbar(
            x,
            t["mean"],
            yerr=[[t["mean"] - t["ci"][0]], [t["ci"][1] - t["mean"]]],
            fmt="s",
            color="#D55E00",
            capsize=4,
        )
        xs.append(x)
        labs.append(f"grade {g}\nn={t['n']}")
    ax.set_xticks(xs, labs)
    ax.set_ylabel("Canopy-integral CRPS, 2022-2024 (lower = better)")
    ax.set_title(
        f"Reliability tiers (model: {chosen}, blue) vs current evidence grades (orange), 95 % CI"
    )
    fig.savefig(R / "tiers_vs_grades.png", dpi=100)
    plt.close(fig)
    print(
        json.dumps(
            {
                "gate": gate,
                "by_tier": {
                    k: (v.get("n"), v.get("mean"))
                    for k, v in tm.items()
                    if k.startswith("R") and k != "R4_minus_R1"
                },
                "spearman": sp,
                "gbm-crop": sp_e_b,
                "gbm-grade": sp_e_c,
                "grade_check": grade_check,
                "level": level,
            },
            indent=1,
            default=float,
        )
    )


if __name__ == "__main__":
    main()
