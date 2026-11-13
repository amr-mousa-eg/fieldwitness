"""USDA Ag Data Commons (National Agricultural Library) search client.

Searches open-access agricultural datasets from USDA Ag Data Commons (soils, crop trials,
tillage practices, long-term agroecological research):
Catalog: https://data.nal.usda.gov / https://agdatacommons.nal.usda.gov
API endpoint: https://api.figshare.com/v2/articles/search (Institution 1146 = USDA NAL)

Provenance tag: 'E' (USDA National Agricultural Library / ARS research datasets).
Licence: Public domain / CC0 / Open Government License.
"""

from __future__ import annotations

from typing import Any

import requests

FIGSHARE_SEARCH_API = "https://api.figshare.com/v2/articles/search"
USDA_NAL_INSTITUTION_ID = 1146


def search_ag_data_commons(
    query: str,
    page: int = 1,
    page_size: int = 10,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Search USDA Ag Data Commons for open research datasets matching query terms."""
    payload = {
        "search_for": query,
        "institution": USDA_NAL_INSTITUTION_ID,
        "page": page,
        "page_size": page_size,
    }
    r = (session or requests).post(FIGSHARE_SEARCH_API, json=payload, timeout=20)
    r.raise_for_status()
    items = r.json()
    records = []
    for it in items:
        records.append(
            {
                "id": it.get("id"),
                "title": it.get("title"),
                "doi": it.get("doi"),
                "url": it.get("url_public_html"),
                "published_date": it.get("published_date"),
                "tag": "E",
                "source": "USDA Ag Data Commons (NAL / ARS)",
            }
        )
    return records
