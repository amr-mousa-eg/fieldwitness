"""T4.6 check: compare posterior irrigation (mm) against Kansas WIMAS pumping records.

Requires user-accepted WIMAS export CSV placed under data/wimas/.
Usage: uv run python scripts/validate/check_wimas.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fieldwitness.validate.eo_checks import evaluate_wimas_irrigation

DEFAULT_SIM = Path("results/validation/sim_seasonal_irrigation.parquet")
DEFAULT_WIMAS = Path("data/wimas/ks_t14slh_wimas.csv")
DEFAULT_OUT = Path("results/validation/wimas_irrigation_check.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sim-seasons", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--wimas-csv", type=Path, default=DEFAULT_WIMAS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.sim_seasons.exists() or not args.wimas_csv.exists():
        payload = {
            "schema_version": "1.0",
            "status": "pending_user_wimas_csv",
            "note": (
                "Place user-downloaded KGS WIMAS CSV in data/wimas/ after accepting KGS disclaimer."
            ),
            "missing": [str(args.sim_seasons), str(args.wimas_csv)],
        }
    else:
        sim_df = pd.read_parquet(args.sim_seasons)
        wimas_df = pd.read_csv(args.wimas_csv)
        payload = {
            "schema_version": "1.0",
            "status": "ok",
            **evaluate_wimas_irrigation(sim_df, wimas_df),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
