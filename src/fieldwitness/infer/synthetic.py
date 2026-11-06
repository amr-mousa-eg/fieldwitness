"""Synthetic fields with known hidden values (T4.2).

Truth is drawn from the priors (`infer.priors.sample`), the season is simulated with
`infer.forward.simulate` under real POWER weather of a random year, then observed through a real
cloud-gap pattern and noise, both taken from the Kansas HLS series (the "census"):
- gaps: the day-of-year set of a randomly chosen real field-year;
- noise: robust sd of NDVI differences between observations at most 6 days apart (tag D). It
  includes real change between dates, so it overstates pure noise (conservative).
Everything is seeded. Weather is read through `data.power.read` (the `as_of` guard applies).
"""

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.infer import forward, priors
from fieldwitness.physics.forcing import forcing

SEED = priors.SEED
MIN_OBS = 10  # a field-year with fewer clear dates is not used as a gap template


def census(series: pd.DataFrame) -> dict:
    """series: columns field_id, date, ndvi. Returns gap templates and the noise sd."""
    s = series.dropna(subset=["ndvi"]).sort_values(["field_id", "date"])
    s = s.assign(year=s["date"].dt.year, doy=s["date"].dt.day_of_year)
    gaps = [g["doy"].to_numpy() for _, g in s.groupby(["field_id", "year"]) if len(g) >= MIN_OBS]
    d_ndvi, d_day = [], []
    for _, g in s.groupby("field_id"):
        d_ndvi.append(np.diff(g["ndvi"].to_numpy()))
        d_day.append(np.diff(g["date"].to_numpy().astype("datetime64[D]").astype(int)))
    d_ndvi, d_day = np.concatenate(d_ndvi), np.concatenate(d_day)
    close = (d_day > 0) & (d_day <= 6)
    mad = np.median(np.abs(d_ndvi[close] - np.median(d_ndvi[close])))
    sd = float(mad / 0.6745 / np.sqrt(2.0))
    return {
        "gap_templates": gaps,
        "noise_sd": sd,
        "n_templates": len(gaps),
        "median_obs_per_year": float(np.median([len(g) for g in gaps])),
        "tag": "D",
    }


def weather_years(cfg: dict) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """{year: (rain[365], eto[365])} for the config point; 29 Feb dropped."""
    pt = cfg["weather_point"]
    y0, y1 = cfg["weather_years"]
    w = power.read(pt["lon"], pt["lat"], f"{y0}-01-01", f"{y1}-12-31")
    _, elev = power.cached(pt["lon"], pt["lat"])
    f = forcing(w, pt["lat"], float(elev or 0.0))
    out = {}
    for y in range(y0, y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) == 365 and not fy.isna().any().any():
            out[y] = (fy["rain"].to_numpy(), fy["eto"].to_numpy())
    return out


def make_fields(n: int, cen: dict, wx: dict, seed: int = SEED, cfg: dict | None = None) -> dict:
    """n synthetic fields. Returns truth (dict of arrays), year, obs_doy / obs_ndvi (lists),
    true_ndvi (365, n), eta_mm (n,)."""
    cfg = cfg or forward.load_cfg()
    crop = forward.crop_params(cfg["crop"], cfg["region"])
    rng = np.random.default_rng(seed)
    truth = priors.sample(n, seed=seed)
    years = sorted(wx)
    yr = rng.choice(years, size=n)
    true = np.zeros((forward.DAYS, n))
    eta = np.zeros(n)
    for y in years:
        idx = np.flatnonzero(yr == y)
        if idx.size == 0:
            continue
        sub = {k: np.asarray(v)[idx] for k, v in truth.items()}
        r = forward.simulate(wx[y][0], wx[y][1], sub, crop, cfg)
        true[:, idx], eta[idx] = r["ndvi"], r["eta_mm"]
    obs_doy, obs_ndvi = [], []
    tpl = cen["gap_templates"]
    for j in range(n):
        d = np.unique(np.clip(tpl[rng.integers(len(tpl))], 1, forward.DAYS))
        v = true[d - 1, j] + rng.normal(0.0, cen["noise_sd"], d.size)
        obs_doy.append(d)
        obs_ndvi.append(np.clip(v, -1.0, 1.0))
    return {
        "truth": truth,
        "year": yr,
        "obs_doy": obs_doy,
        "obs_ndvi": obs_ndvi,
        "true_ndvi": true,
        "eta_mm": eta,
        "tag": "D",
    }
