"""T6.2: pooled per-field posterior worlds -> results/rotate/posterior_draws.json.

Usage: uv run python -u scripts/t62_draws.py [n_ref] [k]
Same ABC fit as scripts/t45_credibility.py (every CSB-labelled maize/sorghum season with HLS;
POWER weather of the field's cell). The k closest worlds of each season are pooled, then 30 are
subsampled (seeded) per field. Stored per world: taw_mm, kc_scale, budget_mm (0 = rainfed), tag D.
Fields with no fitted season (e.g. winter-wheat-only) get PRIOR worlds (tag A), flagged
"source": "prior". Field-level traits (TAW, irrigation) are pooled across crops; sow offset is
crop-specific and is not stored.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import labels, power
from fieldwitness.data.ssurgo_taw import get_field_taw_base
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.physics.forcing import forcing
from fieldwitness.rotate.evaluate import N_WORLDS, subsample_draws

_ap = argparse.ArgumentParser(description="Pool per-field posterior worlds.")
_ap.add_argument("n_ref", nargs="?", type=int, default=3000)
_ap.add_argument("k", nargs="?", type=int, default=150)
_ap.add_argument("--taw-source", choices=("config", "ssurgo"), default="config")
_args = _ap.parse_args()
n_ref, k, taw_source = _args.n_ref, _args.k, _args.taw_source
SEED = priors.SEED
CROPS = ("maize", "sorghum")
MIN_OBS = 10

cfg0 = forward.load_cfg()
region = cfg0["region"]
taw_base = float(cfg0["taw_base_mm"])
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
series["year"] = series["date"].dt.year
series["doy"] = series["date"].dt.dayofyear
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
lab = labels.read(region)
lab = lab[lab["crop"].isin(CROPS)]
noise = synthetic.census(series)["noise_sd"]
rng = np.random.default_rng(SEED + 62)
crop_p = {c: forward.crop_params(c, region) for c in CROPS}
cfgs = {c: {**cfg0, "crop": c} for c in CROPS}
by_field = {fid: g for fid, g in series.groupby("field_id")}


def weather(lon, lat, years):
    """{year: (rain, eto)} with 365 days (29 Feb dropped); years with gaps are skipped."""
    w = power.read(lon, lat, f"{min(years)}-01-01", f"{max(years)}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    out = {}
    for y in years:
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (fy["rain"].to_numpy(float), fy["eto"].to_numpy(float))
    return out


def worlds(h, field_taw_base: float = taw_base):
    irrig = np.asarray(h["irrigated"], bool)
    return {
        "taw_mm": field_taw_base * np.asarray(h["taw_scale"], float),
        "kc_scale": np.asarray(h["kc_mid_scale"], float),
        "budget_mm": np.where(irrig, np.asarray(h["irrigation_mm"], float), 0.0),
    }


prior_hidden = priors.sample(2000, seed=SEED + 620)
prior_pool = worlds(prior_hidden, taw_base)
t0 = time.time()
fields = {}
for i, fid in enumerate(pilot.index):
    f_taw_base = get_field_taw_base(field_id=str(fid)) if taw_source == "ssurgo" else taw_base
    lf = lab[lab["field_id"] == fid]
    parts, years = [], []
    if len(lf):
        r = pilot.loc[fid]
        wx = weather(r["lon"], r["lat"], sorted(set(lf["year"])))
        for rec in lf.itertuples():
            g = by_field[fid]
            g = g[g["year"] == rec.year].dropna(subset=["ndvi"]).drop_duplicates("doy")
            g = g[(g["doy"] >= 1) & (g["doy"] <= 365)].sort_values("doy")
            if len(g) < MIN_OBS or rec.year not in wx:
                continue
            ref = abc.reference_table(
                *wx[rec.year], n_ref, crop_p[rec.crop], cfgs[rec.crop], seed=SEED + 1000 + rec.year
            )
            p = abc.posterior(g["doy"].to_numpy(int), g["ndvi"].to_numpy(float), ref, noise, k, rng)
            w = worlds(ref["hidden"], f_taw_base)
            parts.append({key: v[p["idx"]] for key, v in w.items()})
            years.append(int(rec.year))
    if parts:
        pool = {key: np.concatenate([q[key] for q in parts]) for key in parts[0]}
        src, tag = "posterior", "D"
    else:
        pool = worlds(prior_hidden, f_taw_base) if taw_source == "ssurgo" else prior_pool
        src, tag = "prior", "A"
    d = subsample_draws(pool, N_WORLDS, seed=SEED + i)
    fields[str(fid)] = {
        "source": src,
        "tag": tag,
        "years": years,
        "taw_mm": [round(float(x), 2) for x in d["taw_mm"]],
        "kc_scale": [round(float(x), 4) for x in d["kc_scale"]],
        "budget_mm": [round(float(x), 1) for x in d["budget_mm"]],
    }
    if i % 20 == 0:
        print(i, f"{time.time() - t0:.0f}s", flush=True)

n_post = sum(v["source"] == "posterior" for v in fields.values())
out = {
    "summary": {
        "n_fields": len(fields),
        "posterior": n_post,
        "prior_fallback": len(fields) - n_post,
        "n_worlds": N_WORLDS,
        "n_ref": n_ref,
        "k": k,
        "seed": SEED,
        "caveat": "in-sample fit; prior fallback is tag A; sow offset not stored",
    },
    "fields": fields,
}
Path("results/rotate").mkdir(parents=True, exist_ok=True)
Path("results/rotate/posterior_draws.json").write_text(json.dumps(out), "utf-8")
print(json.dumps(out["summary"]))
