"""T6.8: weather what-ifs. Sensitivity tests on past weather, not climate projections.

A scenario shifts historical POWER weather: temperature +dT degC on T2M_MAX and T2M_MIN (RH2M,
wind, radiation unchanged, so vapour pressure follows via FAO-56 Eq. 19 with the shifted T) and
rainfall x (1 + dP/100). Grid = PLAN T6.8 (3 temperatures x 4 rainfall). Tag D, shifts are A.
"""

import numpy as np
import pandas as pd

from fieldwitness.physics.forcing import forcing

DT_GRID = (0.0, 1.0, 2.0)
DP_GRID = (-20.0, -10.0, 0.0, 10.0)
BASELINE_ID = "t+0_p+0"
WEATHER_METRICS = (
    "ryi",
    "cvar10_ryi",
    "cover_days",
    "water_use_mm",
    "irrigation_mm",
    "cvar10_water_mm",
)


def scenario_id(dt: float, dp: float) -> str:
    return f"t{dt:+.0f}_p{dp:+.0f}"


def grid() -> list[tuple[str, float, float]]:
    return [(scenario_id(t, p), t, p) for t in DT_GRID for p in DP_GRID]


def perturb(weather: pd.DataFrame, dt_c: float, dp_pct: float) -> pd.DataFrame:
    """Copy of POWER weather with temperature shifted and rain scaled. NaN stays NaN."""
    w = weather.copy()
    w["T2M_MAX"] = w["T2M_MAX"] + dt_c
    w["T2M_MIN"] = w["T2M_MIN"] + dt_c
    w["PRECTOTCORR"] = w["PRECTOTCORR"] * (1.0 + dp_pct / 100.0)
    return w


def yearly_arrays(
    weather: pd.DataFrame, lat: float, elev: float, y0: int, y1: int
) -> tuple[np.ndarray, np.ndarray]:
    """(rain, eto) arrays (n_years, 365); incomplete years and 29 Feb are dropped."""
    f = forcing(weather, lat, elev)
    rain, eto = [], []
    for y in range(y0, y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return np.array(rain), np.array(eto)
