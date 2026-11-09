import numpy as np
import pandas as pd

from fieldwitness.packs.sim3d import (
    build_field_sim3d,
    build_weekly_calendar,
    find_median_gs_rain_year,
)
from fieldwitness.schemas import FieldSim3D, check_tagged


def test_build_weekly_calendar():
    weeks = build_weekly_calendar(start_year=2022, n_seasons=3)
    assert len(weeks) == 156
    assert weeks[0].week == 0
    assert weeks[0].year == 2022
    assert weeks[0].week_start == "2022-01-01"
    assert weeks[52].year == 2023
    assert weeks[104].year == 2024
    assert weeks[155].week == 155


def test_find_median_gs_rain_year():
    # Mock weather across 2001..2021
    dates = pd.date_range("2001-01-01", "2021-12-31", freq="D")
    rng = np.random.default_rng(42)
    rain = rng.uniform(0, 5, size=len(dates))
    df = pd.DataFrame(
        {
            "T2M_MAX": 25.0,
            "T2M_MIN": 15.0,
            "RH2M": 50.0,
            "WS2M": 3.0,
            "ALLSKY_SFC_SW_DWN": 18.0,
            "PRECTOTCORR": rain,
        },
        index=dates,
    )
    df.index.name = "date"
    yr = find_median_gs_rain_year(df, lat=38.34, elev=900.0, y0=2001, y1=2021)
    assert 2001 <= yr <= 2021


def test_build_field_sim3d():
    dates = pd.date_range("2001-01-01", "2021-12-31", freq="D")
    rng = np.random.default_rng(123)
    df = pd.DataFrame(
        {
            "T2M_MAX": 25.0,
            "T2M_MIN": 15.0,
            "RH2M": 50.0,
            "WS2M": 3.0,
            "ALLSKY_SFC_SW_DWN": 18.0,
            "PRECTOTCORR": rng.uniform(0, 5, size=len(dates)),
        },
        index=dates,
    )
    df.index.name = "date"

    cur_seq = ("sorghum", "fallow", "winter_wheat")
    top_alts = [
        {"sequence": ["fallow", "sorghum", "cover_crop"], "rank": 1},
        {"sequence": ["sorghum", "sorghum", "fallow"], "rank": 2},
    ]

    m = build_field_sim3d(
        fid="test_field_123",
        cur_seq=cur_seq,
        top_alts=top_alts,
        weather_full=df,
        lat=38.34,
        elev=900.0,
        taw_mm=160.0,
        kc_scale=1.0,
        budget_mm=100.0,
        region_id="ks_t14slh",
        start_year=2022,
    )

    assert isinstance(m, FieldSim3D)
    assert m.schema_version == "1.0"
    assert m.field_id == "test_field_123"
    assert m.tag == "D"
    assert len(m.weeks) == 156
    assert len(m.alternatives) == 2
    assert "t+0_p+0" in m.current.scenarios
    assert len(m.current.scenarios["t+0_p+0"].soil_water_mm) == 156
    assert check_tagged(m) == []
