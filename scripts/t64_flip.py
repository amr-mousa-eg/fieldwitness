"""T6.4: flip analysis per field (what to measure next + counterfactual flip).

Usage: uv run python -u scripts/t64_flip.py [budget_seconds]   (default 500; rerun until done)
Resumable: results/rotate/flip.json holds finished fields; each call continues where it stopped.
Uses 20 seeded posterior worlds per field (cost), POWER 2001-2024. Writes flip.json and, when all
fields are done, flip_summary.json.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.evaluate import subsample_draws
from fieldwitness.rotate.flip import INPUTS, analyse
from fieldwitness.rotate.rank import load_presets

sys.path.insert(0, str(Path(__file__).parent))
from t62_weather import weather  # noqa: E402

REGION, N_WORLDS = "ks_t14slh", 20
budget = float(sys.argv[1]) if len(sys.argv) > 1 else 500.0
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
pdraws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
cands, presets = enumerate_candidates(REGION), load_presets()
path = Path("results/rotate/flip.json")
out = json.loads(path.read_text("utf-8")) if path.exists() else {}
t0 = time.time()
for fid in pilot.index:
    if str(fid) in out:
        continue
    if time.time() - t0 > budget:
        break
    r = pilot.loc[fid]
    rain, eto = weather(r["lon"], r["lat"])
    w = subsample_draws({k: pdraws[str(fid)][k] for k in INPUTS}, n=N_WORLDS)
    res = analyse(rain, eto, cands, REGION, w, presets)
    res["source"] = pdraws[str(fid)]["source"]
    out[str(fid)] = res
    path.write_text(json.dumps(out), "utf-8")
done = len(out)
print(f"{done}/{len(pilot)} fields, {time.time() - t0:.0f}s", flush=True)
if done == len(pilot):
    summ = {"n_fields": done, "n_worlds": N_WORLDS, "n_candidates": len(cands), "presets": {}}
    for name in presets["presets"]:
        ps = [o["presets"][name] for o in out.values()]
        best = Counter(max(p["flip_share"], key=p["flip_share"].get) for p in ps)
        summ["presets"][name] = {
            "mean_flip_share": {
                x: round(sum(p["flip_share"][x] for p in ps) / done, 3) for x in INPUTS
            },
            "most_influential_input": dict(best),
            "fields_with_any_flip_in_grid": {
                x: sum(p["counterfactual"][x] is not None for p in ps) for x in INPUTS
            },
        }
    Path("results/rotate/flip_summary.json").write_text(json.dumps(summ, indent=2), "utf-8")
    print(json.dumps(summ)[:1500])
