"""T6.2: evaluate all Kansas candidates for every pilot field from stored posterior worlds.

Usage: uv run python -u scripts/t62_run.py
Reads results/rotate/posterior_draws.json (30 worlds/field; 15 fields are prior fallback, tag A),
POWER 2001-2024 of the field's cell. Writes results/rotate/evaluation.json (metrics per field and
candidate, with p_by_slot per option) and results/rotate/t62_runtime.json (seconds per field).
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.physics.forcing import forcing
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.evaluate import evaluate

REGION = "ks_t14slh"
Y0, Y1 = 2001, 2024
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
pdraws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
cands = enumerate_candidates(REGION)


def weather(lon, lat):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue  # skip incomplete years
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return np.array(rain), np.array(eto)


out, secs = {}, []
t0 = time.time()
for i, fid in enumerate(pilot.index):
    r = pilot.loc[fid]
    d = pdraws[str(fid)]
    t1 = time.time()
    rain, eto = weather(r["lon"], r["lat"])
    res = evaluate(rain, eto, cands, REGION, d)
    secs.append(time.time() - t1)
    res.update(source=d["source"], n_years=int(rain.shape[0]))
    out[str(fid)] = res
    if i % 20 == 0:
        print(i, f"{time.time() - t0:.0f}s", flush=True)

rt = {
    "n_fields": len(out),
    "n_candidates": len(cands),
    "max_s": round(max(secs), 1),
    "median_s": round(float(np.median(secs)), 1),
    "limit_s": 60,
    "pass": bool(max(secs) < 60),
}
Path("results/rotate/evaluation.json").write_text(json.dumps(out), "utf-8")
Path("results/rotate/t62_runtime.json").write_text(json.dumps(rt, indent=2), "utf-8")
print(json.dumps(rt))
