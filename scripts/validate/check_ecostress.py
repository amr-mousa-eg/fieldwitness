"""Validate simulated FAO-56 ETa & observed 30 m/100 m thermal stress (Landsat C2 L2 / ECOSTRESS).

Usage: uv run python scripts/validate/check_ecostress.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fieldwitness.data import power
from fieldwitness.validate.eo_checks import (
    evaluate_ecostress_eta,
    evaluate_landsat_lst_thermal,
)

DEFAULT_SIM = Path("results/validation/sim_daily_eta.parquet")
DEFAULT_ECO = Path("data/context/ecostress_overpasses.parquet")
DEFAULT_LST_DIR = Path("data/context/landsat_lst")
DEFAULT_OUT = Path("results/validation/ecostress_eta_check.json")

REGION_CENTROIDS = {
    "ks_t14slh": (-101.08, 38.28),
    "ua_central_t36uvu": (30.56, 48.20),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sim-daily", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--ecostress", type=Path, default=DEFAULT_ECO)
    ap.add_argument("--landsat-dir", type=Path, default=DEFAULT_LST_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload: dict[str, Any] = {"schema_version": "1.1"}
    if not args.sim_daily.exists() or not args.ecostress.exists():
        payload["ecostress"] = {
            "status": "auth_required_no_netrc",
            "collection": "ECO_L3T_JET.003 (C4057232489-LPCLOUD)",
            "note": (
                "Unauthenticated lp-prod-protected requests return HTTP 302 to "
                "urs.earthdata.nasa.gov (no _netrc in environment); Landsat 8/9 C2 L2 "
                "ST_B10 provides public 30 m/100 m thermal observations instead."
            ),
            "missing": [str(args.sim_daily), str(args.ecostress)],
        }
        payload["status"] = "landsat_lst_substitute"
    else:
        sim_df = pd.read_parquet(args.sim_daily)
        eco_df = pd.read_parquet(args.ecostress)
        payload["ecostress"] = {"status": "ok", **evaluate_ecostress_eta(sim_df, eco_df)}
        payload["status"] = "ok"

    lst_checks: dict[str, Any] = {}
    for region_id, (lon, lat) in REGION_CENTROIDS.items():
        lst_path = args.landsat_dir / f"{region_id}_lst.parquet"
        if not lst_path.exists():
            continue
        lst_df = pd.read_parquet(lst_path)
        pwr_df = power.read(lon, lat, "2017-01-01", "2024-12-31")
        lst_checks[region_id] = evaluate_landsat_lst_thermal(pwr_df, lst_df, heat_threshold_c=35.0)
    if lst_checks:
        payload["landsat_lst"] = lst_checks

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
