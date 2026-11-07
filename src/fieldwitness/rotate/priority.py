"""Priority metrics that depend only on the crop sequence (PLAN.md T6.7, part 1).

Metrics (labels exactly as in PLAN T6.7), all tag D (derived by rules from verified crop data):
- legume_share: share of seasons with a Fabaceae crop ("nitrogen-fixing crops in the rotation").
  Family from GBIF, `config/crops.yaml`. No kg N claim.
- family_breaks: number of family changes between consecutive seasons
  ("pest and disease break opportunities"). Fallow has no family, so a transition into or out
  of fallow counts as a break (it interrupts the host, A, UNVERIFIED team choice).
- deep_root_share: share of seasons with a crop whose maximum rooting depth is above
  DEEP_ROOT_M ("deep-rooting crops in the rotation"). Depth: FAO-56 Table 22 range in
  `config/crops.yaml` (verified); the threshold is a team choice (A, UNVERIFIED), compared with
  the upper end of the range.
- forage_value: share of seasons whose crop has a forage use. No cited source read yet, so the
  per-crop yes/no list is tag A, UNVERIFIED (PLAN allows tag A in that case).
Erosion exposure and residue proxy need simulated cover and rain: later part of T6.7.
"""

from fieldwitness.config import CropsFile, load_crops
from fieldwitness.schemas import SEQUENCE_ONLY_METRICS, Tagged

DEEP_ROOT_M = 1.5  # A, UNVERIFIED team choice; compared with the upper end of Table 22 range
# A, UNVERIFIED: forage use per crop key (no source read). Unlisted crops count as no.
FORAGE_CROPS = frozenset({"cover_crop", "sorghum", "maize", "oats", "alfalfa"})

LABELS = {
    "legume_share": "nitrogen-fixing crops in the rotation",
    "family_breaks": "pest and disease break opportunities",
    "deep_root_share": "deep-rooting crops in the rotation",
    "forage_value": "forage use in the rotation (assumed list)",
}
NON_CROP = ("fallow", "cover_crop")


def _family(crop: str, crops: CropsFile) -> str | None:
    f = crops.crops[crop].family
    return f.value if f is not None else None


def _deep(crop: str, crops: CropsFile) -> bool:
    rd = crops.crops[crop].root_depth_m
    if rd is None or not rd.verified:
        return False
    hi = rd.range[1] if rd.range else (rd.value if isinstance(rd.value, float) else None)
    return hi is not None and hi >= DEEP_ROOT_M


def legume_share(seq: tuple[str, ...], crops: CropsFile) -> float:
    return sum(_family(c, crops) == "Fabaceae" for c in seq) / len(seq)


def family_breaks(seq: tuple[str, ...], crops: CropsFile) -> int:
    """Count transitions where the next season is not the same family as the previous one."""
    n = 0
    for a, b in zip(seq, seq[1:], strict=False):
        fa, fb = _family(a, crops), _family(b, crops)
        if fa is None or fb is None or fa != fb:
            n += 1
    return n


def deep_root_share(seq: tuple[str, ...], crops: CropsFile) -> float:
    return sum(_deep(c, crops) for c in seq) / len(seq)


def forage_share(seq: tuple[str, ...]) -> float:
    return sum(c in FORAGE_CROPS for c in seq) / len(seq)


def sequence_metrics(seq: tuple[str, ...], crops: CropsFile | None = None) -> dict[str, Tagged]:
    """The four sequence-only metrics as `Tagged` values (keys = SEQUENCE_ONLY_METRICS)."""
    crops = crops or load_crops()
    d = "crop family: GBIF backbone + USDA PLANTS (config/crops.yaml)"
    out = {
        "legume_share": Tagged(
            value=legume_share(seq, crops), unit="share of seasons", tag="D", source=d
        ),
        "family_breaks": Tagged(
            value=float(family_breaks(seq, crops)),
            unit="count",
            tag="D",
            source=d + "; fallow/cover counts as a break (A)",
        ),
        "deep_root_share": Tagged(
            value=deep_root_share(seq, crops),
            unit="share of seasons",
            tag="D",
            source=f"FAO-56 Table 22 max rooting depth >= {DEEP_ROOT_M} m (threshold A)",
        ),
        "forage_value": Tagged(
            value=forage_share(seq),
            unit="share of seasons",
            tag="A",
            source="team list of forage crops, no source read (A, UNVERIFIED)",
        ),
    }
    assert set(out) == set(SEQUENCE_ONLY_METRICS)
    return out
