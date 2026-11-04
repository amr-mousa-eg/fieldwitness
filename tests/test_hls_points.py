import geopandas as gpd
from shapely.affinity import rotate
from shapely.geometry import box

from fieldwitness.data.hls_series import PERIODS, chunk_by_field, interior_points
from fieldwitness.resolve.pixels import interior_pixel_counts

GRID = {"epsg": "EPSG:32614", "ulx": 300000.0, "uly": 4300020.0, "size_m": 109800.0}


def _fields():
    geoms = [
        rotate(box(300107, 4299107, 300707, 4299607), 23, origin="centroid"),
        box(305005, 4294715, 305305, 4295015),
        box(310005, 4290015, 310060, 4290060),  # too small: no interior pixel
    ]
    return gpd.GeoDataFrame({"field_id": ["a", "b", "c"]}, geometry=geoms, crs=GRID["epsg"])


def test_uncapped_points_equal_interior_pixel_counts():
    f = _fields()
    pts = interior_points(f, GRID, max_per_field=None)
    counts = interior_pixel_counts(list(f.geometry), GRID["ulx"], GRID["uly"], buffer_m=15)
    for fid, n in zip(f["field_id"], counts, strict=True):
        assert sum(p["category"] == fid for p in pts) == n


def test_cap_and_ids():
    pts = interior_points(_fields(), GRID, max_per_field=12)
    assert sum(p["category"] == "a" for p in pts) == 12
    assert len({p["id"] for p in pts}) == len(pts)
    assert interior_points(_fields(), GRID, 12) == pts  # seeded, deterministic


def test_periods_cover_sep2015_to_2024():
    assert PERIODS[0] == ("2015", "09-01-2015", "12-31-2015")
    assert PERIODS[-1] == ("2024", "01-01-2024", "12-31-2024")
    assert len(PERIODS) == 10


def test_chunks_never_split_a_field_and_respect_the_cap():
    coords = [{"category": f"f{i // 7}", "id": str(i)} for i in range(70)]  # 10 fields x 7 points
    chunks = chunk_by_field(coords, max_coords=20)
    assert all(len(c) <= 20 for c in chunks)
    assert sum(len(c) for c in chunks) == 70
    for c in chunks:
        fields = {p["category"] for p in c}
        assert all(sum(p["category"] == f for p in c) == 7 for f in fields)
