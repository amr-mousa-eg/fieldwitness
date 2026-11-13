"""Unit tests for the open Sentinel-2 L2A COG HTTP Range reader (`fieldwitness.data.s2_cog`)."""

import datetime as dt
import struct
import zlib

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely

from fieldwitness.data import hls_qa, s2_cog
from fieldwitness.data.asof import as_of


def _make_synthetic_tiff(
    arr: np.ndarray, bps: int = 16, compression: int = 8, predictor: int = 2
) -> bytes:
    """Build a minimal valid single-IFD Classic TIFF COG in memory for unit tests."""
    h, w = arr.shape
    raw_arr = arr.astype("<u2" if bps == 16 else "<u1").copy()
    if predictor == 2:
        diff = raw_arr.copy()
        diff[:, 1:] = raw_arr[:, 1:] - raw_arr[:, :-1]
        raw_bytes = diff.tobytes()
    else:
        raw_bytes = raw_arr.tobytes()
    tile_payload = zlib.compress(raw_bytes) if compression == 8 else raw_bytes

    # 8-byte header -> IFD at offset 8
    # 9 tags: 256, 257, 258, 259, 317, 322, 323, 324, 325
    n_tags = 9
    ifd_off = 8
    tile_off = ifd_off + 2 + n_tags * 12 + 4
    entries = [
        (256, 4, 1, w),
        (257, 4, 1, h),
        (258, 3, 1, bps),
        (259, 3, 1, compression),
        (317, 3, 1, predictor),
        (322, 4, 1, w),
        (323, 4, 1, h),
        (324, 4, 1, tile_off),
        (325, 4, 1, len(tile_payload)),
    ]
    buf = bytearray(b"II" + struct.pack("<HI", 42, ifd_off))
    buf.extend(struct.pack("<H", n_tags))
    for tag, typ, cnt, val in entries:
        buf.extend(struct.pack("<HHII", tag, typ, cnt, val))
    buf.extend(struct.pack("<I", 0))
    buf.extend(tile_payload)
    return bytes(buf)


def test_parse_cog_ifds_and_decode_predictor2_uint16_and_uint8():
    u16 = np.array([[1000, 1250, 900, 3000], [500, 400, 100, 65000]], dtype=np.uint16)
    tiff16 = _make_synthetic_tiff(u16, bps=16, compression=8, predictor=2)
    endian, ifds = s2_cog.parse_cog_ifds(tiff16)
    assert endian == "<"
    assert len(ifds) == 1
    ifd = ifds[0]
    raw_tile = tiff16[ifd.tile_offsets[0] : ifd.tile_offsets[0] + ifd.tile_byte_counts[0]]
    decoded = s2_cog.decode_tiff_tile(
        raw_tile,
        ifd.tile_width,
        ifd.tile_height,
        ifd.bits_per_sample,
        ifd.compression,
        ifd.predictor,
        endian,
    )
    assert np.array_equal(decoded, u16)

    u8 = np.array([[4, 4, 5, 9], [3, 4, 5, 8]], dtype=np.uint8)
    tiff8 = _make_synthetic_tiff(u8, bps=8, compression=8, predictor=2)
    endian8, ifds8 = s2_cog.parse_cog_ifds(tiff8)
    ifd8 = ifds8[0]
    raw_tile8 = tiff8[ifd8.tile_offsets[0] : ifd8.tile_offsets[0] + ifd8.tile_byte_counts[0]]
    dec8 = s2_cog.decode_tiff_tile(
        raw_tile8,
        ifd8.tile_width,
        ifd8.tile_height,
        ifd8.bits_per_sample,
        ifd8.compression,
        ifd8.predictor,
        endian8,
    )
    assert np.array_equal(dec8, u8)


def test_select_balanced_scenes_deduplicates_dates():
    feats = [
        {
            "id": "sc1",
            "properties": {"datetime": "2021-06-10T09:00:00Z", "eo:cloud_cover": 25.0},
            "assets": {"red": {}, "nir": {}, "scl": {}},
        },
        {
            "id": "sc2",
            "properties": {"datetime": "2021-06-10T09:05:00Z", "eo:cloud_cover": 5.0},
            "assets": {"red": {}, "nir": {}, "scl": {}},
        },
        {
            "id": "sc3",
            "properties": {"datetime": "2021-06-15T09:00:00Z", "eo:cloud_cover": 10.0},
            "assets": {"red": {}, "nir": {}, "scl": {}},
        },
        {
            "id": "sc4",
            "properties": {"datetime": "2021-06-20T09:00:00Z", "eo:cloud_cover": 30.0},
            "assets": {"red": {}, "nir": {}, "scl": {}},
        },
    ]
    picked = s2_cog.select_balanced_scenes(feats, max_per_month=2, max_total=10)
    ids = [p["id"] for p in picked]
    assert ids == ["sc2", "sc3"]


def test_extract_scene_applies_offset_scl_mask_and_asof(monkeypatch):
    # Test Collection 1 baseline 05.00 offset=-0.1 and SCL mask {4, 5}
    red_arr = np.full((512, 512), 2000, dtype=np.uint16)  # 2000 * 0.0001 - 0.1 = 0.10
    nir_arr = np.full((512, 512), 6000, dtype=np.uint16)  # 6000 * 0.0001 - 0.1 = 0.50
    scl_arr = np.full((512, 512), 4, dtype=np.uint8)
    scl_arr[0, 0] = 9  # cloud high prob -> must be excluded

    red_arr[0, 0] = 9000  # would distort if not masked by SCL=9

    def fake_fetch(url, target_dim, tx, ty, session=None, timeout=30):
        if "B04" in url:
            return red_arr, 100
        if "B08" in url:
            return nir_arr, 100
        return scl_arr, 50

    monkeypatch.setattr(s2_cog, "fetch_cog_tile", fake_fetch)

    grid = {"epsg": "EPSG:32636", "ulx": 400000.0, "uly": 5400000.0, "size_m": 109800.0}
    poly = shapely.box(400000.0, 5399700.0, 400300.0, 5400000.0)
    pilot = gpd.GeoDataFrame({"field_id": ["f_ua_1"], "geometry": [poly]}, crs="EPSG:32636").to_crs(
        "EPSG:4326"
    )
    px_df = s2_cog.sample_interior_pixels_20m(pilot, grid)
    assert len(px_df) > 0

    scene = {
        "id": "S2A_36UVU_20210701_0_L2A",
        "properties": {"datetime": "2021-07-01T09:00:00Z"},
        "assets": {
            "red": {
                "href": "https://example.com/B04.tif",
                "raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}],
            },
            "nir": {
                "href": "https://example.com/B08.tif",
                "raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}],
            },
            "scl": {"href": "https://example.com/SCL.tif", "raster:bands": [{"nodata": 0}]},
        },
    }
    df1, nbytes = s2_cog.extract_scene_table(scene, px_df)
    assert nbytes == 250
    assert df1.loc[0, "field_id"] == "f_ua_1"
    # NDVI = (0.5 - 0.1) / (0.5 + 0.1) = 0.6667
    assert df1.loc[0, "ndvi"] == pytest.approx(2.0 / 3.0, abs=1e-4)
    assert df1.loc[0, "source_tag"] == "O"

    # Element84 harmonised COGs (earthsearch:boa_offset_applied=True) ignore advertised -0.1
    scene_es = {
        **scene,
        "properties": {"datetime": "2021-07-01T09:00:00Z", "earthsearch:boa_offset_applied": True},
    }
    df_es, _ = s2_cog.extract_scene_table(scene_es, px_df)
    # Without double subtraction: red=0.20, nir=0.60 -> NDVI=(0.6-0.2)/(0.6+0.2)=0.5
    assert df_es.loc[0, "ndvi"] == pytest.approx(0.5, abs=1e-4)

    # Verify hls_qa.read respects as_of cutoff with this exact schema
    scene_2022 = {
        **scene,
        "id": "S2A_36UVU_20220701_0_L2A",
        "properties": {"datetime": "2022-07-01T09:00:00Z"},
    }
    df2, _ = s2_cog.extract_scene_table(scene_2022, px_df)
    both = pd.concat([df1, df2], ignore_index=True)
    with as_of(dt.date(2021, 12, 31)):
        clipped = hls_qa.read("ua_test", table=both)
        assert clipped["date"].max().date() <= dt.date(2021, 12, 31)
        assert len(clipped) == 1
