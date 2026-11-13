"""Phase 4 evaluation of symmetric and asymmetric CQR prediction intervals.

Pre-registered in DECISIONS.md (2026-11-13).
Reads:
  - Calibration: results/hindcast/conformal/pseudo_cut{2018,2019,2020}.jsonl
  - Held-out test: results/hindcast/ks_t14slh_records.jsonl
  - Coordinates for 10 km spatial blocks: results/validation/soil_ssurgo_check.csv

Writes:
  - results/hindcast/conformal/cqr_evaluation.json
  - results/hindcast/conformal/cqr_evaluation.md

Usage: uv run python scripts/t74_conformal_eval.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fieldwitness.infer.calibration import (
    apply_cqr,
    assign_spatial_blocks,
    interval_score,
    leave_block_out_cqr,
)

CAL_FILES = (
    Path("results/hindcast/conformal/pseudo_cut2018.jsonl"),
    Path("results/hindcast/conformal/pseudo_cut2019.jsonl"),
    Path("results/hindcast/conformal/pseudo_cut2020.jsonl"),
)
TEST_FILE = Path("results/hindcast/ks_t14slh_records.jsonl")
COORDS_FILE = Path("results/validation/soil_ssurgo_check.csv")
OUT_JSON = Path("results/hindcast/conformal/cqr_evaluation.json")
OUT_MD = Path("results/hindcast/conformal/cqr_evaluation.md")

METRICS = ("canopy_integral", "cover_days", "peak", "sos")
RUNS = ("forecast", "forced")
BY = ["crop", "run", "metric"]
POSITIVE_FLOOR_METRICS = {"canopy_integral", "cover_days"}
N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 42


def _load_blocks(coords_path: Path = COORDS_FILE) -> dict[str, str]:
    rows = []
    with coords_path.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"field_id": r["field_id"], "lon": float(r["lon"]), "lat": float(r["lat"])})
    df = pd.DataFrame(rows)
    df["block"] = assign_spatial_blocks(df, block_km=10.0)
    return dict(zip(df["field_id"], df["block"], strict=True))


def _load_records(paths: tuple[Path, ...], blocks: dict[str, str], source: str) -> pd.DataFrame:
    out = []
    for p in paths:
        for line in p.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            fid = rec["field_id"]
            blk = blocks.get(fid, "unknown")
            for s in rec["seasons"]:
                for run in RUNS:
                    if run not in s:
                        continue
                    for met in METRICS:
                        if met not in s[run]:
                            continue
                        q = s[run][met]["q"]
                        out.append(
                            {
                                "field_id": fid,
                                "block": blk,
                                "year": s["year"],
                                "crop": s["crop"],
                                "run": run,
                                "metric": met,
                                "y": float(s["observed"][met]),
                                "q_lo": float(q[0]),
                                "q50": float(q[2]),
                                "q_hi": float(q[4]),
                                "cov90_stored": float(s[run][met]["covered90"]),
                                "source": source,
                            }
                        )
    return pd.DataFrame(out)


def _block_bootstrap_mean(
    df: pd.DataFrame,
    col: str,
    n_resamples: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    d = df.dropna(subset=[col]).reset_index(drop=True)
    if len(d) == 0:
        return {"value": None, "ci_low": None, "ci_high": None, "n": 0}
    blocks = d["block"].unique()
    idx = [d.index[d["block"] == b].to_numpy() for b in blocks]
    rng = np.random.default_rng(seed)
    v = d[col].to_numpy(float)
    boots = [
        float(np.mean(v[np.concatenate([idx[i] for i in rng.choice(len(blocks), len(blocks))])]))
        for _ in range(n_resamples)
    ]
    return {
        "value": round(float(np.mean(v)), 4),
        "ci_low": round(float(np.percentile(boots, 2.5)), 4),
        "ci_high": round(float(np.percentile(boots, 97.5)), 4),
        "n": int(len(d)),
    }


def evaluate() -> dict[str, Any]:
    blocks = _load_blocks()
    cal = _load_records(CAL_FILES, blocks, "cal")
    test = _load_records((TEST_FILE,), blocks, "test")

    all_blocks = sorted(set(cal["block"]).union(set(test["block"])))
    lbo = leave_block_out_cqr(cal, BY, all_blocks, level=0.90)

    out = test.copy()
    for mode in ("stored", "cqr_sym", "cqr_asym"):
        los = []
        his = []
        for row in out.itertuples(index=False):
            floor = 0.0 if row.metric in POSITIVE_FLOOR_METRICS else None
            if mode == "stored":
                lo, hi = apply_cqr(row.q_lo, row.q_hi, 0.0, 0.0, lower_bound=floor)
            else:
                params = lbo.get(((row.crop, row.run, row.metric), row.block))
                if mode == "cqr_sym":
                    m = params["m_sym"] if params and params["m_sym"] is not None else 0.0
                    lo, hi = apply_cqr(row.q_lo, row.q_hi, m, m, lower_bound=floor)
                else:
                    mlo = params["m_lo"] if params and params["m_lo"] is not None else 0.0
                    mhi = params["m_hi"] if params and params["m_hi"] is not None else 0.0
                    lo, hi = apply_cqr(row.q_lo, row.q_hi, mlo, mhi, lower_bound=floor)
            los.append(float(lo))
            his.append(float(hi))
        out[f"lo_{mode}"] = los
        out[f"hi_{mode}"] = his
        in_band = (out["y"] >= out[f"lo_{mode}"]) & (out["y"] <= out[f"hi_{mode}"])
        out[f"cov_{mode}"] = in_band.astype(float)
        out[f"width_{mode}"] = out[f"hi_{mode}"] - out[f"lo_{mode}"]
        out[f"winkler_{mode}"] = interval_score(
            out[f"lo_{mode}"], out[f"hi_{mode}"], out["y"], alpha=0.10
        )

    summary_rows: list[dict[str, Any]] = []
    for (crop, run, metric), g in out[out["run"] == "forecast"].groupby(BY):
        n = int(len(g))
        row: dict[str, Any] = {
            "crop": crop,
            "run": run,
            "metric": metric,
            "n": n,
            "too_few_to_judge": n < 20,
        }
        if n >= 20:
            for mode in ("stored", "cqr_sym", "cqr_asym"):
                row[mode] = {
                    "cov90": _block_bootstrap_mean(g, f"cov_{mode}"),
                    "width90": _block_bootstrap_mean(g, f"width_{mode}"),
                    "winkler90": _block_bootstrap_mean(g, f"winkler_{mode}"),
                }
            cov_asym = row["cqr_asym"]["cov90"]["value"]
            wink_asym = row["cqr_asym"]["winkler90"]["value"]
            wink_stored = row["stored"]["winkler90"]["value"]
            strict_pass = 0.85 <= cov_asym <= 0.95 and wink_asym < wink_stored
            practical_pass = cov_asym >= 0.80 and wink_asym < wink_stored
            row["gate_85_95"] = "pass" if strict_pass else "fail"
            row["gate_80_floor"] = "pass" if practical_pass else "fail"
        summary_rows.append(row)

    payload = {
        "schema_version": "1.0",
        "tag": "D",
        "source": "model:calibration@v1 (CQR pre-registered 2026-11-13)",
        "n_cal_rows": int(len(cal)),
        "n_test_rows": int(len(test)),
        "n_spatial_blocks": int(len(all_blocks)),
        "forecast_summary": summary_rows,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    hdr = (
        "| Crop | Metric | n | Stored Cov90 | Sym CQR Cov90 | Asym CQR Cov90 | "
        "Stored Winkler | Sym Winkler | Asym Winkler | Gate (85–95%) | Gate (>=80%) |"
    )
    lines = [
        "# Phase 4 Split-CQR Interval Recalibration Evaluation (Forecast Mode, 2022–2024)",
        "",
        (
            f"Calibration: rolling-origin 2019–2021 (`n={len(cal)}` rows); "
            f"Held-out Test: 2022–2024 (`n={len(test)}` rows)."
        ),
        (
            f"Spatial blocks: `{len(all_blocks)}` (10 km grid), 1,000 block bootstrap resamples "
            "(`seed=42`). Point medians `q50` unchanged."
        ),
        "",
        hdr,
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary_rows:
        if r["too_few_to_judge"]:
            lines.append(
                f"| {r['crop']} | {r['metric']} | {r['n']} | too few to judge | "
                "— | — | — | — | — | n/a | n/a |"
            )
            continue
        lines.append(
            f"| {r['crop']} | {r['metric']} | {r['n']} | "
            f"{r['stored']['cov90']['value'] * 100:.1f}% | "
            f"{r['cqr_sym']['cov90']['value'] * 100:.1f}% | "
            f"{r['cqr_asym']['cov90']['value'] * 100:.1f}% | "
            f"{r['stored']['winkler90']['value']:.1f} | "
            f"{r['cqr_sym']['winkler90']['value']:.1f} | "
            f"{r['cqr_asym']['winkler90']['value']:.1f} | "
            f"**{r['gate_85_95']}** | **{r['gate_80_floor']}** |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    res = evaluate()
    print(f"Wrote {OUT_JSON} and {OUT_MD} ({len(res['forecast_summary'])} cells)")
