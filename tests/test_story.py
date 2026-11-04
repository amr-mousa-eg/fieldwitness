import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from fieldwitness.story.bare import bare_calendar
from fieldwitness.story.smooth import load_story, savgol, smooth_series

CFG = load_story()


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.tuples(st.integers(1, 3000), st.floats(-1.0, 1.0)),
        min_size=2,
        max_size=60,
        unique_by=lambda t: t[0],
    )
)
def test_smooth_length_and_range(obs):
    obs.sort()
    days = np.array([o[0] for o in obs], float)
    vals = np.array([o[1] for o in obs])
    grid, sm = smooth_series(days, vals)
    assert len(grid) == len(sm)
    ok = sm[np.isfinite(sm)]
    assert ok.size == 0 or (ok.min() >= -1 and ok.max() <= 1)


def test_savgol_keeps_quadratic_exactly():
    x = np.arange(30, dtype=float)
    y = 0.001 * x**2 + 0.01 * x
    assert np.allclose(savgol(y, 7, 2), y)
    assert len(savgol(y, 7, 2)) == len(y)


def test_long_gap_not_filled():
    days = np.array([1, 6, 11, 200, 205, 210], float)
    vals = np.array([0.2, 0.3, 0.4, 0.6, 0.5, 0.4])
    grid, sm = smooth_series(days, vals, CFG["smoothing"])
    mid = (grid > 20) & (grid < 190)
    assert np.isnan(sm[mid]).all()


def _series(bare_months):
    rows = []
    for y in range(2016, 2024):
        for m in range(1, 13):
            for dday in (5, 15, 25):
                rows.append((pd.Timestamp(y, m, dday), 0.1 if m in bare_months else 0.7))
    return pd.DataFrame(rows, columns=["date", "ndvi"])


def test_bare_calendar_shares_and_insufficient():
    s = _series({7, 8})
    s = s[~((s.date.dt.month == 3) & (s.date.dt.year >= 2017))]  # March: 1 year only
    cal = bare_calendar(s, CFG)
    assert len(cal) == 12
    assert cal[6].bare_share.value == 1.0 and cal[6].bare_share.tag == "O"
    assert cal[0].bare_share.value == 0.0
    assert cal[2].insufficient and cal[2].bare_share is None


def _wheat(dip: float) -> pd.DataFrame:
    # synthetic winter wheat: bare 0.15; Nov peak 0.6; Jan dip `dip`; May peak 0.85; harvest July
    pts = []
    for y in range(2016, 2021):
        pts += [(f"{y}-08-15", 0.15), (f"{y}-10-01", 0.15), (f"{y}-11-15", 0.6)]
        pts += [(f"{y}-12-20", 0.55), (f"{y + 1}-01-15", dip), (f"{y + 1}-02-15", dip + 0.03)]
        pts += [(f"{y + 1}-03-15", 0.5), (f"{y + 1}-05-10", 0.85)]
        pts += [(f"{y + 1}-06-20", 0.5), (f"{y + 1}-07-15", 0.15)]
    s = pd.DataFrame(pts, columns=["date", "ndvi"])
    s["date"] = pd.to_datetime(s["date"])
    return s.sort_values("date").reset_index(drop=True)


def test_winter_dormancy_dip_above_bare_is_one_season():
    from fieldwitness.story.seasons import detect_seasons

    s = _wheat(0.45)
    got = [x for x in detect_seasons(s["date"], s["ndvi"], CFG) if 2018 <= x.year <= 2020]
    assert [x.year for x in got] == [2018, 2019, 2020]
    assert all(x.variant == "winter" for x in got)
