"""Conformal recalibration: quantile rule, Mondrian, leave-block-out, unchanged medians."""

import copy

import numpy as np
import pandas as pd
import pytest

from fieldwitness.infer import conformal as cf


def test_scores_hand_example():
    s, h = cf.scores([12.0, 8.0, 10.0], [8.0, 8.0, 10.0], [10.0, 10.0, 10.0], [12.0, 12.0, 10.0])
    assert h.tolist() == [2.0, 2.0, 0.0]
    assert s[0] == 1.0 and s[1] == 1.0 and np.isnan(s[2])  # zero width excluded


def test_quantile_rule_hand_computed():
    s = np.arange(1, 31, dtype=float)  # scores 1..30, n = 30
    # k = ceil(31 * 0.9) = ceil(27.9) = 28 -> 28th smallest = 28
    assert cf.conformal_multiplier(s, 0.90) == 28.0
    # k = ceil(31 * 0.5) = ceil(15.5) = 16
    assert cf.conformal_multiplier(s, 0.50) == 16.0
    # k = ceil(31 * 0.8) = ceil(24.8) = 25
    assert cf.conformal_multiplier(s, 0.80) == 25.0
    # n = 29 < 30: too few to calibrate
    assert cf.conformal_multiplier(s[:29], 0.90) is None
    # exact product: n = 39, (n + 1) * 0.9 = 36 exactly -> k = 36
    assert cf.conformal_multiplier(np.arange(1, 40, dtype=float), 0.90) == 36.0
    # NaN scores are ignored, not counted
    assert cf.conformal_multiplier(np.r_[s, np.nan], 0.90) == 28.0


def _cal():
    rows = []
    for crop, scale in (("maize", 1.0), ("sorghum", 2.0)):
        for i in range(40):
            rows.append(
                {"crop": crop, "run": "forecast", "block": f"b{i % 4}", "s": scale * (i + 1)}
            )
    rows += [{"crop": "winter_wheat", "run": "forecast", "block": "b0", "s": 1.0}] * 10
    return pd.DataFrame(rows)


def test_mondrian_split_per_crop():
    m = cf.mondrian(_cal(), ["crop", "run"], 0.9)
    # n = 40: k = ceil(41 * 0.9) = 37 -> maize 37, sorghum 74
    assert m[("maize", "forecast")] == (37.0, 40)
    assert m[("sorghum", "forecast")] == (74.0, 40)
    assert m[("winter_wheat", "forecast")] == (None, 10)  # too few to calibrate


def test_leave_block_out():
    cal = _cal()
    m = cf.leave_block_out(cal, ["crop", "run"], 0.9, ["b0", "b9"])
    # maize without block b0 (i % 4 == 0): 30 scores {2,3,4,6,7,8,...,40}; k = ceil(31*0.9) = 28
    rest = sorted(x + 1 for x in range(40) if x % 4 != 0)
    assert m[(("maize", "forecast"), "b0")] == (float(rest[27]), 30)
    # a block with no calibration scores leaves the pooled value
    assert m[(("maize", "forecast"), "b9")] == (37.0, 40)
    assert m[(("winter_wheat", "forecast"), "b0")] == (None, 0)


def test_point_predictions_bit_identical():
    q = {"q": [46.724, 51.995, 54.983, 58.205, 64.111]}
    keep = copy.deepcopy(q)
    q50 = np.array([q["q"][2]])
    h = np.array([(q["q"][4] - q["q"][0]) / 2])
    lo, hi = cf.interval(q50, h, np.array([1.7]))
    assert q == keep  # stored quantiles untouched
    assert q50[0] == 54.983  # median unchanged (bit-identical)
    assert (lo[0] + hi[0]) / 2 == pytest.approx(54.983, abs=1e-12)  # centred on the median


def test_winkler():
    w = cf.winkler([0.0, 0.0, 0.0], [10.0, 10.0, 10.0], [5.0, -1.0, 12.0], 0.1)
    assert w.tolist() == [10.0, 30.0, 50.0]
