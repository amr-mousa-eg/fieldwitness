import numpy as np
import pandas as pd
import pytest

from fieldwitness.physics import eto as e
from fieldwitness.physics.forcing import forcing


def _weather(n=5):
    idx = pd.date_range("2020-07-01", periods=n, name="date")
    return pd.DataFrame(
        {
            "T2M_MAX": 30.0,
            "T2M_MIN": 15.0,
            "RH2M": 55.0,
            "WS2M": 2.0,
            "ALLSKY_SFC_SW_DWN": 24.0,
            "PRECTOTCORR": [0.0, 1.0, 2.0, 0.0, 3.0][:n],
        },
        index=idx,
    )


def test_forcing_matches_eto_daily_and_passes_rain():
    w = _weather()
    f = forcing(w, 38.0, 400.0)
    ea = e.actual_vp_rh_mean(30.0, 15.0, 55.0)
    expect = e.eto_daily(30.0, 15.0, 24.0, 2.0, ea, 400.0, 38.0, w.index.day_of_year.to_numpy())
    assert np.allclose(f["eto"], expect)
    assert list(f["rain"]) == [0.0, 1.0, 2.0, 0.0, 3.0]
    assert ((f["eto"] > 2) & (f["eto"] < 12)).all()


def test_missing_input_gives_nan_not_fill():
    w = _weather()
    w.loc[w.index[1], "WS2M"] = np.nan
    f = forcing(w, 38.0, 400.0)
    assert np.isnan(f["eto"].iloc[1]) and f["eto"].notna().sum() == 4


def test_missing_column_raises():
    with pytest.raises(KeyError):
        forcing(_weather().drop(columns="RH2M"), 38.0, 400.0)
