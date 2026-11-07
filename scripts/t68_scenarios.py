"""T6.8: evaluate every candidate under 12 weather what-ifs per pilot field (resumable).

Usage: uv run python -u scripts/t68_scenarios.py [max_seconds]
Reads posterior_draws.json, POWER 2001-2024. Uses N_SC worlds per field (cost; A). Writes
results/rotate/scenarios.json (per field/scenario: six weather-sensitive metrics + balanced rank
order) and, when all fields are done, scenarios_summary.json. Sensitivity tests, not projections.
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

from fieldwitness.data import power
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.evaluate import evaluate, subsample_draws
from fieldwitness.rotate.rank import load_presets, rank_field
from fieldwitness.rotate.scenarios import WEATHER_METRICS, grid, perturb, yearly_arrays

REGION, Y0, Y1, N_SC = "ks_t14slh", 2001, 2024, 10
OUT = Path("results/rotate/scenarios.json")
budget_s = float(sys.argv[1]) if len(sys.argv) > 1 else 540.0
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
pdraws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
cands = enumerate_candidates(REGION)
presets = load_presets()
done = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
t0 = time.time()
for fid in pilot.index:
    if str(fid) in done:
        continue
    if time.time() - t0 > budget_s:
        break
    r = pilot.loc[fid]
    w = power.read(r["lon"], r["lat"], f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(r["lon"], r["lat"])
    pd_ = pdraws[str(fid)]
    d = subsample_draws({k: pd_[k] for k in ("taw_mm", "kc_scale", "budget_mm")}, n=N_SC)
    per = {}
    for sid, dt, dp in grid():
        rain, eto = yearly_arrays(perturb(w, dt, dp), r["lat"], float(elev or 0.0), Y0, Y1)
        ev = evaluate(rain, eto, cands, REGION, d)
        rk = rank_field(ev, presets)["rank"]["balanced"]
        per[sid] = {m: ev[m] for m in WEATHER_METRICS} | {"rank_balanced": rk}
    done[str(fid)] = per
    if len(done) % 10 == 0:
        OUT.write_text(json.dumps(done), "utf-8")
        print(len(done), f"{time.time() - t0:.0f}s", flush=True)
OUT.write_text(json.dumps(done), "utf-8")
print("fields done", len(done), "of", len(pilot), flush=True)
