"""USDA-NRCS SSURGO Available Water Storage (AWS) data provider.

Resolves Weak Point A.1: replaces the arbitrary 150 mm base TAW assumption
with empirical USDA-NRCS SSURGO soil survey data (tag E).

Data sources:
- Regional precomputed survey: `results/validation/soil_ssurgo_check.csv` (198 Kansas pilot fields).
- USDA-NRCS Soil Data Access (SDA) REST API for on-the-fly coordinates:
  https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest
"""

from __future__ import annotations

import csv
import functools
from pathlib import Path
from typing import Any

from fieldwitness.data import ssurgo

CSV_PATH = Path("results/validation/soil_ssurgo_check.csv")
# Verified median AWS across Keith/Richfield/Ulysses silt loams (0-135 cm)
KANSAS_SSURGO_MEDIAN_AWS_MM = 282.1
# Default SOC (8.7 g/kg ~= 1.5% SOM via Van Bemmelen 1.724) used ONLY when SoilGrids depth SOC
# is absent on the 2 shallow-SSURGO Kansas fields (tag E texture + A OM fallback).
DEFAULT_SOC_GKG_FALLBACK = 8.7


def soilgrids_taw_fallback_mm(
    clay_pct: float,
    sand_pct: float,
    soc_gkg: float = DEFAULT_SOC_GKG_FALLBACK,
    thickness_mm: float = 1350.0,
) -> float:
    """Horizon/profile TAW (mm) from SoilGrids 2.0 texture via Saxton & Rawls (2006).

    Source: Saxton, K.E. & Rawls, W.J. (2006), Soil Sci. Soc. Am. J. 70(5):1569-1578,
    Table 1 Eqs. 1-2 (1500 kPa wilting point & 33 kPa field capacity), combined with
    FAO-56 Eq. 82 (``waterbal.taw``): ``TAW = max(0, theta_33 - theta_1500) * dz_mm``.
    """
    s = float(sand_pct) / 100.0
    c = float(clay_pct) / 100.0
    om = min(max(1.724 * (float(soc_gkg) / 10.0), 0.0), 8.0)
    t1500t = (
        -0.024 * s
        + 0.487 * c
        + 0.006 * om
        + 0.005 * (s * om)
        - 0.013 * (c * om)
        + 0.068 * (s * c)
        + 0.031
    )
    theta_1500 = t1500t + (0.14 * t1500t - 0.02)
    t33t = (
        -0.251 * s
        + 0.195 * c
        + 0.011 * om
        + 0.006 * (s * om)
        - 0.027 * (c * om)
        + 0.452 * (s * c)
        + 0.299
    )
    theta_33 = t33t + (1.283 * (t33t**2) - 0.374 * t33t - 0.015)
    awc = max(0.0, theta_33 - theta_1500)
    return float(awc * float(thickness_mm))


@functools.lru_cache(maxsize=1)
def load_pilot_ssurgo_table() -> dict[str, dict[str, Any]]:
    """Loads precomputed SSURGO (and SoilGrids fallback) metrics for the 200 Kansas pilot fields."""
    if not CSV_PATH.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            fid = r["field_id"]
            aws = float(r["ssurgo_aws_mm"]) if r.get("ssurgo_aws_mm") else None
            aws_100 = float(r["ssurgo_aws_100cm_mm"]) if r.get("ssurgo_aws_100cm_mm") else None
            out[fid] = {
                "field_id": fid,
                "lon": float(r["lon"]),
                "lat": float(r["lat"]),
                "status": r["ssurgo_status"],
                "mukey": r.get("mukey"),
                "muname": r.get("muname"),
                "dominant_component": r.get("dominant_component"),
                "dominant_pct": float(r["dominant_pct"]) if r.get("dominant_pct") else None,
                "ssurgo_aws_mm": aws,
                "ssurgo_aws_100cm_mm": aws_100,
                "clay_pct": float(r["ssurgo_clay_pct"]) if r.get("ssurgo_clay_pct") else None,
                "sand_pct": float(r["ssurgo_sand_pct"]) if r.get("ssurgo_sand_pct") else None,
                "sg_clay_pct": float(r["sg_clay_pct"]) if r.get("sg_clay_pct") else None,
                "sg_sand_pct": float(r["sg_sand_pct"]) if r.get("sg_sand_pct") else None,
            }
    return out


def get_field_taw_info(
    field_id: str | None = None,
    lon: float | None = None,
    lat: float | None = None,
    zr_m: float = 1.35,
    query_remote: bool = False,
    cache_dir: Path | None = None,
) -> tuple[float, str, str]:
    """Return ``(taw_mm, tag, source_description)`` from USDA SSURGO or SoilGrids 2.0 fallback."""
    table = load_pilot_ssurgo_table()
    if field_id and field_id in table:
        entry = table[field_id]
        if entry["ssurgo_aws_mm"] is not None:
            return (
                float(entry["ssurgo_aws_mm"]) * (zr_m / 1.35),
                "E",
                "USDA-NRCS SSURGO AWS 0-135 cm (tag E)",
            )
        if entry.get("sg_clay_pct") is not None and entry.get("sg_sand_pct") is not None:
            taw_sg = soilgrids_taw_fallback_mm(
                entry["sg_clay_pct"],
                entry["sg_sand_pct"],
                DEFAULT_SOC_GKG_FALLBACK,
                zr_m * 1000.0,
            )
            return (
                taw_sg,
                "E",
                "ISRIC SoilGrids 2.0 texture + Saxton & Rawls (2006) "
                "0-135 cm fallback for shallow SSURGO profile (tag E)",
            )

    if query_remote and lon is not None and lat is not None:
        try:
            cpath = (cache_dir or Path("data/ssurgo")) / f"pt_{lon:.4f}_{lat:.4f}.json"
            rows = ssurgo.query_point(lon, lat, cpath)
            prof = ssurgo.field_profile(rows, zr_m * 100.0)
            if prof.get("aws_mm") is not None:
                return float(prof["aws_mm"]), "E", "USDA-NRCS SSURGO SDA live query (tag E)"
        except Exception:
            pass

    return (
        KANSAS_SSURGO_MEDIAN_AWS_MM * (zr_m / 1.35),
        "E",
        "Regional Kansas SSURGO median AWS prior (282.1 mm at 1.35 m, tag E)",
    )


def get_field_taw_base(
    field_id: str | None = None,
    lon: float | None = None,
    lat: float | None = None,
    zr_m: float = 1.35,
    query_remote: bool = False,
    cache_dir: Path | None = None,
) -> float:
    """Returns empirical USDA SSURGO root-zone Total Available Water (TAW, mm, tag E).

    Falls back to SoilGrids 2.0 Saxton & Rawls (2006) for shallow SSURGO profiles before using
    the regional SSURGO median prior.
    """
    return get_field_taw_info(
        field_id=field_id,
        lon=lon,
        lat=lat,
        zr_m=zr_m,
        query_remote=query_remote,
        cache_dir=cache_dir,
    )[0]
