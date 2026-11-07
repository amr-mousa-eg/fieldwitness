"""T6.8 summary: scenario counts, size, share of fields whose balanced rank 1 changes."""

import json
from pathlib import Path

d = json.loads(Path("results/rotate/scenarios.json").read_text("utf-8"))
base = "t+0_p+0"
n_sc = {len(v) for v in d.values()}
chg = {}
for per in d.values():
    r0 = per[base]["rank_balanced"]
    for sid, p in per.items():
        # rank_balanced is the best-first order: [0] is the rank-1 candidate
        chg.setdefault(sid, []).append(p["rank_balanced"][0] != r0[0])
out = {
    "fields": len(d),
    "scenarios_per_field": sorted(n_sc),
    "total_mb": round(Path("results/rotate/scenarios.json").stat().st_size / 1e6, 2),
    "kb_per_field": round(Path("results/rotate/scenarios.json").stat().st_size / 1e3 / len(d), 1),
    "share_fields_rank1_changes_vs_baseline": {
        k: round(sum(v) / len(v), 3) for k, v in chg.items()
    },
    "note": "sensitivity tests on past weather, not climate projections; shifts are tag A",
}
Path("results/rotate/scenarios_summary.json").write_text(json.dumps(out, indent=1), "utf-8")
print(json.dumps(out))
