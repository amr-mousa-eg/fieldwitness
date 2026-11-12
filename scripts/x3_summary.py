# ruff: noqa: E501  (markdown table rows)
"""Experiment 3 (pre-registered in DECISIONS.md 2026-11-12): score the clean 2025 test.

Usage: uv run python -u scripts/x3_summary.py
Inputs : results/hindcast/clean2025/records_{calendar,gdd}.jsonl (scripts/x3_clean2025.py)
Outputs: results/hindcast/clean2025/summary.json and summary.md

Same metrics and bootstrap as the before/after comparison (10 km blocks, 1,000 resamples,
seed 42; `results/hindcast/gdd_before_after/code/aggregate.py`). Verdict rule H3 (fixed in the
pre-registration): winter wheat forecast paired difference (gdd - calendar) of peak-timing
absolute error has CI entirely < 0 AND that of canopy CRPS is not entirely > 0. n < 20: no verdict.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path("results/hindcast/gdd_before_after/code").resolve()))
import aggregate as ag  # noqa: E402

C = Path("results/hindcast/clean2025")


def main() -> None:
    pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    blocks = dict(zip(pilot["field_id"], pilot["block"], strict=True))
    cal = ag.season_rows(ag.read_jsonl(C / "records_calendar.jsonl"), blocks, "calendar")
    gdd = ag.season_rows(ag.read_jsonl(C / "records_gdd.jsonl"), blocks, "gdd")
    assert set(cal["year"]) <= {2025} and set(gdd["year"]) <= {2025}
    m = ag.paired(cal, gdd)
    cells = {}
    for run in ag.RUN_TYPES:
        for crop in ag.CROPS:

            def sel(d, run=run, crop=crop):
                return d[(d["run"] == run) & (d["crop"] == crop)]

            cells[f"{run}/{crop}"] = {
                "calendar": ag.cell(sel(cal)),
                "gdd": ag.cell(sel(gdd)),
                "gdd_minus_calendar": ag.diff_cell(sel(m)),
            }
    w = cells["forecast/winter_wheat"]["gdd_minus_calendar"]
    if w["too_few_to_judge"]:
        verdict = {"h3": "no verdict (n < 20)", "n": w["n"]}
    else:
        t_ok = w["peak_abs_err"]["ci_high"] < 0
        c_ok = not (w["ci_crps"]["ci_low"] > 0)
        verdict = {
            "h3": "pass" if (t_ok and c_ok) else "fail",
            "timing_ci_below_zero": t_ok,
            "crps_not_worse": c_ok,
            "n": w["n"],
        }
    doc = {
        "experiment": "Experiment 3: clean 2025 test of the heat clock for winter wheat",
        "preregistration": "DECISIONS.md 2026-11-12 (commit fb48b78)",
        "cutoff": "2021-12-31",
        "scored_year": 2025,
        "cells": cells,
        "verdict": verdict,
        "tag": "D (model) vs O (HLS) statistics; labels E (CSB 2018-2025 edition)",
    }
    (C / "summary.json").write_text(json.dumps(doc, indent=1), "utf-8")

    def f(c, nd=2, pct=False):
        if not isinstance(c, dict):
            return ""
        k, s, d = (100, "%", 0) if pct else (1, "", nd)
        return f"{c['value'] * k:.{d}f}{s} [{c['ci_low'] * k:.{d}f}, {c['ci_high'] * k:.{d}f}]"

    lines = [
        "# Experiment 3: clean 2025 test (calendar vs heat clock)",
        "",
        "Pre-registered in `DECISIONS.md` (commit `fb48b78`) before any 2025 data was on this "
        "machine. Calibration unchanged (seasons <= 2021). 2025 played no part in any choice.",
        "",
        f"**Verdict (H3, winter wheat, forecast run): {verdict['h3']}** (n = {verdict['n']}).",
        "",
        "| Run | Crop | Mode | n | Canopy CRPS | Peak error (d) | Signed (d) | 90 % cov. canopy | 90 % cov. peak |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    names = {"maize": "Maize", "sorghum": "Sorghum", "winter_wheat": "Winter wheat"}
    for key, cell in cells.items():
        run, crop = key.split("/")
        for mode, c in cell.items():
            label = "gdd - calendar" if mode == "gdd_minus_calendar" else mode
            if c["too_few_to_judge"]:
                lines.append(
                    f"| {run} | {names[crop]} | {label} | {c['n']} | too few to judge | | | | |"
                )
                continue
            pct = mode != "gdd_minus_calendar"
            lines.append(
                f"| {run} | {names[crop]} | {label} | {c['n']} | {f(c['ci_crps'])} | "
                f"{f(c['peak_abs_err'], 1)} | {f(c['peak_signed_err'], 1)} | "
                f"{f(c['ci_cov90'], pct=pct)} | {f(c['peak_cov90'], pct=pct)} |"
            )
    lines += [
        "",
        "Maize and sorghum rows are exploratory (not part of the verdict). The candidate under "
        "test is gdd for winter wheat only; maize and sorghum stay on the calendar clock.",
    ]
    (C / "summary.md").write_text("\n".join(lines), "utf-8")
    print(json.dumps(verdict))


if __name__ == "__main__":
    main()
