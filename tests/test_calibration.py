"""Unit tests for asymmetric and symmetric CQR prediction interval calibration."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fieldwitness.infer import calibration as cal


def test_assign_spatial_blocks_clusters_nearby_points():
    df = pd.DataFrame(
        {
            "lon": [-101.00, -101.01, -100.50],
            "lat": [38.50, 38.51, 38.90],
        }
    )
    blks = cal.assign_spatial_blocks(df, block_km=10.0)
    assert blks.iloc[0] == blks.iloc[1]
    assert blks.iloc[0] != blks.iloc[2]


def test_asymmetric_cqr_recovers_one_sided_negative_bias():
    # Simulated negatively biased intervals where y falls below q_lo ~40% of the time
    rng = np.random.default_rng(7)
    n = 120
    q_lo = np.full(n, 40.0)
    q_hi = np.full(n, 70.0)
    y = np.concatenate([rng.uniform(25.0, 39.5, size=50), rng.uniform(42.0, 65.0, size=70)])
    df = pd.DataFrame(
        {
            "crop": "winter_wheat",
            "run": "forecast",
            "metric": "canopy_integral",
            "block": [f"b{i % 5}" for i in range(n)],
            "y": y,
            "q_lo": q_lo,
            "q_hi": q_hi,
        }
    )
    params = cal.fit_cqr_offsets(df, ["crop", "run", "metric"], level=0.90)
    entry = params[("winter_wheat", "forecast", "canopy_integral")]
    assert entry["n"] == n
    assert entry["m_lo"] is not None and entry["m_lo"] > 0.0
    assert entry["m_hi"] is not None and entry["m_hi"] < 0.0  # upper tail was already over-covered

    lo, hi = cal.apply_cqr(q_lo, q_hi, entry["m_lo"], entry["m_hi"], lower_bound=0.0)
    cov = np.mean((y >= lo) & (y <= hi))
    assert cov >= 0.90


def test_leave_block_out_excludes_held_out_block():
    rows = []
    for b_idx, blk in enumerate(("b0", "b1", "b2")):
        for i in range(18):
            rows.append(
                {
                    "crop": "maize",
                    "run": "forecast",
                    "metric": "cover_days",
                    "block": blk,
                    "y": 50.0 + b_idx * 20.0 + i * 0.1,
                    "q_lo": 45.0,
                    "q_hi": 55.0,
                }
            )
    df = pd.DataFrame(rows)
    lbo = cal.leave_block_out_cqr(df, ["crop", "run", "metric"], ["b0", "b1", "b2"], level=0.90)
    # Without b2 (largest values y=90..91.7), m_hi must be substantially smaller than without b0
    mhi_no_b2 = lbo[(("maize", "forecast", "cover_days"), "b2")]["m_hi"]
    mhi_no_b0 = lbo[(("maize", "forecast", "cover_days"), "b0")]["m_hi"]
    assert mhi_no_b2 is not None and mhi_no_b0 is not None
    assert mhi_no_b2 < mhi_no_b0
