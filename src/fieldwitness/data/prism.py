"""Oregon State University PRISM Climate Data client.

Accesses the official PRISM centralized public web service for 4 km and 800 m
historical meteorological data (precipitation, Tmax, Tmin, dewpoint):
Endpoint: https://services.nacse.org/prism/data/get/us/4km/{variable}/{date}

Scale contract: 4 km coarse weather forcing/context (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'E' (external non-NASA meteorological model, Oregon State University).
Licence: Free for research/educational use; commercial redistribution terms apply.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from fieldwitness.data.asof import cutoff, guard, limit_end, register

PRISM_BASE_URL = "https://services.nacse.org/prism/data/get/us/4km"
CACHE_DIR = Path("data/weather/prism")
VARIABLES = ["ppt", "tmax", "tmin", "tmean"]


def prism_url(variable: str, date: dt.date, res_km: int = 4) -> str:
    """Generate official PRISM download URL for a given variable and date."""
    if variable not in VARIABLES:
        raise ValueError(f"Unknown PRISM variable {variable}, expected one of {VARIABLES}")
    d_str = date.strftime("%Y%m%d")
    return f"https://services.nacse.org/prism/data/get/us/{res_km}km/{variable}/{d_str}"


def parse_prism_daily_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse list of extracted PRISM daily weather records into standard DataFrame.

    Columns: ['date', 'ppt_mm', 'tmax_c', 'tmin_c', 'tmean_c', 'scale_flag', 'tag', 'source']
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "date",
                "ppt_mm",
                "tmax_c",
                "tmin_c",
                "tmean_c",
                "scale_flag",
                "tag",
                "source",
            ]
        )
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["scale_flag"] = True
    df["tag"] = "E"
    df["source"] = "PRISM Climate Group (Oregon State University, 4 km gridded)"
    return df.sort_values("date").reset_index(drop=True)


@register("prism", weather=True)
def read_prism(
    region_id: str = "ks_t14slh",
    start: dt.date | None = None,
    end: dt.date | None = None,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read regional PRISM daily meteorological series respecting active as_of cutoff."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_prism_daily.parquet"
        if not p.exists():
            return pd.DataFrame(
                columns=[
                    "date",
                    "ppt_mm",
                    "tmax_c",
                    "tmin_c",
                    "tmean_c",
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

    guard(df["date"], "prism", weather=True)
    return df.reset_index(drop=True)
