"""USFS / DOI LANDFIRE connector.

Accesses USFS / DOI LANDFIRE vegetation, fuel, and ecological disturbance products (30 m):
Product API: https://lfps.usgs.gov/api/products

Scale contract: 30 m spatial resolution matches HLS grid (CLAUDE.md Rule 5).
Provenance tag: 'E' (USDA Forest Service / US Department of the Interior).
Licence: Public domain.
"""

from __future__ import annotations

from typing import Any

import requests

LANDFIRE_PRODUCTS_API = "https://lfps.usgs.gov/api/products"


def fetch_available_products(session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Query LANDFIRE product catalog for available layers and versions."""
    r = (session or requests).get(LANDFIRE_PRODUCTS_API, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("products", [])


def filter_vegetation_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter product list to vegetation, canopy cover, and disturbance layers."""
    keywords = ("vegetation", "canopy", "fuel", "disturbance", "evc", "evt", "biomass")
    out = []
    for p in products:
        name = p.get("productName", "").lower()
        theme = p.get("theme", "").lower()
        if any(k in name or k in theme for k in keywords):
            out.append(
                {
                    "name": p.get("productName"),
                    "theme": p.get("theme"),
                    "layer": p.get("layerName"),
                    "acronym": p.get("acronym"),
                    "version": p.get("version"),
                    "tag": "E",
                    "source": "USFS / DOI LANDFIRE 30 m Products",
                }
            )
    return out
