from fieldwitness.agree.grade import Effect, grade_option

CFG = {
    "A": {"credibility_min": 0.6, "max_key_inputs_tag_A": 0},
    "B": {"min_agreeing_witnesses": 2},
    "D": {"min_share_inputs_tag_A": 0.5},
}
PHYS = Effect(0.10, 0.02, 0.18)
GOOD = {"taw": "D", "kc": "D", "weather": "E"}


def test_grade_a():
    g, _ = grade_option(PHYS, Effect(0.08, 0.0, 0.16), 0.7, GOOD, CFG)
    assert g == "A"


def test_grade_b_physics_plus_own_past_no_neighbours():
    g, r = grade_option(PHYS, None, 0.7, GOOD, CFG)
    assert g == "B" and any("no neighbour" in x for x in r)


def test_grade_b_when_tag_a_input_blocks_a():
    g, r = grade_option(PHYS, Effect(0.08, 0.0, 0.16), 0.7, {**GOOD, "kc": "A"}, CFG)
    assert g == "B" and any("block grade A" in x for x in r)


def test_grade_b_neighbours_agree_low_credibility():
    g, _ = grade_option(PHYS, Effect(0.08, 0.0, 0.16), 0.3, GOOD, CFG)
    assert g == "B"


def test_grade_c_low_credibility_no_neighbours():
    g, _ = grade_option(PHYS, None, 0.3, GOOD, CFG)
    assert g == "C"


def test_grade_c_missing_credibility():
    g, _ = grade_option(PHYS, None, None, GOOD, CFG)
    assert g == "C"


def test_grade_c_neighbours_disagree_sign():
    g, r = grade_option(PHYS, Effect(-0.05, -0.1, -0.01), 0.3, GOOD, CFG)
    assert g == "C" and any("disagree" in x for x in r)


def test_grade_neighbours_disjoint_intervals():
    g, _ = grade_option(PHYS, Effect(0.5, 0.3, 0.7), 0.3, GOOD, CFG)
    assert g == "C"


def test_grade_d_mostly_assumptions():
    g, _ = grade_option(PHYS, Effect(0.08, 0.0, 0.16), 0.9, {"a": "A", "b": "A", "c": "D"}, CFG)
    assert g == "D"


def test_exactly_half_assumptions_is_not_d():
    g, _ = grade_option(PHYS, None, 0.9, {"a": "A", "b": "D"}, CFG)
    assert g == "B"


def test_d_without_inputs_or_physics():
    assert grade_option(PHYS, None, 0.9, {}, CFG)[0] == "D"
    assert grade_option(None, None, 0.9, GOOD, CFG)[0] == "D"
