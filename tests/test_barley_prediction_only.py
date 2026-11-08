"""T7.1c: barley is prediction_only: canopy predictions from Kc + stage lengths, never an RYI.

Synthetic field, real stage lengths from config/crops.yaml (fr_toulouse_t31tcj winter barley,
ua_central_t36uvu spring barley). Sowing days are team choices (A, UNVERIFIED): winter barley
reuses the winter-wheat day (-78), spring barley 105 (15 Apr, Table 11 row "March/Apr").
"""

import numpy as np
import pytest

from fieldwitness.infer import forward

H = {
    "sow_offset_days": np.array([0.0]),
    "taw_scale": np.array([1.0]),
    "irrigated": np.array([False]),
    "irrigation_mm": np.array([0.0]),
    "kc_mid_scale": np.array([1.0]),
}
EASY = {
    y: (np.full(365, 2.0), np.full(365, 3.0)) for y in (2019, 2020)
}  # synthetic weather, no real data


def _cfg(crop: str, sow: int) -> dict:
    cfg = forward.load_cfg()
    return {**cfg, "crop": crop, "nominal_sow_doy": {**cfg["nominal_sow_doy"], crop: sow}}


def test_barley_has_no_ky_so_no_ryi():
    for crop, region in (
        ("winter_barley", "fr_toulouse_t31tcj"),
        ("spring_barley", "ua_central_t36uvu"),
    ):
        p = forward.crop_params(crop, region)
        assert p["ky"] is None


def test_winter_barley_toulouse_canopy_prediction():
    cfg = _cfg("winter_barley", -78)
    crop = forward.crop_params("winter_barley", "fr_toulouse_t31tcj")
    assert crop["stages"] == (30, 140, 40, 30)
    r, e = forward.season_weather(EASY, 2020, cfg)
    out = forward.simulate(r, e, H, crop, cfg)
    nd = out["ndvi"][:, 0]
    assert out["ndvi"].shape == (365, 1) and int(out["sow_day"][0]) == -78
    assert nd.max() > cfg["ndvi_bare"] + 0.4  # canopy develops
    assert np.all(np.isfinite(nd))


def test_spring_barley_ukraine_canopy_prediction():
    cfg = _cfg("spring_barley", 105)
    crop = forward.crop_params("spring_barley", "ua_central_t36uvu")
    assert crop["stages"] == (20, 25, 60, 30)
    r, e = forward.season_weather(EASY, 2020, cfg)
    out = forward.simulate(r, e, H, crop, cfg)
    nd = out["ndvi"][:, 0]
    assert nd[:105].max() == pytest.approx(cfg["ndvi_bare"])  # bare before sowing
    peak = int(np.argmax(nd))
    assert 105 + 20 + 25 - 1 <= peak <= 105 + 20 + 25 + 60
