import numpy as np
import pandas as pd
import pytest

from fieldwitness.neighbours import table
from fieldwitness.story.smooth import load_story


def _series(year=2020, drop=False):
    d = pd.date_range(f"{year}-03-01", f"{year}-11-15", freq="5D")
    x = np.arange(len(d))
    v = 0.2 + 0.6 * np.exp(-(((x - 20) / 10.0) ** 2))
    if drop:
        v = np.where(x > 30, v * 0.5, v)
    return d.to_numpy(), v


def test_outcomes_known_curve():
    cfg = load_story()
    d, v = _series()
    o = table.season_outcomes(d, v, 2020, (91, 304), cfg)
    assert o is not None
    assert 0.7 < o["peak_ndvi"] <= 0.85
    assert 0 < o["cover_days"] <= o["season_length"] <= 214
    assert o["canopy_drop"] > 0.3  # NDVI falls from the peak back to ~0.2


def test_sparse_series_returns_none():
    cfg = load_story()
    d, v = _series()
    assert table.season_outcomes(d[:5], v[:5], 2020, (91, 304), cfg) is None


def test_contrast_counts():
    df = pd.DataFrame(
        {
            "field_id": ["a", "a", "b"],
            "crop": ["maize"] * 3,
            "prev_crop": ["sorghum", "sorghum", "maize"],
            "canopy_integral": [1.0, 2.0, np.nan],
        }
    )
    c = table.contrast_counts(df)
    assert c.to_dict("records") == [
        {"crop": "maize", "prev_crop": "sorghum", "n": 2, "n_fields": 1}
    ]


@pytest.mark.needs_data("data/neighbours/ks_t14slh_field_season.parquet")
def test_table_tagged_and_unique():
    df = pd.read_parquet("data/neighbours/ks_t14slh_field_season.parquet")
    assert not df.duplicated(["field_id", "year"]).any()
    for col in df.columns:
        assert col in table.TAGS or col in {"field_id", "year", "lon", "lat", "block"}


def test_write_classifier_tags_crop_as_d(tmp_path, monkeypatch):
    monkeypatch.setattr(table, "OUT", tmp_path / "data")
    monkeypatch.setattr(table, "RESULTS", tmp_path / "results")
    df = pd.DataFrame(
        {
            "field_id": ["f1", "f2"],
            "year": [2020, 2020],
            "crop": ["maize", "sunflower"],
            "prev_crop": ["sunflower", "maize"],
            "prev2_crop": ["winter_wheat", "winter_wheat"],
            "crop_source": ["classifier", "classifier"],
            "canopy_integral": [35.0, 28.0],
        }
    )
    summary = table.write(df, region_id="ua_test")
    assert summary["region_id"] == "ua_test"
    assert summary["tags"]["crop"] == "D"
    assert summary["tags"]["prev_crop"] == "D"
    assert summary["tags"]["prev2_crop"] == "D"
    assert (tmp_path / "data" / "ua_test_field_season.parquet").exists()
    assert (tmp_path / "results" / "ua_test_field_season_summary.json").exists()
    assert (tmp_path / "results" / "ua_test_precrop_contrast_counts.csv").exists()
