"""USGS / MRLC National Land Cover Database (NLCD) connector.

Accesses 30 m Land Cover (NLCD 2021 / 2019) via MRLC WCS / WMS services:
WCS Endpoint: https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/wcs
WMS Endpoint: https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/wms

Scale contract: 30 m resolution matches HLS grid (CLAUDE.md Rule 5).
Provenance tag: 'E' (Multi-Resolution Land Characteristics Consortium / USGS).
Licence: Public domain.
"""

from __future__ import annotations

from typing import Any

# Standard Anderson Level II NLCD Land Cover Classes
NLCD_CLASSES: dict[int, str] = {
    11: "Open Water",
    12: "Perennial Ice/Snow",
    21: "Developed, Open Space",
    22: "Developed, Low Intensity",
    23: "Developed, Medium Intensity",
    24: "Developed, High Intensity",
    31: "Barren Land",
    41: "Deciduous Forest",
    42: "Evergreen Forest",
    43: "Mixed Forest",
    52: "Shrub/Scrub",
    71: "Grassland/Herbaceous",
    81: "Pasture/Hay",
    82: "Cultivated Crops",
    90: "Woody Wetlands",
    95: "Emergent Herbaceous Wetlands",
}


def build_wms_getmap_url(
    bbox: tuple[float, float, float, float],
    width: int = 256,
    height: int = 256,
    year: int = 2021,
) -> str:
    """Generate OGC WMS GetMap URL for NLCD land cover rendering."""
    layer = f"NLCD_{year}_Land_Cover_L48"
    w, s, e, n = bbox
    return (
        f"https://www.mrlc.gov/geoserver/mrlc_display/{layer}/wms?"
        "service=WMS&version=1.3.0&request=GetMap&"
        f"layers={layer}&styles=&"
        f"bbox={s},{w},{n},{e}&"
        "crs=EPSG:4326&"
        f"width={width}&height={height}&"
        "format=image/png&transparent=true"
    )


def is_agricultural_pixel(code: int) -> bool:
    """Check if NLCD code is agricultural land use (81 Pasture, 82 Crops)."""
    return code in (81, 82)


def parse_land_cover_code(code: int) -> dict[str, Any]:
    """Parse integer land cover code into class name and agricultural status."""
    name = NLCD_CLASSES.get(code, "Unknown")
    return {
        "code": code,
        "class_name": name,
        "is_crop": code == 82,
        "is_agricultural": code in (81, 82),
        "tag": "E",
        "source": "USGS NLCD 30 m Land Cover",
    }
