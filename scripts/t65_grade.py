"""T6.5: grade every option of every pilot field (physics witness + own-past credibility only).

Usage: uv run python -u scripts/t65_grade.py
Physics effect of an option = RYI(option) - RYI(Current), per weather start year (mean over the
field's posterior worlds); value = median over years, interval = 5th-95th percentile over years.
UNVERIFIED (A): this interval is weather variability, not parameter uncertainty.
Neighbour effects do not exist yet (T5.2 blocked), so the best possible grade is B.
Key-input tags (A, UNVERIFIED): taw, kc_scale, irrigation budget = D if posterior else A;
sowing dates = A (team choice); weather (POWER) = D.
Writes results/rotate/grades.json and grades_summary.json.
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from fieldwitness.agree.grade import Effect, grade_option
from fieldwitness.agree.trials import get_trial_effect
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.current import all_current
from fieldwitness.rotate.evaluate import evaluate

REGION = "ks_t14slh"
Y0, Y1 = 2001, 2024
from fieldwitness.data import power  # noqa: E402
from fieldwitness.physics.forcing import forcing  # noqa: E402

cfg = yaml.safe_load(Path("config/grading.yaml").read_text("utf-8"))["grades"]
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
pdraws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
ev = json.loads(Path("results/rotate/evaluation.json").read_text("utf-8"))
cred = {
    f["field_id"]: f["credibility"]
    for f in json.loads(Path("results/inference/credibility.json").read_text("utf-8"))["fields"]
}
allowed = set(json.loads(Path("results/rotate/current_summary.json").read_text("utf-8"))["allowed"])
cands = enumerate_candidates(REGION)
currents = all_current(allowed)


def weather(lon, lat):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return np.array(rain), np.array(eto)


out, grades, skipped = {}, Counter(), Counter()
for fid in pilot.index:
    fid = str(fid)
    cur = currents[fid]
    d, e = pdraws[fid], ev[fid]
    if not cur.simulatable or cur.second_crops or len(cur.sequence) < 3:
        skipped["current_not_simulatable"] += 1
        continue
    r = pilot.loc[fid]
    rain, eto = weather(r["lon"], r["lat"])
    try:
        c_res = evaluate(rain, eto, [tuple(cur.sequence)], REGION, d)
    except Exception as ex:  # noqa: BLE001
        skipped[f"current_eval_failed:{type(ex).__name__}"] += 1
        continue
    cy = c_res["ryi_by_year"][0]
    if cy is None:
        skipped["current_ryi_nan"] += 1
        continue
    cy = np.array(cy, float)
    t_model = "D" if d["source"] == "posterior" else "A"
    tags = {
        "taw": t_model,
        "kc_scale": t_model,
        "irrigation_budget": t_model,
        "sowing_dates": "A",
        "weather": "D",
    }
    opts = []
    for cand, oy in zip(e["candidates"], e["ryi_by_year"], strict=True):
        if oy is None:
            continue
        diff = np.array(oy, float) - cy
        phys = Effect(
            float(np.nanmedian(diff)),
            float(np.nanpercentile(diff, 5)),
            float(np.nanpercentile(diff, 95)),
        )
        trial_eff, bench = get_trial_effect(cand)
        g, reasons = grade_option(phys, None, cred.get(fid), tags, cfg, trials=trial_eff)
        grades[g] += 1
        opt_entry = {
            "option": cand,
            "grade": g,
            "reasons": reasons,
            "physics_ryi_effect": [phys.value, phys.lo90, phys.hi90],
        }
        if bench is not None and trial_eff is not None:
            opt_entry["agronomic_trial"] = {
                "source": "K-State Research and Extension (Tag E)",
                "citation": bench.citation,
                "trial_name": bench.trial_name,
                "yield_advantage_pct": bench.yield_advantage_pct,
                "water_storage_delta_mm": bench.water_storage_differential_mm,
                "trial_ryi_effect": [trial_eff.value, trial_eff.lo90, trial_eff.hi90],
            }
        opts.append(opt_entry)
    out[fid] = {
        "current": cur.sequence,
        "credibility": cred.get(fid),
        "tags": tags,
        "options": opts,
    }

Path("results/rotate/grades.json").write_text(json.dumps(out), "utf-8")
summ = {
    "n_fields_graded": len(out),
    "skipped": dict(skipped),
    "grade_counts_all_options": dict(grades),
    "note": "no neighbour witness (T5.2 blocked) -> max grade B; "
    "physics interval = weather variability (A)",
}
Path("results/rotate/grades_summary.json").write_text(json.dumps(summ, indent=2), "utf-8")
print(json.dumps(summ))
