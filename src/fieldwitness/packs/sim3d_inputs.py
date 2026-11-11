"""Inputs of the in-browser 3D simulation (Rotation Builder, Level B).

File: <field_id>.sim3d_inputs.json.

The Field in 3D pack (`packs/sim3d.py`) holds weekly series for Current + top 3 alternatives only.
The Rotation Builder lets a user play any ranked rotation of the field, so the browser re-runs the
same deterministic 3D path (`sim3d.simulate_weekly`) from the inputs written here:
- weather: the field's median-rain year (same rule as the 3D pack) for three of the T6.8 what-ifs
  (normal t+0_p+0, dry t+0_p-20, hot t+2_p+0), daily rain and FAO-56 ETo for 365 days (tag D,
  POWER forcing; the browser tiles the year 4x exactly as `precompute_scenario_weather` does);
- params: posterior medians of TAW, Kc scale and seasonal irrigation budget (tag D, the same
  numbers `packs/run.py` passes to `build_field_sim3d`);
- slots: the daily Kc curve, sowing day, Kc mid and p of each simulated crop key, plus the stage
  lengths and root depths the 3D pack uses for labels (tag A/E, from `config/crops.yaml` via
  `rotate.slots`; FAO-56 Tables 11, 12, 22).
Nothing here is a new estimate: every number is an input the Python 3D path already uses.

`reference()` writes unrounded Python results for parity testing (not shipped; gitignored dir).
Run from the project root (it reads data/ and results/):
  python -m fieldwitness.packs.sim3d_inputs ks_t14slh [--reference N --ref-dir DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.packs import sim3d as S
from fieldwitness.rotate.candidates import MAX_CONSECUTIVE_FAMILY
from fieldwitness.rotate.slots import _crops, option_slots

SCHEMA_VERSION = "1.0"
CASES = {"normal": "t+0_p+0", "dry": "t+0_p-20", "hot": "t+2_p+0"}  # T6.8 what-if ids
SIM_KEYS = ("maize", "sorghum", "winter_wheat", "cover_crop", "fallow")  # simulated season keys
DEFAULT_STAGES = [20, 30, 40, 20]  # same fallback as sim3d._compute_option_metadata (A)
Y0, Y1 = 2001, 2024
DIGITS = 6  # daily mm rounded to 1e-6: far below the parity tolerance


def _slot(crop: str, region_id: str) -> dict:
    spec = option_slots((crop,), region_id)[0]
    cfg = _crops().crops
    stages = (
        [int(x) for x in cfg[crop].stage_lengths_days[region_id].value]
        if crop in cfg and region_id in cfg[crop].stage_lengths_days
        else DEFAULT_STAGES
    )
    return {
        "kind": spec.kind,
        "kc": [round(float(x), DIGITS) for x in spec.kc],
        "sow_day": None if spec.sow_day is None else int(spec.sow_day),
        "kc_mid": float(spec.kc_mid),
        "p": float(spec.p),
        "stages_days": stages,
        "zr_max_m": float(S._crop_root_depth_max(crop)),
        # botanical family (crops.yaml, GBIF-verified); the builder explains the family rule
        "family": cfg[crop].family.value if crop in cfg and cfg[crop].family else None,
    }


def scenario_weather(weather: pd.DataFrame, lat: float, elev: float) -> tuple[int, dict]:
    """Median-rain year and its daily (rain, eto) for the three cases, as in the 3D pack."""
    year = S.find_median_gs_rain_year(weather, lat, elev, y0=2001, y1=2021)
    sids, rain_12, eto_12 = S.precompute_scenario_weather(
        weather[weather.index.year == year], lat, elev
    )
    out = {}
    for case, sid in CASES.items():
        k = sids.index(sid)
        out[case] = {
            "rain_mm": [round(float(x), DIGITS) for x in rain_12[: S.DAYS, 0, k]],
            "eto_mm": [round(float(x), DIGITS) for x in eto_12[: S.DAYS, 0, k]],
        }
    return year, out


def field_inputs(fid: str, lon: float, lat: float, draws: dict, region_id: str) -> dict:
    weather = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    year, cases = scenario_weather(weather, lat, float(elev or 0.0))
    return {
        "schema_version": SCHEMA_VERSION,
        "field_id": fid,
        "region_id": region_id,
        "weather_year": year,
        "weather": {
            "cases": CASES,
            "days": S.DAYS,
            "tiles": S.T_DAYS // S.DAYS,
            "series": cases,
            "unit": "mm per day",
            "tag": "D",
            "source": "NASA POWER daily weather of the median-rain year; ETo FAO-56 Eq. 6; "
            "what-if shifts tag A (T6.8)",
        },
        "params": {
            "taw_mm": float(np.median(draws["taw_mm"])),
            "kc_scale": float(np.median(draws["kc_scale"])),
            "budget_mm": float(np.median(draws["budget_mm"])),
            "tag": "D",
            "source": "posterior median over draws (results/rotate/posterior_draws.json)",
        },
        "slots": {
            "crops": {c: _slot(c, region_id) for c in SIM_KEYS},
            "kc_fallow": 0.3,
            "p_fallow": 0.55,
            "cover_frac": 0.5,
            "zr_ini_m": 0.20,
            "max_family_run": int(MAX_CONSECUTIVE_FAMILY),
            "tag": "A",
            "source": "config/crops.yaml (FAO-56 Tables 11, 12, 22) via rotate.slots; "
            "fallow Kc 0.3, p 0.55, root start 0.2 m are team choices (A, UNVERIFIED)",
        },
        "note": "Inputs of the in-browser 3D replay; numbers are model inputs, not results.",
    }


def _inputs_to_arrays(inp: dict) -> tuple[np.ndarray, np.ndarray]:
    """(1460, 3) rain, eto exactly as the browser builds them (tile the year 4x)."""
    ser = inp["weather"]["series"]
    rain = np.stack([np.tile(ser[c]["rain_mm"], 4) for c in CASES], axis=-1)
    eto = np.stack([np.tile(ser[c]["eto_mm"], 4) for c in CASES], axis=-1)
    return rain, eto


def reference(inp: dict, seqs: list[tuple[str, ...]], region_id: str) -> dict:
    """Unrounded Python weekly series for `seqs` x 3 cases from the shipped inputs."""
    rain, eto = _inputs_to_arrays(inp)
    p = inp["params"]
    sim = S.simulate_weekly(seqs, rain, eto, p["taw_mm"], p["kc_scale"], p["budget_mm"], region_id)
    out = []
    for o, seq in enumerate(seqs):
        crops, stages, roots = sim["metas"][o]
        out.append(
            {
                "sequence": list(seq),
                "crops": crops,
                "stages": stages,
                "root_depth_m": roots,
                "canopy_cover": sim["canopy_cover"][:, o].tolist(),
                "cases": {
                    c: {
                        k: sim[k][:, o, i].tolist()
                        for k in ("soil_water_mm", "ks", "irrigation_mm", "rain_mm")
                    }
                    for i, c in enumerate(CASES)
                },
            }
        )
    return {"field_id": inp["field_id"], "options": out}


def spread_fields(pilot: pd.DataFrame, n: int) -> list[str]:
    """n fields spread over the spatial blocks: round-robin over blocks, west to east."""
    by_block = [g.sort_values("lon")["field_id"].tolist() for _, g in pilot.groupby("block")]
    picked: list[str] = []
    i = 0
    while len(picked) < min(n, len(pilot)):
        for ids in by_block:
            if i < len(ids) and len(picked) < n:
                picked.append(ids[i])
        i += 1
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("region_id")
    ap.add_argument("--out", default="packs")
    ap.add_argument("--reference", type=int, default=0, help="fields for the parity reference")
    ap.add_argument("--ref-dir", default="results/validation/sim3d_parity_ref")
    a = ap.parse_args()
    pilot = pd.read_parquet(f"data/fields/{a.region_id}_pilot.parquet")
    draws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
    out = Path(a.out) / a.region_id
    ref_ids = set(spread_fields(pilot, a.reference)) if a.reference else set()
    ref_dir = Path(a.ref_dir)
    if ref_ids:
        ref_dir.mkdir(parents=True, exist_ok=True)
    for _, r in pilot.iterrows():
        fid = r["field_id"]
        inp = field_inputs(fid, float(r["lon"]), float(r["lat"]), draws[fid], a.region_id)
        (out / f"{fid}.sim3d_inputs.json").write_text(
            json.dumps(inp, separators=(",", ":")), "utf-8"
        )
        if fid in ref_ids:
            pack = json.loads((out / f"{fid}.json").read_text("utf-8"))
            seqs = [tuple(o["sequence"]) for o in pack["options"] if o["option_id"] != "current"]
            ref = reference(inp, seqs, a.region_id)
            (ref_dir / f"{fid}.json").write_text(json.dumps(ref), "utf-8")
    print(f"wrote {len(pilot)} inputs to {out}; reference for {len(ref_ids)} fields in {ref_dir}")


if __name__ == "__main__":
    main()
