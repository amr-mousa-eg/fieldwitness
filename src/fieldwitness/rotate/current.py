"""Current rotation of a field (PLAN.md T6.0): its last three seasons, always option 1 ("Current").

Tier 1-2: seasons come from the CSB labels (tag E, USDA; confidence 1.0 because it is a label, not
a model output). Tier 3 will use the classifier (T2.3, postponed) and its `crop_conf`.
All reads go through `labels.read`, so the `as_of` guard applies.
"""

from dataclasses import dataclass, field

import pandas as pd

from fieldwitness.data import labels as labels_mod

CURRENT_ID = "current"
N_SEASONS = 3
FALLOW = "fallow"


@dataclass(frozen=True)
class CurrentRotation:
    field_id: str
    years: tuple[int, ...]  # season years, oldest first
    sequence: list[str]  # crop keys or history states, oldest first
    confidence: float  # min over seasons; 1.0 for labels
    tag: str = "E"
    simulatable: bool = True
    gaps: list[str] = field(default_factory=list)  # shown to the user (PLAN T6.0)
    second_crops: dict[int, str] = field(default_factory=dict)  # year -> double-crop second crop

    @property
    def option_id(self) -> str:
        return CURRENT_ID


def current_rotation(
    field_id: str,
    allowed: set[str],
    table: pd.DataFrame | None = None,
    region_id: str = "ks_t14slh",
) -> CurrentRotation:
    """Last `N_SEASONS` labelled seasons of one field (after the `as_of` cut-off, if active).

    `allowed` = crops the physics can simulate (rotation options) ; fallow is always simulatable.
    A season whose label is outside that set stays in the sequence and is listed as a gap.
    """
    t = labels_mod.read(region_id, table)
    t = t[t["field_id"] == field_id].sort_values("year").tail(N_SEASONS)
    if t.empty:
        raise ValueError(f"no labels for field {field_id}")
    ok = allowed | {FALLOW}
    seq, gaps, second = [], [], {}
    for r in t.itertuples():
        seq.append(r.crop)
        if isinstance(r.double_crop_second, str):
            second[int(r.year)] = r.double_crop_second
            gaps.append(
                f"{r.year}: double crop {r.crop} + {r.double_crop_second}; "
                f"only the first crop is simulated"
            )
        if r.crop not in ok:
            gaps.append(f"{r.year}: '{r.crop}' is not simulated (no rotation-option parameters)")
    if len(seq) < N_SEASONS:
        gaps.append(f"only {len(seq)} labelled season(s) available")
    return CurrentRotation(
        field_id=field_id,
        years=tuple(int(y) for y in t["year"]),
        sequence=seq,
        confidence=1.0,
        simulatable=all(c in ok for c in seq),
        gaps=gaps,
        second_crops=second,
    )


def all_current(
    allowed: set[str], table: pd.DataFrame | None = None, region_id: str = "ks_t14slh"
) -> dict[str, CurrentRotation]:
    """Current rotation for every field in the label table."""
    t = labels_mod.read(region_id, table)
    return {f: current_rotation(f, allowed, t, region_id) for f in sorted(t["field_id"].unique())}
