"""Erosion exposure and residue proxy (PLAN T6.7, part 2). Both are tag D, relative, unitless.

Inputs are the simulated daily canopy proxy of an option (`physics.rotation._layout`, deterministic
per option: Kc / Kc_mid of crop and cover-crop stages, 0 on bare fallow) and daily rain.
Compare only between options of the same field. NOT tonnes of soil, NOT soil carbon.

- erosion_exposure = slope_factor x mean over weather start years of
  (sum over the S timeline years of rain mm on days with low cover and rain >= EROSIVE_RAIN_MM) / S.
  Low cover = canopy proxy < cover_frac (same 0.5 as `cover_days`).
- residue_proxy = 0.5 x canopy integral share + 0.5 x cover-day share, each over the S years
  (0..1). "organic matter input (proxy, not soil carbon)".

UNVERIFIED (A, team choices, no source read): EROSIVE_RAIN_MM = 12.7 (recalled value for an
erosive-storm cut, not checked in a paper); slope factor = tan(slope) (monotone, same for all
options of a field, so it never changes the order of options); the 50/50 residue weights; the
indicator form of "low cover". Key inputs are therefore tag A even though the metric is D.
"""

import math

import numpy as np

from fieldwitness.physics.rotation import DAYS, SlotSpec, _layout
from fieldwitness.schemas import Tagged

EROSIVE_RAIN_MM = 12.7  # A, UNVERIFIED
COVER_FRAC = 0.5
LABELS = {
    "erosion_exposure": "erosion exposure (relative index, not tonnes of soil)",
    "residue_proxy": "organic matter input (proxy, not soil carbon)",
}


def option_canopy(slots: list[SlotSpec]) -> np.ndarray:
    """Daily canopy proxy for timeline years 1..S (shape (S*365,))."""
    canopy = _layout(slots, 0.3, 0.55, COVER_FRAC)[4]
    return canopy[DAYS:]


def slope_factor(slope_deg: float) -> float:
    return math.tan(math.radians(slope_deg))


def erosion_exposure(
    canopy: np.ndarray,
    rain: np.ndarray,
    slope_deg: float,
    threshold_mm: float = EROSIVE_RAIN_MM,
    cover_frac: float = COVER_FRAC,
) -> float:
    """canopy: (S*365,); rain: (n_years, 365) of weather years; start y forces years y..y+S."""
    canopy, rain = np.asarray(canopy, float), np.asarray(rain, float)
    S = canopy.size // DAYS
    n_start = rain.shape[0] - S
    if n_start < 1:
        raise ValueError("not enough weather years for the sequence length")
    flat = rain.reshape(-1)
    low = canopy < cover_frac
    tot = np.empty(n_start)
    for y in range(n_start):
        r = flat[(y + 1) * DAYS : (y + 1 + S) * DAYS]  # timeline year i uses weather year y+i
        tot[y] = r[low & (r >= threshold_mm)].sum()
    return float(slope_factor(slope_deg) * tot.mean() / S)


def residue_proxy(canopy: np.ndarray, cover_frac: float = COVER_FRAC) -> float:
    canopy = np.asarray(canopy, float)
    return float(0.5 * canopy.mean() + 0.5 * (canopy >= cover_frac).mean())


def exposure_metrics(
    slots: list[SlotSpec], rain: np.ndarray, slope_deg: float
) -> dict[str, Tagged]:
    c = option_canopy(slots)
    return {
        "erosion_exposure": Tagged(
            value=erosion_exposure(c, rain, slope_deg),
            unit="relative index",
            tag="D",
            source="simulated cover x POWER rain x NASADEM slope; thresholds A, UNVERIFIED",
        ),
        "residue_proxy": Tagged(
            value=residue_proxy(c),
            unit="relative index 0-1",
            tag="D",
            source="simulated canopy integral + cover days; 50/50 weights A",
        ),
    }
