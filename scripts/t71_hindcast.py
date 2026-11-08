"""T7.1/T7.2: hindcast for ks_t14slh with cut-off 2021-12-31 -> results/hindcast/.

Usage: uv run python -u scripts/t71_hindcast.py [n_ref] [k] [max_fields]
Resumable: finished fields are appended to results/hindcast/ks_t14slh_records.jsonl.

Per pilot field, inside `as_of(2021-12-31)`:
  1. fit: ABC on every CSB-labelled maize/sorghum season <= 2021 with HLS (same as T4.5/T6.2);
     the hidden-variable posteriors are pooled per crop (sow offset included).
     No fitted season of the crop: TAW/Kc/irrigation come from the other crop's pool (sow offset
     from the prior); no fitted season at all: prior (flag `fit_source`).
  2. predict, for each later season (2022-2024) whose observed CSB label is maize or sorghum
     (conditional scoring): 200 samples = hidden vector from the pool x weather
       forecast mode: a random past POWER year <= 2021 (what a farmer had on 1 Jan 2022)
       forced mode:   the real POWER weather of that year, read ONLY through `forcing_weather()`
     The simulated canopy is sampled on the observed HLS dates (+ HLS noise sd) and summarised with
     the same statistics as the observation (SOS, peak day, canopy integral, cover days).
Scoring (outside the guard, by design): CRPS from samples, 50/90 % coverage, timing error of the
median (days), observed = HLS of that year (tag O stats; canopy statistics tag D).
Winter wheat (T7.1a) is placed with sowing day -78 (`rotate/slots.py`) and driven by previous +
harvest-year weather; only the harvest-year HLS is used, and it draws from its own rng so the
maize/sorghum draws are unchanged. Sunflower, barley, soybean are not modelled (no verified
parameters), so those field-seasons are not scored. Fitting never reads HLS or labels after 2021.
"""

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from fieldwitness.data import labels, power
from fieldwitness.data.asof import as_of, forcing_weather
from fieldwitness.infer import abc, forward, priors, synthetic
from fieldwitness.physics.forcing import forcing
from fieldwitness.rotate.slots import SOW_DAY

n_ref = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
k = int(sys.argv[2]) if len(sys.argv) > 2 else 100
max_fields = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
CUT = dt.date(2021, 12, 31)
SCORE_YEARS = (2022, 2023, 2024)
S = 200  # samples per prediction
SEED = priors.SEED
CROPS = ("maize", "sorghum", "winter_wheat")  # winter wheat (T7.1a): sown the previous autumn
MIN_OBS = 10
QS = (0.05, 0.25, 0.5, 0.75, 0.95)
METRICS = ("sos", "peak", "canopy_integral", "cover_days")

cfg0 = forward.load_cfg()
region = cfg0["region"]
taw_base = float(cfg0["taw_base_mm"])
cover_thr = float(
    yaml.safe_load(Path("config/story.yaml").read_text("utf-8"))["cover"]["ndvi_threshold"]
)
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
series["year"] = series["date"].dt.year
series["doy"] = series["date"].dt.dayofyear
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet").set_index("field_id")
noise = synthetic.census(series[series["year"] <= CUT.year])["noise_sd"]
crop_p = {c: forward.crop_params(c, region) for c in CROPS}
NOMINAL = {**cfg0["nominal_sow_doy"], "winter_wheat": SOW_DAY["winter_wheat"]}  # A, UNVERIFIED
cfgs = {c: {**cfg0, "crop": c, "nominal_sow_doy": NOMINAL} for c in CROPS}
by_field = {fid: g for fid, g in series.groupby("field_id")}
OUT = Path("results/hindcast")
OUT.mkdir(parents=True, exist_ok=True)
# T7.4b: 4th argument 0.5 keeps a seeded 50 % of the clear HLS dates in FITTING seasons only
# (scoring still uses all dates); records go to a separate file.
THIN = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
REC = OUT / (
    "ks_t14slh_records.jsonl" if THIN >= 1 else f"ks_t14slh_records_thin{round(THIN * 100)}.jsonl"
)


def thin(doy, nd, fid, year):
    if THIN >= 1:
        return doy, nd
    r = np.random.default_rng([SEED, 74, int(year), sum(map(ord, str(fid)))])
    keep = np.sort(r.choice(len(doy), size=max(1, round(THIN * len(doy))), replace=False))
    return doy[keep], nd[keep]


def weather(lon, lat, years):
    w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31))
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    out = {}
    for y in years:
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (fy["rain"].to_numpy(float), fy["eto"].to_numpy(float))
    return out


def obs_series(fid, year):
    g = by_field[fid]
    g = g[g["year"] == year].dropna(subset=["ndvi"]).drop_duplicates("doy")
    g = g[(g["doy"] >= 1) & (g["doy"] <= 365)].sort_values("doy")
    return g["doy"].to_numpy(int), g["ndvi"].to_numpy(float)


def stats(doy, nd):
    """(N, 4) in METRICS order from series sampled on `doy`; nd (m, N)."""
    s = abc.summary_stats(doy, nd)  # sos, peak_day, eos, integral, peak_ndvi
    g = abc._interp_daily(np.asarray(doy), np.asarray(nd, float), 365)
    cover = (g >= cover_thr).sum(0)
    return np.stack([s[:, 0], s[:, 1], s[:, 3], cover], axis=1)


def crps(x, y):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    i = np.arange(1, n + 1)
    # E|X-X'| via the sorted-sample identity
    ex = 2.0 * np.sum((2 * i - n - 1) * x) / (n * n)
    return float(np.mean(np.abs(x - y)) - 0.5 * ex)


def predict(pool, wx_list, doy, rng):
    """pool: dict of hidden arrays; wx_list: list of (rain, eto) to draw from; -> (S, 4) stats."""
    idx = rng.integers(0, len(pool["taw_scale"]), S)
    hid = {key: np.asarray(v)[idx] for key, v in pool.items()}
    which = rng.integers(0, len(wx_list), S)
    sim = np.zeros((len(doy), S))
    eta = np.zeros(S)
    for w in np.unique(which):
        m = which == w
        h = {key: v[m] for key, v in hid.items()}
        out = forward.simulate(*wx_list[w], h, CURRENT["p"], CURRENT["cfg"])
        sim[:, m] = out["ndvi"][doy - 1, :]
        eta[m] = out["eta_mm"]
    sim = np.clip(sim + rng.normal(0.0, noise, sim.shape), -1.0, 1.0)
    return stats(doy, sim), eta


CURRENT: dict = {}
rng = np.random.default_rng(SEED + 71)
rng_w = np.random.default_rng(SEED + 72)  # winter wheat only: maize/sorghum draws stay unchanged
done = set()
if REC.exists():
    done = {json.loads(line)["field_id"] for line in REC.read_text("utf-8").splitlines() if line}
prior_all = priors.sample(S * 5, seed=SEED + 710)
t0 = time.time()
n_new = 0
leak = {"max_fit_year": 0}
for fid in pilot.index:
    if fid in done or n_new >= max_fields:
        continue
    n_new += 1
    r = pilot.loc[fid]
    lon, lat = r["lon"], r["lat"]
    recs = []
    with as_of(CUT):
        lab = labels.read(region)
        lf = lab[(lab["field_id"] == fid) & lab["crop"].isin(CROPS)]
        wx_past = weather(lon, lat, list(range(2001, CUT.year + 1)))
        pools = {c: [] for c in CROPS}
        for rec in lf.itertuples():
            doy, nd = thin(*obs_series(fid, rec.year), fid, rec.year)
            wxy = forward.season_weather(wx_past, rec.year, cfgs[rec.crop])
            if len(doy) < MIN_OBS or wxy is None or rec.year > CUT.year:
                continue
            leak["max_fit_year"] = max(leak["max_fit_year"], int(rec.year))
            ref = abc.reference_table(
                *wxy,
                n_ref,
                crop_p[rec.crop],
                cfgs[rec.crop],
                seed=SEED + 1000 + rec.year,
            )
            rg = rng_w if rec.crop == "winter_wheat" else rng
            p = abc.posterior(doy, nd, ref, noise, k, rg)
            pools[rec.crop].append({key: v[p["idx"]] for key, v in ref["hidden"].items()})
        pooled = {
            c: {key: np.concatenate([q[key] for q in pools[c]]) for key in pools[c][0]}
            for c in CROPS
            if pools[c]
        }
        # scoring targets and forced weather (forced channel only)
        targets = []
        with forcing_weather():
            for y in SCORE_YEARS:
                targets.append((y, weather(lon, lat, [y - 1, y])))
    # observed labels: scoring channel, outside the guard
    lab_all = labels.read(region)
    for y, wy_all in targets:
        row = lab_all[(lab_all["field_id"] == fid) & (lab_all["year"] == y)]
        if row.empty or row["crop"].iloc[0] not in CROPS:
            continue
        c = row["crop"].iloc[0]
        doy, nd = obs_series(fid, y)
        if len(doy) < MIN_OBS:
            continue
        if c in pooled:
            pool, src = pooled[c], "own_crop_posterior"
        elif others := [
            v for c2, v in pooled.items() if c == "winter_wheat" or c2 != "winter_wheat"
        ]:  # a spring crop never borrows from winter wheat (keeps maize/sorghum records unchanged)
            other = others[0]
            pool = {key: v for key, v in other.items()}
            pool["sow_offset_days"] = prior_all["sow_offset_days"]
            src = "other_crop_posterior"
        else:
            pool, src = prior_all, "prior"
        CURRENT.update(p=crop_p[c], cfg=cfgs[c])
        rg = rng_w if c == "winter_wheat" else rng
        wy = forward.season_weather(wy_all, y, cfgs[c])
        obs = stats(doy, nd[:, None])[0]
        entry = {
            "year": y,
            "crop": c,
            "fit_source": src,
            "observed": dict(zip(METRICS, obs.tolist(), strict=True)),
        }
        for mode in ("forecast", "forced"):
            if mode == "forecast":
                wl = [w2 for yy in wx_past if (w2 := forward.season_weather(wx_past, yy, cfgs[c]))]
            elif wy is not None:
                wl = [wy]
            else:
                continue
            st, eta = predict(pool, wl, doy, rg)
            m = {}
            for j, name in enumerate(METRICS):
                x, o = st[:, j], float(obs[j])
                q = np.quantile(x, QS)
                lo5, hi5 = np.quantile(x, [0.25, 0.75])
                lo9, hi9 = np.quantile(x, [0.05, 0.95])
                m[name] = {
                    "q": [round(float(v), 3) for v in q],
                    "crps": crps(x, o),
                    "covered50": bool(lo5 <= o <= hi5),
                    "covered90": bool(lo9 <= o <= hi9),
                    "err_median": float(np.median(x) - o),
                }
            m["water_use_mm_q"] = [round(float(v), 1) for v in np.quantile(eta, QS)]
            entry[mode] = m
        recs.append(entry)
    with REC.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"field_id": str(fid), "seasons": recs}) + "\n")
    if n_new % 10 == 0:
        print(n_new, f"{time.time() - t0:.0f}s", flush=True)

print(json.dumps({"fields_done_this_run": n_new, **leak, "cutoff": str(CUT)}))
