"""Priors for the hidden field variables (T4.1). Tag A (team choices, see config/priors.yaml).

Variables: sow_offset_days, taw_scale, irrigated, irrigation_mm, kc_mid_scale. `sample` returns
a dict of arrays of length n; irrigation_mm is 0 where irrigated is False. Seeded (SEED).
"""

from pathlib import Path

import numpy as np
import yaml

SEED = 20261114
VARIABLES = ("sow_offset_days", "taw_scale", "irrigated", "irrigation_mm", "kc_mid_scale")
_CONFIG = Path(__file__).resolve().parents[3] / "config" / "priors.yaml"


def load(path: Path | str | None = None) -> dict:
    with open(path or _CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    missing = [v for v in VARIABLES if v not in cfg]
    if missing:
        raise ValueError(f"priors.yaml lacks {missing}")
    for name, spec in cfg.items():
        if not spec.get("reason"):
            raise ValueError(f"prior {name} has no reason")
    return cfg


def _draw(spec: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    kind = spec["kind"]
    if kind == "uniform":
        return rng.uniform(spec["low"], spec["high"], n)
    if kind == "loguniform":
        return np.exp(rng.uniform(np.log(spec["low"]), np.log(spec["high"]), n))
    if kind == "bernoulli":
        return rng.random(n) < spec["p"]
    raise ValueError(f"unknown prior kind {kind}")


def sample(n: int, seed: int = SEED, cfg: dict | None = None) -> dict[str, np.ndarray]:
    """Draw n joint prior samples (independent variables)."""
    cfg = cfg or load()
    rng = np.random.default_rng(seed)
    out = {v: _draw(cfg[v], rng, n) for v in VARIABLES}
    out["sow_offset_days"] = np.rint(out["sow_offset_days"]).astype(int)
    out["irrigation_mm"] = np.where(out["irrigated"], out["irrigation_mm"], 0.0)
    return out
