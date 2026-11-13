"""USDA-NRCS STATSGO2 (U.S. General Soil Map) data provider.

Provides generalized national soil attributes (Available Water Capacity, texture, drainage)
via USDA Soil Data Access (SDA) REST API when detailed 1:24,000 SSURGO survey is unavailable:
Endpoint: https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest
Catalog: areasymbol = 'US' (National STATSGO2 database)

Scale contract: 1:250,000 regional generalized mapping (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'E' (USDA NRCS Soil Survey Geographic Database).
Licence: Public domain (US Government Work).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from fieldwitness.data import ssurgo

URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"


def statsgo_point_sql(lon: float, lat: float) -> str:
    """SQL query for STATSGO2 national mapunit components and horizons (areasymbol = 'US')."""
    return (
        "SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.majcompflag, "
        "h.hzdept_r, h.hzdepb_r, h.awc_r, h.claytotal_r, h.sandtotal_r "
        "FROM mapunit mu "
        "INNER JOIN legend l ON l.lkey = mu.lkey "
        "INNER JOIN component c ON c.mukey = mu.mukey "
        "LEFT JOIN chorizon h ON h.cokey = c.cokey "
        "WHERE l.areasymbol = 'US' AND mu.mukey IN "
        "(SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84("
        f"'point({lon:.6f} {lat:.6f})')) "
        "ORDER BY c.comppct_r DESC, c.cokey, h.hzdept_r"
    )


def query_statsgo_point(
    lon: float,
    lat: float,
    cache_path: Path | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Query SDA for STATSGO2 generalized soil profile at lon/lat coordinate."""
    if cache_path and cache_path.exists():
        return ssurgo.parse(json.loads(cache_path.read_text(encoding="utf-8")))

    query = statsgo_point_sql(lon, lat)
    payload = {"query": query, "format": "JSON+COLUMNNAME"}
    r = (session or requests).post(URL, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data), encoding="utf-8")
    return ssurgo.parse(data)


def statsgo_profile(rows: list[dict[str, Any]], zr_cm: float = 135.0) -> dict[str, Any]:
    """Compute depth-weighted available water storage (AWS) from STATSGO2 components."""
    prof = ssurgo.field_profile(rows, zr_cm)
    prof["scale_flag"] = True
    prof["tag"] = "E"
    prof["source"] = "USDA-NRCS STATSGO2 General Soil Map (1:250,000)"
    return prof
