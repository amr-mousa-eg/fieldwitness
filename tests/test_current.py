import datetime as dt

import pandas as pd
import pytest

from fieldwitness.config import load_crops, load_regions, rotation_options
from fieldwitness.data.asof import as_of
from fieldwitness.rotate.current import all_current, current_rotation

ALLOWED = {"maize", "winter_wheat", "sorghum"}


def _table():
    rows = []
    for fid, crops in {
        "a": ["fallow", "winter_wheat", "sorghum", "maize", "winter_wheat"],
        "b": ["perennial_forage"] * 5,
        "c": ["winter_wheat", "maize"],
    }.items():
        for i, c in enumerate(crops):
            rows.append((fid, 2020 + i, c, None))
    rows.append(("a", 2025, "maize", "sorghum"))
    return pd.DataFrame(rows, columns=["field_id", "year", "crop", "double_crop_second"])


def test_last_three_oldest_first():
    cur = current_rotation("a", ALLOWED, _table())
    assert cur.years == (2023, 2024, 2025)
    assert cur.sequence == ["maize", "winter_wheat", "maize"]
    assert cur.option_id == "current"


def test_gap_for_unsimulated_crop():
    cur = current_rotation("b", ALLOWED, _table())
    assert not cur.simulatable and len(cur.gaps) == 3


def test_short_history_flagged():
    cur = current_rotation("c", ALLOWED, _table())
    assert len(cur.sequence) == 2 and any("only 2" in g for g in cur.gaps)


def test_double_crop_gap_and_second():
    cur = current_rotation("a", ALLOWED, _table())
    assert cur.second_crops == {2025: "sorghum"}


def test_as_of_hides_future_seasons():
    with as_of(dt.date(2023, 12, 31)):
        cur = current_rotation("a", ALLOWED, _table())
    assert max(cur.years) == 2023


def test_unknown_field():
    with pytest.raises(ValueError):
        current_rotation("zzz", ALLOWED, _table())


def test_every_kansas_field_has_current():
    """T6.0 acceptance on the real label table: every pilot field gets a Current option."""
    crops = load_crops()
    reg = load_regions()["ks_t14slh"]
    allowed = set(rotation_options(crops, reg.crops))
    res = all_current(allowed)
    assert len(res) == 200
    assert all(len(r.sequence) == 3 and r.confidence == 1.0 for r in res.values())
