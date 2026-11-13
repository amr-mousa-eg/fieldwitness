"""Validate simulated soil moisture & rainfall extremes against NASA SMAP L4 & GPM IMERG.

Requires local data files when run against full region archives; prints structured
status and exits cleanly if external inputs are not staged yet.

Usage: uv run python scripts/validate/check_smap_gpm.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fieldwitness.validate.eo_checks import (
    evaluate_extreme_rain_agreement,
    evaluate_smap_soil_moisture,
)

DEFAULT_SMAP = Path("data/context/ks_t14slh_smap.parquet")
DEFAULT_SIM = Path("results/validation/sim_daily_moisture.parquet")
DEFAULT_POWER = Path("data/weather/ks_t14slh_power_daily.parquet")
DEFAULT_IMERG = Path("data/context/ks_t14slh_imerg_daily.parquet")
DEFAULT_OUT = Path("results/validation/smap_gpm_check.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smap", type=Path, default=DEFAULT_SMAP)
    ap.add_argument("--sim-daily", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--power", type=Path, default=DEFAULT_POWER)
    ap.add_argument("--imerg", type=Path, default=DEFAULT_IMERG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report: dict[str, object] = {"schema_version": "1.0"}
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
            "status": "pending_local_data",
            "missing": [str(args.power), str(args.imerg)],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
