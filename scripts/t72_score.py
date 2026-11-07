"""T7.2: aggregate results/hindcast/ks_t14slh_records.jsonl -> results/hindcast/ks_t14slh.json.

Rows (method "fieldwitness", mode forecast/forced, metric): n, mean CRPS, covered50/covered90
(share of field-seasons with the observation inside the central interval), mean absolute error of
the median (`mae_median`; for sos/peak this is the timing error in days), and for canopy_integral
the Spearman rho across fields (pooled over scored years and per year). Validated with
RegionHindcast. Baselines (T7.3) are added by their own script.
"""

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.schemas import HindcastRow, RegionHindcast


def rho(a, b):  # Spearman = Pearson of ranks (no scipy)
    return float(a.rank().corr(b.rank()))


METRICS = ("sos", "peak", "canopy_integral", "cover_days")
recs = [
    json.loads(x)
    for x in Path("results/hindcast/ks_t14slh_records.jsonl").read_text("utf-8").splitlines()
    if x
]
flat = [dict(field_id=r["field_id"], **s) for r in recs for s in r["seasons"]]
rows, per_year = [], {}
for mode in ("forecast", "forced"):
    for metric in METRICS:
        v = [(s[mode][metric], s["observed"][metric], s["year"]) for s in flat if mode in s]
        if not v:
            continue
        sc = {
            "crps": float(np.mean([a["crps"] for a, _, _ in v])),
            "covered50": float(np.mean([a["covered50"] for a, _, _ in v])),
            "covered90": float(np.mean([a["covered90"] for a, _, _ in v])),
            "mae_median": float(np.mean([abs(a["err_median"]) for a, _, _ in v])),
        }
        if metric == "canopy_integral":
            df = pd.DataFrame(
                {
                    "pred": [a["q"][2] for a, _, _ in v],
                    "obs": [o for _, o, _ in v],
                    "y": [y for _, _, y in v],
                }
            )
            sc["spearman"] = rho(df["pred"], df["obs"])
            for y, g in df.groupby("y"):
                per_year[f"{mode}_{y}"] = {"n": int(len(g)), "spearman": rho(g["pred"], g["obs"])}
        rows.append(
            HindcastRow(method="fieldwitness", mode=mode, metric=metric, n=len(v), scores=sc)
        )

by_src = pd.Series([s["fit_source"] for s in flat]).value_counts().to_dict()
by_crop = pd.Series([s["crop"] for s in flat]).value_counts().to_dict()
out = RegionHindcast(
    schema_version="1",
    region_id="ks_t14slh",
    cutoff=dt.date(2021, 12, 31),
    scored_years=[2022, 2023, 2024],
    crop_observed_source="label",
    rows=rows,
    story_field_id=next((r["field_id"] for r in recs if r["seasons"]), ""),
    data_as_of=dt.date(2021, 12, 31),
)
doc = out.model_dump(mode="json")
doc["extra"] = {
    "n_field_seasons": len(flat),
    "fit_source": by_src,
    "crop": by_crop,
    "spearman_by_year": per_year,
    "tag": "D (model) vs O (HLS) statistics; labels tag E",
    "caveats": (
        "conditional on the observed CSB crop; maize/sorghum only; "
        "fit years <= 2021 only; baselines B0-B3 not yet run"
    ),
}
Path("results/hindcast/ks_t14slh.json").write_text(json.dumps(doc, indent=1), "utf-8")
for r in rows:
    print(r.mode, r.metric, r.n, {k: round(v, 3) for k, v in r.scores.items()})
print(by_src, by_crop, per_year)
