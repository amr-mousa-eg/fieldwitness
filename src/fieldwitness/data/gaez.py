"""FAO Global Agro-Ecological Zones (GAEZ v4) connector.

Accesses FAO/IIASA Global Agro-Ecological Zones (GAEZ v4) spatial services:
Endpoint: https://gaez-services.fao.org/server/rest/services
Themes:
- LR: Land Resources (soil qualities, terrain slope constraints)
- res01-res07: Agro-climatic suitability, moisture regimes, crop suitability
Scale contract: 5 arc-minute (~10 km) coarse regional context (CLAUDE.md Rule 5: scale_flag=True).
Provenance tag: 'E' (FAO / IIASA Agro-Ecological Zones framework).
Licence: CC-BY-4.0 (FAO / IIASA).
"""

from __future__ import annotations

from typing import Any

import requests

GAEZ_SERVICES_URL = "https://gaez-services.fao.org/server/rest/services"


def list_gaez_services(session: requests.Session | None = None) -> list[dict[str, str]]:
    """Query FAO GAEZ REST directory for available ImageServer themes."""
    r = (session or requests).get(f"{GAEZ_SERVICES_URL}?f=json", timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("services", [])


def identify_gaez_pixel(
    service_name: str,
    lon: float,
    lat: float,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Identify GAEZ pixel value at coordinates."""
    url = f"{GAEZ_SERVICES_URL}/{service_name}/ImageServer/identify"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "f": "json",
    }
    try:
        r = (session or requests).get(url, params=params, timeout=20)
        r.raise_for_status()
        res = r.json()
        val = res.get("value")
        return {
            "service": service_name,
            "value": val,
            "scale_flag": True,
            "tag": "E",
            "source": f"FAO GAEZ v4 ({service_name})",
        }
    except Exception as e:
        return {
            "service": service_name,
            "value": None,
            "error": str(e),
            "scale_flag": True,
            "tag": "E",
            "source": f"FAO GAEZ v4 ({service_name})",
        }
