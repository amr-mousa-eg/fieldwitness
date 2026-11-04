"""Daily forcing for the water balance: POWER weather -> ETo, rain (T3.1).

Inputs are the columns returned by `fieldwitness.data.power.read` (units in power.UNITS).
ETo uses FAO-56 Eq. 6 via `physics.eto.eto_daily` with the mean-RH route for actual vapour
pressure (FAO-56 Eq. 19; POWER gives only RH2M, not RHmax/RHmin) and Rs from POWER
ALLSKY_SFC_SW_DWN. Soil heat flux G = 0 for daily steps (FAO-56 Eq. 42).
POWER is coarse (scale flag always raised, CLAUDE.md rule 5): context/forcing only. Tag: D.
"""

import numpy as np
import pandas as pd

from fieldwitness.physics import eto as e

REQUIRED = ["T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]


def forcing(weather: pd.DataFrame, lat_deg: float, z_m: float) -> pd.DataFrame:
    """Return DataFrame indexed by date with columns `eto` (mm/day) and `rain` (mm/day).

    Days with any missing input give NaN ETo (never filled silently).
    """
    missing = [c for c in REQUIRED if c not in weather.columns]
    if missing:
        raise KeyError(f"weather is missing columns: {missing}")
    w = weather
    tmax, tmin = w["T2M_MAX"].to_numpy(float), w["T2M_MIN"].to_numpy(float)
    ea = e.actual_vp_rh_mean(tmax, tmin, w["RH2M"].to_numpy(float))
    doy = w.index.day_of_year.to_numpy()
    eto = e.eto_daily(
        tmax,
        tmin,
        w["ALLSKY_SFC_SW_DWN"].to_numpy(float),
        w["WS2M"].to_numpy(float),
        ea,
        z_m,
        lat_deg,
        doy,
    )
    return pd.DataFrame(
        {"eto": np.asarray(eto, float), "rain": w["PRECTOTCORR"].to_numpy(float)},
        index=w.index,
    )
