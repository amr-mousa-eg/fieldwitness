import pytest

from fieldwitness.config import load_crops
from fieldwitness.rotate.candidates import enumerate_candidates
from fieldwitness.rotate.priority import (
    deep_root_share,
    family_breaks,
    legume_share,
    sequence_metrics,
)
from fieldwitness.schemas import SEQUENCE_ONLY_METRICS

CROPS = load_crops()


def test_legume_share():
    assert legume_share(("soybean", "maize", "soybean"), CROPS) == pytest.approx(2 / 3)
    assert legume_share(("maize", "sorghum", "fallow"), CROPS) == 0.0


def test_family_breaks():
    assert family_breaks(("maize", "sorghum", "winter_wheat"), CROPS) == 0  # all Poaceae
    assert family_breaks(("maize", "soybean", "maize"), CROPS) == 2
    assert family_breaks(("maize", "fallow", "maize"), CROPS) == 2  # fallow counts (A)


def test_deep_root_share():
    # winter wheat range 1.5-1.8 m -> deep; maize 1.0-1.7 -> deep; fallow -> no depth
    assert deep_root_share(("winter_wheat", "fallow", "fallow"), CROPS) == pytest.approx(1 / 3)


def test_all_metrics_present_and_tagged_for_every_kansas_option():
    for seq in enumerate_candidates("ks_t14slh"):
        m = sequence_metrics(seq, CROPS)
        assert set(m) == SEQUENCE_ONLY_METRICS
        assert all(t.value is not None and t.tag in ("D", "A") for t in m.values())
        assert 0 <= m["legume_share"].value <= 1
        assert 0 <= m["family_breaks"].value <= len(seq) - 1
