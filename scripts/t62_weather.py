"""Shared POWER weather loader for the rotate scripts (same logic as scripts/t62_run.py)."""

import numpy as np

from fieldwitness.data import power
from fieldwitness.physics.forcing import forcing

Y0, Y1 = 2001, 2024


def weather(lon, lat):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue  # skip incomplete years
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return np.array(rain), np.array(eto)
