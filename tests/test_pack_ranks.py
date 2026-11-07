"""Built Kansas packs carry each option's own rank (bug fix: they used to carry the sort order).

Checks every pack against `results/rotate/ranking.json` (T6.3) and every scenario file against
`results/rotate/scenarios.json` (T6.8). Needs the locally built packs (`packs/` is gitignored).
"""

import json
from pathlib import Path

import pytest

from fieldwitness.packs.build import PRESET
from fieldwitness.rotate.rank import rank_positions

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs" / "ks_t14slh"
RANKING = ROOT / "results" / "rotate" / "ranking.json"
SCENARIOS = ROOT / "results" / "rotate" / "scenarios.json"


def _oid(cand: list[str]) -> str:
    return "|".join(cand)


def _field_packs():
    for f in sorted(PACKS.glob("*.json")):
        if f.name.count(".") == 1 and f.stem not in {"index", "hindcast", "layers"}:
            yield f


def test_rank_positions_inverts_order():
    assert rank_positions([2, 0, 1]) == [2, 3, 1]
    assert rank_positions([]) == []


@pytest.mark.needs_data("packs/ks_t14slh/index.json", "results/rotate/ranking.json")
def test_every_pack_option_rank_matches_ranking_json():
    rk = json.loads(RANKING.read_text("utf-8"))
    files = list(_field_packs())
    assert len(files) == len(rk)
    for f in files:
        p = json.loads(f.read_text("utf-8"))
        r = rk[p["field"]["field_id"]]
        want = dict(zip(map(_oid, r["candidates"]), rank_positions(r["rank"][PRESET]), strict=True))
        got = {o["option_id"]: o["rank"] for o in p["options"] if o["option_id"] != "current"}
        assert got == want, f.name
        # rank 1 is the option with the highest balanced score (ties: lowest candidate index)
        score = r["score"][PRESET]
        top = next(oid for oid, k in got.items() if k == 1)
        i_top = [_oid(c) for c in r["candidates"]].index(top)
        assert score[i_top] == max(score), f.name
        assert i_top == min(i for i, s in enumerate(score) if s == max(score)), f.name


@pytest.mark.needs_data("packs/ks_t14slh/index.json", "results/rotate/scenarios.json")
def test_every_scenario_rank_matches_scenarios_json():
    sc = json.loads(SCENARIOS.read_text("utf-8"))
    rk = json.loads(RANKING.read_text("utf-8"))
    for f in _field_packs():
        fid = f.name.split(".")[0]
        cands = [_oid(c) for c in rk[fid]["candidates"]]
        fs = json.loads((PACKS / f"{fid}.scenarios.json").read_text("utf-8"))
        for s in fs["scenarios"]:
            order = sc[fid][s["scenario_id"]]["rank_balanced"]
            assert s["ranks"] == dict(zip(cands, rank_positions(order), strict=True)), fid
            assert s["ranks"][cands[order[0]]] == 1, fid
