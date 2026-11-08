"""T7.4c ablation table from the T7.3 baseline results (reuse, no new simulation).

Without witness 2 = B2 (uncalibrated physics). Without witness 3 = full model
(neighbour witness is off since T5.3). Tags: D model, E labels.
"""

import json
from pathlib import Path

SRC = Path("results/hindcast/ks_t14slh_baselines.json")
OUT = Path("results/hindcast/ablation.md")

d = json.loads(SRC.read_text(encoding="utf-8"))
rows = {(r["method"], r["metric"]): r for r in d["table"]}
metrics = ["sos", "peak", "canopy_integral", "cover_days"]
lines = [
    f"# T7.4c Ablation (Kansas, forecast mode, cut-off {d['cutoff']}, "
    f"n={d['n_field_seasons']} field-seasons)",
    "",
    "Forecast CRPS (days, or canopy units for canopy_integral); lower is better.",
    "Reused from T7.3, no new run.",
    "",
    "| Variant | " + " | ".join(metrics) + " |",
    "|---|" + "---|" * len(metrics),
]
variants = [
    ("Full model (3 witnesses, witness 3 off since T5.3)", "fieldwitness"),
    ("Without witness 2 (= B2, uncalibrated physics)", "B2"),
    ("Without witness 3 (= full model; witness 3 is already off)", "fieldwitness"),
]
for label, m in variants:
    cells = []
    for k in metrics:
        r = rows.get((m, k))
        cells.append(f"{r['crps']:.2f}" if r and "crps" in r else "n/a")
    lines.append(f"| {label} | {' | '.join(cells)} |")
lines += [
    "",
    "Notes:",
    "- Witness 3 ablation equals the full model by construction: neighbour effects",
    "  (T5.2) do not exist (Gate 5 failed).",
    "- Table covers the 266 maize/sorghum field-seasons of T7.3; winter wheat (T7.1b)",
    "  is not in the baselines file.",
    "- Weak skill overall (T7.1/T7.2, T7.4b): differences here are not evidence that",
    "  witness 2 helps or hurts.",
]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT)
