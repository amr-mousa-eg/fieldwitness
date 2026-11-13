"""ECMWF ERA5 Reanalysis client.

Retrieves ECMWF ERA5 and ERA5-Land global atmospheric reanalysis variables:
- Daily max/min 2m air temperature (°C)
- Daily precipitation sum (mm)
- Daily FAO-56 reference evapotranspiration ETo (mm)
- Solar radiation & 10m wind speed

Source: ECMWF Copernicus Climate Change Service.
Scale contract: 0.1° / 0.25° coarse forcing/context (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'E' (external non-NASA European reanalysis).
Licence: Copernicus Open Access Licence (free with attribution).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from fieldwitness.data.asof import cutoff, guard, limit_end, register

OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = Path("data/weather/era5")


def fetch_era5_point(
    lat: float,
    lon: float,
    start: dt.date,
    end: dt.date,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch ERA5 daily meteorological time series for a point from the open archive API."""
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "et0_fao_evapotranspiration",
            "wind_speed_10m_max",
            "shortwave_radiation_sum",
        ],
        "timezone": "UTC",
    }
    r = (session or requests).get(OPENMETEO_ARCHIVE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def parse_era5_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse ERA5 daily JSON payload into standardized DataFrame.
    Output columns include date, tmax_c, tmin_c, rain_mm, eto_mm,
    wind_max_ms, rad_mj_m2, scale_flag, tag, source.
    """
    daily = payload.get("daily", {})
    times = daily.get("time", [])
    if not times:
        return pd.DataFrame(
            columns=[
                "date",
                "tmax_c",
                "tmin_c",
                "rain_mm",
                "eto_mm",
                "wind_max_ms",
                "rad_mj_m2",
                "scale_flag",
                "tag",
                "source",
            ]
        )

    tmax = daily.get("temperature_2m_max", [None] * len(times))
    tmin = daily.get("temperature_2m_min", [None] * len(times))
    rain = daily.get("precipitation_sum", [None] * len(times))
    eto = daily.get("et0_fao_evapotranspiration", [None] * len(times))
    wind = daily.get("wind_speed_10m_max", [None] * len(times))
    rad = daily.get("shortwave_radiation_sum", [None] * len(times))

    rows = []
    for i, t in enumerate(times):
        rows.append(
            {
                "date": dt.date.fromisoformat(t),
                "tmax_c": float(tmax[i]) if tmax[i] is not None else None,
                "tmin_c": float(tmin[i]) if tmin[i] is not None else None,
                "rain_mm": float(rain[i]) if rain[i] is not None else None,
                "eto_mm": float(eto[i]) if eto[i] is not None else None,
                "wind_max_ms": float(wind[i]) if wind[i] is not None else None,
                "rad_mj_m2": float(rad[i]) if rad[i] is not None else None,
                "scale_flag": True,
                "tag": "E",
                "source": "ECMWF ERA5 Reanalysis (0.1 deg / 0.25 deg)",
            }
        )
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


@register("era5", weather=True)
def read_era5(
    region_id: str = "ks_t14slh",
    start: dt.date | None = None,
    end: dt.date | None = None,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read regional ERA5 daily meteorology, clipped to the active as_of cut-off and guarded."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_era5_daily.parquet"
        if not p.exists():
            return pd.DataFrame(
                columns=[
                    "date",
                    "tmax_c",
                    "tmin_c",
                    "rain_mm",
                    "eto_mm",
                    "wind_max_ms",
                    "rad_mj_m2",
                    "scale_flag",
                    "tag",
                    "source",
                ]
            )
        df = pd.read_parquet(p)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]
    if start is not None:
        df = df[df["date"] >= start]
    if end is not None:
        hi = limit_end(end, weather=True)
        df = df[df["date"] <= hi]

    guard(df["date"], "era5", weather=True)
    return df.reset_index(drop=True)
