"""T6.7: all priority metrics for every Kansas pilot field x candidate option.

Usage: uv run python -u scripts/t67_priority.py
Writes results/rotate/priority.json (per field: option key "a|b|c" -> metric -> value, tag) and
priority_summary.json (counts, label check). Erosion/residue: see rotate/exposure.py (A thresholds).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.exposure import LABELS as EXP_LABELS
from fieldwitness.rotate.exposure import exposure_metrics
from fieldwitness.rotate.priority import LABELS as SEQ_LABELS
from fieldwitness.rotate.priority import sequence_metrics
from fieldwitness.rotate.slots import option_slots

REGION = "ks_t14slh"
Y0, Y1 = 2001, 2024
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
slope = pd.read_parquet("data/context/ks_t14slh_slope.parquet").set_index("field_id")
cands = enumerate_candidates(REGION)
slots = {c: option_slots(c, REGION) for c in cands}
seq = {c: sequence_metrics(c) for c in cands}


def rain_years(lon, lat):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    out = []
    for y in range(Y0, Y1 + 1):
        d = w[(w.index.year == y) & ~((w.index.month == 2) & (w.index.day == 29))]
        col = "PRECTOTCORR" if "PRECTOTCORR" in d else None
        if col is None or len(d) != 365 or d[col].isna().any():
            continue
        out.append(d[col].to_numpy(float))
    return np.array(out)


res, n_missing = {}, 0
for fid in pilot.index:
    r = pilot.loc[fid]
    rain = rain_years(r["lon"], r["lat"])
    sl = float(slope.loc[fid, "slope_deg_mean"])
    f = {}
    for c in cands:
        m = {**seq[c], **exposure_metrics(slots[c], rain, sl)}
        if any(v.value is None for v in m.values()):
            n_missing += 1
        f["|".join(c)] = {k: {"value": v.value, "tag": v.tag} for k, v in m.items()}
    res[str(fid)] = f

labels = {**SEQ_LABELS, **EXP_LABELS}
summ = {
    "n_fields": len(res),
    "n_options": len(cands),
    "metrics": sorted(labels),
    "n_options_with_missing_metric": n_missing,
    "labels": labels,
}
Path("results/rotate/priority.json").write_text(json.dumps(res), "utf-8")
Path("results/rotate/priority_summary.json").write_text(json.dumps(summ, indent=2), "utf-8")
print(json.dumps({k: v for k, v in summ.items() if k != "labels"}))
