"""Validate simulated FAO-56 ETa against NASA ECOSTRESS ECO_L3T_JET v003 overpasses.

Usage: uv run python scripts/validate/check_ecostress.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fieldwitness.validate.eo_checks import evaluate_ecostress_eta

DEFAULT_SIM = Path("results/validation/sim_daily_eta.parquet")
DEFAULT_ECO = Path("data/context/ecostress_overpasses.parquet")
DEFAULT_OUT = Path("results/validation/ecostress_eta_check.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sim-daily", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--ecostress", type=Path, default=DEFAULT_ECO)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.sim_daily.exists() or not args.ecostress.exists():
        payload = {
            "schema_version": "1.0",
            "status": "pending_local_data",
            "collection": "ECO_L3T_JET.003 (C4057232489-LPCLOUD)",
            "missing": [str(args.sim_daily), str(args.ecostress)],
        }
    else:
        sim_df = pd.read_parquet(args.sim_daily)
        eco_df = pd.read_parquet(args.ecostress)
        payload = {
            "schema_version": "1.0",
            "status": "ok",
            **evaluate_ecostress_eta(sim_df, eco_df),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
