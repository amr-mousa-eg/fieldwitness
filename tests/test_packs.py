"""T8.1 pack builder: pure parts always; full build on 2 fields only with local data."""

import json
from datetime import date

import pytest

from fieldwitness.packs import build as B
from fieldwitness.packs.run import _slim, build_region
from fieldwitness.schemas import FieldPack, FieldScenarios, RegionIndex, check_tagged


def test_slim_drops_null_bounds_but_keeps_value():
    o = {"value": None, "lo90": None, "hi90": 1.0, "unit": "x"}
    assert _slim(o) == {"value": None, "hi90": 1.0, "unit": "x"}


def test_field_scenarios_has_12_and_no_sequence_only_metrics():
    ids = [f"t+{t}_p{p}" for t in (0, 1, 2) for p in ("-20", "-10", "+0", "+10")]
    cands = [["sorghum", "fallow", "sorghum"], ["fallow", "maize", "fallow"]]
    one = {
        "ryi": [0.1, 0.2],
        "cvar10_ryi": [0.0, 0.1],
        "cover_days": [10, 20],
        "water_use_mm": [900.0, 950.0],
        "irrigation_mm": [0.0, 5.0],
        "cvar10_water_mm": [1000.0, 1100.0],
        "rank_balanced": [2, 1],
    }
    fs = B.field_scenarios("f", {i: one for i in ids}, cands, "D", date(2024, 12, 31))
    assert len(fs.scenarios) == 12 and fs.baseline_id in ids
    assert fs.scenarios[0].ranks["fallow|maize|fallow"] == 1
    assert not check_tagged(fs)
    FieldScenarios.model_validate_json(fs.model_dump_json())


@pytest.mark.needs_data("data/fields/ks_t14slh_hls_series.parquet")
def test_build_two_fields(tmp_path):
    res = build_region("ks_t14slh", out_root=tmp_path, limit=2)
    assert res["problems"] == [] and res["fields"] == 2
    d = tmp_path / "ks_t14slh"
    idx = RegionIndex.model_validate_json((d / "index.json").read_text("utf-8"))
    fid = idx.fields[0].field_id
    pack = FieldPack.model_validate_json((d / f"{fid}.json").read_text("utf-8"))
    assert pack.options[0].option_id == "current" and len(pack.options) == 37
    assert all(o.explanation.gaps and o.explanation.risks for o in pack.options)
    assert not check_tagged(pack)
    assert (d / f"{fid}.series.json").stat().st_size < 300_000
    json.loads((d / f"{fid}.scenarios.json").read_text("utf-8"))
