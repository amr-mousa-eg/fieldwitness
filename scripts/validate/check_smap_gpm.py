"""Validate simulated soil moisture & rainfall extremes against NASA SMAP L4, GPM IMERG & ERA5.

Requires local data files when run against full region archives; prints structured
status and exits cleanly if external inputs are not staged yet.

Usage: uv run python scripts/validate/check_smap_gpm.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fieldwitness.data import era5, power
from fieldwitness.validate.eo_checks import (
    evaluate_extreme_rain_agreement,
    evaluate_smap_soil_moisture,
)

DEFAULT_SMAP = Path("data/context/ks_t14slh_smap.parquet")
DEFAULT_SIM = Path("results/validation/sim_daily_moisture.parquet")
DEFAULT_POWER = Path("data/weather/ks_t14slh_power_daily.parquet")
DEFAULT_IMERG = Path("data/context/ks_t14slh_imerg_daily.parquet")
DEFAULT_ERA5_DIR = Path("data/weather/era5")
DEFAULT_OUT = Path("results/validation/smap_gpm_check.json")

REGION_CENTROIDS = {
    "ks_t14slh": (-101.08, 38.28),
    "ua_central_t36uvu": (30.56, 48.20),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smap", type=Path, default=DEFAULT_SMAP)
    ap.add_argument("--sim-daily", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--power", type=Path, default=DEFAULT_POWER)
    ap.add_argument("--imerg", type=Path, default=DEFAULT_IMERG)
    ap.add_argument("--era5-dir", type=Path, default=DEFAULT_ERA5_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report: dict[str, Any] = {"schema_version": "1.1"}
    if args.smap.exists() and args.sim_daily.exists():
        smap_df = pd.read_parquet(args.smap)
        sim_df = pd.read_parquet(args.sim_daily)
        report["smap"] = evaluate_smap_soil_moisture(sim_df, smap_df)
    else:
        report["smap"] = {
            "status": "pending_local_data",
            "missing": [str(args.smap), str(args.sim_daily)],
        }

    if args.power.exists() and args.imerg.exists():
        p_df = pd.read_parquet(args.power)
        i_df = pd.read_parquet(args.imerg)
        report["gpm_imerg"] = evaluate_extreme_rain_agreement(p_df, i_df)
    else:
        report["gpm_imerg"] = {
            "status": "auth_required_no_netrc",
            "collection": "GPM_3IMERGDF.07 (C2723754864-GES_DISC)",
            "pc_zarr_excluded": "gpm-imerg-hhr.zarr chunks [12, 3600, 1800] exceed 1 GB policy cap",
            "missing": [str(args.power), str(args.imerg)],
        }

    era5_checks: dict[str, Any] = {}
    for region_id, (lon, lat) in REGION_CENTROIDS.items():
        ep = args.era5_dir / f"{region_id}_era5_daily.parquet"
        if not ep.exists():
            continue
        e_df = era5.read_era5(region_id=region_id, table=pd.read_parquet(ep))
        pwr = power.read(lon, lat, "2001-01-01", "2024-12-31").reset_index()
        date_col = "index" if "index" in pwr.columns else "date"
        p_norm = pd.DataFrame(
            {"date": pwr[date_col], "rain_mm": pwr["PRECTOTCORR"].to_numpy(float)}
        )
        e_norm = pd.DataFrame({"date": e_df["date"], "rain_mm": e_df["rain_mm"].to_numpy(float)})
        q99_p = float(p_norm["rain_mm"].quantile(0.99))
        q99_e = float(e_norm["rain_mm"].quantile(0.99))
        era5_src = "ECMWF ERA5 0.25 deg (Open-Meteo Archive, tag E) vs NASA POWER"
        era5_checks[region_id] = {
            "fixed_25mm": evaluate_extreme_rain_agreement(
                p_norm, e_norm, threshold_mm=25.0, external_source=era5_src
            ),
            "q99_power_mm": round(q99_p, 2),
            "q99_era5_mm": round(q99_e, 2),
            "q99_agreement": evaluate_extreme_rain_agreement(
                p_norm, e_norm, threshold_mm=round(q99_p, 2), external_source=era5_src
            ),
            "external_source": era5_src,
        }
    if era5_checks:
        report["era5_extreme_rain"] = era5_checks

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
