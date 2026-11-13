"""NASA NLDAS & GLDAS Land Data Assimilation Systems connector.

Accesses North American and Global Land Data Assimilation Systems:
- NLDAS-2: 0.125° (~12.5 km) hourly/daily forcing and Noah land surface model variables.
  CMR Short Name: NLDAS_FORA0125_H (C2033151148-GES_DISC), NLDAS_NOAH0125_H (C2069246977-GES_DISC)
- GLDAS-2: 0.25° (~25 km) 3-hourly/daily global land surface states.
  CMR Short Name: GLDAS_NOAH025_3H (C1342986035-GES_DISC)

Scale contract: Coarse regional context/forcing (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'D' (derived land data assimilation model).
Licence: NASA Open Data Policy (public domain).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"


def search_ldas_granules(
    short_name: str,
    bbox: tuple[float, float, float, float],
    start: dt.date,
    end: dt.date,
    version: str = "2.0",
    page_size: int = 10,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Query CMR for NLDAS or GLDAS granules."""
    params = {
        "short_name": short_name,
        "version": version,
        "bounding_box": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
        "page_size": page_size,
    }
    r = (session or requests).get(CMR_GRANULES_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("feed", {}).get("entry", [])


def ldas_metadata(short_name: str) -> dict[str, Any]:
    """Return standard scale-contract metadata for LDAS product."""
    is_nldas = "NLDAS" in short_name.upper()
    res_km = 12.5 if is_nldas else 25.0
    return {
        "short_name": short_name,
        "resolution_km": res_km,
        "scale_flag": True,
        "tag": "D",
        "source": f"NASA {'NLDAS-2' if is_nldas else 'GLDAS-2'} Land Data Assimilation System",
    }
