"""Unit tests for T2.4 WorldCereal / OGH-GHLC10 cross-check (pure local / synthetic arrays)."""

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from fieldwitness.story import worldcereal_check as wc


def test_binary_metrics_exact_scores():
    yt = np.array([True, True, False, False, True, False])
    yp = np.array([True, False, False, True, True, False])
    m = wc._binary_metrics(yt, yp)
    assert m["tp"] == 2
    assert m["fp"] == 1
    assert m["fn"] == 1
    assert m["tn"] == 2
    assert m["accuracy"] == round(4 / 6, 4)
    assert m["precision"] == round(2 / 3, 4)
    assert m["recall"] == round(2 / 3, 4)
    assert m["f1"] == round(2 / 3, 4)


def test_sample_fields_ghlc_and_evaluate_agreement_with_15m_buffer():
    # Two disjoint 400 m x 400 m fields in UTM 36N -> converted to EPSG:4326
    f1 = box(420000, 5320000, 420400, 5320400)
    f2 = box(430000, 5330000, 430400, 5330400)
    pilot = gpd.GeoDataFrame(
        {"field_id": ["f1", "f2"], "block": ["b1", "b2"]},
        geometry=[f1, f2],
        crs="EPSG:32636",
    ).to_crs("EPSG:4326")

    minx, miny, maxx, maxy = pilot.total_bounds
    dlon = 0.00027
    dlat = 0.00027
    lon0 = minx - 5 * dlon
    lat0 = maxy + 5 * dlat
    w = int(np.ceil((maxx - lon0) / dlon)) + 10
    h = int(np.ceil((lat0 - miny) / dlat)) + 10

    arr = np.full((h, w), wc.OTHER_CROP_CLASS, dtype=np.uint8)
    # Paint f1 centroid region with MAIZE_CLASS (3)
    c1 = pilot.iloc[0].geometry.centroid
    ci = int((c1.x - lon0) / dlon)
    ri = int((lat0 - c1.y) / dlat)
    arr[ri - 12 : ri + 12, ci - 12 : ci + 12] = wc.MAIZE_CLASS

    meta = {"year": 2021, "lon0": lon0, "lat0": lat0, "dlon": dlon, "dlat": dlat}
    sampled = wc.sample_fields_ghlc(pilot, arr, meta, buffer_m=15.0)
    assert len(sampled) == 2
    r1 = sampled[sampled["field_id"] == "f1"].iloc[0]
    r2 = sampled[sampled["field_id"] == "f2"].iloc[0]
    assert bool(r1["ghlc_is_maize"]) is True
    assert bool(r2["ghlc_is_maize"]) is False
    assert bool(r2["ghlc_is_cropland"]) is True

    clf = pd.DataFrame(
        {
            "field_id": ["f1", "f2", "f1"],
            "year": [2021, 2021, 2022],
            "crop": ["maize", "winter_wheat", "sunflower"],
            "crop_conf": [0.85, 0.90, 0.70],
        }
    )
    ev = wc.evaluate_agreement(clf, sampled, conf_threshold=0.5, n_boot=50)
    assert ev["n"] == 2
    assert ev["maize_vs_non_maize"]["f1"] == 1.0
    assert ev["non_maize_other_crop_agreement"] == 1.0
    assert len(ev["maize_vs_non_maize"]["f1_ci95"]) == 2
