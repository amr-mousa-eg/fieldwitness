"""Field identity, scale flags, point lookup and pilot-field selection (PLAN.md T1.4).

Rules (user decisions 2026-11-04, DECISIONS.md / PLAN.md):
- field_id = SHA-1 hex of the WKB of the geometry in EPSG:4326, coordinates rounded to 6 decimals.
- A field is an annual arable crop parcel on the current year (fieldwitness.data.hcat).
- Interior pixels: HLS 30 m pixel centres >= 15 m inside the field edge
  (fieldwitness.resolve.pixels).
- Scale flag: raised when pixel area > field area / 4 (CLAUDE.md rule 5, config/grading.yaml).
"""

import hashlib
import math

import geopandas as gpd
import numpy as np
import shapely
from rasterio import features
from rasterio.transform import from_origin
from shapely.geometry import Point

from fieldwitness.resolve.pixels import HLS_RES_M, interior_pixel_counts

# Coarse context datasets (CLAUDE.md rule 5): their grid cells are far larger than any field, so
# their scale flags are always raised; they are used as context or forcing only.
COARSE_ALWAYS = ("POWER", "SoilGrids", "SMAP", "GRACE")
SEED = 20261114


def field_id(geom_4326) -> str:
    """SHA-1 hex of the WKB of the EPSG:4326 geometry rounded to 6 decimals."""
    g = shapely.set_precision(geom_4326, 1e-6)
    return hashlib.sha1(shapely.to_wkb(g, output_dimension=2, byte_order=1)).hexdigest()


def scale_flags(area_m2: float, ratio: float = 4.0) -> dict[str, bool]:
    """Scale flags per dataset: True when the dataset's pixel area > field area / ratio."""
    flags = {name: True for name in COARSE_ALWAYS}
    flags["HLS"] = HLS_RES_M**2 > area_m2 / ratio
    return flags


def interior_pixel_counts_raster(geoms, ulx: float, uly: float, buffer_m: float) -> np.ndarray:
    """Independent check of `interior_pixel_counts`: GDAL rasterisation (pixel-centre rule) of each
    inward-buffered polygon on the HLS 30 m grid of the tile."""
    out = np.zeros(len(geoms), dtype=np.int64)
    for k, geom in enumerate(geoms):
        inner = geom.buffer(-buffer_m)
        if inner.is_empty:
            continue
        minx, miny, maxx, maxy = inner.bounds
        c0 = math.floor((minx - ulx) / HLS_RES_M)
        r0 = math.floor((uly - maxy) / HLS_RES_M)
        c1 = math.ceil((maxx - ulx) / HLS_RES_M)
        r1 = math.ceil((uly - miny) / HLS_RES_M)
        transform = from_origin(ulx + c0 * HLS_RES_M, uly - r0 * HLS_RES_M, HLS_RES_M, HLS_RES_M)
        mask = features.rasterize(
            [(inner, 1)], out_shape=(r1 - r0, c1 - c0), transform=transform, all_touched=False
        )
        out[k] = int(mask.sum())
    return out


def resolve_point(lon: float, lat: float, fields: gpd.GeoDataFrame) -> gpd.GeoSeries | None:
    """Return the field polygon containing (lon, lat), or None ("no field")."""
    pt = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(fields.crs).iloc[0]
    hits = fields[fields.geometry.contains(pt)]
    return None if hits.empty else hits.iloc[0]


def block_ids(geoms_utm, ulx: float, uly: float, block_m: float = 10_000) -> list[str]:
    """10 km block of each field's representative point on the tile grid (for blocked splits)."""
    pts = shapely.point_on_surface(np.asarray(list(geoms_utm)))
    xs, ys = shapely.get_x(pts), shapely.get_y(pts)
    return [
        f"c{int((x - ulx) // block_m):02d}r{int((uly - y) // block_m):02d}"
        for x, y in zip(xs, ys, strict=True)
    ]


def select_pilot_fields(
    candidates: gpd.GeoDataFrame, quotas: dict[str, int], seed: int = SEED
) -> gpd.GeoDataFrame:
    """Stratified sample: per crop `quotas[crop]` fields, spread over 10 km blocks by taking one
    field per block in a seeded random block order, repeatedly. `candidates` needs columns
    `crop` and `block`. Deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    picked = []
    for crop, n in quotas.items():
        pool = candidates[candidates["crop"] == crop]
        by_block = {
            b: list(rng.permutation(g.index.to_numpy()))
            for b, g in pool.groupby("block", sort=True)
        }
        order = list(rng.permutation(sorted(by_block)))
        chosen: list = []
        while len(chosen) < n and any(by_block.values()):
            for b in order:
                if by_block[b] and len(chosen) < n:
                    chosen.append(by_block[b].pop())
        picked += chosen
    return candidates.loc[picked]


def candidate_fields(
    gdf: gpd.GeoDataFrame, grid: dict, min_px: int = 4, buffer_m: float = 15.0
) -> gpd.GeoDataFrame:
    """Fields whose representative point lies in the tile and that have >= `min_px` interior
    pixels. Adds field_id, area_m2, interior_px, block and the HLS scale flag."""
    utm = gdf.to_crs(grid["epsg"])
    tile = shapely.box(
        grid["ulx"], grid["uly"] - grid["size_m"], grid["ulx"] + grid["size_m"], grid["uly"]
    )
    utm = utm[shapely.within(shapely.point_on_surface(utm.geometry.values), tile)].copy()
    utm["interior_px"] = interior_pixel_counts(
        list(utm.geometry), grid["ulx"], grid["uly"], buffer_m=buffer_m
    )
    utm = utm[utm["interior_px"] >= min_px].copy()
    utm["area_m2"] = utm.geometry.area
    utm["block"] = block_ids(utm.geometry, grid["ulx"], grid["uly"])
    wgs = utm.to_crs("EPSG:4326")
    utm["field_id"] = [field_id(g) for g in wgs.geometry]
    utm["hls_scale_flag"] = [scale_flags(a)["HLS"] for a in utm["area_m2"]]
    return utm


def quotas_ok(selected: gpd.GeoDataFrame, quotas: dict[str, int]) -> bool:
    """True if the selection has exactly the requested number of fields per crop."""
    counts = selected["crop"].value_counts()
    return all(int(counts.get(c, 0)) == n for c, n in quotas.items())
