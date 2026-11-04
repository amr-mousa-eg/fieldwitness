import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from fieldwitness.data.soilgrids import PROPERTIES, field_medians


def _tif(path, arr):
    t = from_origin(0.0, 1.0, 0.25, 0.25)  # 4 x 4 cells of 0.25 degree, top-left (0, 1)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="int16",
        crs="EPSG:4326",
        transform=t,
    ) as dst:
        dst.write(arr.astype("int16"), 1)


def test_median_over_cells_inside_and_zero_is_missing(tmp_path):
    arr = np.array([[100, 200, 0, 0], [300, 400, 0, 0], [0, 0, 0, 0], [0, 0, 0, 999]])
    f = tmp_path / "x.tif"
    _tif(f, arr)
    fields = gpd.GeoDataFrame(
        geometry=[box(0, 0.5, 0.5, 1.0), box(0.5, 0.5, 1.0, 1.0)], crs="EPSG:4326"
    )
    (m1, n1), (m2, n2) = field_medians(f, fields)
    assert (m1, n1) == (250.0, 4)  # cells 100, 200, 300, 400
    assert (m2, n2) == (None, 0)  # only zeros -> missing


def test_representative_point_fallback_for_small_field(tmp_path):
    arr = np.full((4, 4), 123)
    f = tmp_path / "y.tif"
    _tif(f, arr)
    tiny = gpd.GeoDataFrame(geometry=[box(0.01, 0.01, 0.05, 0.05)], crs="EPSG:4326")
    assert field_medians(f, tiny) == [(123.0, 1)]


def test_conversion_factors_match_isric_table():
    assert PROPERTIES["bdod"] == ("cg/cm3", 100, "kg/dm3")
    assert PROPERTIES["soc"] == ("dg/kg", 10, "g/kg")
    assert all(PROPERTIES[p] == ("g/kg", 10, "%") for p in ("clay", "sand", "silt"))


def test_zero_in_a_quantile_is_kept_when_the_mean_has_data(tmp_path):
    q05 = np.array([[0, 0, 5, 5]] * 4)  # genuine zeros in a lower quantile
    mean = np.array([[10, 10, 0, 0]] * 4)  # right half is no-data (mean = 0)
    _tif(tmp_path / "q.tif", q05)
    _tif(tmp_path / "m.tif", mean)
    left = gpd.GeoDataFrame(geometry=[box(0, 0, 0.5, 1.0)], crs="EPSG:4326")
    right = gpd.GeoDataFrame(geometry=[box(0.5, 0, 1.0, 1.0)], crs="EPSG:4326")
    assert field_medians(tmp_path / "q.tif", left, nodata_from=tmp_path / "m.tif") == [(0.0, 8)]
    assert field_medians(tmp_path / "q.tif", right, nodata_from=tmp_path / "m.tif") == [(None, 0)]
