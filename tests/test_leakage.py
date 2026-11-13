"""Leakage tests (CLAUDE.md rule 6, PLAN.md T1.1): every registered reader, run under
as_of(2021-12-31) on fixture data that contains later records, returns nothing after the cut-off.
A reader registered without a case here makes the suite fail."""

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

import fieldwitness.data.cocorahs  # noqa: F401
import fieldwitness.data.context  # noqa: F401  (registers its reader)
import fieldwitness.data.ecostress  # noqa: F401
import fieldwitness.data.era5  # noqa: F401
import fieldwitness.data.gpm_imerg  # noqa: F401
import fieldwitness.data.hls_qa  # noqa: F401  (registers its reader)
import fieldwitness.data.labels  # noqa: F401  (registers its reader)
import fieldwitness.data.nwis  # noqa: F401
import fieldwitness.data.power  # noqa: F401  (registers its reader)
import fieldwitness.data.prism  # noqa: F401
from fieldwitness.data.asof import READERS, LeakageError, as_of, forcing_weather, guard

CUT = dt.date(2021, 12, 31)
FIX = Path(__file__).parent / "fixtures"


def _power_loader(lon, lat):
    from fieldwitness.data.power import parse

    return parse(json.loads((FIX / "power_daily_trimmed.json").read_text(encoding="utf-8")))


def _labels_table():
    return pd.DataFrame(
        {
            "field_id": ["f1"] * 4,
            "year": [2020, 2021, 2022, 2023],
            "crop": ["maize", "winter_wheat", "sorghum", "fallow"],
        }
    )


def _grace_table():
    return pd.DataFrame(
        {
            "time": pd.to_datetime(["2021-06-16", "2021-12-16", "2022-06-16"]),
            "lwe_cm": [1.0, 2.0, 3.0],
        }
    )


def _hls_table():
    return pd.DataFrame({"date": pd.to_datetime(["2020-06-01", "2021-12-31", "2022-03-01"])})


def _daily_weather_table(extra_cols=None):
    df = pd.DataFrame({"date": ["2021-06-01", "2021-12-31", "2022-03-01"]})
    if extra_cols:
        for k, v in extra_cols.items():
            df[k] = v
    return df


CASES = {
    "grace": lambda fn: list(pd.to_datetime(fn(table=_grace_table())["time"])),
    "power": lambda fn: fn(-100.66, 38.34, end=dt.date(2024, 12, 31), loader=_power_loader).index,
    "labels": lambda fn: [dt.date(y, 12, 31) for y in fn(table=_labels_table())["year"]],
    "hls_series": lambda fn: list(
        fn("x", end=dt.date(2024, 12, 31), table=_hls_table())["date"].dt.date
    ),
    "gpm_imerg": lambda fn: list(
        fn(
            table=_daily_weather_table(
                {"rain_mm": [1.0, 2.0, 3.0], "scale_flag": [True] * 3, "tag": ["O"] * 3}
            )
        )["date"]
    ),
    "ecostress": lambda fn: list(
        fn(
            table=pd.DataFrame(
                {
                    "field_id": ["f1"] * 3,
                    "date": ["2021-06-01", "2021-12-31", "2022-03-01"],
                    "eta_mm": [2.0, 3.0, 4.0],
                    "qc_good": [True] * 3,
                    "tag": ["D"] * 3,
                }
            )
        )["date"]
    ),
    "nwis_gw": lambda fn: list(
        fn(
            table=pd.DataFrame(
                {
                    "site_id": ["s1"] * 3,
                    "site_name": ["w1"] * 3,
                    "lat": [38.0] * 3,
                    "lon": [-100.0] * 3,
                    "date": ["2021-06-01", "2021-12-31", "2022-03-01"],
                    "depth_to_water_ft": [40.0] * 3,
                    "depth_to_water_m": [12.0] * 3,
                    "tag": ["E"] * 3,
                }
            )
        )["date"]
    ),
    "prism": lambda fn: list(
        fn(
            table=_daily_weather_table(
                {
                    "ppt_mm": [1.0, 2.0, 3.0],
                    "tmax_c": [20.0] * 3,
                    "tmin_c": [10.0] * 3,
                    "tmean_c": [15.0] * 3,
                    "scale_flag": [True] * 3,
                    "tag": ["E"] * 3,
                }
            )
        )["date"]
    ),
    "era5": lambda fn: list(
        fn(
            table=_daily_weather_table(
                {
                    "tmax_c": [25.0] * 3,
                    "tmin_c": [10.0] * 3,
                    "rain_mm": [0.0] * 3,
                    "eto_mm": [4.0] * 3,
                    "wind_max_ms": [5.0] * 3,
                    "rad_mj_m2": [15.0] * 3,
                    "scale_flag": [True] * 3,
                    "tag": ["E"] * 3,
                }
            )
        )["date"]
    ),
    "cocorahs": lambda fn: list(
        fn(
            table=pd.DataFrame(
                {
                    "station_id": ["st1"] * 3,
                    "date": ["2021-06-01", "2021-12-31", "2022-03-01"],
                    "lat": [38.0] * 3,
                    "lon": [-100.0] * 3,
                    "rain_mm": [1.0, 2.0, 3.0],
                    "tag": ["E"] * 3,
                }
            )
        )["date"]
    ),
}


def test_every_registered_reader_has_a_leakage_case():
    assert set(READERS) == set(CASES)


@pytest.mark.parametrize("name", sorted(CASES))
def test_reader_returns_nothing_after_cutoff(name):
    fn, _ = READERS[name]
    with as_of(CUT):
        dates = [d.date() if hasattr(d, "date") else d for d in CASES[name](fn)]
    assert dates and max(dates) <= CUT
    dates_free = [d.date() if hasattr(d, "date") else d for d in CASES[name](fn)]
    assert max(dates_free) > CUT  # the fixture really contains later data


def test_guard_raises_on_late_record():
    with as_of(CUT), pytest.raises(LeakageError):
        guard([dt.date(2022, 1, 1)], "test")


def test_forcing_channel_only_for_weather_readers():
    with as_of(CUT), forcing_weather():
        guard([dt.date(2022, 1, 1)], "weather", weather=True)  # allowed
        with pytest.raises(LeakageError):
            guard([dt.date(2022, 1, 1)], "labels", weather=False)


def test_power_forced_mode_returns_post_cutoff_weather():
    fn, _ = READERS["power"]
    with as_of(CUT), forcing_weather():
        idx = fn(-100.66, 38.34, end=dt.date(2024, 12, 31), loader=_power_loader).index
    assert max(idx).date() > CUT
