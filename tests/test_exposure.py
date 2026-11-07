import numpy as np

from fieldwitness.physics.rotation import DAYS, fallow_slot
from fieldwitness.rotate.exposure import erosion_exposure, exposure_metrics, residue_proxy
from fieldwitness.rotate.slots import option_slots


def _rain(n=10, val=20.0):
    return np.full((n, DAYS), val)


def test_full_cover_has_no_exposure_and_bare_has_most():
    bare, cover = np.zeros(2 * DAYS), np.ones(2 * DAYS)
    assert erosion_exposure(cover, _rain(), 2.0) == 0.0
    assert erosion_exposure(bare, _rain(), 2.0) > 0.0


def test_below_threshold_rain_gives_zero():
    assert erosion_exposure(np.zeros(DAYS), _rain(val=5.0), 2.0) == 0.0


def test_scales_with_slope_and_is_per_rotation_year():
    c, r = np.zeros(2 * DAYS), _rain()
    assert erosion_exposure(c, r, 4.0) > erosion_exposure(c, r, 2.0)
    one = erosion_exposure(np.zeros(DAYS), r, 2.0)
    assert np.isclose(erosion_exposure(c, r, 2.0), one)


def test_residue_proxy_bounds():
    assert residue_proxy(np.zeros(DAYS)) == 0.0
    assert residue_proxy(np.ones(DAYS)) == 1.0


def test_option_metrics_fallow_vs_sorghum():
    rain = _rain(val=15.0)
    fal = exposure_metrics([fallow_slot()] * 3, rain, 1.7)
    sor = exposure_metrics(option_slots(("sorghum",) * 3, "ks_t14slh"), rain, 1.7)
    assert fal["residue_proxy"].value == 0.0
    assert sor["residue_proxy"].value > 0.0
    assert sor["erosion_exposure"].value < fal["erosion_exposure"].value
    assert all(m.tag == "D" for m in {**fal, **sor}.values())
