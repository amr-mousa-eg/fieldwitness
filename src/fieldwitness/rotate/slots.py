"""Crop key -> `SlotSpec` for the multi-year timeline (T6.2). Output tag: A/E (config values).

Numbers come from `config/crops.yaml` (FAO-56 Tables 11, 12, 22, 24; verified flags there).
Team choices (tag A, UNVERIFIED), kept here in one place:
- sowing days (0-based day of the harvest year, negative = previous autumn): maize 105 and
  sorghum 152 as in `config/synthetic.yaml`; winter wheat -78 = 15 Oct (Table 11 says "October");
- winter wheat in Table 11 (Idaho row) lasts 335 days, so it ends in mid-September: kept as
  printed, not tuned;
- cover crop (oats proxy): stage lengths 20/25/60/30 d = FAO-56 Table 11 row "Barley/Oats/Wheat,
  March/Apr, 35-45 deg L" (read from docs/refs/fao56_eq/html/x0490e0b.htm); the timeline caps it
  at the gap before the next crop.
"""

from functools import lru_cache

import numpy as np

from fieldwitness.config import load_crops
from fieldwitness.physics.kc import kc_curve
from fieldwitness.physics.rotation import SlotSpec, fallow_slot

SOW_DAY = {"maize": 105, "sorghum": 152, "winter_wheat": -78}  # A, UNVERIFIED
COVER_STAGES = (20, 25, 60, 30)  # FAO-56 Table 11, Barley/Oats/Wheat, March/Apr, 35-45 deg L
COVER_SOW_DAY = None  # placed by the timeline layout, not by a date


@lru_cache(maxsize=1)
def _crops():
    return load_crops()


def _kc_ini(c, region_id: str) -> float:
    k = c.kc_ini
    if hasattr(k, "by_region"):
        return float(getattr(k, k.by_region[region_id]).value)
    return float(k.value)


def slot_spec(crop: str, region_id: str) -> SlotSpec:
    """One `SlotSpec` for a crop key of `rotation_options` (raises KeyError if not modelled)."""
    if crop == "fallow":
        return fallow_slot()
    c = _crops().crops[crop]
    kc_ini, kc_mid, kc_end = _kc_ini(c, region_id), float(c.kc_mid.value), float(c.kc_end.value)
    p = float(c.p.value)
    if crop == "cover_crop":
        kc = kc_curve(COVER_STAGES, kc_ini, kc_mid, kc_end)
        return SlotSpec("cover", kc, COVER_SOW_DAY, kc_mid, None, p)
    if crop not in SOW_DAY:
        raise KeyError(f"no sowing day for {crop}")
    stages = tuple(int(x) for x in c.stage_lengths_days[region_id].value)
    ky = None if c.ky is None or c.ky.value is None else float(c.ky.value)
    kc = kc_curve(stages, kc_ini, kc_mid, kc_end)
    return SlotSpec("crop", np.asarray(kc), SOW_DAY[crop], kc_mid, ky, p)


def option_slots(seq: tuple[str, ...], region_id: str) -> list[SlotSpec]:
    return [slot_spec(c, region_id) for c in seq]
