"""Pure aggregation helpers for the GDD before/after presentation (pre-registered 2026-11-12).

Same block bootstrap as `scripts/t7_diagnosis.py` (10 km blocks, 1,000 resamples, seed 42,
percentile 95 % CI); the median uses the same resampled blocks. No model is run here.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

N_BOOT = 1000
SEED = 42
MIN_N = 20
CROPS = ("maize", "sorghum", "winter_wheat")
RUN_TYPES = ("forecast", "forced")
TIMING_BAND_DAYS = 5.0  # noise band, tag A (pre-registered)
CRPS_BAND_SHARE = 0.10  # of the crop's calendar-mode mean forecast CRPS, tag A (pre-registered)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text("utf-8").splitlines() if x.strip()]


def season_rows(recs: list[dict], blocks: dict, mode: str) -> pd.DataFrame:
    """One row per (field, season, run type) with the scored metrics of one phenology mode."""
    out = []
    for r in recs:
        for s in r["seasons"]:
            for run in RUN_TYPES:
                if run not in s:
                    continue
                m = s[run]
                out.append(
                    {
                        "field_id": r["field_id"],
                        "block": blocks[r["field_id"]],
                        "year": s["year"],
                        "crop": s["crop"],
                        "mode": mode,
                        "run": run,
                        "ci_crps": m["canopy_integral"]["crps"],
                        "peak_abs_err": abs(m["peak"]["err_median"]),
                        "peak_signed_err": m["peak"]["err_median"],
                        "ci_cov90": float(m["canopy_integral"]["covered90"]),
                        "peak_cov90": float(m["peak"]["covered90"]),
                    }
                )
    return pd.DataFrame(out)


def baseline_rows(base: list[dict], blocks: dict, mode: str) -> pd.DataFrame:
    out = []
    for e in base:
        for b in ("B0", "B1", "B2"):
            out.append(
                {
                    "field_id": e["field_id"],
                    "block": blocks[e["field_id"]],
                    "year": e["year"],
                    "crop": e["crop"],
                    "mode": mode,
                    "run": "forecast",
                    "method": b,
                    "ci_crps": e[b]["canopy_integral"]["crps"],
                    "peak_abs_err": abs(e[b]["peak"]["err_median"]),
                    "peak_signed_err": e[b]["peak"]["err_median"],
                    "ci_cov90": float(e[b]["canopy_integral"]["covered90"]),
                    "peak_cov90": float(e[b]["peak"]["covered90"]),
                }
            )
    return pd.DataFrame(out)


def boot(values, blocks, stat: str = "mean", n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Statistic and percentile 95 % CI over resampled whole blocks (t7_diagnosis method)."""
    v = np.asarray(values, float)
    b = np.asarray(blocks)
    f = np.mean if stat == "mean" else np.median
    ub = pd.unique(b)
    idx = [np.flatnonzero(b == k) for k in ub]
    rng = np.random.default_rng(seed)
    res = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(ub), size=len(ub), replace=True)
        res[i] = f(v[np.concatenate([idx[j] for j in pick])])
    return {
        "value": float(f(v)),
        "ci_low": float(np.percentile(res, 2.5)),
        "ci_high": float(np.percentile(res, 97.5)),
        "n": len(v),
    }


METRICS = {
    "ci_crps": "mean",
    "peak_abs_err": "mean",
    "peak_signed_err": "median",
    "ci_cov90": "mean",
    "peak_cov90": "mean",
}


def cell(df: pd.DataFrame) -> dict:
    """Metrics of one cell; None values with a flag when n < MIN_N."""
    if len(df) < MIN_N:
        return {"n": len(df), "too_few_to_judge": True}
    out = {"n": len(df), "too_few_to_judge": False}
    for met, stat in METRICS.items():
        out[met] = boot(df[met], df["block"], stat)
    return out


def paired(cal: pd.DataFrame, gdd: pd.DataFrame) -> pd.DataFrame:
    keys = ["field_id", "block", "year", "crop", "run"]
    m = cal.merge(gdd, on=keys, suffixes=("_cal", "_gdd"), validate="one_to_one")
    for met in METRICS:
        m[f"d_{met}"] = m[f"{met}_gdd"] - m[f"{met}_cal"]
    return m


def diff_cell(m: pd.DataFrame) -> dict:
    if len(m) < MIN_N:
        return {"n": len(m), "too_few_to_judge": True}
    out = {"n": len(m), "too_few_to_judge": False}
    for met in METRICS:
        out[met] = boot(m[f"d_{met}"], m["block"], "mean")
    return out


def classify(delta: float, band: float) -> str:
    """'improved' (delta < -band), 'worse' (delta > band) or 'within noise' (|delta| <= band)."""
    if delta < -band:
        return "improved"
    if delta > band:
        return "worse"
    return "within noise"


def per_field(m_forecast: pd.DataFrame, cal_mean_crps: dict) -> pd.DataFrame:
    """Field-mean gdd - calendar per (field, crop) with pre-registered noise bands."""
    g = (
        m_forecast.groupby(["crop", "field_id"])[["d_peak_abs_err", "d_ci_crps"]]
        .mean()
        .reset_index()
    )
    g["n_seasons"] = m_forecast.groupby(["crop", "field_id"]).size().to_numpy()
    g["timing_class"] = [classify(d, TIMING_BAND_DAYS) for d in g["d_peak_abs_err"]]
    g["crps_band"] = g["crop"].map(lambda c: CRPS_BAND_SHARE * cal_mean_crps[c])
    g["crps_class"] = [classify(d, b) for d, b in zip(g["d_ci_crps"], g["crps_band"], strict=True)]
    return g


def pick_examples(eligible: dict, k: dict, seed: int = SEED) -> dict:
    """Pre-registered draw: fresh default_rng(seed) per crop, sorted ids, no replacement."""
    return {
        c: [
            str(x)
            for x in np.random.default_rng(seed).choice(sorted(eligible[c]), k[c], replace=False)
        ]
        for c in k
    }


def beats(fw: pd.DataFrame, base: pd.DataFrame) -> dict:
    """Bk - FW forecast canopy CRPS per baseline on paired seasons; beats if CI > 0."""
    out = {}
    for b, g in base.groupby("method"):
        m = fw.merge(g, on=["field_id", "year", "crop", "block"], suffixes=("_fw", "_b"))
        r = boot(m["ci_crps_b"] - m["ci_crps_fw"], m["block"])
        out[b] = {**r, "fieldwitness_beats": r["ci_low"] > 0, "baseline_beats": r["ci_high"] < 0}
    return out
