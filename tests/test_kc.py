import numpy as np
import pytest

from fieldwitness.physics.kc import kc_adjust, kc_curve


def test_curve_shape_fig34():
    kc = kc_curve((30, 40, 50, 50), 0.3, 1.2, 0.35)
    assert len(kc) == 170
    assert np.all(kc[:30] == 0.3)
    assert np.all(kc[69:120] == 1.2)
    assert kc[-1] == pytest.approx(0.35)
    assert np.all(np.diff(kc[29:70]) > 0)  # development rises
    assert np.all(np.diff(kc[119:]) < 0)  # late season falls


def test_curve_padding_and_errors():
    kc = kc_curve((10, 10, 10, 10), 0.3, 1.0, 0.5, n_days=50)
    assert len(kc) == 50 and np.all(kc[40:] == 0.5)
    with pytest.raises(ValueError):
        kc_curve((0, 0, 0, 0), 0.3, 1.0, 0.5)


def test_adjust_standard_climate_is_identity():
    # u2 = 2, RHmin = 45 -> bracket is zero (Eq. 62/65)
    assert kc_adjust(1.2, 2.0, 45.0, 2.0) == pytest.approx(1.2)


def test_adjust_direction_and_value():
    # h = 3 m gives factor (h/3)^0.3 = 1; hand calc of the bracket.
    assert kc_adjust(1.2, 4.0, 25.0, 3.0) == pytest.approx(1.2 + 0.08 + 0.08)
    assert kc_adjust(1.2, 1.0, 65.0, 3.0) == pytest.approx(1.2 - 0.04 - 0.08)


def test_end_threshold_and_clipping():
    assert kc_adjust(0.35, 4.0, 25.0, 3.0, end=True) == 0.35
    assert kc_adjust(0.35, 4.0, 25.0, 3.0) > 0.35
    assert kc_adjust(1.0, 99.0, 0.0, 3.0) == kc_adjust(1.0, 6.0, 20.0, 3.0)
