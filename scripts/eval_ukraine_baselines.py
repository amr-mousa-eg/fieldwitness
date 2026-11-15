"""E2.1: Leak-free out-of-sample hindcast and baselines B0, B1, B2 for ua_central_t36uvu.

Usage: uv run python -u scripts/eval_ukraine_baselines.py

Mirrors scripts/t71_hindcast.py, t72_score.py, and t73_baselines.py with cut-off 2021-12-31
inside `fieldwitness.data.asof.as_of(CUT)`:
  - Reads Sentinel-2 20 m NDVI (tag O) and causal TWDTW crop labels (crop_source = "classifier",
    tag D) strictly <= 2021-12-31 to calibrate per-field ABC posteriors using ISRIC SoilGrids 2.0
    0-135 cm Saxton & Rawls TAW (tag E) and NASA POWER 2001-2021 weather.
  - Scores held-out 2022-2024 seasons across sunflower, maize, and winter_wheat on all four
    phenology/canopy metrics (sos, peak, canopy_integral, cover_days) for:
      * fieldwitness (forecast mode: past <=2021 weather + forced mode: target-year weather)
      * B0 (empirical own-field <=2021 stats or regional crop pool)
      * B1 (uncalibrated FAO-56 default parameters + SoilGrids TAW x past weather)
      * B2 (uncalibrated prior draws + SoilGrids TAW x past weather)
    B3 is omitted cleanly with a transparent note (Panel-OBDML estimates cover deltas).

Outputs:
  - results/hindcast/ua_central_t36uvu_records.jsonl
  - results/hindcast/ua_central_t36uvu_baselines.json
  - packs/demo/ua_central_t36uvu/hindcast.json
"""

from __future__ import annotations

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
from fieldwitness.packs.validate import validate_dir
from fieldwitness.physics.forcing import forcing
from fieldwitness.schemas import HindcastRow, RegionHindcast

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.build_ukraine_demo_packs import (  # noqa: E402
    REGION,
    UA_NOMINAL_SOW_DOY,
    _load_soil_profile,
)

CUT = dt.date(2021, 12, 31)
SCORE_YEARS = (2022, 2023, 2024)
CROPS = ("sunflower", "maize", "winter_wheat")
METRICS = ("sos", "peak", "canopy_integral", "cover_days")
QS = (0.05, 0.25, 0.5, 0.75, 0.95)
SEED = priors.SEED
S = 200
N_REF = 2000
K_ABC = 100
MIN_OBS_SUMMER = 10
MIN_OBS_WINTER = 8

OUT_RES = Path("results/hindcast")
PACK_DIR = Path("packs/demo") / REGION


def _weather(lon: float, lat: float, years: list[int]) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31))
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    out: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for y in years:
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (fy["rain"].to_numpy(float), fy["eto"].to_numpy(float))
    return out


def _obs_series(by_field: dict[str, pd.DataFrame], fid: str, year: int, crop: str):
    g = by_field.get(fid)
    if g is None:
        return np.array([], int), np.array([], float)
    g = g[g["year"] == year].dropna(subset=["ndvi"]).drop_duplicates("doy")
    if crop == "winter_wheat":
        g = g[(g["doy"] >= 60) & (g["doy"] <= 220)]
    else:
        g = g[(g["doy"] >= 1) & (g["doy"] <= 365)]
    g = g.sort_values("doy")
    return g["doy"].to_numpy(int), g["ndvi"].to_numpy(float)


def _min_obs(crop: str) -> int:
    return MIN_OBS_WINTER if crop == "winter_wheat" else MIN_OBS_SUMMER


def _stats(doy: np.ndarray, nd: np.ndarray, cover_thr: float) -> np.ndarray:
    s = abc.summary_stats(doy, nd)
    g = abc._interp_daily(np.asarray(doy), np.asarray(nd, float), 365)
    cover = (g >= cover_thr).sum(0)
    return np.stack([s[:, 0], s[:, 1], s[:, 3], cover], axis=1)


def _crps(x: np.ndarray, y: float) -> float:
    x = np.sort(np.asarray(x, float))
    n = len(x)
    i = np.arange(1, n + 1)
    ex = 2.0 * np.sum((2 * i - n - 1) * x) / (n * n)
    return float(np.mean(np.abs(x - y)) - 0.5 * ex)


def _score(x: np.ndarray, o: float) -> dict:
    x = np.asarray(x, float)
    q = np.quantile(x, QS)
    lo5, hi5 = q[1], q[3]
    lo9, hi9 = q[0], q[4]
    return {
        "q": [round(float(v), 3) for v in q],
        "crps": _crps(x, o),
        "covered50": bool(lo5 <= o <= hi5),
        "covered90": bool(lo9 <= o <= hi9),
        "err_median": float(q[2] - o),
    }


def _simulate_pool(
    pool: dict[str, np.ndarray],
    wx_list: list[tuple[np.ndarray, np.ndarray]],
    doy: np.ndarray,
    crop_p: dict,
    cfg: dict,
    noise: float,
    cover_thr: float,
    rng: np.random.Generator,
    sample_pool: bool = True,
) -> np.ndarray:
    if sample_pool:
        idx = rng.integers(0, len(pool["taw_scale"]), S)
        hid = {k: np.asarray(v)[idx] for k, v in pool.items()}
    else:
        hid = pool
    which = rng.integers(0, len(wx_list), S)
    sim = np.zeros((len(doy), S))
    for w_i in np.unique(which):
        m = which == w_i
        h = {k: v[m] for k, v in hid.items()}
        out = forward.simulate(*wx_list[w_i], h, crop_p, cfg)
        sim[:, m] = out["ndvi"][doy - 1, :]
    sim = np.clip(sim + rng.normal(0.0, noise, sim.shape), -1.0, 1.0)
    return _stats(doy, sim, cover_thr)


def _rho(a: list[float], b: list[float]) -> float:
    ra = pd.Series(a).rank().to_numpy()
    rb = pd.Series(b).rank().to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    t0 = time.time()
    OUT_RES.mkdir(parents=True, exist_ok=True)
    cfg0 = forward.load_cfg()
    cover_thr = float(
        yaml.safe_load(Path("config/story.yaml").read_text("utf-8"))["cover"]["ndvi_threshold"]
    )
    idx_doc = json.loads((PACK_DIR / "index.json").read_text("utf-8"))
    demo_ids = [f["field_id"] for f in idx_doc["fields"]]
    demo_set = set(demo_ids)
    story_field_id = idx_doc["fields"][0]["field_id"]

    pilot = pd.read_parquet(f"data/fields/{REGION}_pilot.parquet").set_index("field_id")
    series = pd.read_parquet(f"data/fields/{REGION}_hls_series.parquet")
    series["year"] = series["date"].dt.year
    series["doy"] = series["date"].dt.day_of_year
    series = series[series["field_id"].isin(demo_set)].copy()
    by_field = {fid: g for fid, g in series.groupby("field_id")}

    # SoilGrids 2.0 0-135 cm TAW [E] per field
    _, soil_taw_map = _load_soil_profile(Path(f"data/soil/{REGION}_fields.parquet"))
    crop_p = {c: forward.crop_params(c, REGION) for c in CROPS}

    # Strictly pre-cutoff sensor noise sd and priors
    series_pre = series[series["date"].dt.date <= CUT]
    noise = synthetic.census(series_pre)["noise_sd"]
    prior_pool = priors.sample(S * 5, seed=SEED + 710)
    prior_hid = priors.sample(S, seed=SEED + 730)
    default_hid = {
        "sow_offset_days": np.zeros(S, int),
        "taw_scale": np.ones(S),
        "irrigated": np.zeros(S, bool),
        "irrigation_mm": np.zeros(S),
        "kc_mid_scale": np.ones(S),
    }

    rng = np.random.default_rng(SEED + 71)
    rng_w = np.random.default_rng(SEED + 72)
    rng_b = np.random.default_rng(SEED + 73)

    # Pre-cutoff stage: fit ABC posteriors, B0 pools, and past weather inside `as_of(CUT)`
    past_b0: dict[tuple[str, str], list[np.ndarray]] = {}
    pool_b0: dict[str, list[np.ndarray]] = {c: [] for c in CROPS}
    pooled_post: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    wx_past_by_coord: dict[tuple[float, float], dict] = {}
    wx_tgt_by_coord: dict[tuple[float, float], dict] = {}
    max_fit_year = 0

    with as_of(CUT):
        lab_pre = labels.read(REGION)
        lab_pre = lab_pre[
            lab_pre["field_id"].isin(demo_set)
            & lab_pre["crop"].isin(CROPS)
            & (lab_pre["year"] <= CUT.year)
        ]
        # Pre-warm weather caches for unique field coordinates
        for fid in demo_ids:
            lon, lat = float(pilot.loc[fid, "lon"]), float(pilot.loc[fid, "lat"])
            key = (round(lon, 2), round(lat, 2))
            if key not in wx_past_by_coord:
                wx_past_by_coord[key] = _weather(lon, lat, list(range(2001, CUT.year + 1)))

        with forcing_weather():
            for key in wx_past_by_coord:
                lon, lat = key
                wx_tgt_by_coord[key] = _weather(
                    lon, lat, list(range(min(SCORE_YEARS) - 1, max(SCORE_YEARS) + 1))
                )

        # Collect B0 pools across all <= 2021 labelled field-seasons
        for r in lab_pre.itertuples():
            doy, nd = _obs_series(by_field, r.field_id, int(r.year), str(r.crop))
            if len(doy) < _min_obs(str(r.crop)):
                continue
            st = _stats(doy, nd[:, None], cover_thr)[0]
            past_b0.setdefault((r.field_id, str(r.crop)), []).append(st)
            pool_b0[str(r.crop)].append(st)

        # Fit ABC posteriors per field strictly <= 2021
        for i, fid in enumerate(demo_ids):
            lon, lat = float(pilot.loc[fid, "lon"]), float(pilot.loc[fid, "lat"])
            wx_past = wx_past_by_coord[(round(lon, 2), round(lat, 2))]
            taw_mm = soil_taw_map.get(fid, 150.0)
            lf = lab_pre[lab_pre["field_id"] == fid]
            pools: dict[str, list[dict[str, np.ndarray]]] = {c: [] for c in CROPS}
            for rec in lf.itertuples():
                c = str(rec.crop)
                y = int(rec.year)
                doy, nd = _obs_series(by_field, fid, y, c)
                if len(doy) < _min_obs(c) or y > CUT.year:
                    continue
                cfg_c = {
                    **cfg0,
                    "region": REGION,
                    "crop": c,
                    "taw_base_mm": taw_mm,
                    "nominal_sow_doy": UA_NOMINAL_SOW_DOY,
                }
                wxy = forward.season_weather(wx_past, y, cfg_c)
                if wxy is None:
                    continue
                max_fit_year = max(max_fit_year, y)
                ref = abc.reference_table(
                    *wxy,
                    N_REF,
                    crop_p[c],
                    cfg_c,
                    seed=SEED + 1000 + y,
                )
                rg = rng_w if c == "winter_wheat" else rng
                p = abc.posterior(doy, nd, ref, noise, K_ABC, rg)
                pools[c].append({k: v[p["idx"]] for k, v in ref["hidden"].items()})
            pooled_post[fid] = {
                c: {k: np.concatenate([q[k] for q in pools[c]]) for k in pools[c][0]}
                for c in CROPS
                if pools[c]
            }
            if (i + 1) % 30 == 0:
                print(
                    f"  [fit <= {CUT.year}] {i + 1}/{len(demo_ids)} fields "
                    f"({time.time() - t0:.1f}s)",
                    flush=True,
                )

    # Target observed labels (classifier D) read outside guard for 2022-2024 scoring only
    lab_all = labels.read(REGION)
    lab_all = lab_all[lab_all["field_id"].isin(demo_set)]

    records: list[dict] = []
    flat: list[dict] = []
    b0_sources: list[str] = []

    for i, fid in enumerate(demo_ids):
        lon, lat = float(pilot.loc[fid, "lon"]), float(pilot.loc[fid, "lat"])
        coord_key = (round(lon, 2), round(lat, 2))
        wx_past = wx_past_by_coord[coord_key]
        wx_tgt = wx_tgt_by_coord[coord_key]
        taw_mm = soil_taw_map.get(fid, 150.0)
        f_pooled = pooled_post[fid]
        f_seasons: list[dict] = []

        for y in SCORE_YEARS:
            row = lab_all[(lab_all["field_id"] == fid) & (lab_all["year"] == y)]
            if row.empty or str(row["crop"].iloc[0]) not in CROPS:
                continue
            c = str(row["crop"].iloc[0])
            doy, nd = _obs_series(by_field, fid, y, c)
            if len(doy) < _min_obs(c):
                continue

            cfg_c = {
                **cfg0,
                "region": REGION,
                "crop": c,
                "taw_base_mm": taw_mm,
                "nominal_sow_doy": UA_NOMINAL_SOW_DOY,
            }
            if c in f_pooled:
                pool, src = f_pooled[c], "own_crop_posterior"
            elif others := [
                v for c2, v in f_pooled.items() if c == "winter_wheat" or c2 != "winter_wheat"
            ]:
                other = others[0]
                pool = {k: v for k, v in other.items()}
                pool["sow_offset_days"] = prior_pool["sow_offset_days"]
                src = "other_crop_posterior"
            else:
                pool, src = prior_pool, "prior"

            wl_past = [
                w2
                for yy in sorted(wx_past)
                if (w2 := forward.season_weather(wx_past, yy, cfg_c)) is not None
            ]
            wy_tgt = forward.season_weather(wx_tgt, y, cfg_c)
            if not wl_past:
                continue

            rg = rng_w if c == "winter_wheat" else rng
            obs = _stats(doy, nd[:, None], cover_thr)[0]
            season_rec: dict = {
                "field_id": fid,
                "year": int(y),
                "crop": c,
                "fit_source": src,
                "observed": dict(zip(METRICS, obs.tolist(), strict=True)),
            }

            # fieldwitness forecast + forced
            for mode in ("forecast", "forced"):
                wl = wl_past if mode == "forecast" else ([wy_tgt] if wy_tgt is not None else [])
                if not wl:
                    continue
                st_fw = _simulate_pool(pool, wl, doy, crop_p[c], cfg_c, noise, cover_thr, rg, True)
                season_rec[mode] = {
                    m_name: _score(st_fw[:, j], float(obs[j])) for j, m_name in enumerate(METRICS)
                }

            # Baselines B0, B1, B2 (forecast mode)
            own = past_b0.get((fid, c))
            b0_src = "own_field_past" if own else "region_crop_pool"
            b0_sources.append(b0_src)
            st_b0 = np.array(own if own else pool_b0[c])
            st_b1 = _simulate_pool(
                default_hid, wl_past, doy, crop_p[c], cfg_c, noise, cover_thr, rng_b, False
            )
            st_b2 = _simulate_pool(
                prior_hid, wl_past, doy, crop_p[c], cfg_c, noise, cover_thr, rng_b, False
            )
            for bname, st_b, bsrc in (
                ("B0", st_b0, b0_src),
                ("B1", st_b1, "default_hidden"),
                ("B2", st_b2, "prior"),
            ):
                season_rec[bname] = {
                    "source": bsrc,
                    "n_samples": int(len(st_b)),
                    **{
                        m_name: _score(st_b[:, j], float(obs[j]))
                        for j, m_name in enumerate(METRICS)
                    },
                }

            f_seasons.append(season_rec)
            flat.append(season_rec)

        records.append({"field_id": fid, "seasons": f_seasons})
        if (i + 1) % 30 == 0:
            print(
                f"  [score 2022-2024] {i + 1}/{len(demo_ids)} fields, {len(flat)} seasons "
                f"({time.time() - t0:.1f}s)",
                flush=True,
            )

    (OUT_RES / f"{REGION}_records.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )

    hind_rows: list[HindcastRow] = []
    # Keep UI mode order: forecast rows first (fieldwitness, B0, B1, B2), then forced fieldwitness
    spec = [
        ("fieldwitness", "forecast"),
        ("B0", "forecast"),
        ("B1", "forecast"),
        ("B2", "forecast"),
        ("fieldwitness", "forced"),
    ]
    for method, mode in spec:
        for m_name in METRICS:
            sub = [s for s in flat if (mode in s if method == "fieldwitness" else method in s)]
            sc_list = [
                (s[mode][m_name] if method == "fieldwitness" else s[method][m_name]) for s in sub
            ]
            if not sc_list:
                continue
            sc: dict[str, float] = {
                "crps": float(np.mean([a["crps"] for a in sc_list])),
                "covered50": float(np.mean([a["covered50"] for a in sc_list])),
                "covered90": float(np.mean([a["covered90"] for a in sc_list])),
                "mae_median": float(np.mean([abs(a["err_median"]) for a in sc_list])),
            }
            if m_name == "canopy_integral":
                r_sp = _rho(
                    [a["q"][2] for a in sc_list],
                    [float(s["observed"][m_name]) for s in sub],
                )
                if np.isfinite(r_sp):
                    sc["spearman"] = r_sp
            hind_rows.append(
                HindcastRow(method=method, mode=mode, metric=m_name, n=len(sc_list), scores=sc)
            )

    # Pick a scored field with >= 2 seasons as story_field_id when available
    rich_story = next((r["field_id"] for r in records if len(r["seasons"]) >= 2), story_field_id)
    data_as_of = dt.date.fromisoformat(str(idx_doc["data_as_of"]))
    reg_hind = RegionHindcast(
        schema_version="1.2",
        region_id=REGION,
        cutoff=CUT,
        scored_years=list(SCORE_YEARS),
        crop_observed_source="classifier",
        rows=hind_rows,
        story_field_id=rich_story,
        data_as_of=data_as_of,
    )
    (PACK_DIR / "hindcast.json").write_text(
        json.dumps(reg_hind.model_dump(mode="json"), separators=(",", ":")),
        encoding="utf-8",
    )

    detail = {
        "region_id": REGION,
        "cutoff": str(CUT),
        "max_fit_year": max_fit_year,
        "n_fields": len(demo_ids),
        "n_field_seasons": len(flat),
        "crops": pd.Series([s["crop"] for s in flat]).value_counts().to_dict(),
        "fit_sources": pd.Series([s["fit_source"] for s in flat]).value_counts().to_dict(),
        "b0_sources": pd.Series(b0_sources).value_counts().to_dict(),
        "rows": [r.model_dump(mode="json") for r in hind_rows],
        "caveats": (
            "Tier 3 crop states come from causal Sentinel-2 phenology+TWDTW classifier [D] "
            "(WorldCereal 2021 cropland 98.25%, wheat-maize 0.0%, "
            "maize-vs-sunflower kappa=0.035); "
            "B3 omitted because Panel-OBDML contrasts cover cover_days deltas, "
            "not NDVI trajectories."
        ),
    }
    (OUT_RES / f"{REGION}_baselines.json").write_text(json.dumps(detail, indent=2), "utf-8")

    probs = validate_dir(Path("packs/demo"))
    if probs:
        raise SystemExit(f"Pack validation failed: {probs[:5]}")

    print(f"Leak check max_fit_year={max_fit_year} <= {CUT.year}; total scored={len(flat)}")
    for r in hind_rows:
        print(
            f"  {r.mode:8s} | {r.method:12s} | {r.metric:15s} | n={r.n} | "
            + " ".join(f"{k}={v:.3f}" for k, v in r.scores.items()),
            flush=True,
        )


if __name__ == "__main__":
    main()
