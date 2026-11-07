import numpy as np
import pandas as pd

from fieldwitness.packs import extras as X
from fieldwitness.schemas import check_tagged


def test_bare_by_option_fallow_always_bare_and_crop_not():
    fallow = np.zeros(2 * 365)
    crop = np.ones(2 * 365)
    out = X.bare_by_option({"fallow": fallow, "crop": crop})
    assert out["fallow"].values == [1.0] * 12
    assert out["crop"].values == [0.0] * 12
    assert out["fallow"].tag == "D" and len(out["fallow"].x) == 12


def test_worst_month_share_none_when_empty():
    assert X.worst_month_share([], "frost") is None


def test_regions_list_and_smap_layer_tagged():
    rl = X.regions_list([("ks_t14slh", "Kansas", 1)])
    assert rl.regions[0].tier == 1
    rows = [
        {"region_id": "r", "month": f"{y}-{m:02d}", "anomaly": 0.01 * (y - 2016)}
        for y in (2016, 2017, 2018)
        for m in range(1, 13)
    ]
    lay = X.smap_layer(pd.DataFrame(rows), -100.0, 38.0)
    assert lay.scale_flag and lay.grid.years == [2016, 2017, 2018]
    assert abs(lay.trend.value - 0.01) < 1e-6
    assert check_tagged(lay) == []
