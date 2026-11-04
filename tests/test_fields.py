import geopandas as gpd
import shapely
from shapely.affinity import rotate
from shapely.geometry import Polygon, box

from fieldwitness.resolve.fields import (
    field_id,
    interior_pixel_counts_raster,
    quotas_ok,
    resolve_point,
    scale_flags,
    select_pilot_fields,
)
from fieldwitness.resolve.pixels import interior_pixel_counts

ULX, ULY = 300000.0, 4300020.0  # T14SLH grid origin (CMR)


def test_field_id_is_stable_under_sub_rounding_noise_and_order_free_of_crs_details():
    g = box(-100.9, 38.0, -100.89, 38.01)
    noisy = shapely.affinity.translate(g, 1e-8, -1e-8)
    assert field_id(g) == field_id(noisy)
    assert len(field_id(g)) == 40
    assert field_id(g) != field_id(box(-100.9, 38.0, -100.89, 38.02))


def test_scale_flags():
    assert scale_flags(30 * 30 * 4 + 1)["HLS"] is False  # just larger than 4 pixels
    assert scale_flags(30 * 30 * 3)["HLS"] is True
    assert all(scale_flags(1e9)[k] for k in ("POWER", "SoilGrids", "SMAP", "GRACE"))


def test_vector_and_raster_interior_counts_agree_on_irregular_polygons():
    shapes = [
        rotate(box(ULX + 107, ULY - 913, ULX + 707, ULY - 413), 23, origin="centroid"),
        Polygon(
            [
                (ULX + 2000, ULY - 2000),
                (ULX + 2900, ULY - 2050),
                (ULX + 2600, ULY - 2700),
                (ULX + 2100, ULY - 2500),
            ]
        ),
        box(ULX + 5005, ULY - 5305, ULX + 5305, ULY - 5005),
    ]
    for buf in (15, 30):
        a = interior_pixel_counts(shapes, ULX, ULY, buffer_m=buf)
        b = interior_pixel_counts_raster(shapes, ULX, ULY, buffer_m=buf)
        assert (a == b).all(), (buf, a, b)


def test_resolve_point_returns_polygon_or_none():
    fields = gpd.GeoDataFrame({"fid": [1]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")
    assert resolve_point(0.5, 0.5, fields)["fid"] == 1
    assert resolve_point(2, 2, fields) is None


def test_pilot_selection_is_deterministic_and_respects_quotas():
    rows = [
        {"crop": c, "block": f"b{i % 7}"} for i, c in enumerate(["maize"] * 50 + ["sorghum"] * 30)
    ]
    cand = gpd.GeoDataFrame(rows, geometry=[box(i, 0, i + 1, 1) for i in range(80)])
    q = {"maize": 10, "sorghum": 5}
    a = select_pilot_fields(cand, q)
    b = select_pilot_fields(cand, q)
    assert list(a.index) == list(b.index)
    assert quotas_ok(a, q)
    assert a[a["crop"] == "maize"]["block"].nunique() == 7  # spread over all blocks first
