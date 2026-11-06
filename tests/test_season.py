import numpy as np

from fieldwitness.physics import kc as kcm
from fieldwitness.physics import season, waterbal


def test_ryi_formula():
    assert np.isclose(season.relative_yield_index(80, 100, 1.25), 1 - 1.25 * 0.2)
    assert season.relative_yield_index(100, 100, 1.25) == 1.0
    assert season.relative_yield_index(0, 100, 5.0) == 0.0  # clipped
    assert np.isnan(season.relative_yield_index(80, 100, None))


def test_season_outputs_rainfed_vs_irrigated():
    kc = kcm.kc_curve((20, 30, 40, 30), 0.3, 1.2, 0.5)
    etc = kc * 6.0
    rain = np.zeros(len(kc))
    t = waterbal.taw(0.30, 0.15, 1.0)
    r = waterbal.run(rain, etc, t, 0.5)
    i = waterbal.run(rain, etc, t, 0.5, waterbal.trigger_at_raw(0.8))
    a = season.season_outputs(r, etc, kc, 1.2, 1.25)
    b = season.season_outputs(i, etc, kc, 1.2, 1.25)
    assert a["tag"] == "D" and a["irr_mm"] == 0
    assert b["irr_mm"] > 0 and b["irr_gross_mm"] > b["irr_mm"]
    assert 0 <= a["ryi"] < b["ryi"] <= 1
    assert a["cover_days"] == b["cover_days"] > 0
    assert a["canopy"].max() == 1.0
