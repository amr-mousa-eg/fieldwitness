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


def test_cropformer_analytical_gradients_match_finite_diff():
    """Analytical gradients for MAE and classifier backprop must match finite differences."""
    cf = CropFormerNumPy(d_in=4, d_model=8, n_heads=2, n_classes=3, seed=7)
    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 0.5, (6, 4))
    doy = np.array([10.0, 45.0, 90.0, 140.0, 200.0, 260.0])
    mask = np.array([False, True, False, True, False, False])

    # 1. Classifier loss gradients
    _, g_cls = cf._cls_loss_and_grads(x, doy, y_idx=1, sample_weight=1.3)
    eps = 1e-6
    for pname in (
        "W_in",
        "b_in",
        "W_q",
        "W_k",
        "W_v",
        "W_o",
        "W_ff1",
        "b_ff1",
        "W_ff2",
        "b_ff2",
        "w_pool",
        "W_cls",
        "b_cls",
    ):
        arr = getattr(cf, pname)
        grad = g_cls[pname]
        # Check a few coordinates per tensor
        for flat_i in (0, arr.size // 2, arr.size - 1):
            idx = np.unravel_index(flat_i, arr.shape)
            orig = float(arr[idx])
            arr[idx] = orig + eps
            lp, _ = cf._cls_loss_and_grads(x, doy, y_idx=1, sample_weight=1.3)
            arr[idx] = orig - eps
            lm, _ = cf._cls_loss_and_grads(x, doy, y_idx=1, sample_weight=1.3)
            arr[idx] = orig
            num = (lp - lm) / (2.0 * eps)
            assert np.isclose(grad[idx], num, rtol=1e-4, atol=1e-5), (pname, idx, grad[idx], num)

    # 2. MAE reconstruction gradients
    _, g_mae = cf._mae_loss_and_grads(x, doy, mask)
    for pname in ("W_in", "mask_token", "W_q", "W_ff1", "W_dec", "b_dec"):
        arr = getattr(cf, pname)
        grad = g_mae[pname]
        for flat_i in (0, arr.size - 1):
            idx = np.unravel_index(flat_i, arr.shape)
            orig = float(arr[idx])
            arr[idx] = orig + eps
            lp, _ = cf._mae_loss_and_grads(x, doy, mask)
            arr[idx] = orig - eps
            lm, _ = cf._mae_loss_and_grads(x, doy, mask)
            arr[idx] = orig
            num = (lp - lm) / (2.0 * eps)
            assert np.isclose(grad[idx], num, rtol=1e-4, atol=1e-5), (pname, idx, grad[idx], num)


def test_cropformer_mae_pretrain_and_finetune_converge():
    """MAE pretraining decreases reconstruction loss and fine-tuning separates synthetic regimes."""
    rng = np.random.default_rng(2026)
    doy = np.linspace(1, 300, 15)
    samples = []
    ones = np.ones_like(doy)
    for _ in range(12):
        # Summer high peak
        nd_s = 0.2 + 0.65 * np.exp(-0.5 * ((doy - 200.0) / 35.0) ** 2) + rng.normal(0, 0.02, 15)
        samples.append({"x": np.stack([nd_s, nd_s * 0.7, ones], 1), "doy": doy, "crop": "maize"})
        # Spring winter-wheat peak
        nd_w = 0.2 + 0.60 * np.exp(-0.5 * ((doy - 125.0) / 30.0) ** 2) + rng.normal(0, 0.02, 15)
        samples.append(
            {"x": np.stack([nd_w, nd_w * 0.7, ones], 1), "doy": doy, "crop": "winter_wheat"}
        )
        # Low fallow
        nd_f = 0.18 + rng.normal(0, 0.02, 15)
        samples.append({"x": np.stack([nd_f, nd_f * 0.7, ones], 1), "doy": doy, "crop": "fallow"})

    cf = CropFormerNumPy(
        d_in=3, d_model=16, n_heads=2, classes=["winter_wheat", "maize", "fallow"], seed=11
    )
    mae_losses = cf.pretrain_mae(samples, epochs=15, lr=0.02, batch_size=8)
    assert len(mae_losses) == 15
    assert mae_losses[-1] < mae_losses[0]

    ft_losses = cf.fine_tune(samples, epochs=25, lr=0.015, batch_size=8)
    assert len(ft_losses) == 25
    assert ft_losses[-1] < ft_losses[0]
    preds = [cf.predict(s["x"], s["doy"])[0] == s["crop"] for s in samples]
    assert np.mean(preds) >= 0.9
