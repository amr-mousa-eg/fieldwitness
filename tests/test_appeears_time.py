import datetime as dt

import pytest

from fieldwitness.data.appeears import decode_time

# Raw `time` values and units from AppEEARS task 09338e93-d3fa-493d-bc4a-476ac22a2b88 NetCDF files,
# paired with the Date column of the same task's Statistics CSVs (docs/api_notes.md).
L30_UNITS = "days since 2013-04-11 00:00:00"
S30_UNITS = "days since 2015-11-28 00:00:00"


@pytest.mark.parametrize(
    ("units", "raw", "expected"),
    [
        (L30_UNITS, [3642, 3650, 3851], ["2023-04-01", "2023-04-09", "2023-10-27"]),
        (S30_UNITS, [2685, 2690, 2890], ["2023-04-05", "2023-04-10", "2023-10-27"]),
    ],
)
def test_decode_matches_statistics_csv_dates(units, raw, expected):
    assert decode_time(raw, units) == [dt.date.fromisoformat(d) for d in expected]


def test_rejects_other_units():
    with pytest.raises(ValueError):
        decode_time([1], "hours since 2013-04-11 00:00:00")


def test_rejects_fractional_days():
    with pytest.raises(ValueError):
        decode_time([1.5], L30_UNITS)
