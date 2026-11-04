"""T3.1 check against FAO-56 Example 18 (Uccle, 6 July; Ch. 4, x0490e08.htm).

Expected values are the ones printed in Example 18; it rounds intermediate results, so
intermediate values are compared at the printed precision and ETo within 0.02 mm/day.
"""

import pytest

from fieldwitness.physics import eto as e

TMAX, TMIN, RHMAX, RHMIN = 21.5, 12.3, 84.0, 63.0
Z, LAT, DOY, N_SUN = 100.0, 50.80, 187, 9.25  # 50°48'N, 100 m, J = 187 (Table 2.5)
U2 = 2.078  # Example 18 converts 10 km/h at 10 m to u2 with Eq. 47


def test_example18_intermediate_values():
    p = e.pressure(Z)
    assert p == pytest.approx(100.1, abs=0.05)
    assert e.slope_vp((TMAX + TMIN) / 2) == pytest.approx(0.122, abs=0.0005)
    assert e.psychrometric_constant(p) == pytest.approx(0.0666, abs=0.00005)
    assert e.sat_vp(TMAX) == pytest.approx(2.564, abs=0.0005)
    assert e.sat_vp(TMIN) == pytest.approx(1.431, abs=0.0005)
    assert e.mean_sat_vp(TMAX, TMIN) == pytest.approx(1.997, abs=0.0005)
    ea = e.actual_vp_rh_minmax(TMAX, TMIN, RHMAX, RHMIN)
    assert ea == pytest.approx(1.409, abs=0.0005)
    ra = e.extraterrestrial_radiation(LAT, DOY)
    assert ra == pytest.approx(41.09, abs=0.005)
    assert e.daylight_hours(LAT, DOY) == pytest.approx(16.1, abs=0.05)
    rs = e.solar_radiation_angstrom(N_SUN, LAT, DOY)
    assert rs == pytest.approx(22.07, abs=0.05)
    rso = e.clear_sky_radiation(ra, Z)
    assert rso == pytest.approx(30.90, abs=0.005)
    assert e.net_shortwave(rs) == pytest.approx(17.00, abs=0.05)
    assert e.net_longwave(TMAX, TMIN, ea, rs, rso) == pytest.approx(3.71, abs=0.01)


def test_example18_eto():
    ea = e.actual_vp_rh_minmax(TMAX, TMIN, RHMAX, RHMIN)
    rs = e.solar_radiation_angstrom(N_SUN, LAT, DOY)
    eto = e.eto_daily(TMAX, TMIN, rs, U2, ea, Z, LAT, DOY)
    assert eto == pytest.approx(3.88, abs=0.02)  # Example 18: 3.88 ≈ 3.9 mm/day


def test_mean_rh_route_and_arrays():
    import numpy as np

    t = np.array([TMAX, TMAX + 5.0])
    ea = e.actual_vp_rh_mean(t, TMIN, 70.0)
    assert ea.shape == (2,) and np.all(ea > 0)
    out = e.eto_daily(t, TMIN, 22.07, U2, ea, Z, LAT, DOY)
    assert out.shape == (2,) and out[1] > out[0]  # hotter day, more ETo
