"""USDA National Agriculture Imagery Program (NAIP) connector.

Accesses high-resolution (0.6 m to 1.0 m) aerial orthophotography collected during
agricultural growing seasons across CONUS via The National Map (TNM) ImageServer:
Endpoint: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer

Scale contract: <1 m resolution provides sub-pixel ground verification (CLAUDE.md Rule 5).
Provenance tag: 'E' (USDA Farm Production and Conservation / FSA / USGS).
Licence: Public domain.
"""

from __future__ import annotations

NAIP_IMAGE_SERVER = (
    "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer"
)


def naip_export_image_url(
    bbox: tuple[float, float, float, float],
    size: tuple[int, int] = (512, 512),
    image_format: str = "png",
) -> str:
    """Generate ArcGIS REST exportImage URL for NAIP orthophotography tile.

    Args:
        bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
        size: Width, height in pixels.
        image_format: Output image format ('png', 'jpg').
    """
    w, s, e, n = bbox
    bbox_str = f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}"
    size_str = f"{size[0]},{size[1]}"
    return (
        f"{NAIP_IMAGE_SERVER}/exportImage?"
        f"bbox={bbox_str}&"
        "bboxSR=4326&"
        "imageSR=4326&"
        f"size={size_str}&"
        f"format={image_format}&"
        "f=image"
    )
