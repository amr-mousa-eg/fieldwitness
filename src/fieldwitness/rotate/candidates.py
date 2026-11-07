"""Candidate rotations (PLAN.md T6.1): hard constraints only, no simulation.

A candidate is a sequence of N_SEASONS crop keys (oldest first). Constraints, in this order:
1. allowed crops = `fieldwitness.config.rotation_options` of the region, minus user bans;
2. calendar fit: total stage length (FAO-56 Table 11 row of the region) must fit the season
   window of the crop in `config/regions.yaml` (tag A, month-granular, so `SLACK_DAYS` tolerance);
   crops without stage lengths (fallow, cover crop) always fit. Observed local SOS/EOS are not
   used yet (T2.2 failed its acceptance), so the configured windows stand in. UNVERIFIED (A);
3. at most `max_consecutive_family` seasons in a row of the same botanical family
   (default 2, a team choice, tag A, UNVERIFIED). Fallow has no family and breaks a run;
4. at least one harvested crop, and no two consecutive non-crop seasons (fallow / cover crop)
   (team choice 2026-11-07, tag A, UNVERIFIED).
"""

from calendar import monthrange
from itertools import product

from fieldwitness.config import CropsFile, Region, load_crops, load_regions, rotation_options

N_SEASONS = 3
MAX_CONSECUTIVE_FAMILY = 2  # A, UNVERIFIED team choice
SLACK_DAYS = 7  # A: windows are whole months, stage sums are in days
NON_CROP_KEYS = frozenset({"fallow", "cover_crop"})
WINTER_CROPS = {"winter_wheat", "winter_barley"}


def _window_days(start: int, end: int) -> int:
    """Days from the 1st of `start` to the end of `end` (wraps over New Year)."""
    n = (end - start) % 12 + 1
    return sum(monthrange(2001, (start - 1 + k) % 12 + 1)[1] for k in range(n))


def fits_calendar(crop: str, region_id: str, crops: CropsFile, region: Region) -> bool:
    c = crops.crops[crop]
    p = c.stage_lengths_days.get(region_id)
    if not c.stage_lengths_days:
        return True  # fallow / cover crop: window set per region (A)
    if p is None or p.value is None:
        return False  # no verified stage lengths for this region
    key = "winter_wheat" if crop in WINTER_CROPS else "summer"
    seas = region.seasons.get(key)
    if seas is None:
        return False
    return sum(p.value) <= _window_days(seas.start, seas.end) + SLACK_DAYS


def family_of(crop: str, crops: CropsFile) -> str | None:
    f = crops.crops[crop].family
    return f.value if f is not None else None


def family_ok(seq: tuple[str, ...], crops: CropsFile, max_run: int) -> bool:
    run, prev = 0, None
    for c in seq:
        fam = family_of(c, crops)
        run = run + 1 if (fam is not None and fam == prev) else 1
        prev = fam
        if fam is not None and run > max_run:
            return False
    return True


def non_crop_ok(seq: tuple[str, ...], crops: CropsFile) -> bool:
    """Team constraints (A, UNVERIFIED, 2026-11-07): at least one harvested crop and at most
    one consecutive non-crop season (fallow or cover crop)."""
    nc = [c in NON_CROP_KEYS for c in seq]
    if all(nc):
        return False
    return not any(a and b for a, b in zip(nc, nc[1:], strict=False))


def allowed_crops(
    region_id: str,
    bans: set[str] | frozenset[str] = frozenset(),
    crops: CropsFile | None = None,
    regions: dict[str, Region] | None = None,
) -> list[str]:
    crops = crops or load_crops()
    regions = regions or load_regions()
    region = regions[region_id]
    opts = rotation_options(crops, region.crops or [])
    return [c for c in opts if c not in bans and fits_calendar(c, region_id, crops, region)]


def enumerate_candidates(
    region_id: str,
    bans: set[str] | frozenset[str] = frozenset(),
    max_consecutive_family: int = MAX_CONSECUTIVE_FAMILY,
    n_seasons: int = N_SEASONS,
    crops: CropsFile | None = None,
    regions: dict[str, Region] | None = None,
) -> list[tuple[str, ...]]:
    """All sequences passing the hard constraints, in lexicographic order (deterministic)."""
    crops = crops or load_crops()
    regions = regions or load_regions()
    pool = sorted(allowed_crops(region_id, bans, crops, regions))
    return [
        s
        for s in product(pool, repeat=n_seasons)
        if family_ok(s, crops, max_consecutive_family) and non_crop_ok(s, crops)
    ]
