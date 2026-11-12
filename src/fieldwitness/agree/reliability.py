"""Reliability tiers learned from measured error (experiment, branch only).

Pre-registered in DECISIONS.md (2026-11-12, "reliability tiers learned from measured error").
Not used by packs, the app or `config/grading.yaml`. Tiers R1-R4 are relative reliability, not
evidence grades, and do not use the neighbour witness. Outputs tag D.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

CROPS = ("maize", "sorghum", "winter_wheat")
MIN_OBS = 10
SCALE_FLOOR = 1.0  # tag A
FEATURES = (
    "n_clear_fit",
    "credibility",
    "rel_spread",
    "area_ha",
    "crop_maize",
    "crop_sorghum",
    "crop_winter_wheat",
)
MODELS = ("null", "crop", "grade", "credibility", "gbm")  # simplicity order
SEED = 20261114
N_BOOT = 1000
BOOT_SEED = 42


# ---------------- features (all known at the cut-off) ----------------


def n_clear_fit(series: pd.DataFrame, labels: pd.DataFrame, field_id: str, cut_year: int) -> int:
    """Clear HLS observations summed over the field's fit seasons (<= cut-off).

    Fit season: labelled maize/sorghum/winter-wheat year <= cut_year with >= MIN_OBS clear,
    de-duplicated observation days in 1..365 (the T7.1 rule without its weather check).
    Only rows dated in years <= cut_year are read.
    """
    lab = labels[
        (labels["field_id"] == field_id) & (labels["year"] <= cut_year) & labels["crop"].isin(CROPS)
    ]
    s = series[(series["field_id"] == field_id) & (series["date"].dt.year <= cut_year)]
    s = s.dropna(subset=["ndvi"])
    total = 0
    for y in lab["year"]:
        doy = s.loc[s["date"].dt.year == y, "date"].dt.day_of_year
        n = int(doy[(doy >= 1) & (doy <= 365)].nunique())
        if n >= MIN_OBS:
            total += n
    return total


def rel_spread(q: list[float]) -> float:
    """(q95 - q5) / q50 of the forecast canopy integral (the prediction itself)."""
    return float((q[4] - q[0]) / q[2]) if q[2] > 0 else float("nan")


def grade_number(fit_source: str, credibility: float | None) -> int:
    """Current grade rule of t7_grade_validity: prior -> D (3); cred >= 0.6 -> B (1); else C (2)."""
    if fit_source == "prior":
        return 3
    if credibility is not None and np.isfinite(credibility) and credibility >= 0.6:
        return 1
    return 2


def build_rows(recs, cut_year, series, labels, pilot, cred) -> pd.DataFrame:
    """One row per scored forecast field-season with features and targets.

    `cred` maps field_id -> credibility (or None) at this cut-off.
    """
    area = dict(zip(pilot["field_id"], pilot["area_ha"], strict=True))
    block = dict(zip(pilot["field_id"], pilot["block"], strict=True))
    nfit = {}
    out = []
    for r in recs:
        fid = r["field_id"]
        if fid not in nfit:
            nfit[fid] = n_clear_fit(series, labels, fid, cut_year)
        for s in r["seasons"]:
            if "forecast" not in s or s["crop"] not in CROPS:
                continue
            f = s["forecast"]
            c = cred.get(fid)
            out.append(
                {
                    "field_id": fid,
                    "block": block[fid],
                    "cut_year": cut_year,
                    "year": s["year"],
                    "crop": s["crop"],
                    "fit_source": s["fit_source"],
                    "n_clear_fit": nfit[fid],
                    "credibility": np.nan if c is None else float(c),
                    "rel_spread": rel_spread(f["canopy_integral"]["q"]),
                    "area_ha": float(area[fid]),
                    **{f"crop_{k}": float(s["crop"] == k) for k in CROPS},
                    "grade": grade_number(s["fit_source"], c),
                    "crps_ci": f["canopy_integral"]["crps"],
                    "obs_ci": s["observed"]["canopy_integral"],
                    "peak_abs_err": abs(f["peak"]["err_median"]),
                }
            )
    df = pd.DataFrame(out)
    return add_target(df)


def add_target(df: pd.DataFrame) -> pd.DataFrame:
    """y = log(CRPS / S), S = max(1, median observed canopy integral per field and crop)."""
    df = df.copy()
    s = df.groupby(["field_id", "crop"])["obs_ci"].transform("median")
    df["scale"] = np.maximum(SCALE_FLOOR, s)
    df["y"] = np.log(df["crps_ci"] / df["scale"])
    return df


# ---------------- models ----------------


def fit_predict(name: str, train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    y = train["y"].to_numpy(float)
    if name == "null":
        return np.full(len(test), y.mean())
    if name == "crop":
        m = train.groupby("crop")["y"].mean()
        return test["crop"].map(m).fillna(y.mean()).to_numpy(float)
    if name in ("grade", "credibility"):
        from sklearn.linear_model import LinearRegression

        def x(d):
            if name == "grade":
                return d[["grade"]].to_numpy(float)
            c = d["credibility"].to_numpy(float)
            return np.column_stack([np.nan_to_num(c, nan=0.0), np.isnan(c).astype(float)])

        return LinearRegression().fit(x(train), y).predict(x(test))
    if name == "gbm":
        from sklearn.ensemble import HistGradientBoostingRegressor

        g = HistGradientBoostingRegressor(
            max_depth=2, max_iter=100, learning_rate=0.1, min_samples_leaf=20, random_state=SEED
        )
        cols = list(FEATURES)
        return g.fit(train[cols].to_numpy(float), y).predict(test[cols].to_numpy(float))
    raise ValueError(name)


def lobo_cv(df: pd.DataFrame, name: str) -> np.ndarray:
    """Out-of-fold predictions, leave-one-10-km-block-out."""
    pred = np.empty(len(df))
    d = df.reset_index(drop=True)
    for b in d["block"].unique():
        te = d["block"] == b
        pred[te.to_numpy()] = fit_predict(name, d[~te], d[te])
    return pred


def choose(cv: pd.DataFrame) -> str:
    """Simplest model (MODELS order) with loss <= best loss + SE of the best."""
    best = cv.loc[cv["loss"].idxmin()]
    limit = best["loss"] + best["se"]
    for m in MODELS:
        if cv.loc[cv["model"] == m, "loss"].iloc[0] <= limit:
            return m
    return str(best["model"])


# ---------------- tiers ----------------


def tier_bounds(pred_train) -> list[float]:
    return [float(v) for v in np.quantile(np.asarray(pred_train, float), [0.25, 0.5, 0.75])]


def assign_tiers(pred, bounds) -> np.ndarray:
    """R1..R4 as 1..4: tier = 1 + number of bounds strictly below the prediction (ties lower)."""
    p = np.asarray(pred, float)[:, None]
    return 1 + (p > np.asarray(bounds, float)[None, :]).sum(1)


# ---------------- block bootstrap (t7_diagnosis scheme: 10 km blocks, 1,000, seed 42) -------


def _resamples(blocks, n_boot=N_BOOT, seed=BOOT_SEED):
    b = np.asarray(blocks)
    ub = pd.unique(b)
    idx = [np.flatnonzero(b == k) for k in ub]
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        pick = rng.choice(len(ub), size=len(ub), replace=True)
        yield np.concatenate([idx[i] for i in pick])


def boot_tier_means(values, tiers, blocks) -> dict:
    """Per tier mean + CI, and mean(R4) - mean(R1) + CI, on the same resamples."""
    v, t = np.asarray(values, float), np.asarray(tiers)
    res = {k: [] for k in (1, 2, 3, 4)}
    diff = []
    for ix in _resamples(blocks):
        vv, tt = v[ix], t[ix]
        m = {k: vv[tt == k].mean() if (tt == k).any() else np.nan for k in (1, 2, 3, 4)}
        for k in m:
            res[k].append(m[k])
        diff.append(m[4] - m[1])
    out = {}
    for k in (1, 2, 3, 4):
        sel = t == k
        a = np.array(res[k])
        out[f"R{k}"] = {
            "n": int(sel.sum()),
            "mean": float(v[sel].mean()) if sel.any() else None,
            "ci": [float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5))]
            if sel.any()
            else None,
        }
    d = np.array(diff)
    full = (v[t == 4].mean() - v[t == 1].mean()) if ((t == 4).any() and (t == 1).any()) else np.nan
    out["R4_minus_R1"] = {
        "mean": float(full),
        "ci": [float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))]
        if np.isfinite(full)
        else None,
    }
    return out


def boot_spearman(pred, real, blocks, pred2=None) -> dict:
    """Spearman(pred, real) with CI; with pred2 also rho(pred) - rho(pred2) and its CI."""
    p, r = np.asarray(pred, float), np.asarray(real, float)
    p2 = None if pred2 is None else np.asarray(pred2, float)

    def rho(a, b):
        if np.ptp(a) == 0 or np.ptp(b) == 0:
            return 0.0  # constant predictor: no ranking
        return float(spearmanr(a, b).statistic)

    vals, diffs = [], []
    for ix in _resamples(blocks):
        a = rho(p[ix], r[ix])
        vals.append(a)
        if p2 is not None:
            diffs.append(a - rho(p2[ix], r[ix]))
    out = {
        "rho": rho(p, r),
        "ci": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
    }
    if p2 is not None:
        out["diff"] = rho(p, r) - rho(p2, r)
        out["diff_ci"] = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    return out


def ordered(means: list) -> bool:
    """True if strictly increasing (R1 < R2 < R3 < R4); a missing tier mean fails."""
    return all(
        a is not None and b is not None and a < b
        for a, b in zip(means[:-1], means[1:], strict=True)
    )
