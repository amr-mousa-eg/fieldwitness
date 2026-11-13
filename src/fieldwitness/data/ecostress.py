"""NASA ECOSTRESS (ECOSystem Spaceborne Thermal Radiometer Experiment on Space Station) connector.

Collections verified in CMR & AppEEARS (docs/api_notes.md):
- ECO_L3T_JET.003 (Concept ID C4057232489-LPCLOUD, 70 m tiled ET PT-JPL, daytime ETa).
- ECO_L3T_JET.002 (Concept ID C2076106409-LPCLOUD, 70 m, full archive 2018-07-10 onwards).

Scale contract: 70 m resolution meets field scale contract (CLAUDE.md Rule 5: interior pixels only).
Provenance tag: 'O' for direct radiometric thermal observations; 'D' for PT-JPL derived ETa.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from fieldwitness.data.asof import cutoff, guard, register

CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION_V003 = "ECO_L3T_JET.003"
CONCEPT_ID_V003 = "C4057232489-LPCLOUD"
CACHE_DIR = Path("data/context/ecostress")

ECOSTRESS_APPEEARS_LAYERS = [
    {"product": "ECO_L3T_JET.003", "layer": "ET_PT_JPL_daily"},
    {"product": "ECO_L3T_JET.003", "layer": "ET_PT_JPL_quality"},
]


def build_ecostress_task(
    name: str,
    geojson: dict[str, Any],
    start_date: str,
    end_date: str,
    version: str = "003",
) -> dict[str, Any]:
    """Build an AppEEARS area task body for ECOSTRESS tiled evapotranspiration."""
    prod = f"ECO_L3T_JET.{version}"
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start_date, "endDate": end_date}],
            "layers": [
                {"product": prod, "layer": "ET_PT_JPL_daily"},
                {"product": prod, "layer": "ET_PT_JPL_quality"},
            ],
            "geo": geojson,
            "output": {"format": {"type": "netcdf4"}, "projection": "native"},
        },
    }


def search_ecostress_overpasses(
    lon: float,
    lat: float,
    start: dt.date,
    end: dt.date,
    version: str = "003",
    page_size: int = 20,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Query CMR for ECOSTRESS overpasses intersecting a field centroid."""
    params = {
        "short_name": "ECO_L3T_JET",
        "version": version,
        "point": f"{lon},{lat}",
        "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
        "page_size": page_size,
    }
    r = (session or requests).get(CMR_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("feed", {}).get("entry", [])


def parse_overpasses_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse list of overpass records into structured evaluation DataFrame.

    Required columns for eo_checks: ['field_id', 'date', 'eta_mm', 'qc_good']
    """
    if not rows:
        return pd.DataFrame(columns=["field_id", "date", "eta_mm", "qc_good", "tag", "source"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    if "qc_good" not in df.columns:
        df["qc_good"] = True
    df["tag"] = "D"
    df["source"] = f"NASA ECOSTRESS ECO_L3T_JET.{version_tag(rows)} (70 m)"
    return df.sort_values(["field_id", "date"]).reset_index(drop=True)


def version_tag(rows: list[dict[str, Any]]) -> str:
    if rows and "version" in rows[0]:
        return str(rows[0]["version"])
    return "003"


@register("ecostress", weather=False)
def read_ecostress_overpasses(
    region_id: str = "ks_t14slh",
    field_id: str | None = None,
    table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Read cached ECOSTRESS overpasses respecting active as_of date."""
    if table is not None:
        df = table.copy()
    else:
        p = CACHE_DIR / f"{region_id}_ecostress.parquet"
        if not p.exists():
            return pd.DataFrame(columns=["field_id", "date", "eta_mm", "qc_good", "tag", "source"])
        df = pd.read_parquet(p)

    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cutoff()
    if c is not None:
        df = df[df["date"] <= c]
    if field_id:
        df = df[df["field_id"] == field_id]

    guard(df["date"], "ecostress", weather=False)
    return df.reset_index(drop=True)
