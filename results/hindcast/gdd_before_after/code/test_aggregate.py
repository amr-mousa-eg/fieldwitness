"""Tests for the before/after aggregation helpers.

Run: uv run pytest -q results/hindcast/gdd_before_after/code
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate as ag  # noqa: E402


def test_boot_matches_t7_diagnosis_algorithm():
    # same algorithm as scripts/t7_diagnosis.block_bootstrap (blocks in order of appearance)
    rng0 = np.random.default_rng(0)
    df = pd.DataFrame({"block": rng0.choice(list("abcdefgh"), 60), "v": rng0.normal(size=60)})
    blocks = df["block"].unique()
    rng = np.random.default_rng(42)
    idxs = [df.index[df["block"] == b].to_numpy() for b in blocks]
    means = []
    for _ in range(1000):
        s = rng.choice(len(blocks), size=len(blocks), replace=True)
        means.append(df.loc[np.concatenate([idxs[i] for i in s]), "v"].mean())
    r = ag.boot(df["v"], df["block"])
    assert r["value"] == pytest.approx(df["v"].mean())
    assert r["ci_low"] == pytest.approx(np.percentile(means, 2.5))
    assert r["ci_high"] == pytest.approx(np.percentile(means, 97.5))


def test_boot_median_constant():
    r = ag.boot([3.0] * 10, list("aabbccddee"), stat="median")
    assert r == {"value": 3.0, "ci_low": 3.0, "ci_high": 3.0, "n": 10}


def test_classify_band_edges():
    assert ag.classify(-5.0, 5.0) == "within noise"
    assert ag.classify(5.0, 5.0) == "within noise"
    assert ag.classify(-5.01, 5.0) == "improved"
    assert ag.classify(5.01, 5.0) == "worse"


def test_cell_too_few():
    df = pd.DataFrame({"block": ["a"] * 19, **{m: [1.0] * 19 for m in ag.METRICS}})
    assert ag.cell(df) == {"n": 19, "too_few_to_judge": True}


def test_per_field_means_and_classes():
    m = pd.DataFrame(
        {
            "crop": ["maize"] * 3,
            "field_id": ["f1", "f1", "f2"],
            "d_peak_abs_err": [-10.0, -2.0, 1.0],
            "d_ci_crps": [0.5, 0.5, 3.0],
        }
    )
    g = ag.per_field(m, {"maize": 20.0}).set_index("field_id")
    assert g.loc["f1", "d_peak_abs_err"] == -6.0 and g.loc["f1", "timing_class"] == "improved"
    assert g.loc["f1", "n_seasons"] == 2
    assert g.loc["f2", "crps_class"] == "worse"  # 3.0 > 10 % of 20
    assert g.loc["f1", "crps_class"] == "within noise"


def test_pick_examples_fixed_rule():
    elig = {"maize": ["c", "a", "b", "d"], "sorghum": ["x", "y", "z"]}
    got = ag.pick_examples(elig, {"maize": 2, "sorghum": 3})
    exp = list(np.random.default_rng(42).choice(["a", "b", "c", "d"], 2, replace=False))
    assert got["maize"] == exp
    assert sorted(got["sorghum"]) == ["x", "y", "z"]
