"""Experiment 2 (DECISIONS.md 2026-11-12): T7.3 baselines in calendar or gdd phenology mode.

Usage: uv run python -u scripts/x2_gdd_baselines.py [calendar|gdd]
Copy of scripts/t73_baselines.py with only these changes: weather also returns POWER Tmax/Tmin,
the physics baselines B1/B2 run in the given phenology mode, targets are read from
results/hindcast/gdd/records_<mode>.jsonl and outputs go to results/hindcast/gdd/baselines_<mode>.*
(the published files are never written). B0 does not use phenology. Winter wheat seasons
are skipped, as in the published baselines (DECISIONS.md 2026-11-09, item 2).

Original T7.3 description follows.
Same targets (field-seasons in ks_t14slh_records.jsonl), same observed statistics, same scoring
(CRPS from samples, 50/90 % coverage, MAE of the median), forecast weather = random past POWER
year <= 2021, cut-off 2021-12-31 inside `as_of`. Nothing dated after the cut-off is read for the
baseline predictions; labels/HLS of the scored year are read only as the observation.

  B0 field mean: empirical distribution of the field's own earlier seasons of the same crop
     (HLS stats, <= 2021); if none, of the same crop on all pilot fields <= 2021.
  B1 FAO-table engine: default hidden vector (sow offset 0, taw_scale 1, kc_mid_scale 1, rainfed)
     x past weather years. Default sowing date and soil of the crop table, no fitting.
  B2 uncalibrated physics: hidden vector drawn from the prior x past weather years.
  B3 neighbour-only: NOT RUN (T5.2 neighbour effects do not exist; blocked on dependencies).
"""

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from fieldwitness.data import labels, power
from fieldwitness.data.asof import as_of
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.physics.forcing import forcing

MODE = sys.argv[1] if len(sys.argv) > 1 else "gdd"
assert MODE in ("calendar", "gdd")
CUT = dt.date(2021, 12, 31)
S = 200
SEED = priors.SEED
CROPS = ("maize", "sorghum")
MIN_OBS = 10
METRICS = ("sos", "peak", "canopy_integral", "cover_days")
OUT = Path("results/hindcast/gdd")

cfg0 = forward.load_cfg()
region = cfg0["region"]
cover_thr = float(
    yaml.safe_load(Path("config/story.yaml").read_text("utf-8"))["cover"]["ndvi_threshold"]
)
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
series["year"] = series["date"].dt.year
series["doy"] = series["date"].dt.dayofyear
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
noise = synthetic.census(series[series["year"] <= CUT.year])["noise_sd"]
crop_p = {c: forward.crop_params(c, region) for c in CROPS}
cfgs = {c: {**cfg0, "crop": c, "phenology_mode": MODE} for c in CROPS}
by_field = {fid: g for fid, g in series.groupby("field_id")}


def weather(lon, lat, years):
    w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31))
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    out = {}
    for y in years:
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (
                fy["rain"].to_numpy(float),
                fy["eto"].to_numpy(float),
                w.loc[fy.index, "T2M_MAX"].to_numpy(float),
                w.loc[fy.index, "T2M_MIN"].to_numpy(float),
            )
    return out


def obs_series(fid, year):
    g = by_field[fid]
    g = g[g["year"] == year].dropna(subset=["ndvi"]).drop_duplicates("doy")
    g = g[(g["doy"] >= 1) & (g["doy"] <= 365)].sort_values("doy")
    return g["doy"].to_numpy(int), g["ndvi"].to_numpy(float)


def stats(doy, nd):
    s = abc.summary_stats(doy, nd)
    g = abc._interp_daily(np.asarray(doy), np.asarray(nd, float), 365)
    cover = (g >= cover_thr).sum(0)
    return np.stack([s[:, 0], s[:, 1], s[:, 3], cover], axis=1)


def crps(x, y):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    i = np.arange(1, n + 1)
    ex = 2.0 * np.sum((2 * i - n - 1) * x) / (n * n)
    return float(np.mean(np.abs(x - y)) - 0.5 * ex)


def score(x, o):
    x = np.asarray(x, float)
    lo5, hi5 = np.quantile(x, [0.25, 0.75])
    lo9, hi9 = np.quantile(x, [0.05, 0.95])
    return {
        "q": [round(float(v), 3) for v in np.quantile(x, (0.05, 0.25, 0.5, 0.75, 0.95))],
        "crps": crps(x, o),
        "covered50": bool(lo5 <= o <= hi5),
        "covered90": bool(lo9 <= o <= hi9),
        "err_median": float(np.median(x) - o),
    }


def simulate(hid, wx_list, doy, crop, rng):
    which = rng.integers(0, len(wx_list), S)
    sim = np.zeros((len(doy), S))
    for w in np.unique(which):
        m = which == w
        h = {k: v[m] for k, v in hid.items()}
        rain, eto, tmax, tmin = wx_list[w]
        out = forward.simulate(rain, eto, h, crop_p[crop], cfgs[crop], tmax, tmin)
        sim[:, m] = out["ndvi"][doy - 1, :]
    sim = np.clip(sim + rng.normal(0.0, noise, sim.shape), -1.0, 1.0)
    return stats(doy, sim)


default_hid = {
    "sow_offset_days": np.zeros(S, int),
    "taw_scale": np.ones(S),
    "irrigated": np.zeros(S, bool),
    "irrigation_mm": np.zeros(S),
    "kc_mid_scale": np.ones(S),
}
prior_hid = priors.sample(S, seed=SEED + 730)
rng = np.random.default_rng(SEED + 73)

recs = [json.loads(x) for x in (OUT / f"records_{MODE}.jsonl").read_text("utf-8").splitlines() if x]

# past stats <= cut-off (B0), leak-free: labels read inside as_of
past: dict[tuple[str, str], list[np.ndarray]] = {}
crop_pool: dict[str, list[np.ndarray]] = {c: [] for c in CROPS}
wx_cache: dict[str, dict] = {}
with as_of(CUT):
    lab = labels.read(region)
    lab = lab[lab["crop"].isin(CROPS) & (lab["year"] <= CUT.year)]
    for r in lab.itertuples():
        if r.field_id not in by_field:
            continue
        doy, nd = obs_series(r.field_id, r.year)
        if len(doy) < MIN_OBS:
            continue
        st = stats(doy, nd[:, None])[0]
        past.setdefault((r.field_id, r.crop), []).append(st)
        crop_pool[r.crop].append(st)
    for fid in {x["field_id"] for x in recs if x["seasons"]}:
        lon, lat = pilot.loc[fid, "lon"], pilot.loc[fid, "lat"]
        wx_cache[fid] = weather(lon, lat, list(range(2001, CUT.year + 1)))

rows = []
for rec in recs:
    fid = rec["field_id"]
    for s in rec["seasons"]:
        c, y = s["crop"], s["year"]
        if c not in CROPS:  # published baselines cover maize/sorghum only (DECISIONS 2026-11-09)
            continue
        doy, nd = obs_series(fid, y)
        obs = stats(doy, nd[:, None])[0]
        wl = list(wx_cache[fid].values())
        own = past.get((fid, c))
        b0_src = "own_field_past" if own else "region_crop_pool"
        b0 = np.array(own if own else crop_pool[c])
        preds = {
            "B0": (b0, b0_src),
            "B1": (simulate(default_hid, wl, doy, c, rng), "default_hidden"),
            "B2": (simulate(prior_hid, wl, doy, c, rng), "prior"),
        }
        e = {"field_id": fid, "year": y, "crop": c}
        for name, (st, src) in preds.items():
            e[name] = {"source": src, "n_samples": int(len(st))}
            for j, m in enumerate(METRICS):
                e[name][m] = score(st[:, j], float(obs[j]))
        rows.append(e)

with (OUT / f"baselines_{MODE}.jsonl").open("w", encoding="utf-8") as fh:
    for e in rows:
        fh.write(json.dumps(e) + "\n")

# comparison table (forecast mode of fieldwitness vs baselines)
fw = [
    {"field_id": r["field_id"], **s}
    for r in recs
    for s in r["seasons"]
    if "forecast" in s and s["crop"] in CROPS
]
key = {(e["field_id"], e["year"]): e for e in rows}


def rho(a, b):
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


table = []
for method in ("fieldwitness", "B0", "B1", "B2"):
    for m in METRICS:
        sc = []
        for s in fw:
            e = key[(s["field_id"], s["year"])]
            sc.append(s["forecast"][m] if method == "fieldwitness" else e[method][m])
        row = {
            "method": method,
            "metric": m,
            "n": len(sc),
            "crps": float(np.mean([a["crps"] for a in sc])),
            "covered50": float(np.mean([a["covered50"] for a in sc])),
            "covered90": float(np.mean([a["covered90"] for a in sc])),
            "mae_median": float(np.mean([abs(a["err_median"]) for a in sc])),
        }
        if m == "canopy_integral":
            obs_v = [s["observed"][m] for s in fw]
            row["spearman"] = rho([a["q"][2] for a in sc], obs_v)
        table.append(row)

doc = {
    "region_id": "ks_t14slh",
    "cutoff": str(CUT),
    "mode": "forecast",
    "n_field_seasons": len(fw),
    "b3": "NOT RUN: neighbour effects (T5.2) do not exist; dependency decision open",
    "b0_sources": pd.Series([e["B0"]["source"] for e in rows]).value_counts().to_dict(),
    "caveats": (
        "same field-seasons and statistics as the fieldwitness forecast; B0 intervals come from "
        "few past seasons (coverage unreliable); B1/B2 add HLS noise like fieldwitness; "
        "tags: model D, observed O/D, labels E"
    ),
    "table": table,
}
(OUT / f"baselines_{MODE}.json").write_text(json.dumps(doc, indent=1), "utf-8")
for r in table:
    print(
        r["method"],
        r["metric"],
        {k: round(v, 3) for k, v in r.items() if k not in ("method", "metric")},
    )
sys.stdout.flush()
