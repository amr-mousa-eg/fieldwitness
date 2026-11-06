import numpy as np

from fieldwitness.infer import abc


def test_stats_on_triangle():
    doy = np.arange(1, 366)
    v = np.interp(doy, [1, 100, 200, 300, 365], [0.2, 0.2, 0.8, 0.2, 0.2])
    s = abc.summary_stats(doy, v)[0]
    assert abs(s[0] - 150) <= 1 and s[1] == 200 and abs(s[2] - 250) <= 1
    assert abs(s[4] - 0.8) < 1e-9 and s[3] > 0


def test_sparse_interp_matches_dense():
    doy = np.arange(1, 366)
    v = 0.5 + 0.3 * np.sin(doy / 58.0)
    sub = doy[::7]
    a = abc.summary_stats(doy, v)[0]
    b = abc.summary_stats(sub, v[::7])[0]
    assert abs(a[1] - b[1]) < 10 and abs(a[4] - b[4]) < 0.01


def test_coverage_calibrated_when_truth_from_posterior():
    rng = np.random.default_rng(1)
    post = rng.normal(size=(500, 2000))
    truth = rng.normal(size=2000)
    assert abs(abc.interval_coverage(post, truth, 0.9) - 0.9) < 0.03
    assert abs(abc.interval_coverage(post, truth, 0.5) - 0.5) < 0.04


def test_posterior_picks_matching_world():
    rng = np.random.default_rng(0)
    doy = np.arange(5, 365, 10)
    peaks = np.linspace(0.5, 0.9, 50)
    t = np.arange(1, 366)
    ndvi = np.stack([0.15 + (p - 0.15) * np.exp(-(((t - 200) / 50.0) ** 2)) for p in peaks], 1)
    ref = {"ndvi": ndvi}
    post = abc.posterior(doy, ndvi[doy - 1, 20], ref, 0.001, 3, rng)
    assert np.abs(post["idx"] - 20).max() <= 8  # 50 worlds; random picks would average ~16 away
