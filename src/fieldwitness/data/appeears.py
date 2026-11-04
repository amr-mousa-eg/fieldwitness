"""Helpers for AppEEARS area-task outputs."""

import datetime as dt
import re

import numpy as np

_UNITS = re.compile(r"^days since (\d{4}-\d{2}-\d{2})(?:[ T]00:00:00(?:\.0+)?)?$")


def decode_time(values, units: str) -> list[dt.date]:
    """Decode the `time` variable of an AppEEARS HLS NetCDF file into calendar dates.

    AppEEARS writes `units = "days since <product start date> 00:00:00"` (2013-04-11 for HLSL30,
    2015-11-28 for HLSS30) together with `calendar = "julian"`. The values are plain day counts:
    read that way they match the dates in the task's Statistics CSV exactly, whereas a true Julian
    calendar (e.g. via cftime) would shift dates by ~13 days. So the calendar attribute is ignored.
    Source: AppEEARS task 09338e93-d3fa-493d-bc4a-476ac22a2b88, checked against its Statistics CSVs
    (docs/api_notes.md). Open the file with `decode_times=False` and pass `ds["time"].values` and
    `ds["time"].attrs["units"]`.
    """
    m = _UNITS.match(units.strip())
    if m is None:
        raise ValueError(f"unsupported AppEEARS time units: {units!r}")
    days = np.asarray(values)
    if days.size and not np.all(days == np.round(days)):
        raise ValueError("AppEEARS time values are expected to be whole days")
    base = dt.date.fromisoformat(m.group(1))
    return [base + dt.timedelta(days=int(d)) for d in days.ravel()]
