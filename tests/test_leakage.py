"""Leakage tests (CLAUDE.md rule 6, PLAN.md T1.1): every registered reader, run under
as_of(2021-12-31) on fixture data that contains later records, returns nothing after the cut-off.
A reader registered without a case here makes the suite fail."""

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

import fieldwitness.data.context  # noqa: F401  (registers its reader)
import fieldwitness.data.labels  # noqa: F401  (registers its reader)
import fieldwitness.data.power  # noqa: F401  (registers its reader)
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


CASES = {
    "grace": lambda fn: list(pd.to_datetime(fn(table=_grace_table())["time"])),
    "power": lambda fn: fn(-100.66, 38.34, end=dt.date(2024, 12, 31), loader=_power_loader).index,
    "labels": lambda fn: [dt.date(y, 12, 31) for y in fn(table=_labels_table())["year"]],
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
