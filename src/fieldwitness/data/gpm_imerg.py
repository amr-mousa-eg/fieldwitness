"""NASA Global Precipitation Measurement (GPM) & IMERG client and validation bridge.

Product: GPM IMERG Final Daily (GPM_3IMERGDF v07, Concept ID C2723754864-GES_DISC).
Resolution: 0.1° (~10 km) half-hourly / daily precipitation estimates.
Scale contract: Coarse forcing/context only (CLAUDE.md Rule 5); scale_flag is always True.
Licence: NASA Open Data Policy (public domain).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from fieldwitness.data.asof import cutoff, guard, limit_end, register

CMR_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION_CONCEPT_ID = "C2723754864-GES_DISC"
SHORT_NAME = "GPM_3IMERGDF"
VERSION = "07"
CACHE_DIR = Path("data/context/imerg")


def cmr_search_granules(
    bbox: tuple[float, float, float, float],
    start: dt.date,
    end: dt.date,
    page_size: int = 10,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Search for GPM IMERG granules in NASA CMR for a given bounding box and date range."""
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "bounding_box": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
        "page_size": page_size,
    }
    r = (session or requests).get(CMR_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    feed = r.json().get("feed", {})
    return feed.get("entry", [])


def parse_imerg_daily_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse simulated or retrieved IMERG daily precipitation records into standard DataFrame.

    Output columns: ['date', 'rain_mm', 'scale_flag', 'tag', 'source']
    """
    if not records:
        return pd.DataFrame(columns=["date", "rain_mm", "scale_flag", "tag", "source"])
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["scale_flag"] = True
    df["tag"] = "O"
    df["source"] = f"NASA GPM IMERG Final Daily ({SHORT_NAME}.{VERSION}, 0.1 deg)"
    return df.sort_values("date").reset_index(drop=True)


@register("gpm_imerg", weather=True)
def read_imerg(
    region_id: str = "ks_t14slh",
    start: dt.date | None = None,
    end: dt.date | None = None,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read cached regional GPM IMERG daily precipitation, respecting active as_of cutoff."""
    if table is not None:
        df = table.copy()
    else:
        parquet_path = CACHE_DIR / f"{region_id}_imerg_daily.parquet"
        if not parquet_path.exists():
            return pd.DataFrame(columns=["date", "rain_mm", "scale_flag", "tag", "source"])
        df = pd.read_parquet(parquet_path)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]
    if start is not None:
        df = df[df["date"] >= start]
    if end is not None:
        hi = limit_end(end, weather=True)
        df = df[df["date"] <= hi]

    guard(df["date"], "gpm_imerg", weather=True)
    return df.reset_index(drop=True)


def calculate_rain_anomaly(
    daily_df: pd.DataFrame,
    baseline_years: tuple[int, int] = (2001, 2020),
) -> pd.DataFrame:
    """Compute monthly precipitation totals and anomalies relative to baseline climatology."""
    if daily_df.empty:
        return pd.DataFrame()
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = df.groupby(["year", "month"], as_index=False)["rain_mm"].sum()
    base = monthly[monthly["year"].between(baseline_years[0], baseline_years[1])]
    if base.empty:
        clim = monthly.groupby("month")["rain_mm"].mean()
    else:
        clim = base.groupby("month")["rain_mm"].mean()

    monthly["climatology_mm"] = monthly["month"].map(clim)
    monthly["anomaly_mm"] = monthly["rain_mm"] - monthly["climatology_mm"]
    monthly["anomaly_pct"] = np.where(
        monthly["climatology_mm"] > 0,
        (monthly["anomaly_mm"] / monthly["climatology_mm"]) * 100.0,
        0.0,
    )
    return monthly
