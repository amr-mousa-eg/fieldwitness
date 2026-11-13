"""Tests for K-State long-term agronomic trial benchmarks."""

from fieldwitness.agree.trials import (
    classify_rotation_system,
    match_rotation_to_trials,
)


def test_classify_rotation_system():
    assert classify_rotation_system(["winter_wheat", "sorghum", "fallow"]) == "wheat_sorghum_fallow"
    assert classify_rotation_system(["winter_wheat", "fallow", "winter_wheat"]) == "wheat_fallow"
    assert (
        classify_rotation_system(["winter_wheat", "winter_wheat", "winter_wheat"])
        == "continuous_wheat"
    )
    assert (
        classify_rotation_system(["winter_wheat", "cover_crop", "sorghum"])
        == "cover_crop_fallow_replacement"
    )


def test_match_rotation_to_trials():
    trial = match_rotation_to_trials(["winter_wheat", "sorghum", "fallow"])
    assert trial is not None
    assert trial.duration_years == 30
    assert "Schlegel" in trial.citation
    assert trial.yield_advantage_pct == 42.0
    assert trial.water_storage_differential_mm == 68.0

    # Continuous wheat penalty
    cw = match_rotation_to_trials(["winter_wheat", "winter_wheat", "winter_wheat"])
    assert cw is not None
    assert cw.yield_advantage_pct < 0
    assert cw.water_storage_differential_mm < 0
