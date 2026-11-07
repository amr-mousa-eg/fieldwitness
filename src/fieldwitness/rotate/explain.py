"""Deterministic strategy explanation (PLAN.md T6.6, schema ``Explanation``).

Pure templates over computed numbers and flags. No LLM. Every sentence names the number
or flag it comes from. ``gaps`` and ``risks`` are never empty: the fixed lines below hold
for every option (the metric weights are tag A; disease, markets, timing and equipment are
not modelled).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fieldwitness.schemas import Explanation

NON_CROP = ("fallow", "cover_crop")


@dataclass(frozen=True)
class Delta:
    """One metric versus Current: value with 90 % interval, unit, source tag."""

    value: float
    lo90: float
    hi90: float
    unit: str
    tag: str


@dataclass(frozen=True)
class ExplainInput:
    sequence: tuple[str, ...]
    current: tuple[str, ...]
    grade: str
    grade_reasons: tuple[str, ...]
    credibility: float | None
    key_input_tags: dict[str, str]
    deltas: dict[str, Delta] = field(default_factory=dict)
    profile: str = "balanced"
    rank: int | None = None  # 1-based (1 = best), as Option.rank
    pareto: bool | None = None
    family: dict[str, str | None] = field(default_factory=dict)
    ky_verified: dict[str, bool] = field(default_factory=dict)
    scale_flag: bool = False
    has_neighbours: bool = False
    is_current: bool = False


def family_breaks(seq: tuple[str, ...], family: dict[str, str | None]) -> int:
    """Count steps where the crop family changes, or a fallow/cover season intervenes."""
    n = 0
    for a, b in zip(seq, seq[1:], strict=False):
        if a in NON_CROP or b in NON_CROP:
            n += 1
        elif family.get(a) is not None and family.get(a) != family.get(b):
            n += 1
    return n


def _fmt(d: Delta) -> str:
    sign = "+" if d.value > 0 else ""
    return (
        f"{sign}{d.value:.2f} {d.unit} vs Current (90 % interval {d.lo90:.2f} to "
        f"{d.hi90:.2f}, tag {d.tag})"
    )


def explain(x: ExplainInput) -> Explanation:
    seq = " > ".join(x.sequence)
    why: list[str] = []
    evidence: list[str] = []
    benefits: list[str] = []
    gaps: list[str] = []
    risks: list[str] = []

    # why
    if x.is_current:
        why.append(f"This is the field's current rotation ({seq}), from crop labels (tag E).")
    else:
        if x.rank is not None:
            why.append(f"Rank {x.rank} under the '{x.profile}' priority profile (weights tag A).")
        if x.pareto is not None:
            why.append(
                "On the Pareto front: no other option is better on every metric."
                if x.pareto
                else "Not on the Pareto front: another option is at least as good on every metric."
            )
        fb = family_breaks(x.sequence, x.family)
        why.append(f"{fb} crop-family break(s) in the {len(x.sequence)}-season sequence.")
        n_crop = sum(1 for c in x.sequence if c not in NON_CROP)
        why.append(f"{n_crop} harvested crop season(s) out of {len(x.sequence)}.")

    # evidence
    evidence.append(f"Evidence grade {x.grade}: " + "; ".join(x.grade_reasons) + ".")
    if x.credibility is None:
        evidence.append("Own-past credibility: missing for this field.")
    else:
        evidence.append(f"Own-past credibility {x.credibility:.2f} (tag D, in-sample).")
    evidence.append("Physics witness: FAO-56 water balance over posterior worlds (tag D).")
    evidence.append(
        "Neighbour witness present."
        if x.has_neighbours
        else "Neighbour witness absent: grade cannot exceed B."
    )

    # benefits
    for name in sorted(x.deltas):
        benefits.append(f"{name}: {_fmt(x.deltas[name])}.")
    if not benefits:
        benefits.append(
            "No metric change to report."
            if x.is_current
            else "No metric deltas available for this option."
        )

    # gaps
    tag_a = sorted(k for k, t in x.key_input_tags.items() if t == "A")
    if tag_a:
        gaps.append("Key inputs that are assumptions (tag A): " + ", ".join(tag_a) + ".")
    if not x.has_neighbours:
        gaps.append("No neighbour witness (Phase 5 estimate missing).")
    if x.scale_flag:
        gaps.append("Scale flag raised: pixel area exceeds a quarter of the field area.")
    gaps.append("Priority weights and crop-family limit are team choices (tag A, UNVERIFIED).")

    # risks
    missing_ky = sorted(
        {c for c in x.sequence if c not in NON_CROP and not x.ky_verified.get(c, False)}
    )
    if missing_ky:
        risks.append("No verified yield-response factor Ky for: " + ", ".join(missing_ky) + ".")
    if any(c in NON_CROP for c in x.sequence):
        risks.append("Fallow and cover seasons score 0 in the Relative Yield Index (no harvest).")
    risks.append(
        "Local review needed: disease and pest pressure, sowing timing, markets and equipment "
        "are not modelled."
    )

    return Explanation(why=why, evidence=evidence, benefits=benefits, gaps=gaps, risks=risks)
