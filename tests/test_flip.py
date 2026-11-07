import numpy as np

from fieldwitness.rotate.flip import _grid_worlds, advice, smallest_flip, top1_per_world
from fieldwitness.rotate.rank import METRICS

W = {k: 0.0 for k in METRICS} | {"ryi": 1.0}


def test_top1_picks_best_and_breaks_ties_by_index():
    m = np.zeros((3, 2, 6))
    m[2, 0, 0] = 1.0  # world 0: option 2 has best ryi
    # world 1: all equal -> lowest index
    assert top1_per_world(m, W).tolist() == [2, 0]


def test_smallest_flip_orders_by_step_then_sign():
    top = {(-1, 0.1): 0, (1, 0.1): 0, (-1, 0.2): 0, (1, 0.2): 3}
    assert smallest_flip(top, 0, (0.1, 0.2)) == {"sign": 1, "step": 0.2, "new_top": 3}
    assert smallest_flip({(-1, 0.1): 0}, 0, (0.1,)) is None


def _res(share, cf):
    return {"presets": {"balanced": {"flip_share": share, "counterfactual": cf}}}


def test_advice_picks_largest_share_and_reports_flips():
    none = {"taw_mm": None, "kc_scale": None, "budget_mm": None}
    cf = none | {"kc_scale": {"sign": -1, "step": 0.2, "new_top": 3}}
    a = advice(_res({"taw_mm": 0.1, "kc_scale": 0.4, "budget_mm": 0.0}, cf), "balanced")
    assert "Kc" in a.measure_next and "40%" in a.measure_next
    assert a.flip_probability.value == 0.4 and a.flip_probability.tag == "D"
    assert "rank 1 changes at -20%" in a.counterfactual_flip
    z = advice(_res({"taw_mm": 0.0, "kc_scale": 0.0, "budget_mm": 0.0}, none), "balanced")
    assert z.measure_next.startswith("No uncertain")


def test_grid_changes_one_input_and_clips_budget():
    med = {"taw_mm": 100.0, "kc_scale": 1.0, "budget_mm": 30.0}
    g, keys = _grid_worlds(med)
    for j, (x, _sign, _s) in enumerate(keys):
        for k in med:
            if k != x:
                assert g[k][j] == med[k]
        assert g[x][j] >= 0.0
    assert min(g["budget_mm"]) == 0.0
