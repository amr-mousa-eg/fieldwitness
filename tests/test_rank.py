import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fieldwitness.rotate.rank import (
    METRICS,
    load_presets,
    oriented,
    pareto_mask,
    rank_field,
    regret,
    scores,
)


def ev(n=6, seed=0):
    r = np.random.default_rng(seed)
    return {
        "ryi": [None, *r.uniform(0.3, 1, n - 1).tolist()],
        "cvar10_ryi": [None, *r.uniform(0.1, 0.8, n - 1).tolist()],
        "cover_days": r.integers(0, 300, n).tolist(),
        "water_use_mm": r.uniform(300, 900, n).tolist(),
        "irrigation_mm": r.uniform(0, 300, n).tolist(),
        "cvar10_water_mm": r.uniform(400, 1200, n).tolist(),
        "ryi_by_year": [None, *r.uniform(0.2, 1, (n - 1, 5)).tolist()],
    }


def test_presets_load_and_sum():
    p = load_presets()
    assert p["default_preset"] in p["presets"]
    assert all(abs(sum(w.values()) - 1) < 1e-9 for w in p["presets"].values())


def test_pareto_simple():
    m = np.array([[1, 1], [2, 2], [3, 0], [0, 3], [2, 2]], float)
    # row 0 dominated by row 1; rows 1 and 4 tie (neither dominates) so both stay
    assert pareto_mask(m).tolist() == [False, True, True, True, True]


@given(st.lists(st.lists(st.integers(0, 5), min_size=3, max_size=3), min_size=2, max_size=12))
def test_dominated_never_outscores_dominator(rows):
    m = np.array(rows, float)
    w = {k: 1 / len(METRICS) for k in METRICS}
    # reuse scores() with 3 columns padded to 6 so the metric names line up
    pad = np.hstack([m, m])
    s = scores(pad, w)
    for i in range(len(m)):
        for j in range(len(m)):
            if (m[j] >= m[i]).all() and (m[j] > m[i]).any():
                assert s[j] >= s[i] - 1e-12


def test_rank_reproducible_and_complete():
    p = load_presets()
    a, b = rank_field(ev(), p), rank_field(ev(), p)
    assert a == b
    for name in p["presets"]:
        assert sorted(a["rank"][name]) == list(range(6))


def test_orientation_missing_ryi_is_zero():
    m = oriented(ev())
    assert m[0, 0] == 0.0 and m[0, 1] == 0.0
    assert (m[:, 3] <= 0).all()  # water negated


def test_regret_nonnegative_zero_for_best():
    rg = regret(ev())
    assert rg.min() == pytest.approx(0.0)
    assert (rg >= 0).all()
    assert (rg.min(0) == 0).all()  # every year has a zero-regret option


def test_ties_break_by_index():
    e = {k: [1.0, 1.0, 1.0] for k in METRICS}
    e["ryi_by_year"] = [[0.5], [0.5], [0.5]]
    r = rank_field(e, load_presets())
    assert r["rank"]["balanced"] == [0, 1, 2]
