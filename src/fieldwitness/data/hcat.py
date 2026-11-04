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
