"""Experiment 1: distance-adjusted propensity score matching (DAPSM) for the neighbour witness.

Pre-registered in DECISIONS.md (2026-11-12, "Pre-registration: two algorithm experiments").
Same contrasts, confounders, outcomes, strata and thresholds as the T5.xa matching-history design
(`neighbours/matching.py`); only the way treated and reference rows are compared changes:

    D(i, j) = w * |PS_i - PS_j| + (1 - w) * dist_scaled(i, j)

PS = cross-fitted propensity of the existing `fit_plr` (random forest, spatial block folds).
dist_scaled = Haversine distance between field centroids / max pairwise centroid distance of the
pilot fields (fixed rule, geometry only). Matching is 1:1 nearest neighbour with replacement,
never to a row of the same field. Idea after Papadogeorgou, Choirat and Zigler (2019),
"Adjusting for unmeasured spatial confounding with distance adjusted propensity score matching",
Biostatistics 20(2):256-272 (method idea only; no value is taken from the paper).
Thresholds are the T5.3 team choices (tag A, UNVERIFIED rules of thumb), not tuned here.
All outputs tag D (model statistics from satellite outcomes).
"""

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0088  # IUGG mean Earth radius (tag E)
W_GRID = tuple(round(0.1 * i, 1) for i in range(11))


def centroids(pilot: pd.DataFrame) -> pd.DataFrame:
    """Field centroids (lat, lon, WGS 84) from WKB polygons in WGS 84.

    The centroid is computed in UTM zone 14N (EPSG:32614, the zone of tile T14SLH) so it is a
    planar area centroid, then converted back to lon/lat.
    """
    import shapely
    from pyproj import Transformer

    geom = shapely.from_wkb(pilot["geometry"].to_numpy())
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True)
    back = Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True)
    projected = shapely.transform(geom, lambda xy: np.column_stack(fwd.transform(*xy.T)))
    c = shapely.centroid(projected)
    lon, lat = back.transform(shapely.get_x(c), shapely.get_y(c))
    return pd.DataFrame(
        {"field_id": pilot["field_id"].to_numpy(), "lat": np.asarray(lat), "lon": np.asarray(lon)}
    )


def haversine_km(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Pairwise great-circle distances (km) between points given in degrees (Haversine)."""
    p = np.radians(np.asarray(lat, float))
    q = np.radians(np.asarray(lon, float))
    dp = p[:, None] - p[None, :]
    dq = q[:, None] - q[None, :]
    a = np.sin(dp / 2) ** 2 + np.cos(p)[:, None] * np.cos(p)[None, :] * np.sin(dq / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def match(
    ps: np.ndarray, dist_scaled: np.ndarray, treated: np.ndarray, field: np.ndarray, w: float
) -> np.ndarray:
    """For each row, the index of its matched reference row (-1 for reference rows).

    ps (n,), dist_scaled (n, n) between the rows' fields scaled to [0, 1], treated (n,) bool,
    field (n,) field ids. D = w |PS_i - PS_j| + (1 - w) dist; rows of the same field are never
    matched; ties go to the lowest index. With replacement. -1 also when no reference row exists.
    """
    ps = np.asarray(ps, float)
    t = np.asarray(treated, bool)
    field = np.asarray(field)
    ref = np.flatnonzero(~t)
    out = np.full(len(ps), -1)
    for i in np.flatnonzero(t):
        cand = ref[field[ref] != field[i]]
        if not len(cand):
            continue
        d = w * np.abs(ps[i] - ps[cand]) + (1.0 - w) * dist_scaled[i, cand]
        out[i] = cand[np.argmin(d)]  # argmin returns the first (lowest index) minimum
    return out


def match_weights(matches: np.ndarray, treated: np.ndarray) -> np.ndarray:
    """Weights of the matched sample: 1 per matched treated row, match count per reference row."""
    t = np.asarray(treated, bool)
    w = np.zeros(len(t))
    ok = t & (matches >= 0)
    w[ok] = 1.0
    np.add.at(w, matches[ok], 1.0)
    return w


def smd_per_covariate(x: pd.DataFrame, treated: np.ndarray, w: np.ndarray) -> pd.Series:
    """|SMD| per column: weighted mean difference / pooled SD of the unweighted sample.

    Same pooled SD as `diagnostics.balance_smd`; columns with zero or undefined SD are skipped.
    """
    d = np.asarray(treated, bool)
    out = {}
    for c in x.columns:
        v = x[c].to_numpy(dtype=float)
        sd = np.sqrt((v[d].var(ddof=1) + v[~d].var(ddof=1)) / 2) if d.sum() > 1 else 0.0
        if sd == 0 or not np.isfinite(sd) or w[d].sum() == 0 or w[~d].sum() == 0:
            continue
        m1 = np.average(v[d], weights=w[d])
        m0 = np.average(v[~d], weights=w[~d])
        out[c] = abs(m1 - m0) / sd
    return pd.Series(out, dtype=float)


def choose_w(grid: pd.DataFrame) -> float:
    """Pre-registered rule: smallest median (over contrasts) of the per-contrast max |SMD|.

    grid: one row per (contrast, w) with columns `w` and `smd_max`. Ties go to the larger w.
    """
    med = grid.dropna(subset=["smd_max"]).groupby("w")["smd_max"].median()
    best = med.min()
    return float(max(w for w, v in med.items() if np.isclose(v, best, rtol=0, atol=1e-12)))


def matched_effect(
    y: np.ndarray,
    matches: np.ndarray,
    treated: np.ndarray,
    blocks: np.ndarray,
    n_boot: int = 1000,
    seed: int = 20261114,
) -> dict:
    """Matched effect = mean(y_treated - y_matched) with a percentile block-bootstrap 95 % CI.

    Resamples whole 10 km blocks of treated rows with replacement (`n_boot` times, seeded).
    """
    t = np.flatnonzero(np.asarray(treated, bool) & (matches >= 0))
    diff = np.asarray(y, float)[t] - np.asarray(y, float)[matches[t]]
    b = np.asarray(blocks)[t]
    ub = np.unique(b)
    rows = {k: diff[b == k] for k in ub}
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for r in range(n_boot):
        pick = rng.choice(ub, size=len(ub), replace=True)
        means[r] = np.concatenate([rows[k] for k in pick]).mean()
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {
        "effect": float(diff.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_pairs": len(t),
        "status": "fail" if (lo > 0 or hi < 0) else "pass",
    }


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score 95 % interval for a share k/n (Wilson 1927)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (float(mid - half), float(mid + half))
