"""T7.1a: winter crops in the forward model (sowing day < 0, previous + harvest year weather)."""

import numpy as np
import pytest

from fieldwitness.infer import forward
from fieldwitness.rotate.slots import SOW_DAY

CFG = {**forward.load_cfg(), "crop": "winter_wheat"}
CFG["nominal_sow_doy"] = {**CFG["nominal_sow_doy"], "winter_wheat": SOW_DAY["winter_wheat"]}
CROP = forward.crop_params("winter_wheat", CFG["region"])
H = {
    "sow_offset_days": np.array([0.0]),
    "taw_scale": np.array([1.0]),
    "irrigated": np.array([False]),
    "irrigation_mm": np.array([0.0]),
    "kc_mid_scale": np.array([1.0]),
}


def _wx():
    eto = np.full(365, 3.0)
    return {2019: (np.full(365, 2.0), eto), 2020: (np.full(365, 2.0), eto)}


def test_season_weather_concatenates_two_years():
    r, e = forward.season_weather(_wx(), 2020, CFG)
    assert r.shape == e.shape == (730,)
    assert forward.season_weather(_wx(), 2019, CFG) is None  # 2018 missing


def test_winter_wheat_canopy_starts_before_new_year():
    r, e = forward.season_weather(_wx(), 2020, CFG)
    out = forward.simulate(r, e, H, CROP, CFG)
    assert out["ndvi"].shape == (365, 1)
    assert int(out["sow_day"][0]) == SOW_DAY["winter_wheat"] == -78
    nd = out["ndvi"][:, 0]
    ini, dev, mid, _ = CROP["stages"]
    assert nd[: SOW_DAY["winter_wheat"] + ini].max() == pytest.approx(CFG["ndvi_bare"])
    # canopy peaks in the harvest year, after development, before the 335-day window ends
    peak = int(np.argmax(nd))
    assert (
        SOW_DAY["winter_wheat"] + ini + dev - 1 <= peak <= SOW_DAY["winter_wheat"] + ini + dev + mid
    )
    assert nd.max() > 0.5 + CFG["ndvi_bare"]


def test_spring_crop_unchanged_and_bad_span_rejected():
    cfg = {**forward.load_cfg(), "crop": "maize"}
    assert forward.season_weather(_wx(), 2020, cfg)[0].shape == (365,)
    with pytest.raises(ValueError):
        forward.simulate(np.zeros(365), np.zeros(365), H, CROP, CFG)  # winter needs 730 days
