"""Tests for USDA SSURGO TAW data provider."""

from fieldwitness.data.ssurgo_taw import (
    KANSAS_SSURGO_MEDIAN_AWS_MM,
    get_field_taw_base,
    get_field_taw_info,
    load_pilot_ssurgo_table,
    soilgrids_taw_fallback_mm,
)


def test_load_pilot_ssurgo_table():
    table = load_pilot_ssurgo_table()
    assert len(table) >= 198
    # Test known pilot field 7008ff6ba15fc8da1d2ebe4a739699117e7ae646 (Ulysses silt loam)
    fid = "7008ff6ba15fc8da1d2ebe4a739699117e7ae646"
    assert fid in table
    assert table[fid]["muname"].startswith("Ulysses")
    assert round(table[fid]["ssurgo_aws_mm"], 1) == 300.6


def test_get_field_taw_base():
    # Known field
    fid = "7008ff6ba15fc8da1d2ebe4a739699117e7ae646"
    taw = get_field_taw_base(field_id=fid, zr_m=1.35)
    assert round(taw, 1) == 300.6

    # Scaled root zone
    taw_1m = get_field_taw_base(field_id=fid, zr_m=1.0)
    assert round(taw_1m, 1) == round(300.59 * (1.0 / 1.35), 1)

    # Unknown field fallback to High Plains median
    taw_fallback = get_field_taw_base(field_id="unknown_field", zr_m=1.35)
    assert round(taw_fallback, 1) == round(KANSAS_SSURGO_MEDIAN_AWS_MM, 1)


def test_get_field_taw_info_and_soilgrids_fallback():
    taw, tag, src = get_field_taw_info(field_id="7008ff6ba15fc8da1d2ebe4a739699117e7ae646")
    assert round(taw, 1) == 300.6
    assert tag == "E"
    assert "SSURGO" in src

    # Shallow SSURGO field uses SoilGrids 2.0 Saxton & Rawls fallback
    shallow_fid = "189e236596fa05b85f1c19fe582083601b59b353"
    taw_sg, tag_sg, src_sg = get_field_taw_info(field_id=shallow_fid)
    assert tag_sg == "E"
    assert "SoilGrids" in src_sg
    assert 100.0 <= taw_sg <= 350.0
    assert round(soilgrids_taw_fallback_mm(clay_pct=25.0, sand_pct=20.0), 1) > 100.0
