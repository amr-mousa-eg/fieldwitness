"""T6.3: rank candidates per field and weight preset from results/rotate/evaluation.json.

Usage: uv run python -u scripts/t63_rank.py
Writes results/rotate/ranking.json (per field: pareto flags, rank/score per preset, regret) and
results/rotate/ranking_summary.json (counts; rerun check). Deterministic, no randomness.
"""

import json
from collections import Counter
from pathlib import Path

from fieldwitness.rotate.rank import load_presets, rank_field

presets = load_presets()
evals = json.loads(Path("results/rotate/evaluation.json").read_text("utf-8"))
out = {}
for fid, ev in evals.items():
    r = rank_field(ev, presets)
    r["candidates"] = ev["candidates"]
    out[fid] = r

again = {fid: rank_field(ev, presets) for fid, ev in evals.items()}
reproducible = all({k: v for k, v in out[f].items() if k != "candidates"} == again[f] for f in out)
top = {
    name: Counter("-".join(out[f]["candidates"][out[f]["rank"][name][0]]) for f in out).most_common(
        5
    )
    for name in presets["presets"]
}
summary = {
    "n_fields": len(out),
    "n_candidates": len(next(iter(evals.values()))["candidates"]),
    "mean_pareto_share": round(
        sum(sum(o["pareto"]) / len(o["pareto"]) for o in out.values()) / len(out), 3
    ),
    "reproducible": reproducible,
    "top1_by_preset": top,
    "weights_tag": "A",
}
Path("results/rotate/ranking.json").write_text(json.dumps(out), "utf-8")
Path("results/rotate/ranking_summary.json").write_text(json.dumps(summary, indent=2), "utf-8")
print(json.dumps(summary)[:1500])
