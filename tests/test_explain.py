from fieldwitness.rotate.explain import Delta, ExplainInput, explain, family_breaks

FAM = {"maize": "Poaceae", "sorghum": "Poaceae", "soybean": "Fabaceae", "fallow": None}


def _x(**kw):
    base = dict(
        sequence=("maize", "soybean", "fallow"),
        current=("maize", "maize", "maize"),
        grade="C",
        grade_reasons=("no neighbour estimate",),
        credibility=0.5,
        key_input_tags={"taw": "D", "sowing_dates": "A"},
        deltas={"ryi": Delta(0.1, -0.05, 0.2, "RYI", "D")},
        family=FAM,
        ky_verified={"maize": True, "soybean": True},
    )
    base.update(kw)
    return ExplainInput(**base)


def test_family_breaks():
    assert family_breaks(("maize", "maize"), FAM) == 0
    assert family_breaks(("maize", "soybean"), FAM) == 1
    assert family_breaks(("maize", "fallow", "maize"), FAM) == 2


def test_why_has_rank_and_pareto():
    e = explain(_x(rank=0, pareto=True))
    assert any("Rank 1" in s for s in e.why)
    assert any("On the Pareto front" in s for s in e.why)
    assert not any("Not on" in s for s in e.why)
    e = explain(_x(rank=3, pareto=False))
    assert any("Not on the Pareto front" in s for s in e.why)


def test_evidence_grade_and_credibility():
    e = explain(_x())
    assert e.evidence[0].startswith("Evidence grade C")
    assert any("0.50" in s for s in e.evidence)
    e = explain(_x(credibility=None))
    assert any("missing" in s for s in e.evidence)
    assert any("absent" in s for s in explain(_x()).evidence)
    assert any("present" in s for s in explain(_x(has_neighbours=True)).evidence)


def test_benefits_template():
    e = explain(_x())
    assert e.benefits == ["ryi: +0.10 RYI vs Current (90 % interval -0.05 to 0.20, tag D)."]
    assert "No metric deltas" in explain(_x(deltas={})).benefits[0]
    assert "No metric change" in explain(_x(deltas={}, is_current=True)).benefits[0]


def test_gaps_tag_a_and_scale():
    e = explain(_x(scale_flag=True))
    assert any("sowing_dates" in s and "taw" not in s for s in e.gaps)
    assert any("Scale flag" in s for s in e.gaps)
    assert not any("Scale flag" in s for s in explain(_x()).gaps)


def test_risks_ky_and_fallow():
    e = explain(_x(ky_verified={"maize": True}))
    assert any("soybean" in s and "Ky" in s for s in e.risks)
    assert any("Fallow" in s for s in e.risks)
    e = explain(_x(sequence=("maize", "maize"), current=("maize",)))
    assert not any("Fallow" in s for s in e.risks)


def test_gaps_and_risks_never_empty():
    for x in (
        _x(),
        _x(deltas={}, key_input_tags={}, has_neighbours=True, is_current=True),
        _x(sequence=("maize",), ky_verified={"maize": True}),
    ):
        e = explain(x)
        assert e.gaps and e.risks and e.why and e.evidence and e.benefits
