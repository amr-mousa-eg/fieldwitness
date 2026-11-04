import datetime as dt

import numpy as np
import pandas as pd

from fieldwitness.data.context import slope_degrees, smap_monthly_anomaly, trend_cm_per_year


def test_slope_of_a_tilted_plane():
    x = np.arange(50) * 30.0
    dem = np.tile(x * np.tan(np.radians(5.0)), (40, 1))  # 5 degree slope along x
    s = slope_degrees(dem)
    assert np.allclose(s[5:-5, 5:-5], 5.0, atol=1e-6)


def test_trend_recovers_linear_rate():
    t = pd.date_range("2003-01-16", periods=120, freq="MS")
    years = (t - pd.Timestamp("2002-01-01")).days / 365.25
    df = pd.DataFrame({"time": t, "lwe_cm": -1.5 * years + 4.0})
    assert abs(trend_cm_per_year(df) - (-1.5)) < 1e-9


def test_smap_climatology_uses_only_months_up_to_base_end():
    dates = pd.date_range("2016-01-01", "2023-12-31", freq="D")
    vals = np.where(dates.year >= 2022, 0.40, 0.20)  # wetter after the cut-off
    s = pd.DataFrame({"date": dates, "sm_rootzone": vals})
    m = smap_monthly_anomaly(s, base_end=dt.date(2021, 12, 31))
    pre = m[m["month"].dt.year <= 2021]["anomaly"]
    post = m[m["month"].dt.year >= 2022]["anomaly"]
    assert np.allclose(pre, 0.0) and np.allclose(post, 0.20)
