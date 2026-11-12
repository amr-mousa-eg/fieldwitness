"""The post-hackathon stubs import without torch/sbi and raise NotImplementedError."""

import sys

import pytest

from fieldwitness.experimental.neural_infer import AmortisedNPE
from fieldwitness.experimental.neural_physics import NeuralFAO56


@pytest.mark.parametrize("cls", [NeuralFAO56, AmortisedNPE])
def test_stub_raises(cls):
    with pytest.raises(NotImplementedError, match="Post-hackathon work; not implemented"):
        cls()


def test_no_heavy_import_at_module_level():
    assert "torch" not in sys.modules
    assert "sbi" not in sys.modules
