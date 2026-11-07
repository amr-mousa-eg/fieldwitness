"""T6.2 runtime check on a real pilot field: POWER 2001-2024, all Kansas candidates, 30 worlds.

Worlds here are PRIOR draws (priors.yaml, tag A), not posteriors: pooled per-field posterior draws
are the next step. Writes results/rotate/t62_benchmark.json (timing + metric summary).
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.infer import forward, priors
from fieldwitness.physics.forcing import forcing
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.evaluate import evaluate, subsample_draws

REGION = "ks_t14slh"
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
r = pilot.iloc[0]
w = power.read(r["lon"], r["lat"], "2001-01-01", "2024-12-31")
_, elev = power.cached(r["lon"], r["lat"])
f = forcing(w, r["lat"], float(elev or 0.0))
rain, eto = [], []
for y in range(2001, 2025):
    fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
    assert len(fy) == 365 and not fy.isna().any().any(), y
    rain.append(fy["rain"].to_numpy(float))
    eto.append(fy["eto"].to_numpy(float))
rain, eto = np.array(rain), np.array(eto)

cfg = forward.load_cfg()
h = priors.sample(2000)
irrig = np.asarray(h["irrigated"], bool)
pool = {
    "taw_mm": cfg["taw_base_mm"] * np.asarray(h["taw_scale"], float),
    "kc_scale": np.asarray(h["kc_mid_scale"], float),
    "budget_mm": np.where(irrig, np.asarray(h["irrigation_mm"], float), 0.0),
}
cands = enumerate_candidates(REGION)
t0 = time.time()
out = evaluate(rain, eto, cands, REGION, subsample_draws(pool, 30))
dt = time.time() - t0
ok = [x for x in out["ryi"] if x is not None]
summary = {
    "field_id": str(r["field_id"]),
    "n_candidates": len(cands),
    "n_worlds": 30,
    "n_start_years": 21,
    "seconds": round(dt, 1),
    "ryi_range": [round(min(ok), 3), round(max(ok), 3)],
    "water_use_mm_range": [round(min(out["water_use_mm"])), round(max(out["water_use_mm"]))],
    "draws": "prior (A), not posterior",
    "tag": "D",
}
Path("results/rotate").mkdir(parents=True, exist_ok=True)
Path("results/rotate/t62_benchmark.json").write_text(json.dumps(summary, indent=2), "utf-8")
print(json.dumps(summary))
