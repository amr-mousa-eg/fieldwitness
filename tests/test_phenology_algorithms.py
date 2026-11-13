"""Unit and property tests for Advanced Phenology Extraction Algorithms (Phase 1)."""

import numpy as np

from fieldwitness.story.phenology_algorithms import (
    CROPS,
    CropFormerNumPy,
    compute_mlwf,
    standard_dtw_distance,
    twdtw_distance,
    vdtw_distance,
    wddtw_distance,
)


def test_mlwf_properties():
    """MLWF penalty function must be monotonic in time difference and bounded in [0, 1]."""
    t_q = np.array([0.0, 10.0, 45.0, 100.0])
    t_t = np.array([0.0])
    w = compute_mlwf(t_q, t_t, alpha=0.10, beta=45.0)

    assert w.shape == (4, 1)
    # Monotonicity with respect to time lag
    assert 0.0 == w[0, 0] < w[1, 0] < w[2, 0] < w[3, 0]
    # Bound in [0, 1]
    assert 0.0 <= w[0, 0] < 0.1
    # At midpoint beta = 45, normalized logistic value is approx 0.5
    assert np.isclose(w[2, 0], 0.5, atol=0.01)
    # Far away (> 100 days), penalty approaches 1.0
    assert w[3, 0] > 0.99


def test_standard_dtw_zero_distance_identical():
    """Standard DTW distance between identical sequences must be zero."""
    x = np.array([0.2, 0.4, 0.7, 0.8, 0.5, 0.2])
    dist = standard_dtw_distance(x, x)
    assert np.isclose(dist, 0.0, atol=1e-6)

    # Positive for non-identical
    y = np.array([0.8, 0.7, 0.4, 0.2, 0.1, 0.1])
    dist_xy = standard_dtw_distance(x, y)
    assert dist_xy > 0.1


def test_twdtw_penalizes_temporal_lag():
    """TWDTW distance between identical curves must increase when temporal lag is introduced."""
    curve = np.array([0.2, 0.4, 0.8, 0.85, 0.5, 0.2])
    t0 = np.array([100.0, 110.0, 120.0, 130.0, 140.0, 150.0])

    # No lag
    d_sync = twdtw_distance(curve, t0, curve, t0)
    assert d_sync < 0.05

    # Shifted by 80 days
    t_lagged = t0 + 80.0
    d_lag = twdtw_distance(curve, t0, curve, t_lagged)
    assert d_lag > d_sync + 0.3


def test_wddtw_amplitude_offset_invariance():
    """WDDTW operates on derivatives, making it resilient to uniform vertical shifts."""
    x = np.array([0.2, 0.3, 0.6, 0.8, 0.6, 0.3, 0.2])
    x_shifted = x + 0.15  # uniform vertical baseline elevation
    t = np.arange(len(x), dtype=float) * 10.0

    dx = np.gradient(x, 10.0)
    dx_shifted = np.gradient(x_shifted, 10.0)

    # Derivative distance should be identical (within floating point precision)
    d_deriv = wddtw_distance(dx, t, dx_shifted, t)
    assert np.isclose(d_deriv, 0.0, atol=1e-5)


def test_vdtw_scale_invariance():
    """Vector DTW uses spectral angle (cosine distance), invariant to proportional scaling."""
    t = np.arange(5, dtype=float) * 10.0
    vecs1 = np.array(
        [
            [0.2, 0.1, 0.01],
            [0.4, 0.2, 0.03],
            [0.8, 0.4, 0.05],
            [0.5, 0.25, -0.02],
            [0.2, 0.1, -0.01],
        ]
    )
    # Scaled by 0.6 (e.g. drought year)
    vecs2 = vecs1 * 0.60

    d_vec = vdtw_distance(vecs1, t, vecs2, t)
    assert np.isclose(d_vec, 0.0, atol=1e-4)


def test_cropformer_forward_and_properties():
    """CropFormerNumPy forward pass output shapes and deterministic properties."""
    cf1 = CropFormerNumPy(d_in=3, d_model=32, n_heads=4, seed=42)
    cf2 = CropFormerNumPy(d_in=3, d_model=32, n_heads=4, seed=42)

    T = 25
    rng = np.random.default_rng(42)
    x = rng.normal(0, 1, (T, 3))
    doy = np.linspace(-50, 250, T)

    emb1 = cf1.extract_features(x, doy)
    emb2 = cf2.extract_features(x, doy)

    assert emb1.shape == (32,)
    assert np.allclose(emb1, emb2)

    pred, probs = cf1.predict(x, doy)
    assert pred in CROPS
    assert np.isclose(sum(probs.values()), 1.0, atol=1e-5)
    for p in probs.values():
        assert 0.0 <= p <= 1.0
