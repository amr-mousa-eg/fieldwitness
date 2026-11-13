"""USGS National Water Information System (NWIS) connector.

Fetches open, no-key groundwater levels (depth to water table) and daily streamflow
from USGS Water Services REST API:
- Groundwater levels: https://waterservices.usgs.gov/nwis/gwlevels/
- Daily streamflow/discharge: https://waterservices.usgs.gov/nwis/dv/

Provenance tag: 'E' (external non-NASA in-situ observation).
Public domain: US Geological Survey Open Data.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from fieldwitness.data.asof import cutoff, guard, register

NWIS_GW_URL = "https://waterservices.usgs.gov/nwis/gwlevels/"
NWIS_DV_URL = "https://waterservices.usgs.gov/nwis/dv/"
FT_TO_M = 0.3048
CACHE_DIR = Path("data/context/nwis")


def fetch_groundwater_levels(
    bbox: tuple[float, float, float, float],
    start: dt.date | None = None,
    end: dt.date | None = None,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Query USGS NWIS for groundwater depth observations within bounding box (W, S, E, N)."""
    params: dict[str, Any] = {
        "format": "json",
        "bBox": f"{bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f},{bbox[3]:.4f}",
    }
    if start and end:
        params["startDT"] = start.isoformat()
        params["endDT"] = end.isoformat()
    else:
        params["period"] = "P365D"

    r = (session or requests).get(NWIS_GW_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    time_series = data.get("value", {}).get("timeSeries", [])
    records = []
    for ts in time_series:
        source_info = ts.get("sourceInfo", {})
        site_name = source_info.get("siteName", "")
        site_code = source_info.get("siteCode", [{}])[0].get("value", "")
        geo = source_info.get("geoLocation", {}).get("geogLocation", {})
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        values = ts.get("values", [{}])[0].get("value", [])
        for v in values:
            date_str = v.get("dateTime", "")[:10]
            val_str = v.get("value")
            if val_str is not None:
                try:
                    val_ft = float(val_str)
                    records.append(
                        {
                            "site_id": site_code,
                            "site_name": site_name,
                            "lat": lat,
                            "lon": lon,
                            "date": date_str,
                            "depth_to_water_ft": val_ft,
                            "depth_to_water_m": round(val_ft * FT_TO_M, 2),
                        }
                    )
                except ValueError:
                    continue
    return records


def parse_groundwater_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert NWIS groundwater records into cleaned DataFrame with provenance tags."""
    if not records:
        return pd.DataFrame(
            columns=[
                "site_id",
                "site_name",
                "lat",
                "lon",
                "date",
                "depth_to_water_ft",
                "depth_to_water_m",
                "tag",
                "source",
            ]
        )
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["tag"] = "E"
    df["source"] = "USGS NWIS Ground-Water Levels (waterservices.usgs.gov)"
    return df.sort_values("date").reset_index(drop=True)


@register("nwis_gw", weather=False)
def read_groundwater(
    region_id: str = "ks_t14slh",
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read regional NWIS groundwater time series respecting active as_of date."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_groundwater.parquet"
        if not p.exists():
            return pd.DataFrame(
                columns=[
                    "site_id",
                    "site_name",
                    "lat",
                    "lon",
                    "date",
                    "depth_to_water_ft",
                    "depth_to_water_m",
                    "tag",
                    "source",
                ]
            )
        df = pd.read_parquet(p)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]
    guard(df["date"], "nwis_gw", weather=False)
    return df.reset_index(drop=True)
