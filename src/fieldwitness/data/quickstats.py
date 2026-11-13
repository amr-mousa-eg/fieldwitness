"""USDA NASS QuickStats API connector.

Accesses official USDA National Agricultural Statistics Service county-level agricultural data:
API Endpoint: https://quickstats.nass.usda.gov/api/api_GET/
Auth: Requires a free personal API key via NASS_QUICKSTATS_API_KEY environment variable.

CRITICAL GUARDRAIL (CLAUDE.md Rule 4):
No commodity prices, dollar revenues, profit forecasts, or field-level tonnage yields
are extracted or presented. QuickStats data is strictly limited to regional crop presence,
harvested acreage fractions, and county-level crop frequency context.

Scale contract: County-level aggregate context only (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'E' (USDA NASS official agricultural statistics).
Licence: Public domain.
"""

from __future__ import annotations

import os
from typing import Any

import requests

QUICKSTATS_URL = "https://quickstats.nass.usda.gov/api/api_GET/"


def fetch_county_crop_acres(
    state_alpha: str,
    county_name: str,
    year: int,
    commodity: str = "CORN",
    api_key: str | None = None,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch county-level crop acreage statistics from USDA NASS QuickStats.

    Returns empty list if API key is not supplied or request fails.
    """
    key = api_key or os.environ.get("NASS_QUICKSTATS_API_KEY")
    if not key:
        return []

    params = {
        "key": key,
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": commodity.upper(),
        "state_alpha": state_alpha.upper(),
        "county_name": county_name.upper(),
        "year": str(year),
        "statisticcat_desc": "AREA HARVESTED",
        "format": "JSON",
    }

    try:
        r = (session or requests).get(QUICKSTATS_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        raw_items = data.get("data", [])
        records = []
        for it in raw_items:
            val_str = str(it.get("Value", "")).replace(",", "").strip()
            val = float(val_str) if val_str.replace(".", "", 1).isdigit() else None
            records.append(
                {
                    "commodity": it.get("commodity_desc"),
                    "year": int(it.get("year")),
                    "county": it.get("county_name"),
                    "state": it.get("state_alpha"),
                    "acres": val,
                    "unit": "ACRES",
                    "scale_flag": True,
                    "tag": "E",
                    "source": "USDA NASS QuickStats (county-level survey)",
                }
            )
        return records
    except Exception:
        return []
