import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from fieldwitness.physics import waterbal as wb

POLICIES = [wb.rainfed(), wb.trigger_at_raw(0.7), wb.fixed_seasonal_mm(150.0, 0.8)]


def test_eq82_83_84():
    t = wb.taw(0.30, 0.15, 1.0)
    assert np.isclose(t, 150.0)  # Eq. 82
    r = wb.raw(t, 0.5)
    assert np.isclose(r, 75.0)  # Eq. 83
    assert wb.ks(60.0, t, r) == 1.0
    assert np.isclose(wb.ks(112.5, t, r), 0.5)  # Eq. 84: (150-112.5)/75
    assert wb.ks(150.0, t, r) == 0.0


@settings(max_examples=60, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    taw_mm=st.floats(40, 300),
    p=st.floats(0.2, 0.7),
    ro=st.floats(0, 0.3),
    dr0=st.floats(0, 1),
    pol=st.sampled_from(range(3)),
)
def test_mass_bounds(seed, taw_mm, p, ro, dr0, pol):
    rng = np.random.default_rng(seed)
    n = 120
    rain = rng.gamma(0.3, 12.0, (n, 4))
    etc = rng.uniform(0, 9, (n, 4))
    o = wb.run(rain, etc, taw_mm, p, POLICIES[pol], dr0=dr0 * taw_mm, ro_frac=ro)
    prev = np.vstack([np.full((1, 4), dr0 * taw_mm), o["dr"][:-1]])
    resid = prev - o["dr"] - ((rain - o["ro"]) + o["irr"] - o["eta"] - o["dp"])
    assert np.abs(resid).max() < 1e-9  # mass closes every day
    assert (o["ks"] >= 0).all() and (o["ks"] <= 1).all()
    assert (o["dr"] >= 0).all() and (o["dr"] <= taw_mm + 1e-9).all()
    assert (o["eta"] <= etc + 1e-9).all() and (o["eta"] >= -1e-9).all()
    if pol == 2:
        assert o["irr"].sum(axis=0).max() <= 150.0 + 1e-9


def test_irrigation_reduces_stress():
    rain = np.zeros(90)
    etc = np.full(90, 5.0)
    a = wb.run(rain, etc, 100.0, 0.5, wb.rainfed())
    b = wb.run(rain, etc, 100.0, 0.5, wb.trigger_at_raw(1.0))
    assert b["eta"].sum() > a["eta"].sum()
    assert a["irr"].sum() == 0 and b["irr"].sum() > 0


def test_batched_shape():
    rain = np.zeros((30, 5, 3))
    o = wb.run(rain, np.full((30, 5, 3), 4.0), np.full((5, 3), 120.0), 0.5)
    assert o["dr"].shape == (30, 5, 3)
