"""Evidence grade A-D for one option (PLAN.md section 4, T6.5).

Rule (thresholds in ``config/grading.yaml``, all tag A, UNVERIFIED team choices):
  D  decision-driving inputs mostly tag A (share > min_share_inputs_tag_A)
  A  physics and neighbours agree (same sign, 90 % intervals overlap)
     AND credibility >= credibility_min AND key inputs tagged A <= max_key_inputs_tag_A
  B  at least two witnesses agree
  C  otherwise (one witness only, or witnesses disagree)
Witnesses: physics (always, if it has an estimate); own past (counts as agreeing when
credibility >= credibility_min, because credibility measures physics-vs-HLS agreement);
neighbours (agree = same sign and overlapping 90 % intervals).
Without a neighbour estimate the maximum grade is B (PLAN.md walking skeleton).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    """Effect of an option versus Current, with a 90 % interval."""

    value: float
    lo90: float
    hi90: float


def _same_sign(a: Effect, b: Effect) -> bool:
    return a.value != 0 and b.value != 0 and (a.value > 0) == (b.value > 0)


def _overlap(a: Effect, b: Effect) -> bool:
    return max(a.lo90, b.lo90) <= min(a.hi90, b.hi90)


def grade_option(
    physics: Effect | None,
    neighbours: Effect | None,
    credibility: float | None,
    key_input_tags: dict[str, str],
    cfg: dict,
) -> tuple[str, list[str]]:
    """Return (grade, reasons). ``cfg`` is the ``grades`` block of grading.yaml."""
    reasons: list[str] = []
    tags = list(key_input_tags.values())
    n_a = sum(t == "A" for t in tags)
    share_a = n_a / len(tags) if tags else 1.0  # no declared inputs: treat as unknown (A)
    if share_a > cfg["D"]["min_share_inputs_tag_A"]:
        reasons.append(f"{n_a} of {len(tags)} key inputs are assumptions (tag A)")
        return "D", reasons
    if physics is None:
        reasons.append("no physics estimate")
        return "D", reasons

    cred_min = cfg["A"]["credibility_min"]
    cred_ok = credibility is not None and credibility >= cred_min
    reasons.append(
        f"own past agrees (credibility {credibility:.2f} >= {cred_min})"
        if cred_ok
        else "own past not supporting (credibility missing or below threshold)"
    )
    agree = 1 + int(cred_ok)  # physics + own past
    nb_ok = False
    if neighbours is None:
        reasons.append("no neighbour estimate")
    else:
        nb_ok = _same_sign(physics, neighbours) and _overlap(physics, neighbours)
        reasons.append(
            "neighbours agree with physics"
            if nb_ok
            else "neighbours disagree with physics (sign or 90 % intervals)"
        )
        agree += int(nb_ok)

    if nb_ok and cred_ok and n_a <= cfg["A"]["max_key_inputs_tag_A"]:
        return "A", reasons
    if agree >= cfg["B"]["min_agreeing_witnesses"]:
        if nb_ok and n_a > cfg["A"]["max_key_inputs_tag_A"]:
            reasons.append(f"{n_a} key input(s) tagged A block grade A")
        return "B", reasons
    return "C", reasons
