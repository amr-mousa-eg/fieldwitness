"""Build .sim3d.json for all Kansas pilot fields in packs/ks_t14slh and sync to demo & app/public.

Usage: uv run python scripts/build_sim3d.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import power
from fieldwitness.packs import sim3d
from fieldwitness.packs.validate import validate_dir
from fieldwitness.schemas import check_tagged

ROOT = Path(__file__).resolve().parents[1]
REGION = "ks_t14slh"
PACKS_DIR = ROOT / "packs" / REGION
DEMO_DIR = ROOT / "packs" / "demo" / REGION
APP_DIR = ROOT / "app" / "public" / "packs" / REGION


def main() -> int:
    t0 = time.time()
    pilot = pd.read_parquet(ROOT / f"data/fields/{REGION}_pilot.parquet")
    pd_file = ROOT / "results/rotate/posterior_draws.json"
    pd_data = json.loads(pd_file.read_text("utf-8"))["fields"]

    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    APP_DIR.mkdir(parents=True, exist_ok=True)

    n_fields = len(pilot)
    print(f"Building .sim3d.json for {n_fields} fields in {REGION}...")

    # Cache weather and precomputed scenarios per grid point
    wx_cache = {}
    scen_cache = {}
    med_year_cache = {}

    for i, (_, r) in enumerate(pilot.iterrows()):
        fid = str(r["field_id"])
        pack_file = PACKS_DIR / f"{fid}.json"
        if not pack_file.exists():
            print(f"Skipping {fid}: {pack_file} does not exist")
            continue

        pack = json.loads(pack_file.read_text("utf-8"))
        cur_seq = tuple(pack["options"][0]["sequence"])
        alts = sorted(pack["options"][1:], key=lambda o: o["rank"])[:3]

        lon, lat = float(r["lon"]), float(r["lat"])
        pt_key = (round(lon, 2), round(lat, 2))
        if pt_key not in wx_cache:
            wx = power.read(lon, lat, "2001-01-01", "2024-12-31")
            _, elev = power.cached(lon, lat)
            med_yr = sim3d.find_median_gs_rain_year(wx, lat, float(elev or 0.0), 2001, 2021)
            wx_med = wx[wx.index.year == med_yr]
            scen_wx = sim3d.precompute_scenario_weather(wx_med, lat, float(elev or 0.0))
            wx_cache[pt_key] = (wx, float(elev or 0.0))
            med_year_cache[pt_key] = med_yr
            scen_cache[pt_key] = scen_wx
        wx, elev = wx_cache[pt_key]
        med_yr = med_year_cache[pt_key]
        scen_wx = scen_cache[pt_key]

        draws = pd_data[fid]
        taw_mm = float(np.median(draws["taw_mm"]))
        kc_scale = float(np.median(draws["kc_scale"]))
        budget_mm = float(np.median(draws["budget_mm"]))

        model = sim3d.build_field_sim3d(
            fid=fid,
            cur_seq=cur_seq,
            top_alts=alts,
            weather_full=wx,
            lat=lat,
            elev=elev,
            taw_mm=taw_mm,
            kc_scale=kc_scale,
            budget_mm=budget_mm,
            region_id=REGION,
            start_year=2022,
            scen_weather=scen_wx,
            weather_year=med_yr,
        )

        bad = check_tagged(model)
        if bad:
            print(f"ERROR: untagged numbers in {fid}: {bad[:5]}")
            return 1

        json_bytes = json.dumps(model.model_dump(mode="json"), separators=(",", ":")).encode(
            "utf-8"
        )
        if len(json_bytes) >= 300_000:
            print(f"ERROR: file size {len(json_bytes)} >= 300_000 for {fid}")
            return 1

        # Write to packs, demo, and app/public
        (PACKS_DIR / f"{fid}.sim3d.json").write_bytes(json_bytes)
        (DEMO_DIR / f"{fid}.sim3d.json").write_bytes(json_bytes)
        (APP_DIR / f"{fid}.sim3d.json").write_bytes(json_bytes)

        if (i + 1) % 25 == 0 or i == n_fields - 1:
            elapsed = time.time() - t0
            print(f"[{i + 1}/{n_fields}] fields completed in {elapsed:.1f}s")

    print("Validating packs/ks_t14slh...")
    prob1 = validate_dir(PACKS_DIR)
    if prob1:
        print("Validation errors in packs:", prob1[:10])
        return 1

    print("Validating packs/demo/ks_t14slh...")
    prob2 = validate_dir(DEMO_DIR)
    if prob2:
        print("Validation errors in demo:", prob2[:10])
        return 1

    elapsed = time.time() - t0
    print(f"All {n_fields} .sim3d.json files generated and validated in {elapsed:.1f}s!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
