# ruff: noqa: E501
"""Reliability tiers, step 1 of 2 (training data only; DECISIONS.md 2026-11-12).

Usage: uv run python -u scripts/x5_train.py
Reads ONLY the 2019-2021 pseudo-forecasts (cut-offs 2018-2020) and the matching credibility
files; never opens the 2022-2024 records. Writes training_table.csv, cv_results.csv and
model_and_tiers.json (chosen model, frozen tier boundaries) under results/hindcast/reliability/.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.agree import reliability as rl

R = Path("results/hindcast/reliability")
SRC = R / "from_conformal"


def read(p):
    return [json.loads(x) for x in Path(p).read_text("utf-8").splitlines() if x.strip()]


def load_inputs():
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
    labels = pd.read_parquet("data/labels/ks_t14slh.parquet")
    return pilot, series, labels


def cred_at(cut):
    d = json.loads((R / f"credibility_cut{cut}.json").read_text("utf-8"))
    assert d["cutoff"] == f"{cut}-12-31"
    return {k: v["credibility"] for k, v in d["fields"].items()}


def main():
    pilot, series, labels = load_inputs()
    parts = []
    for cut in (2018, 2019, 2020):
        recs = read(SRC / f"pseudo_cut{cut}.jsonl")
        df = rl.build_rows(recs, cut, series, labels, pilot, cred_at(cut))
        assert (df["year"] == cut + 1).all()
        parts.append(df)
    train = rl.add_target(pd.concat(parts, ignore_index=True))
    assert train["year"].max() <= 2021
    train.to_csv(R / "training_table.csv", index=False)

    cv = []
    oof = {}
    for m in rl.MODELS:
        p = rl.lobo_cv(train, m)
        oof[m] = p
        se2 = (p - train["y"].to_numpy()) ** 2
        cv.append(
            {
                "model": m,
                "loss": float(se2.mean()),
                "se": float(se2.std(ddof=1) / np.sqrt(len(se2))),
                "cv_spearman": float(pd.Series(p).rank().corr(train["y"].rank()))
                if np.ptp(p) > 0
                else 0.0,
            }
        )
    cv = pd.DataFrame(cv)
    cv.to_csv(R / "cv_results.csv", index=False)
    chosen = rl.choose(cv)
    pred_train = rl.fit_predict(chosen, train, train)
    bounds = rl.tier_bounds(pred_train)
    doc = {
        "preregistration": "DECISIONS.md 2026-11-12 (commit c28cf32)",
        "training": {
            "seasons": [2019, 2020, 2021],
            "rows": len(train),
            "fields": int(train["field_id"].nunique()),
            "rows_by_crop": train["crop"].value_counts().to_dict(),
            "fields_by_crop": train.groupby("crop")["field_id"].nunique().to_dict(),
            "rows_by_year": {
                str(k): int(v) for k, v in train["year"].value_counts().sort_index().items()
            },
            "mean_crps_ci": float(train["crps_ci"].mean()),
            "source_files_sha256": {
                f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted(SRC.glob("*.jsonl"))
            },
            "source": "copied from the local checkout of branch experiment/conformal (PR #14), results/hindcast/conformal/",
        },
        "cv": cv.to_dict("records"),
        "chosen_model": chosen,
        "rule": "simplest of null < crop < grade < credibility < gbm with CV loss <= best + SE(best)",
        "tier_bounds_log_scaled_crps": bounds,
        "tiers": "R1 <= b1 < R2 <= b2 < R3 <= b3 < R4 (predicted y); relative reliability, not evidence grades",
        "n_distinct_train_predictions": int(np.unique(np.round(pred_train, 12)).size),
        "train_tier_counts": {
            f"R{k}": int(v)
            for k, v in pd.Series(rl.assign_tiers(pred_train, bounds))
            .value_counts()
            .sort_index()
            .items()
        },
        "tag": "D",
    }
    (R / "model_and_tiers.json").write_text(json.dumps(doc, indent=1), "utf-8")
    print(cv.round(4).to_string())
    print(
        json.dumps(
            {
                k: doc[k]
                for k in (
                    "chosen_model",
                    "tier_bounds_log_scaled_crps",
                    "n_distinct_train_predictions",
                    "train_tier_counts",
                )
            },
            indent=1,
        )
    )
    print(
        json.dumps(doc["training"]["rows_by_crop"]), json.dumps(doc["training"]["fields_by_crop"])
    )


if __name__ == "__main__":
    main()
