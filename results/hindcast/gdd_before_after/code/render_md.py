# ruff: noqa: E501  (markdown table rows are long strings)
"""Render results/hindcast/gdd_before_after/summary.md from summary.json (no new numbers)."""

import json
from pathlib import Path

OUT = Path("results/hindcast/gdd_before_after")
d = json.loads((OUT / "summary.json").read_text("utf-8"))
CROP = {"maize": "Maize", "sorghum": "Sorghum", "winter_wheat": "Winter wheat"}


def f(c, pct=False, nd=2):
    if not isinstance(c, dict):
        return ""
    k, s, nd = (100, "%", 0) if pct else (1, "", nd)
    return f"{c['value'] * k:.{nd}f}{s} [{c['ci_low'] * k:.{nd}f}, {c['ci_high'] * k:.{nd}f}]"


L = [
    "# GDD before/after: tables (calendar = before, heat clock gdd = after)",
    "",
    f"Pre-registration: {d['pre_registration']}. All numbers come from the Experiment 2 run "
    "outputs; 95 % CI = spatial block bootstrap (10 km blocks, 1,000 resamples, seed 42). "
    "Statistics tag D (model) scored against O (HLS); crop labels E. Plain-language summary: "
    "`docs/GDD_BEFORE_AFTER.md`.",
    "",
    "## 1. Summary table",
    "",
    "CRPS = canopy-integral CRPS (lower is better). Peak error = mean absolute peak-timing error "
    "(days). Signed = median signed peak-timing error (days, + = model late). Coverage = share of "
    "seasons where the observation fell inside the 90 % interval (canopy integral / peak day).",
    "",
]
for run in ("forecast", "forced"):
    L += [
        f"### {run.capitalize()} run",
        "",
        "| Crop | Method | Mode | n | CRPS | Peak error (d) | Signed (d) | 90 % cov. canopy | 90 % cov. peak |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in d["summary_table"]:
        if r["run"] != run:
            continue
        if r.get("note"):
            L.append(f"| {CROP[r['crop']]} | {r['method']} | | | {r['note']} | | | | |")
            continue
        if r["too_few_to_judge"]:
            L.append(
                f"| {CROP[r['crop']]} | {r['method']} | {r['mode']} | {r['n']} | too few to judge | | | | |"
            )
            continue
        mode = f"**{r['mode']}**" if r["mode"] == "gdd - calendar" else r["mode"]
        pct = r["mode"] != "gdd - calendar"
        L.append(
            f"| {CROP[r['crop']]} | {r['method']} | {mode} | {r['n']} | {f(r['ci_crps'])} | "
            f"{f(r['peak_abs_err'], nd=1)} | {f(r['peak_signed_err'], nd=1)} | "
            f"{f(r['ci_cov90'], pct=pct)} | {f(r['peak_cov90'], pct=pct)} |"
        )
    L.append("")
L += [
    "In the gdd − calendar rows the coverage differences are shares (0.10 = 10 points); the "
    "signed-error row is the mean of per-season differences.",
    "",
    "### Does FieldWitness beat the baselines? (forecast canopy CRPS, baseline − FieldWitness; "
    "beats = CI entirely > 0)",
    "",
    "| Crop | Baseline | Calendar mode | Gdd mode | Beats in both modes |",
    "|---|---|---|---|---|",
]
bt = d["fieldwitness_vs_baselines_forecast_canopy_crps"]
for c in ("maize", "sorghum"):
    for b in ("B0", "B1", "B2"):
        cc, gg = bt[c]["calendar"][b], bt[c]["gdd"][b]

        def word(x):
            return (
                "FW beats"
                if x["fieldwitness_beats"]
                else ("baseline beats FW" if x["baseline_beats"] else "no clear difference")
            )

        L.append(
            f"| {CROP[c]} | {b} | {f(cc)} {word(cc)} | {f(gg)} {word(gg)} | "
            f"{'yes' if bt[c]['fieldwitness_beats_in_both_modes'][b] else 'no'} |"
        )
L += ["| Winter wheat | B0-B2 | no baseline | no baseline | - |", ""]

pc = d["per_field_counts"]
L += [
    "## 2. Per-field view (forecast run; field mean over its scored seasons of the crop)",
    "",
    "Noise bands fixed beforehand (tag A): timing ±5 days; CRPS ±10 % of the crop's calendar "
    "mean forecast CRPS. Histograms: `figures/per_field_histograms.png`; values: `per_field.csv`.",
    "",
    "| Crop | Fields | Timing: improved / within noise / worse | CRPS band | CRPS: improved / within noise / worse |",
    "|---|---|---|---|---|",
]
for c in ("maize", "sorghum", "winter_wheat"):
    t, k = pc[c]["timing"], pc[c]["crps"]
    L.append(
        f"| {CROP[c]} | {pc[c]['fields']} | {t.get('improved', 0)} / {t.get('within noise', 0)} / "
        f"{t.get('worse', 0)} | ±{pc[c]['crps_band']:.2f} | {k.get('improved', 0)} / "
        f"{k.get('within noise', 0)} / {k.get('worse', 0)} |"
    )
L += [
    "",
    "## 3. Year by year (gdd − calendar; `by_year.csv`)",
    "",
    "| Run | Crop | Year | n | Δ CRPS | Δ peak error (d) |",
    "|---|---|---|---|---|---|",
]
for r in d["by_year_difference"]:
    if r["too_few_to_judge"]:
        L.append(
            f"| {r['run']} | {CROP[r['crop']]} | {r['year']} | {r['n']} | too few to judge | |"
        )
    else:
        L.append(
            f"| {r['run']} | {CROP[r['crop']]} | {r['year']} | {r['n']} | {f(r['ci_crps'])} | "
            f"{f(r['peak_abs_err'], nd=1)} |"
        )
L += [
    "",
    "## 5. Winter wheat timing change by pre-registered diagnosis dimensions (forecast)",
    "",
    "| Dimension | Cell | n | Δ peak error (d) |",
    "|---|---|---|---|",
]
for dim, cells in d["winter_wheat_timing_split"].items():
    for k, v in cells.items():
        val = "too few to judge" if v["too_few_to_judge"] else f(v["d_peak_abs_err"], nd=1)
        L.append(f"| {dim} | {k} | {v['n']} | {val} |")
L += [
    "",
    "Early- vs late-season fields is not a pre-registered dimension and was not computed. "
    "**Cause of the timing change: not established.**",
    "",
    "## 4. Example fields",
    "",
    "Random draw (seed 42, rule fixed beforehand): "
    + "; ".join(
        f"{CROP[c]} {', '.join(x[:8] for x in ids)}"
        for c, ids in d["example_fields_random_seed42"].items()
    )
    + ". Charts: `figures/example_*.png`. Selected after the fact (for illustration, not evidence): "
    "`figures/after_the_fact_*.png`.",
    "",
    "## 7. Sanity",
    "",
]
s = d["sanity"]
L += [
    f"- Calendar records vs published: {s['calendar_records_vs_published']['n_identical']} of "
    f"{s['calendar_records_vs_published']['n']} fields identical.",
    f"- Calendar baselines vs published: {s['calendar_baselines_vs_published']['n_identical']} of "
    f"{s['calendar_baselines_vs_published']['n']} field-seasons identical.",
    "- Curve re-runs (identical code plus a read-only hook): records identical in both modes "
    f"({s['curve_reruns']['calendar']['n_predictions']} predictions each).",
    "- Source files: " + "; ".join(f"`{x}`" for x in s["source_files"]) + ".",
    "",
    "## 6. 2025 clean test",
    "",
    "Not possible from local data: HLS ends 2024-12-31 and crop labels end 2024. Estimated "
    "download about 175–185 MB (3 AppEEARS point tasks, by analogy with 2022–2024); not "
    "downloaded. Details: `feasibility_2025.json`.",
    "",
]
(OUT / "summary.md").write_text("\n".join(L), "utf-8")
print("wrote", OUT / "summary.md")
