"""Forward model for inference (T4.2/T4.3): hidden variables + weather -> daily canopy NDVI.

One calendar year, one crop, `n` parameter draws at once. Uses the FAO-56 Kc curve (`kc_curve`)
and water balance (`waterbal.run`, Eq. 82-85). Output tag D (model). The canopy fraction, the
NDVI map and the stress coupling are team choices (tag A, UNVERIFIED), see config/synthetic.yaml.
Caveat: the synthetic "truth" and the ABC forward model are the same code, so recovery tests
show identifiability under a perfect model only, not skill on real fields.
"""

from pathlib import Path

import numpy as np
import yaml

from fieldwitness.physics import waterbal
from fieldwitness.physics.kc import kc_curve

DAYS = 365
_ROOT = Path(__file__).resolve().parents[3]


def load_cfg(path: Path | str | None = None) -> dict:
    return yaml.safe_load(Path(path or _ROOT / "config" / "synthetic.yaml").read_text("utf-8"))


def crop_params(crop: str, region: str, path: Path | str | None = None) -> dict:
    """Plain numbers for one crop from config/crops.yaml (values as printed there)."""
    c = yaml.safe_load(Path(path or _ROOT / "config" / "crops.yaml").read_text("utf-8"))["crops"][
        crop
    ]
    return {
        "stages": tuple(int(x) for x in c["stage_lengths_days"][region]["value"]),
        "kc_ini": float(c["kc_ini"]["value"]),
        "kc_mid": float(c["kc_mid"]["value"]),
        "kc_end": float(c["kc_end"]["value"]),
        "p": float(c["p"]["value"]),
        "ky": float(c["ky"]["value"]),
    }


def simulate(rain, eto, hidden: dict, crop: dict, cfg: dict) -> dict:
    """rain, eto: (365,) mm/day. hidden: arrays of length n (see infer.priors.VARIABLES).

    Returns ndvi (365, n), eta_mm (n,) crop-window ETa, sow_day (n,) 0-based, tag "D".
    """
    rain, eto = np.asarray(rain, float), np.asarray(eto, float)
    if rain.shape != (DAYS,) or eto.shape != (DAYS,):
        raise ValueError(f"rain and eto must have shape ({DAYS},)")
    n = len(hidden["taw_scale"])
    nominal = int(cfg["nominal_sow_doy"][cfg["crop"]])
    sow = nominal + np.rint(np.asarray(hidden["sow_offset_days"])).astype(int)
    length = sum(crop["stages"])
    if sow.min() < 0 or sow.max() + length > DAYS:
        raise ValueError("crop window must fit inside one calendar year")
    kc = np.full((DAYS, n), float(cfg["kc_fallow"]))
    win = np.zeros((DAYS, n), bool)
    cf = np.zeros((DAYS, n))
    scale = np.asarray(hidden["kc_mid_scale"], float)
    for j in range(n):
        k = kc_curve(crop["stages"], crop["kc_ini"], crop["kc_mid"] * scale[j], crop["kc_end"])
        kc[sow[j] : sow[j] + length, j] = k
        win[sow[j] : sow[j] + length, j] = True
        den = crop["kc_mid"] * scale[j] - crop["kc_ini"]
        cf[sow[j] : sow[j] + length, j] = np.clip((k - crop["kc_ini"]) / den, 0.0, 1.0)
    taw = float(cfg["taw_base_mm"]) * np.asarray(hidden["taw_scale"], float)
    irrigated = np.asarray(hidden["irrigated"], bool)
    budget = np.where(irrigated, np.asarray(hidden["irrigation_mm"], float), 0.0)
    pol = waterbal.Policy("fixed_seasonal_mm", 1.0, budget)
    etc = (
        kc * scale[None, :] * eto[:, None]
    )  # scale also applies on fallow days (as in rotation.py)
    wb = waterbal.run(
        np.broadcast_to(rain[:, None], (DAYS, n)),
        etc,
        taw,
        crop["p"],
        pol,
        dr0=float(cfg["dr0_mm"]),
        irr_mask=win,
    )
    cf = cf * (1.0 - float(cfg["stress_coupling"]) * (1.0 - wb["ks"]))
    ndvi = cfg["ndvi_bare"] + (cfg["ndvi_peak"] - cfg["ndvi_bare"]) * cf
    return {
        "ndvi": ndvi,
        "eta_mm": np.where(win, wb["eta"], 0.0).sum(0),
        "sow_day": sow,
        "tag": "D",
    }
