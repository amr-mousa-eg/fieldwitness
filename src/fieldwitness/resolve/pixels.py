"""Interior-pixel counts of field polygons on the HLS 30 m grid of an MGRS tile."""

import math

import numpy as np
import shapely

HLS_RES_M = 30.0


def interior_pixel_counts(
    geoms, ulx: float, uly: float, buffer_m: float, res: float = HLS_RES_M
) -> np.ndarray:
    """Count HLS pixel centres strictly inside each polygon after an inward buffer of `buffer_m`.

    Grid: pixel (col i, row j) has its centre at (ulx + res*(i + 0.5), uly - res*(j + 0.5)), with
    the tile origin ULX/ULY from the HLS granule metadata (CMR AdditionalAttributes). Geometries
    must already be in the tile's UTM CRS (metres). PLAN.md T1.4 defines interior pixels with a
    15 m (half-pixel) inward buffer since 2026-11-04 (was 30 m; the census reports both). Points on
    the boundary do not count (shapely.contains_xy).
    """
    out = np.zeros(len(geoms), dtype=np.int64)
    half = res / 2.0
    for k, geom in enumerate(geoms):
        if geom is None or geom.is_empty:
            continue
        inner = geom.buffer(-buffer_m)
        if inner.is_empty:
            continue
        minx, miny, maxx, maxy = inner.bounds
        i0 = math.ceil((minx - ulx - half) / res)
        i1 = math.floor((maxx - ulx - half) / res)
        j0 = math.ceil((uly - maxy - half) / res)
        j1 = math.floor((uly - miny - half) / res)
        if i1 < i0 or j1 < j0:
            continue
        xs = ulx + res * (np.arange(i0, i1 + 1) + 0.5)
        ys = uly - res * (np.arange(j0, j1 + 1) + 0.5)
        gx, gy = np.meshgrid(xs, ys)
        out[k] = int(shapely.contains_xy(inner, gx.ravel(), gy.ravel()).sum())
    return out
