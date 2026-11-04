import copy
import json
from pathlib import Path

import numpy as np

from fieldwitness.data.power import PARAMETERS, parse

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "power_daily_trimmed.json").read_text(encoding="utf-8")
)  # real POWER response (2026-11-04, Kansas tile centre, 2001-2024), trimmed to 6 days


def test_parse_recorded_response():
    df, elev = parse(FIXTURE)
    assert list(df.columns) == sorted(df.columns) or set(df.columns) == set(PARAMETERS)
    assert set(df.columns) == set(PARAMETERS)
    assert len(df) == 6 and df.index.is_monotonic_increasing
    assert str(df.index[0].date()) == "2001-01-01"
    assert elev is not None and 800 < elev < 900  # 852.2 m returned for this point
    assert df.notna().all().all()


def test_fill_value_becomes_missing():
    payload = copy.deepcopy(FIXTURE)
    first_day = next(iter(payload["properties"]["parameter"]["PRECTOTCORR"]))
    payload["properties"]["parameter"]["PRECTOTCORR"][first_day] = -999.0  # synthetic gap
    df, _ = parse(payload)
    assert np.isnan(df["PRECTOTCORR"].iloc[0])
    assert df["PRECTOTCORR"].iloc[1:].notna().all()
