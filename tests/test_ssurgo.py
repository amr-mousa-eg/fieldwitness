"""Depth weighting and unit conversion for the SSURGO soil check (no network)."""

import pytest

from fieldwitness.data import ssurgo

# Real SDA reply for one Kansas pilot point (2026-11-11, docs/api_notes.md): map unit 2668839,
# Ulysses 99 % + Ness 1 %. NRCS's own muaggatt.aws0100wta for this map unit is 21.44 cm.
PAYLOAD = {
    "Table": [
        list(
            "mukey muname cokey compname comppct_r majcompflag hzdept_r hzdepb_r awc_r "
            "claytotal_r sandtotal_r".split()
        ),
        ["2668839", "Ulysses", "1", "Ulysses", "99", "Yes", "0", "20", "0.22", "26", "20"],
        ["2668839", "Ulysses", "1", "Ulysses", "99", "Yes", "20", "35", "0.21", "29", "16"],
        ["2668839", "Ulysses", "1", "Ulysses", "99", "Yes", "35", "70", "0.21", "29", "16"],
        ["2668839", "Ulysses", "1", "Ulysses", "99", "Yes", "70", "200", "0.22", "26", "22"],
        ["2668839", "Ulysses", "2", "Ness", "1", "No ", "0", "10", "0.16", "42", "6"],
        ["2668839", "Ulysses", "2", "Ness", "1", "No ", "10", "79", "0.14", "46", "3"],
        ["2668839", "Ulysses", "2", "Ness", "1", "No ", "79", "94", "0.19", "38", "4"],
        ["2668839", "Ulysses", "2", "Ness", "1", "No ", "94", "200", "0.19", "33", "4"],
    ]
}


def test_overlap():
    assert ssurgo.overlap_cm(0, 20, 135) == 20
    assert ssurgo.overlap_cm(70, 200, 135) == 65
    assert ssurgo.overlap_cm(150, 200, 135) == 0


def test_unit_conversion_matches_nrcs_aws0100wta():
    # cm/cm x cm = cm of water; x 10 = mm. Component-percent weighting reproduces NRCS 21.44 cm.
    rows = ssurgo.parse(PAYLOAD)
    p = ssurgo.field_profile(rows, zr_cm=100)
    assert p["status"] == "ok"
    assert p["aws_mm"] == pytest.approx(214.4, abs=0.05)
    assert p["dominant"] == "Ulysses"
    assert p["dominant_aws_mm"] == pytest.approx(215.0)  # 10*(.22*20+.21*15+.21*35+.22*30)


def test_depth_weighted_texture():
    rows = [r for r in ssurgo.parse(PAYLOAD) if r["compname"] == "Ulysses"]
    p = ssurgo.component_profile(rows, zr_cm=100)
    assert p["clay_pct"] == pytest.approx((26 * 20 + 29 * 15 + 29 * 35 + 26 * 30) / 100)
    assert p["sand_pct"] == pytest.approx((20 * 20 + 16 * 15 + 16 * 35 + 22 * 30) / 100)


def test_incomplete_or_null_profiles_are_rejected():
    rows = [r for r in ssurgo.parse(PAYLOAD) if r["compname"] == "Ulysses"]
    assert ssurgo.component_profile(rows[:2], zr_cm=100) is None  # covers only 0-35 cm
    rows[1] = {**rows[1], "awc_r": None}
    assert ssurgo.component_profile(rows, zr_cm=100) is None


def test_no_map_unit():
    assert ssurgo.parse({}) == []
    assert ssurgo.field_profile([], zr_cm=135) == {"status": "no map unit"}


def test_point_sql_is_lon_lat():
    assert "point(-101.103500 38.388500)" in ssurgo.point_sql(-101.1035, 38.3885)
