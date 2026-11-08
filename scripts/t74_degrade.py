"""T7.4b: skill when the clear HLS dates used in calibration are thinned to 50 % / 25 %.

Reads results/hindcast/ks_t14slh_records{,_thin50,_thin25}.jsonl (written by
`t71_hindcast.py 2000 100 1000000 <frac>`) -> results/hindcast/ks_t14slh_degradation.json.
Thinning is seeded (SEED) and applies to fitting seasons only; scoring uses all observed dates.
Seasons whose thinned fit has < 10 dates are dropped from fitting (fit_source falls back), so the
scored set is identical across levels. Statistics tag D (model) vs O (HLS).
"""

import json
from pathlib import Path

import numpy as np

H = Path("results/hindcast")
METRICS = ("sos", "peak", "canopy_integral", "cover_days")
LEVELS = {
    "100": "ks_t14slh_records.jsonl",
    "50": "ks_t14slh_records_thin50.jsonl",
    "25": "ks_t14slh_records_thin25.jsonl",
}


def load(name):
    recs = [json.loads(x) for x in (H / name).read_text("utf-8").splitlines() if x]
    return {(r["field_id"], s["year"]): s for r in recs for s in r["seasons"]}


data = {lv: load(f) for lv, f in LEVELS.items()}
keys = sorted(set.intersection(*(set(d) for d in data.values())))
out = {"n_field_seasons": len(keys), "tag": "D vs O", "levels": {}}
for lv, d in data.items():
    res = {"fit_source": {}}
    for k in keys:
        src = d[k]["fit_source"]
        res["fit_source"][src] = res["fit_source"].get(src, 0) + 1
    for mode in ("forecast", "forced"):
        for m in METRICS:
            v = [d[k][mode][m] for k in keys if mode in d[k]]
            res[f"{mode}_{m}"] = {
                "n": len(v),
                "crps": round(float(np.mean([a["crps"] for a in v])), 3),
                "covered50": round(float(np.mean([a["covered50"] for a in v])), 3),
                "covered90": round(float(np.mean([a["covered90"] for a in v])), 3),
                "mae_median": round(float(np.mean([abs(a["err_median"]) for a in v])), 3),
            }
    out["levels"][lv] = res
(H / "ks_t14slh_degradation.json").write_text(json.dumps(out, indent=1), "utf-8")
print(len(keys), "common seasons")
for lv, res in out["levels"].items():
    print(lv, res["fit_source"], {m: res[f"forecast_{m}"]["crps"] for m in METRICS})
