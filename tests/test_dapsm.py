"""Unit tests for Experiment 1 (DAPSM): distance, matching, w-selection rule."""

import numpy as np
import pandas as pd
import pytest

from fieldwitness.neighbours import dapsm


def test_haversine_one_degree_latitude():
    # 1 degree of latitude on a sphere of radius R is R * pi / 180 km.
    d = dapsm.haversine_km(np.array([38.0, 39.0]), np.array([-101.0, -101.0]))
    assert d[0, 1] == pytest.approx(dapsm.EARTH_RADIUS_KM * np.pi / 180, rel=1e-12)
    assert d[0, 0] == 0.0
    assert np.allclose(d, d.T)


def test_haversine_longitude_shrinks_with_cos_lat():
    # Short east-west hop at 60 N is about half of the same hop on the equator.
    eq = dapsm.haversine_km(np.array([0.0, 0.0]), np.array([0.0, 0.01]))[0, 1]
    n60 = dapsm.haversine_km(np.array([60.0, 60.0]), np.array([0.0, 0.01]))[0, 1]
    assert n60 / eq == pytest.approx(0.5, rel=1e-4)


def test_centroids_square_field():
    import shapely

    sq = shapely.box(-101.01, 38.0, -101.0, 38.01)
    pilot = pd.DataFrame({"field_id": ["a"], "geometry": [shapely.to_wkb(sq)]})
    c = dapsm.centroids(pilot)
    assert c.loc[0, "lon"] == pytest.approx(-101.005, abs=1e-5)
    assert c.loc[0, "lat"] == pytest.approx(38.005, abs=1e-5)


def _toy():
    # rows 0,1 treated; 2,3,4 reference. Fields: 0->A, 1->B, 2->A, 3->C, 4->D
    ps = np.array([0.50, 0.20, 0.50, 0.21, 0.90])
    field = np.array(["A", "B", "A", "C", "D"])
    # scaled distance between rows (via their fields)
    dist = np.array(
        [
            [0.0, 0.5, 0.0, 0.9, 0.1],
            [0.5, 0.0, 0.5, 0.8, 0.2],
            [0.0, 0.5, 0.0, 0.9, 0.1],
            [0.9, 0.8, 0.9, 0.0, 0.7],
            [0.1, 0.2, 0.1, 0.7, 0.0],
        ]
    )
    treated = np.array([True, True, False, False, False])
    return ps, dist, treated, field


def test_match_w1_is_pure_propensity_and_skips_same_field():
    ps, dist, treated, field = _toy()
    m = dapsm.match(ps, dist, treated, field, w=1.0)
    # row 0 (PS 0.50) would match row 2 (PS 0.50) but it is the same field A -> next best
    # by PS among rows 3 (0.21) and 4 (0.90): |0.29| < |0.40| -> row 3.
    assert m[0] == 3
    assert m[1] == 3  # PS 0.20 -> 0.21
    assert (m[2:] == -1).all()


def test_match_w0_is_pure_distance():
    ps, dist, treated, field = _toy()
    m = dapsm.match(ps, dist, treated, field, w=0.0)
    assert m[0] == 4  # closest other-field reference (0.1)
    assert m[1] == 4  # 0.2 < 0.5 < 0.8


def test_match_tie_goes_to_lowest_index():
    ps = np.array([0.5, 0.4, 0.6])
    dist = np.zeros((3, 3))
    m = dapsm.match(ps, dist, np.array([True, False, False]), np.array(["a", "b", "c"]), 1.0)
    assert m[0] == 1


def test_match_weights_and_smd():
    treated = np.array([True, True, False, False, False])
    m = np.array([3, 3, -1, -1, -1])
    w = dapsm.match_weights(m, treated)
    assert w.tolist() == [1, 1, 0, 2, 0]
    x = pd.DataFrame({"a": [1.0, 3.0, 0.0, 2.0, 10.0]})
    smd = dapsm.smd_per_covariate(x, treated, w)
    # treated mean 2, matched reference mean 2 -> SMD 0
    assert smd["a"] == pytest.approx(0.0)


def test_choose_w_smallest_median_ties_to_larger_w():
    grid = pd.DataFrame(
        {
            "w": [0.0, 0.0, 0.5, 0.5, 1.0, 1.0],
            "smd_max": [0.4, 0.6, 0.2, 0.4, 0.1, 0.5],
        }
    )
    # medians: 0.0 -> 0.5, 0.5 -> 0.3, 1.0 -> 0.3 (tie) -> larger w
    assert dapsm.choose_w(grid) == 1.0
    grid.loc[grid["w"] == 1.0, "smd_max"] = [0.3, 0.9]
    assert dapsm.choose_w(grid) == 0.5


def test_matched_effect_ci_and_status():
    y = np.array([5.0, 5.0, 1.0, 1.0])
    treated = np.array([True, True, False, False])
    m = np.array([2, 3, -1, -1])
    r = dapsm.matched_effect(y, m, treated, np.array(["b1", "b2", "b1", "b2"]), n_boot=200)
    assert r["effect"] == 4.0 and r["n_pairs"] == 2
    assert r["status"] == "fail"  # CI [4, 4] excludes 0


def test_wilson_interval():
    lo, hi = dapsm.wilson(0, 32)
    assert lo == pytest.approx(0.0, abs=1e-12) and 0.10 < hi < 0.11
    lo, hi = dapsm.wilson(8, 32)
    assert lo < 0.25 < hi
