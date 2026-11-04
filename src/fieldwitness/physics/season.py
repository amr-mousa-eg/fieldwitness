"""Season outputs (T3.4). All outputs tag D (model); Ky tag E (FAO-56 Table 24) or A if unverified.

Relative Yield Index (0-1, never tonnes): FAO-33 seasonal yield response,
    1 - Ya/Ym = Ky * (1 - ETa/ETc)   (FAO-33 form as written in PLAN T3.4; equation number
    UNVERIFIED, not read from the paper; Ky values from FAO-56 Table 24, reproduced from FAO-33),
so RYI = Ya/Ym = 1 - Ky * (1 - sum(ETa)/sum(ETc)), clipped to [0, 1]. Ky None -> RYI NaN.
Canopy proxy: the Kc curve rescaled to [0, 1] by Kc_mid (tag D, shape only; not a measured
cover). Cover days = days the proxy is >= `cover_frac` (A, team choice; UNVERIFIED).
"""

import numpy as np


def relative_yield_index(eta_sum, etc_sum, ky):
    """RYI = 1 - Ky (1 - ETa/ETc), clipped to [0, 1]; NaN if Ky is None or ETc <= 0."""
    eta_sum, etc_sum = np.broadcast_arrays(np.asarray(eta_sum, float), np.asarray(etc_sum, float))
    if ky is None:
        return np.full(eta_sum.shape, np.nan)
    ok = etc_sum > 0
    ratio = np.where(ok, eta_sum / np.where(ok, etc_sum, 1.0), np.nan)
    return np.clip(1.0 - ky * (1.0 - np.minimum(ratio, 1.0)), 0.0, 1.0)


def canopy_proxy(kc, kc_mid):
    """Kc-shaped canopy proxy in [0, 1] (Kc / Kc_mid), tag D."""
    return np.clip(np.asarray(kc, float) / float(kc_mid), 0.0, 1.0)


def season_outputs(wb, etc, kc, kc_mid, ky, cover_frac=0.5):
    """Summarise one `waterbal.run` result `wb` over days (axis 0).

    etc: unstressed crop ET (mm/day), kc: daily Kc (length = days). Returns a dict: eta_mm,
    etc_mm, irr_mm (net), irr_gross_mm, ryi (arrays over trailing axes), cover_days, canopy
    (daily proxy) and tag "D".
    """
    etc = np.broadcast_to(np.asarray(etc, float), wb["eta"].shape)
    eta_mm, etc_mm = wb["eta"].sum(axis=0), etc.sum(axis=0)
    canopy = canopy_proxy(kc, kc_mid)
    return {
        "eta_mm": eta_mm,
        "etc_mm": etc_mm,
        "irr_mm": wb["irr"].sum(axis=0),
        "irr_gross_mm": wb["irr_gross"].sum(axis=0),
        "ryi": relative_yield_index(eta_mm, etc_mm, ky),
        "cover_days": int((canopy >= cover_frac).sum()),
        "canopy": canopy,
        "tag": "D",
    }
