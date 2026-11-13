"""USDA NASS Cropland Data Layer (CDL) CropScape web service connector.

Direct API for USDA Cropland Data Layer (30 m annual crop classifications):
Endpoint: https://nassgeodata.gmu.edu/axis2/services/CDLService/
Methods:
- GetCDLValue (returns pixel crop category at lon/lat coordinate)
- GetCDLStat (returns crop acreages and pixel counts within bounding box)

Scale contract: 30 m resolution matches HLS field-scale requirements (CLAUDE.md Rule 5).
Provenance tag: 'E' (USDA NASS remote sensing crop classification).
Licence: Public domain (US Government Work).
"""

from __future__ import annotations

import re
from typing import Any

import requests

CROPSCAPE_SERVICE = "https://nassgeodata.gmu.edu/axis2/services/CDLService"

# Standard CDL Category codes relevant to pilot rotations
CDL_CODES: dict[int, str] = {
    1: "maize",
    4: "sorghum",
    5: "soybean",
    6: "sunflower",
    23: "spring_wheat",
    24: "winter_wheat",
    27: "rye",
    28: "oats",
    36: "alfalfa",
    61: "fallow",
    121: "developed",
    190: "woody_wetlands",
    195: "herbaceous_wetlands",
}


def parse_cdl_value_response(xml_text: str) -> dict[str, Any]:
    """Parse GetCDLValue XML response into crop category code and name.

    Example response: <return>24, Winter Wheat</return> or XML structure.
    """
    m = re.search(r"(\d+),\s*([^<]+)", xml_text)
    if m:
        category = int(m.group(1))
        category_name = m.group(2).strip()
        standard_crop = CDL_CODES.get(category, category_name.lower().replace(" ", "_"))
        return {
            "category": category,
            "category_name": category_name,
            "crop": standard_crop,
            "tag": "E",
            "source": "USDA NASS Cropland Data Layer (CropScape 30 m)",
        }
    return {
        "category": None,
        "category_name": "unknown",
        "crop": None,
        "tag": "E",
        "source": "USDA NASS Cropland Data Layer (CropScape 30 m)",
    }


def query_cdl_point(
    lon: float,
    lat: float,
    year: int,
    session: requests.Session | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Query CropScape for CDL crop classification at a point."""
    url = f"{CROPSCAPE_SERVICE}/GetCDLValue"
    params = {"year": str(year), "x": f"{lon:.6f}", "y": f"{lat:.6f}"}
    try:
        r = (session or requests).get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return parse_cdl_value_response(r.text)
    except Exception as e:
        return {
            "category": None,
            "category_name": "error",
            "crop": None,
            "error": str(e),
            "tag": "E",
            "source": "USDA NASS Cropland Data Layer (CropScape 30 m)",
        }
