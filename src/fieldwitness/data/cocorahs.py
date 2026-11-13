"""CoCoRaHS (Community Collaborative Rain, Hail & Snow Network) station data helper.

Parses and validates volunteer citizen-science rain gauge measurements from CoCoRaHS:
Export URL: https://data.cocorahs.org/export/exportreports.aspx

Provides ground-level validation for NASA GPM IMERG and NASA POWER daily precipitation.
Provenance tag: 'E' (external non-NASA volunteer rain gauge network).
Licence: Open access / CoCoRaHS terms of use (educational and research reuse).
"""

from __future__ import annotations

import csv
import datetime as dt
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from fieldwitness.data.asof import cutoff, guard, register

CACHE_DIR = Path("data/weather/cocorahs")
INCH_TO_MM = 25.4


def parse_cocorahs_csv(csv_content: str) -> pd.DataFrame:
    """Parse CoCoRaHS export CSV into standardized DataFrame.

    Handles common fields: StationNumber, StationName, Latitude, Longitude,
    ObservationDate, TotalPrecipAmt (inches -> mm).
    """
    reader = csv.DictReader(StringIO(csv_content))
    rows: list[dict[str, Any]] = []
    for r in reader:
        date_str = r.get("ObservationDate") or r.get("Date")
        if not date_str:
            continue
        try:
            obs_date = dt.date.fromisoformat(date_str[:10])
        except ValueError:
            continue

        precip_raw = r.get("TotalPrecipAmt") or r.get("Precip") or ""
        precip_mm: float | None = None
        if precip_raw.strip().upper() == "T":
            precip_mm = 0.05  # Trace precipitation ~0.05 mm
        elif precip_raw.strip().replace(".", "", 1).isdigit():
            precip_mm = round(float(precip_raw) * INCH_TO_MM, 2)

        st_id = r.get("StationNumber") or r.get("StationID") or "unknown"
        lat = float(r["Latitude"]) if r.get("Latitude") else None
        lon = float(r["Longitude"]) if r.get("Longitude") else None

        rows.append(
            {
                "station_id": st_id,
                "date": obs_date,
                "lat": lat,
                "lon": lon,
                "rain_mm": precip_mm,
                "tag": "E",
                "source": "CoCoRaHS Volunteer Precipitation Network",
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["station_id", "date", "lat", "lon", "rain_mm", "tag", "source"]
        )
    df = pd.DataFrame(rows)
    return df.sort_values(["station_id", "date"]).reset_index(drop=True)


@register("cocorahs", weather=True)
def read_cocorahs(
    region_id: str = "ks_t14slh",
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read cached CoCoRaHS station observations respecting active as_of date."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_cocorahs.parquet"
        if not p.exists():
            return pd.DataFrame(
                columns=["station_id", "date", "lat", "lon", "rain_mm", "tag", "source"]
            )
        df = pd.read_parquet(p)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]

    guard(df["date"], "cocorahs", weather=True)
    return df.reset_index(drop=True)
