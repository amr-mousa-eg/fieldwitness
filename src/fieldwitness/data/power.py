"""NASA POWER daily point client (PLAN.md T1.2).

API verified 2026-11-04 (docs/api_notes.md): GET https://power.larc.nasa.gov/api/temporal/daily/point,
community AG, JSON; `properties.parameter.<NAME>` = {YYYYMMDD: value}; fill value -999;
`geometry.coordinates[2]` = elevation (m). One call covering 2001-2024 returned 8,766 days.

Cache: one Parquet file per request point rounded to 0.01 degrees under data/power/ (the POWER
grid size is not stated in the POWER docs we read, so we do not key by grid cell).
POWER is coarse forcing/context only (CLAUDE.md rule 5): scale flag always raised.
"""

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from fieldwitness.data.asof import guard, limit_end, register

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ["T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
UNITS = {  # as returned by the API (parameters.<NAME>.units)
    "T2M_MAX": "C",
    "T2M_MIN": "C",
    "RH2M": "%",
    "WS2M": "m/s",
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
    "PRECTOTCORR": "mm/day",
}
CACHE = Path("data/power")
START = dt.date(2001, 1, 1)
END = dt.date(2024, 12, 31)


def parse(payload: dict) -> tuple[pd.DataFrame, float | None]:
    """POWER JSON -> daily DataFrame (DatetimeIndex 'date', one column per parameter, -999 -> NaN)
    and the returned elevation (m)."""
    par = payload["properties"]["parameter"]
    fill = payload.get("header", {}).get("fill_value", -999.0)
    df = pd.DataFrame({k: pd.Series(v, dtype=float) for k, v in par.items()})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.replace(fill, np.nan).sort_index()
    coords = payload.get("geometry", {}).get("coordinates", [])
    elev = float(coords[2]) if len(coords) > 2 else None
    return df, elev


def _key(lon: float, lat: float) -> str:
    return f"{round(lon, 2):+08.2f}_{round(lat, 2):+07.2f}"


def fetch(lon: float, lat: float, start=START, end=END, session=None) -> dict:
    q = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": round(lon, 2),
        "latitude": round(lat, 2),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    r = (session or requests).get(URL, params=q, timeout=300)
    r.raise_for_status()
    return r.json()


def cached(lon: float, lat: float) -> tuple[pd.DataFrame, float | None]:
    """2001-2024 daily series for the rounded point, from cache or one API call."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{_key(lon, lat)}.parquet"
    meta = f.with_suffix(".json")
    if f.exists() and meta.exists():
        return pd.read_parquet(f), json.loads(meta.read_text())["elevation_m"]
    df, elev = parse(fetch(lon, lat))
    df.to_parquet(f)
    meta.write_text(json.dumps({"elevation_m": elev, "lon": round(lon, 2), "lat": round(lat, 2)}))
    return df, elev


@register("power", weather=True)
def read(lon: float, lat: float, start=START, end=END, loader=cached) -> pd.DataFrame:
    """Daily weather for [start, end], clipped to the active `as_of` cut-off and guarded."""
    df, _ = loader(lon, lat)
    hi = limit_end(end, weather=True)
    out = df.loc[pd.Timestamp(start) : pd.Timestamp(hi)]
    guard((d.date() for d in out.index), "POWER", weather=True)
    return out
