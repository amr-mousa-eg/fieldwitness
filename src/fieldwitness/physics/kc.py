"""Crop coefficient curve (T3.2). Tag: D (model output), parameters tag A/E per config/crops.yaml.

Curve shape: FAO-56 Fig. 34 (flat Kc ini, straight line to Kc mid, flat Kc mid, straight line
to Kc end at the end of the late season). Climate adjustment of Kc mid: FAO-56 Eq. 62; of
Kc end: FAO-56 Eq. 65 (only when the tabulated Kc end >= 0.45). See docs/fao56_equations.md.
"""

import numpy as np


def kc_adjust(kc_tab: float, u2: float, rhmin: float, h_m: float, end: bool = False) -> float:
    """Adjust a tabulated Kc mid / Kc end to local climate (FAO-56 Eq. 62 and Eq. 65, same form).

    u2 = mean 2 m wind (m/s) and rhmin = mean daily minimum RH (%) over the stage, h_m = mean
    plant height (m). Inputs are clipped to the validity limits printed with Eq. 65
    (1-6 m/s, 20-80 %, 0.1-10 m); Eq. 62 has the same form (UNVERIFIED: its limits were not read
    separately). end=True selects Eq. 65: Kc end below 0.45 is returned unchanged (FAO-56 text
    under Eq. 65). end=False is Eq. 62 for Kc mid, with no threshold.
    """
    if end and kc_tab < 0.45:
        return float(kc_tab)
    u = min(max(u2, 1.0), 6.0)
    rh = min(max(rhmin, 20.0), 80.0)
    h = min(max(h_m, 0.1), 10.0)
    return float(kc_tab + (0.04 * (u - 2.0) - 0.004 * (rh - 45.0)) * (h / 3.0) ** 0.3)


def kc_curve(
    stage_days: tuple[int, int, int, int],
    kc_ini: float,
    kc_mid: float,
    kc_end: float,
    n_days: int | None = None,
) -> np.ndarray:
    """Daily Kc from season day 0 (sowing) per FAO-56 Fig. 34.

    stage_days = (initial, development, mid, late) lengths in days. Day i in [0, L) is the i-th
    day after sowing; development rises linearly from kc_ini (end of initial) to kc_mid (end of
    development); late declines linearly from kc_mid to kc_end at the last day of the season.
    Returns an array of length n_days (default: season length); days past the season hold kc_end.
    """
    li, ld, lm, ll = stage_days
    if min(li, ld, lm, ll) < 0 or li + ld + lm + ll == 0:
        raise ValueError("stage lengths must be >= 0 and not all zero")
    total = li + ld + lm + ll
    n = total if n_days is None else n_days
    d = np.arange(n, dtype=float)
    kc = np.full(n, float(kc_end))
    kc[d < li] = kc_ini
    m = (d >= li) & (d < li + ld)
    if ld:
        kc[m] = kc_ini + (kc_mid - kc_ini) * (d[m] - li + 1) / ld
    m = (d >= li + ld) & (d < li + ld + lm)
    kc[m] = kc_mid
    m = (d >= li + ld + lm) & (d < total)
    if ll:
        kc[m] = kc_mid + (kc_end - kc_mid) * (d[m] - (li + ld + lm) + 1) / ll
    return kc
