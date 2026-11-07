"""T8.1 validator: unit checks on tiny dirs, plus the real Kansas packs when present."""

import json
from pathlib import Path

import pytest

from fieldwitness.packs.validate import MAX_BYTES, model_for, validate_dir
from fieldwitness.schemas import FieldCalendar, FieldPack, RegionHindcast


def test_model_for():
    assert model_for("hindcast.json") is RegionHindcast
    assert model_for("f1.calendar.json") is FieldCalendar
    assert model_for("f1.json") is FieldPack


def test_empty_dir_is_a_problem(tmp_path: Path):
    assert validate_dir(tmp_path)


def test_bad_file_and_size(tmp_path: Path):
    (tmp_path / "f1.json").write_text(json.dumps({"nope": 1}))
    (tmp_path / "f2.json").write_text(" " * MAX_BYTES + "{}")
    probs = validate_dir(tmp_path)
    assert any(p.startswith("f1.json") for p in probs)
    assert any("bytes" in p for p in probs)


@pytest.mark.needs_data("packs/ks_t14slh/index.json")
def test_kansas_packs_valid():
    assert validate_dir(Path("packs/ks_t14slh")) == []
