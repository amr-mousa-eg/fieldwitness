"""Tests for NASA and Partner Resource Connectors.

Verifies schema compliance, scale-contract enforcement (Rule 5),
provenance tagging ('O', 'D', 'E'), and temporal as-of guarding (Rule 6).
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from fieldwitness.data.ag_data_commons import search_ag_data_commons
from fieldwitness.data.asof import as_of
from fieldwitness.data.cocorahs import parse_cocorahs_csv, read_cocorahs
from fieldwitness.data.cropscape import parse_cdl_value_response
from fieldwitness.data.ecostress import (
    build_ecostress_task,
    parse_overpasses_dataframe,
    read_ecostress_overpasses,
)
from fieldwitness.data.era5 import parse_era5_payload, read_era5
from fieldwitness.data.gaez import list_gaez_services
from fieldwitness.data.gpm_imerg import (
    calculate_rain_anomaly,
    parse_imerg_daily_dataframe,
    read_imerg,
)
from fieldwitness.data.landfire import filter_vegetation_products
from fieldwitness.data.ldas import ldas_metadata
from fieldwitness.data.naip import naip_export_image_url
from fieldwitness.data.nlcd import (
    build_wms_getmap_url,
    is_agricultural_pixel,
    parse_land_cover_code,
)
from fieldwitness.data.nwis import (
    FT_TO_M,
    parse_groundwater_dataframe,
    read_groundwater,
)
from fieldwitness.data.prism import parse_prism_daily_records, prism_url, read_prism
from fieldwitness.data.quickstats import fetch_county_crop_acres
from fieldwitness.data.statsgo import statsgo_point_sql, statsgo_profile


# =====================================================================
# 1. GPM IMERG
# =====================================================================
def test_imerg_parser_and_asof():
    records = [
        {"date": "2023-05-01", "rain_mm": 12.4},
        {"date": "2023-05-02", "rain_mm": 0.0},
        {"date": "2023-05-03", "rain_mm": 5.8},
    ]
    df = parse_imerg_daily_dataframe(records)
    assert len(df) == 3
    assert set(df.columns) == {"date", "rain_mm", "scale_flag", "tag", "source"}
    assert df["scale_flag"].all()
    assert (df["tag"] == "O").all()

    # asof filtering
    with as_of(dt.date(2023, 5, 2)):
        filtered = read_imerg("test_region", table=df)
        assert len(filtered) == 2
        assert max(filtered["date"]) == dt.date(2023, 5, 2)

    # rain anomaly calculation
    daily_records = [{"date": f"2020-05-{d:02d}", "rain_mm": 2.0} for d in range(1, 31)] + [
        {"date": f"2023-05-{d:02d}", "rain_mm": 4.0} for d in range(1, 31)
    ]
    daily_df = parse_imerg_daily_dataframe(daily_records)
    anomaly_df = calculate_rain_anomaly(daily_df, baseline_years=(2020, 2020))
    assert not anomaly_df.empty
    assert "anomaly_mm" in anomaly_df.columns
    assert anomaly_df.loc[anomaly_df["year"] == 2023, "anomaly_mm"].iloc[0] == pytest.approx(60.0)


# =====================================================================
# 2. ECOSTRESS
# =====================================================================
def test_ecostress_task_and_overpasses():
    coords = [
        [-101.2, 38.2],
        [-100.8, 38.2],
        [-100.8, 38.6],
        [-101.2, 38.6],
        [-101.2, 38.2],
    ]
    geojson = {"type": "Polygon", "coordinates": [coords]}
    task = build_ecostress_task(
        "test_task",
        geojson,
        "2023-06-01",
        "2023-07-01",
    )
    assert task["task_name"] == "test_task"
    assert len(task["params"]["layers"]) == 2
    assert task["params"]["layers"][0]["product"] == "ECO_L3T_JET.003"

    mock_entries = [
        {"field_id": "F1", "date": "2023-06-15", "eta_mm": 4.2},
        {"field_id": "F1", "date": "2023-06-25", "eta_mm": 3.8},
    ]
    df = parse_overpasses_dataframe(mock_entries)
    assert len(df) == 2
    assert "date" in df.columns
    assert "field_id" in df.columns
    assert "eta_mm" in df.columns
    assert (df["tag"] == "D").all()

    # asof guarding
    with as_of(dt.date(2023, 6, 20)):
        filtered = read_ecostress_overpasses("test_region", table=df)
        assert len(filtered) == 1
        assert filtered["date"].iloc[0] == dt.date(2023, 6, 15)


# =====================================================================
# 3. USGS NWIS
# =====================================================================
def test_nwis_groundwater():
    records = [
        {
            "site_id": "381500100500001",
            "site_name": "Test Well 1",
            "lat": 38.15,
            "lon": -100.50,
            "date": "2023-04-10",
            "depth_to_water_ft": 45.50,
            "depth_to_water_m": round(45.50 * FT_TO_M, 2),
        },
        {
            "site_id": "381500100500001",
            "site_name": "Test Well 1",
            "lat": 38.15,
            "lon": -100.50,
            "date": "2023-05-15",
            "depth_to_water_ft": 46.20,
            "depth_to_water_m": round(46.20 * FT_TO_M, 2),
        },
    ]
    df = parse_groundwater_dataframe(records)
    assert len(df) == 2
    assert "depth_to_water_m" in df.columns
    assert df["depth_to_water_m"].iloc[0] == pytest.approx(45.50 * FT_TO_M, rel=1e-2)
    assert (df["tag"] == "E").all()

    # asof guarding
    with as_of(dt.date(2023, 5, 1)):
        filtered = read_groundwater("381500100500001", table=df)
        assert len(filtered) == 1
        assert filtered["date"].iloc[0] == dt.date(2023, 4, 10)


# =====================================================================
# 4. PRISM Climate Data
# =====================================================================
def test_prism_climate():
    url = prism_url("ppt", dt.date(2023, 7, 4), res_km=4)
    assert "services.nacse.org/prism/data/get/us/4km/ppt/20230704" in url

    records = [
        {"date": "2023-06-01", "ppt_mm": 5.2, "tmean_c": 21.0, "tmin_c": 14.0, "tmax_c": 28.0},
        {"date": "2023-06-02", "ppt_mm": 0.0, "tmean_c": 22.5, "tmin_c": 15.0, "tmax_c": 30.0},
    ]
    df = parse_prism_daily_records(records)
    assert len(df) == 2
    assert "ppt_mm" in df.columns
    assert "tmean_c" in df.columns
    assert df["scale_flag"].all()
    assert (df["tag"] == "E").all()

    # asof guarding
    with as_of(dt.date(2023, 6, 1)):
        filtered = read_prism("ks_t14slh", table=df)
        assert len(filtered) == 1
        assert filtered["date"].iloc[0] == dt.date(2023, 6, 1)


# =====================================================================
# 5. ERA5 / ERA5-Land (Open-Meteo)
# =====================================================================
def test_era5_meteorology():
    payload = {
        "daily": {
            "time": ["2023-05-01", "2023-05-02"],
            "temperature_2m_max": [25.4, 27.1],
            "temperature_2m_min": [11.2, 12.8],
            "precipitation_sum": [0.0, 3.4],
            "et0_fao_evapotranspiration": [4.5, 4.1],
        }
    }
    df = parse_era5_payload(payload)
    assert len(df) == 2
    assert "tmax_c" in df.columns
    assert "eto_mm" in df.columns
    assert df["scale_flag"].all()
    assert (df["tag"] == "E").all()

    # asof guarding
    with as_of(dt.date(2023, 5, 1)):
        filtered = read_era5("ks_t14slh", table=df)
        assert len(filtered) == 1
        assert filtered["date"].iloc[0] == dt.date(2023, 5, 1)


# =====================================================================
# 6. USDA CropScape CDL
# =====================================================================
def test_cropscape_cdl():
    xml_resp = """<GetCDLValueResponse xmlns="http://tempuri.org/">
        <return>1, Corn</return>
    </GetCDLValueResponse>"""
    val = parse_cdl_value_response(xml_resp)
    assert val["category"] == 1
    assert val["category_name"] == "Corn"
    assert val["crop"] == "maize"
    assert val["tag"] == "E"

    # Test unknown/fallback
    fallback = parse_cdl_value_response("<return>Error</return>")
    assert fallback["category"] is None
    assert fallback["category_name"] == "unknown"


# =====================================================================
# 7. USDA STATSGO2
# =====================================================================
def test_statsgo_soils():
    sql = statsgo_point_sql(-101.0, 38.0)
    assert "areasymbol = 'US'" in sql
    assert "point(-101.000000 38.000000)" in sql

    mock_sda_rows = [
        {
            "mukey": "667001",
            "muname": "Richfield-Ulysses complex",
            "cokey": "101",
            "compname": "Richfield",
            "comppct_r": 60.0,
            "majcompflag": "Yes",
            "hzdept_r": 0.0,
            "hzdepb_r": 150.0,
            "awc_r": 0.20,
            "claytotal_r": 28.0,
            "sandtotal_r": 25.0,
        },
        {
            "mukey": "667001",
            "muname": "Richfield-Ulysses complex",
            "cokey": "102",
            "compname": "Ulysses",
            "comppct_r": 30.0,
            "majcompflag": "No",
            "hzdept_r": 0.0,
            "hzdepb_r": 150.0,
            "awc_r": 0.18,
            "claytotal_r": 22.0,
            "sandtotal_r": 30.0,
        },
    ]
    prof = statsgo_profile(mock_sda_rows, zr_cm=135.0)
    assert prof["scale_flag"] is True
    assert prof["tag"] == "E"
    assert "source" in prof


# =====================================================================
# 8. USGS NLCD
# =====================================================================
def test_nlcd_land_cover():
    assert is_agricultural_pixel(81) is True  # Pasture/Hay
    assert is_agricultural_pixel(82) is True  # Cultivated Crops
    assert is_agricultural_pixel(11) is False  # Open Water
    assert is_agricultural_pixel(21) is False  # Developed

    info = parse_land_cover_code(82)
    assert info["class_name"] == "Cultivated Crops"
    assert info["is_agricultural"] is True
    assert info["is_crop"] is True
    assert info["tag"] == "E"

    url = build_wms_getmap_url((-101.0, 38.0, -100.9, 38.1), 256, 256)
    assert "NLCD_2021_Land_Cover_L48" in url
    assert "GetMap" in url


# =====================================================================
# 9. USDA NAIP
# =====================================================================
def test_naip_imagery():
    url = naip_export_image_url((-101.0, 38.0, -100.9, 38.1), size=(512, 512))
    assert "exportImage" in url
    assert "bbox=-101.000000,38.000000,-100.900000,38.100000" in url
    assert "size=512,512" in url


# =====================================================================
# 10. USFS LANDFIRE
# =====================================================================
def test_landfire_catalog():
    mock_catalog = [
        {"productName": "Vegetation Type", "theme": "Vegetation", "product_code": "LF_EVT"},
        {"productName": "Fire Fuel Model 40", "theme": "Fuel", "product_code": "LF_FBFM40"},
        {"productName": "Biophysical Settings", "theme": "Vegetation Dynamics", "code": "LF_BPS"},
    ]
    veg = filter_vegetation_products(mock_catalog)
    assert len(veg) == 3
    names = [p["name"] for p in veg]
    assert "Vegetation Type" in names
    assert "Fire Fuel Model 40" in names
    assert "Biophysical Settings" in names


# =====================================================================
# 11. USDA Ag Data Commons
# =====================================================================
def test_ag_data_commons():
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"id": 1001, "title": "Crop Rotation Experiment Data", "doi": "10.15482/USDA.1001"}
    ]
    with patch("requests.post", return_value=mock_resp):
        results = search_ag_data_commons("crop rotation", page_size=5)
        assert len(results) == 1
        assert results[0]["id"] == 1001
        assert "Crop Rotation" in results[0]["title"]
        assert results[0]["tag"] == "E"


# =====================================================================
# 12. NASA LDAS
# =====================================================================
def test_ldas_metadata():
    nldas = ldas_metadata("NLDAS-2")
    assert nldas["resolution_km"] == 12.5
    assert nldas["scale_flag"] is True
    assert nldas["tag"] == "D"

    gldas = ldas_metadata("GLDAS-2")
    assert gldas["resolution_km"] == 25.0
    assert gldas["scale_flag"] is True
    assert gldas["tag"] == "D"


# =====================================================================
# 13. FAO GAEZ
# =====================================================================
def test_gaez_services():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"services": ["GAEZ_Suitability", "GAEZ_AgroClimatic"]}
    with patch("requests.get", return_value=mock_resp):
        services = list_gaez_services()
        assert "GAEZ_Suitability" in services


# =====================================================================
# 14. CoCoRaHS
# =====================================================================
def test_cocorahs_gauge():
    raw_csv = (
        "StationNumber,StationName,Date,TotalPrecipAmt\n"
        "KS-FO-1,Dodge City 1.2 W,2023-05-01,0.50\n"
        "KS-FO-1,Dodge City 1.2 W,2023-05-02,0.00\n"
        "KS-FO-1,Dodge City 1.2 W,2023-05-03,T\n"
    )
    df = parse_cocorahs_csv(raw_csv)
    assert len(df) == 3
    # 0.50 inches = 12.7 mm
    r1 = df.loc[df["date"] == dt.date(2023, 5, 1), "rain_mm"].iloc[0]
    assert r1 == pytest.approx(12.7, rel=1e-2)
    # 'T' (trace) should be 0.05 mm
    assert df.loc[df["date"] == dt.date(2023, 5, 3), "rain_mm"].iloc[0] == 0.05
    assert (df["tag"] == "E").all()

    # asof guarding
    with as_of(dt.date(2023, 5, 2)):
        filtered = read_cocorahs("KS-FO-1", table=df)
        assert len(filtered) == 2
        assert max(filtered["date"]) == dt.date(2023, 5, 2)


# =====================================================================
# 15. USDA NASS QuickStats
# =====================================================================
def test_quickstats_harvested_acres():
    # Without API key, returns []
    assert fetch_county_crop_acres("KS", "Ford", 2023, api_key=None) == []

    # With mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [
            {
                "commodity_desc": "CORN",
                "year": "2023",
                "county_name": "FORD",
                "state_alpha": "KS",
                "Value": "115,000",
            }
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        res = fetch_county_crop_acres("KS", "Ford", 2023, api_key="dummy_key")
        assert len(res) == 1
        assert res[0]["acres"] == 115000.0
        assert res[0]["scale_flag"] is True
        assert res[0]["tag"] == "E"
