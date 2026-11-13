"""Phase 4 SSURGO AWS vs Fixed 150 mm TAW Error Stratification Report.

Pre-registered in DECISIONS.md (2026-11-13). Uses existing committed CSV/JSONL files:
  - results/validation/soil_ssurgo_check.csv (198 fields with SSURGO AWS [E])
  - results/hindcast/ks_t14slh_records.jsonl (2022-2024 forecast errors [D/O])

Does not alter shipped FieldPacks or model parameters.
Usage: uv run python scripts/validate_ssurgo_ablation.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

SOIL_CSV = Path("results/validation/soil_ssurgo_check.csv")
RECORDS_JSONL = Path("results/hindcast/ks_t14slh_records.jsonl")
OUT_JSON = Path("results/validation/ssurgo_ablation_report.json")
OUT_MD = Path("results/validation/ssurgo_ablation_report.md")


def run_stratification() -> dict[str, Any]:
    soil_rows: dict[str, dict[str, float]] = {}
    with SOIL_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("ssurgo_aws_mm") or not r.get("sim_taw_median_mm"):
                continue
            ss = float(r["ssurgo_aws_mm"])
            sim = float(r["sim_taw_median_mm"])
            soil_rows[r["field_id"]] = {
                "ssurgo_aws_mm": ss,
                "sim_taw_median_mm": sim,
                "taw_underestimate_mm": ss - sim,
            }

    joined = []
    for line in RECORDS_JSONL.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        fid = rec["field_id"]
        if fid not in soil_rows:
            continue
        smeta = soil_rows[fid]
        for s in rec["seasons"]:
            if "forecast" not in s:
                continue
            for metric in ("canopy_integral", "cover_days"):
                if metric not in s["forecast"]:
                    continue
                q = s["forecast"][metric]["q"]
                y = float(s["observed"][metric])
                joined.append(
                    {
                        "field_id": fid,
                        "year": int(s["year"]),
                        "crop": s["crop"],
                        "metric": metric,
                        "y": y,
                        "q50": float(q[2]),
                        "signed_err": y - float(q[2]),
                        "abs_err": abs(y - float(q[2])),
                        "cov90": float(s["forecast"][metric]["covered90"]),
                        "regime": (
                            "drought_2022_2023" if int(s["year"]) in (2022, 2023) else "wet_2024"
                        ),
                        **smeta,
                    }
                )

    df = pd.DataFrame(joined)
    # Stratify by SSURGO minus simulated TAW underestimate tertiles
    df["deficit_bin"] = pd.qcut(
        df["taw_underestimate_mm"], q=3, labels=["low_gap", "mid_gap", "high_gap"]
    )

    cells = []
    for (metric, regime, dbin), g in df.groupby(["metric", "regime", "deficit_bin"], observed=True):
        n = int(len(g))
        cells.append(
            {
                "metric": str(metric),
                "regime": str(regime),
                "deficit_bin": str(dbin),
                "n": n,
                "too_few_to_judge": n < 20,
                "mean_taw_gap_mm": round(float(g["taw_underestimate_mm"].mean()), 1),
                "mean_signed_err": round(float(g["signed_err"].mean()), 2),
                "mae": round(float(g["abs_err"].mean()), 2),
                "cov90": round(float(g["cov90"].mean()), 4),
            }
        )

    payload = {
        "schema_version": "1.0",
        "tag": "D",
        "external_soil_source": "USDA-NRCS SSURGO AWS [E]",
        "n_fields_matched": int(df["field_id"].nunique()),
        "mean_ssurgo_aws_mm": round(float(df["ssurgo_aws_mm"].mean()), 1),
        "mean_sim_taw_mm": round(float(df["sim_taw_median_mm"].mean()), 1),
        "cells": cells,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    hdr = (
        "| Metric | Climate Regime | TAW Deficit Tercile | n | "
        "Mean TAW Gap (mm) | Mean Signed Error (y - q50) | MAE | 90% Cov |"
    )
    lines = [
        "# SSURGO AWS vs Fixed 150 mm TAW Prior — Error Stratification Report",
        "",
        (
            f"Fields matched with valid SSURGO profiles: **{payload['n_fields_matched']}**; "
            f"Mean SSURGO AWS `[E]`: **{payload['mean_ssurgo_aws_mm']} mm** vs "
            f"mean shipped sim TAW `[A/D]`: **{payload['mean_sim_taw_mm']} mm**."
        ),
        "",
        hdr,
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in cells:
        flag = " (n<20)" if c["too_few_to_judge"] else ""
        lines.append(
            f"| {c['metric']} | {c['regime']} | {c['deficit_bin']} | {c['n']}{flag} | "
            f"{c['mean_taw_gap_mm']} | {c['mean_signed_err']:+.2f} | "
            f"{c['mae']:.2f} | {c['cov90'] * 100:.1f}% |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    res = run_stratification()
    print(f"Wrote {OUT_JSON} and {OUT_MD} ({res['n_fields_matched']} fields)")
