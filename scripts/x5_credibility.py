"""Reliability tiers experiment (DECISIONS.md 2026-11-12): credibility at each forecast cut-off.

Usage: uv run python -u scripts/x5_credibility.py <cut-off year>
Calls `compute_cutoff_credibility` of scripts/t7_grade_validity.py unchanged, with its module
constant CUT set to <year>-12-31 (the function reads it at call time: series filter and
`as_of`). Writes results/hindcast/reliability/credibility_cut<year>.json. Tag D.
"""

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t7_grade_validity as gv  # noqa: E402

YEAR = int(sys.argv[1])
assert YEAR in (2018, 2019, 2020, 2021)
gv.CUT = dt.date(YEAR, 12, 31)
pilot = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
series["year"] = series["date"].dt.year
series["doy"] = series["date"].dt.day_of_year
res = gv.compute_cutoff_credibility(pilot, series)
out = Path("results/hindcast/reliability") / f"credibility_cut{YEAR}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"cutoff": str(gv.CUT), "fields": res}, indent=1), "utf-8")
n_ok = sum(v["credibility"] is not None for v in res.values())
print(json.dumps({"cutoff": str(gv.CUT), "assessable": n_ok}))
