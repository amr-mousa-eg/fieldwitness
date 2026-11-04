"""Field definition on the HCAT3 crop taxonomy: annual arable crop parcels.

HCAT3 = Hierarchical Crop and Agriculture Taxonomy v3 (EuroCrops,
https://github.com/maja601/EuroCrops/blob/main/hcat_core/HCAT3.csv, fetched 2026-11-04).
Codes are 10 digits; leading digits select increasingly specific groups. The French
RPG/EuroCrops V2 GeoParquet (`hcat:code`) maps its crop codes to HCAT3 via
https://fiboa.org/code/fr/fr.csv.

User decision 2026-11-04 (DECISIONS.md): a field is an *annual arable crop parcel*.
Kept: HCAT3 group 3301 `arable_crops`. Excluded: every other group (3302 pasture/meadow/
grassland, 3303 permanent crops, 3304 mushrooms/energy/GM, 3305 greenhouse, 3306 tree/wood/
forest, 3307 peat/turf, 3308 unmaintained, 3399 not known/other), missing codes, and the 3301
classes below that are fallow, grass leys, multi-year crops or gardens rather than annual field
crops. Used by the census, T1.4 and T1.6.

Two roles (user decision 2026-11-04, DECISIONS.md):
- *Selection* — `is_annual_arable` on the current (most recent) year decides which parcels count
  as fields.
- *Crop history* — `history_state` maps every year of a field's history to a crop state. Fallow
  and temporary grass are kept as the states "fallow" and "temporary_grass", never dropped. A
  field is removed from history analysis only when it leaves arable use (a year coded outside
  HCAT3 group 3301), see `stays_arable`.
"""

ARABLE_PREFIX = "3301"

# 3301 classes excluded by prefix (HCAT3 code prefix -> HCAT3 name, from HCAT3.csv).
EXCLUDED_ARABLE_PREFIXES = {
    "330111": "fallow_land_not_crop",
    "33010901": "temporary_grass",
    "33010902": "poaceae_grasses",  # includes cocksfoot, ryegrass, switchgrass
    "33010830": "miscanthus_silvergrass",  # 3301083000 only; siblings 33010831-39 are kept
    "330112": "kitchen_gardens",
    "330113": "strawberries",  # multi-year planting
    "330120": "asparagus",  # perennial
    "330123": "rhubarb",  # perennial
    "330127": "artichoke",  # perennial
}


def normalise(code) -> str | None:
    """HCAT3 code as a 10-digit string, or None if missing."""
    if code is None:
        return None
    try:
        if bool(code != code):  # NaN
            return None
    except TypeError:  # pandas.NA: comparisons are ambiguous -> missing
        return None
    s = str(int(code)) if not isinstance(code, str) else code.strip()
    return s.zfill(10) if s else None


def is_annual_arable(code) -> bool:
    """True if an HCAT3 code is an annual arable crop parcel under the project definition."""
    c = normalise(code)
    if c is None or not c.startswith(ARABLE_PREFIX):
        return False
    return not any(c.startswith(p) for p in EXCLUDED_ARABLE_PREFIXES)


FALLOW = "fallow"
TEMPORARY_GRASS = "temporary_grass"
OTHER_ARABLE = "other_arable"
UNKNOWN = "unknown"

# History-state prefixes inside 3301 (HCAT3.csv): fallow and grass leys stay in the history.
_HISTORY_PREFIXES = {
    "330111": FALLOW,  # fallow_land_not_crop
    "33010901": TEMPORARY_GRASS,  # temporary_grass
    "33010902": TEMPORARY_GRASS,  # poaceae_grasses (grass leys: ryegrass, cocksfoot, ...)
}


def history_state(code) -> str | None:
    """Crop state of one field-year for crop histories.

    Returns the 10-digit HCAT3 code for an annual arable crop (named via crops.yaml in T1.6),
    "fallow", "temporary_grass", "other_arable" (perennials and gardens inside 3301), "unknown"
    for a missing code, or None when the year is outside arable use (any group other than 3301).
    """
    c = normalise(code)
    if c is None:
        return UNKNOWN
    if not c.startswith(ARABLE_PREFIX):
        return None
    for prefix, state in _HISTORY_PREFIXES.items():
        if c.startswith(prefix):
            return state
    return c if is_annual_arable(c) else OTHER_ARABLE


def stays_arable(codes) -> bool:
    """True if a field stays in arable use every year of its history (else drop it from history
    analysis). Fallow, temporary grass and unknown years do not remove a field."""
    return all(history_state(c) is not None for c in codes)
