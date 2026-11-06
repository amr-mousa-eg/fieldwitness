import numpy as np
import pandas as pd

from fieldwitness.story.seasons import detect_seasons


def _synthetic(peaks):
    """NDVI = 0.15 + gaussian bumps at (day index from 2016-01-01, height)."""
    dates = pd.date_range("2016-01-01", "2019-12-31", freq="5D")
    t = np.arange(len(dates)) * 5.0
    y = np.full(len(t), 0.15)
    for c, h in peaks:
        y = y + (h - 0.15) * np.exp(-((t - c) ** 2) / (2 * 40.0**2))
    return pd.Series(dates), pd.Series(y)


def test_two_single_seasons_in_two_harvest_years():
    d, y = _synthetic([(500, 0.8), (960, 0.75)])  # May 2017, Aug 2018
    s = detect_seasons(d, y)
    assert [x.year for x in s] == [2017, 2018]
    assert [x.index for x in s] == [0, 0]
    assert s[0].eos.value > s[0].peak.value > s[0].sos.value
    assert all(x.sos.tag == "D" and x.peak_ndvi.tag == "O" for x in s)
    assert all(x.sos.unit == "day of harvest year" for x in s)


def test_two_seasons_same_harvest_year_get_index():
    d, y = _synthetic([(430, 0.8), (570, 0.7)])  # Mar and Aug 2017
    s = detect_seasons(d, y)
    assert [x.year for x in s] == [2017, 2017]
    assert [x.index for x in s] == [0, 1]


def test_winter_variant_has_negative_sos():
    d, y = _synthetic([(420, 0.8)])  # peak late Feb 2017; 20% rise about 70 days earlier
    s = detect_seasons(d, y)[0]
    # SOS falls in Dec 2016 -> previous calendar year -> winter green-up, negative day
    assert s.variant == "winter" and s.sos.value <= 0


def test_flat_series_has_no_season():
    d, y = _synthetic([])
    assert detect_seasons(d, y) == []
