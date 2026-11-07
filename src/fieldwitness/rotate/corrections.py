"""Farmer corrections to the Current rotation (PLAN.md T6.9).

A correction is ground data entered by the farmer: tag E, source "farmer". The satellite/label
version is kept next to it, so the UI can show both. Pure functions; the browser stores the
corrections, this module defines what they do to the Current option.

Crop-history corrections change the Current sequence directly (it is just labels). Sowing date
and irrigation change the physics, so they need a re-run: in the static demo only a precomputed
alternative (looked up by key) can be shown, otherwise the status is `RERUN_NEEDED`.
"""

from dataclasses import dataclass, field, replace

from fieldwitness.rotate.current import FALLOW, CurrentRotation

RERUN_NEEDED = "re-run needed: available in live mode"
SOURCE_FARMER = "farmer"
SOURCE_LABEL = "label"


@dataclass(frozen=True)
class Corrections:
    crop_by_year: dict[int, str] = field(default_factory=dict)  # season year -> crop key
    sowing_day: dict[int, int] = field(default_factory=dict)  # season year -> day of year
    irrigated: bool | None = None  # None = not corrected


@dataclass(frozen=True)
class CorrectedCurrent:
    original: CurrentRotation  # satellite/label version, always kept
    corrected: CurrentRotation
    source_by_year: dict[int, str]  # "farmer" or "label"
    needs_rerun: bool  # sowing/irrigation entered but no precomputed alternative
    notes: list[str] = field(default_factory=list)


def apply_corrections(
    cur: CurrentRotation,
    corr: Corrections,
    allowed: set[str],
    alternatives: set[str] | None = None,
) -> CorrectedCurrent:
    """Apply `corr` to `cur`. `alternatives` = correction keys with a precomputed pack."""
    ok = allowed | {FALLOW}
    bad = [y for y in corr.crop_by_year if y not in cur.years]
    if bad:
        raise ValueError(f"years {bad} are not in the Current rotation {cur.years}")
    seq = [corr.crop_by_year.get(y, c) for y, c in zip(cur.years, cur.sequence, strict=True)]
    source = {y: SOURCE_FARMER if y in corr.crop_by_year else SOURCE_LABEL for y in cur.years}
    # farmer entry replaces the label: the double-crop note and the "not simulated" gap
    # for a corrected season no longer apply.
    gaps = [g for g in cur.gaps if not any(g.startswith(f"{y}:") for y in corr.crop_by_year)]
    second = {y: c for y, c in cur.second_crops.items() if y not in corr.crop_by_year}
    for y, c in zip(cur.years, seq, strict=True):
        if source[y] == SOURCE_FARMER and c not in ok:
            gaps.append(f"{y}: '{c}' (farmer-entered) is not simulated")
    corrected = replace(
        cur,
        sequence=seq,
        gaps=gaps,
        second_crops=second,
        simulatable=all(c in ok for c in seq),
    )
    notes = [f"{y}: crop set by farmer (tag E, farmer-entered)" for y in corr.crop_by_year]
    needs_rerun = False
    physics_changed = bool(corr.sowing_day) or corr.irrigated is not None
    if physics_changed or corr.crop_by_year:
        key = correction_key(corr)
        if alternatives is not None and key in alternatives:
            notes.append(f"precomputed alternative '{key}' available")
        elif physics_changed or any(c != o for c, o in zip(seq, cur.sequence, strict=True)):
            needs_rerun = True
            notes.append(RERUN_NEEDED)
    return CorrectedCurrent(cur, corrected, source, needs_rerun, notes)


def correction_key(corr: Corrections) -> str:
    """Stable key of a correction set, used to name a precomputed alternative."""
    parts = [f"c{y}={c}" for y, c in sorted(corr.crop_by_year.items())]
    parts += [f"s{y}={d}" for y, d in sorted(corr.sowing_day.items())]
    if corr.irrigated is not None:
        parts.append(f"irr={int(corr.irrigated)}")
    return ";".join(parts)
