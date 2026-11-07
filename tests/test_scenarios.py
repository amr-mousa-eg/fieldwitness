import numpy as np
import pandas as pd

from fieldwitness.rotate import scenarios as s


def _w():
    idx = pd.date_range("2001-01-01", "2001-12-31")
    n = len(idx)
    return pd.DataFrame(
        {
            "T2M_MAX": np.full(n, 25.0),
            "T2M_MIN": np.full(n, 12.0),
            "RH2M": np.full(n, 60.0),
            "WS2M": np.full(n, 2.0),
            "ALLSKY_SFC_SW_DWN": np.full(n, 18.0),
            "PRECTOTCORR": np.full(n, 2.0),
        },
        index=idx,
    )


def test_grid_is_12_with_baseline():
    g = s.grid()
    assert len(g) == 12 and len({x[0] for x in g}) == 12
    assert s.BASELINE_ID in {x[0] for x in g}


def test_perturb_does_not_mutate_and_scales():
    w = _w()
    p = s.perturb(w, 2.0, -20.0)
    assert (w["T2M_MAX"] == 25.0).all() and (w["PRECTOTCORR"] == 2.0).all()
    assert np.allclose(p["T2M_MAX"], 27.0) and np.allclose(p["T2M_MIN"], 14.0)
    assert np.allclose(p["PRECTOTCORR"], 1.6)


def test_warming_raises_eto_and_rain_scales_linearly():
    w = _w()
    r0, e0 = s.yearly_arrays(w, 38.0, 400.0, 2001, 2001)
    r1, e1 = s.yearly_arrays(s.perturb(w, 2.0, 10.0), 38.0, 400.0, 2001, 2001)
    assert e1.sum() > e0.sum()
    assert np.allclose(r1, r0 * 1.1)


def test_baseline_is_identity():
    w = _w()
    assert s.perturb(w, 0.0, 0.0).equals(w)
