"""T4.5: ABC on real pilot fields -> credibility per field (results/inference/credibility.json).

Usage: uv run python -u scripts/t45_credibility.py [n_ref] [k]
Per pilot field and modelled crop (maize, sorghum; labels from CSB 2017-2024 via data.labels):
  every labelled season is fitted with ABC (POWER weather of the field's own cell, HLS NDVI),
  then observed vs posterior-predictive statistics are compared across the field's seasons:
  - rank score = max(0, Spearman rho of observed vs simulated canopy integral)  (needs >= 3 seasons)
  - timing score = max(0, 1 - median_season(mean |obs - sim| of SOS, peak, EOS) / scale)
  credibility = w * rank + (1 - w) * timing (config/grading.yaml); with < 3 seasons only the
  timing score exists (flag "timing_only"); with no modelled season the field gets null.
CAVEAT: the posterior is fitted on the same season it is compared with (in-sample), so the
score measures consistency of the physics with the field's canopy, not out-of-sample skill.
Winter wheat / sunflower are not modelled (no calendar-year window), so those fields stay null.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from fieldwitness.data import labels, power
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.physics.forcing import forcing

n_ref = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
k = int(sys.argv[2]) if len(sys.argv) > 2 else 150
SEED = priors.SEED
CROPS = ("maize", "sorghum")
MIN_OBS = 10

grading = yaml.safe_load(Path("config/grading.yaml").read_text("utf-8"))["credibility"]
W, SCALE = grading["weight_spearman"], grading["timing_error_scale_days"]
cfg0 = forward.load_cfg()
region = cfg0["region"]
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
series["year"] = series["date"].dt.year
series["doy"] = series["date"].dt.dayofyear
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
lab = labels.read(region)
lab = lab[lab["crop"].isin(CROPS)]
cen = synthetic.census(series)
noise = cen["noise_sd"]
rng = np.random.default_rng(SEED + 45)
crop_p = {c: forward.crop_params(c, region) for c in CROPS}
cfgs = {c: {**cfg0, "crop": c} for c in CROPS}


def weather(lon, lat, years):
    w = power.read(lon, lat, f"{min(years)}-01-01", f"{max(years)}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    out = {}
    for y in years:
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (fy["rain"].to_numpy(float), fy["eto"].to_numpy(float))
    return out


def rank_corr(a, b):
    if len(a) < 3:
        return float("nan")
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


t0 = time.time()
rows = []
by_field = {fid: g for fid, g in series.groupby("field_id")}
pos = pilot.set_index("field_id")
for i, fid in enumerate(pilot["field_id"]):
    lf = lab[lab["field_id"] == fid]
    seasons = {c: [] for c in CROPS}
    if len(lf):
        r = pos.loc[fid]
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
            doy, nd = g["doy"].to_numpy(int), g["ndvi"].to_numpy(float)
            p = abc.posterior(doy, nd, ref, noise, k, rng)
            sim = abc.summary_stats(doy, ref["ndvi"][doy - 1][:, p["idx"]])
            pred = np.median(sim, axis=0)
            seasons[rec.crop].append((rec.year, p["obs_stats"], pred))
    best = max(CROPS, key=lambda c: len(seasons[c]))
    s = seasons[best]
    row = {"field_id": fid, "crop": best if s else None, "n_seasons": len(s)}
    if not s:
        row.update(
            credibility=None, mode="not_assessable", reason="no modelled-crop season with HLS"
        )
    else:
        obs = np.array([x[1] for x in s])
        pr = np.array([x[2] for x in s])
        err = np.abs(obs[:, [0, 1, 2]] - pr[:, [0, 1, 2]]).mean(1)  # SOS, peak, EOS (days)
        med_err = float(np.median(err))
        t_score = max(0.0, 1 - med_err / SCALE)
        rho = rank_corr(obs[:, 3], pr[:, 3])
        if np.isnan(rho):
            cred, mode = t_score, "timing_only"
        else:
            cred, mode = W * max(0.0, rho) + (1 - W) * t_score, "full"
        row.update(
            credibility=round(cred, 3),
            mode=mode,
            spearman=None if np.isnan(rho) else round(rho, 3),
            median_timing_error_days=round(med_err, 1),
            years=[x[0] for x in s],
        )
    rows.append(row)
    if i % 20 == 0:
        print(i, f"{time.time() - t0:.0f}s", flush=True)

cr = [r["credibility"] for r in rows if r["credibility"] is not None]
summary = {
    "n_fields": len(rows),
    "with_credibility": len(cr),
    "full": sum(r["mode"] == "full" for r in rows),
    "timing_only": sum(r["mode"] == "timing_only" for r in rows),
    "not_assessable": sum(r["mode"] == "not_assessable" for r in rows),
    "median": round(float(np.median(cr)), 3) if cr else None,
    "share_ge_0.6": round(float(np.mean(np.array(cr) >= 0.6)), 3) if cr else None,
    "n_ref": n_ref,
    "k": k,
    "tag": "D",
    "caveat": "in-sample posterior predictive; sorghum sow day is a team choice (A)",
}
Path("results/inference").mkdir(parents=True, exist_ok=True)
Path("results/inference/credibility.json").write_text(
    json.dumps({"summary": summary, "fields": rows}, indent=2), "utf-8"
)

# distribution figure (hand-written SVG, no plotting dependency)
bins = np.linspace(0, 1, 11)
h, _ = np.histogram(cr, bins)
W_, H_, m = 420, 240, 35
bw = (W_ - 2 * m) / 10
top = max(h.max(), 1)
bars = "".join(
    f'<rect x="{m + i * bw:.1f}" y="{H_ - m - (c / top) * (H_ - 2 * m):.1f}" width="{bw - 2:.1f}" '
    f'height="{(c / top) * (H_ - 2 * m):.1f}" fill="#4477aa"/>'
    f'<text x="{m + i * bw + bw / 2:.1f}" y="{H_ - m + 14}" font-size="9" '
    f'text-anchor="middle">{bins[i]:.1f}</text>'
    for i, c in enumerate(h)
)
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_}" height="{H_}" '
    f'font-family="sans-serif"><text x="{W_ / 2}" y="16" font-size="12" '
    f'text-anchor="middle">Credibility, pilot fields (tag D), '
    f"n={len(cr)} of {len(rows)}</text>{bars}"
    f'<line x1="{m + 6 * bw:.1f}" x2="{m + 6 * bw:.1f}" y1="{m}" y2="{H_ - m}" stroke="#cc3311" '
    f'stroke-dasharray="4"/><text x="{W_ / 2}" y="{H_ - 6}" font-size="10" text-anchor="middle">'
    f"credibility (red = grade-A minimum 0.6); max count {top}</text></svg>"
)
Path("results/inference/credibility_hist.svg").write_text(svg, "utf-8")
print(json.dumps(summary))
