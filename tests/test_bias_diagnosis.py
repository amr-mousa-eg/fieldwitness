import numpy as np

from fieldwitness.experimental import bias


def test_pinball_crps_zero_for_point_mass_at_truth():
    assert bias.pinball_crps(np.full(5, 3.0), 3.0) == 0.0


def test_pinball_crps_grows_with_distance():
    q = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert bias.pinball_crps(q, 3.0) < bias.pinball_crps(q, 8.0)


def test_block_bootstrap_median_and_ci_contain_statistic():
    rng = np.random.default_rng(0)
    v = rng.normal(2.0, 1.0, 200)
    blocks = np.repeat(np.arange(40), 5)
    m, lo, hi = bias.block_bootstrap(v, blocks)
    assert lo <= m <= hi
    assert abs(m - np.median(v)) < 1e-12


def test_block_bootstrap_is_seeded():
    v = np.arange(50.0)
    b = np.repeat(np.arange(10), 5)
    assert bias.block_bootstrap(v, b) == bias.block_bootstrap(v, b)


def test_summarize_too_few():
    out = bias.summarize(np.ones(5), np.arange(5))
    assert out == {"n": 5, "verdict": "too few to judge"}


def test_summarize_signed_and_absolute():
    err = np.array([-2.0, -1.0, 1.0, 2.0] * 10)
    out = bias.summarize(err, np.repeat(np.arange(20), 2))
    assert out["n"] == 40 and out["median"] == 0.0 and out["mae"] == 1.5


def test_multiplier_recovers_constant_ratio():
    pred = np.array([10.0, 20.0, 40.0])
    m = bias.fit_multiplier(pred, 0.8 * pred)
    assert np.isclose(m, 0.8)
    assert np.allclose(bias.apply_multiplier(np.array([[10.0, 20.0]]), m), [[8.0, 16.0]])


def test_isotonic_is_monotone_and_keeps_quantile_order():
    pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    obs = np.array([2.0, 1.0, 4.0, 3.0, 6.0])
    iso = bias.fit_isotonic(pred, obs)
    q = bias.apply_isotonic(np.array([[0.5, 1.5, 2.5, 3.5, 9.0]]), iso)
    assert np.all(np.diff(q[0]) >= 0)
    assert q[0, 0] == iso.predict([1.0])[0]  # clipped below the fit range


def test_shift_removes_constant_peak_bias():
    s = bias.fit_shift(np.array([10.0, 12.0, 8.0]))
    assert s == -10.0
    assert np.allclose(bias.apply_shift(np.array([100.0, 110.0]), s), [90.0, 100.0])
