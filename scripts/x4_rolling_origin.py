"""Conformal experiment (DECISIONS.md 2026-11-12): rolling-origin pseudo-forecasts.

Usage: uv run python -u scripts/x4_rolling_origin.py <cut-off year>
Executes scripts/t71_hindcast.py unchanged except for three in-memory replacements (asserted):
the cut-off (CUT = <year>-12-31), the scored years (the next season; 2021 -> 2022-2024 as
published) and the output file results/hindcast/conformal/pseudo_cut<year>.jsonl. Published
records are never written. Cut-off 2021 must reproduce results/hindcast/ks_t14slh_records.jsonl.
"""

import sys
from pathlib import Path

YEAR = int(sys.argv[1])
assert YEAR in (2018, 2019, 2020, 2021)
SCORE = (2022, 2023, 2024) if YEAR == 2021 else (YEAR + 1,)
SCRIPT = Path("scripts/t71_hindcast.py")
OUT = Path("results/hindcast/conformal") / f"pseudo_cut{YEAR}.jsonl"
src = SCRIPT.read_text("utf-8")
for old, new in (
    ("CUT = dt.date(2021, 12, 31)", f"CUT = dt.date({YEAR}, 12, 31)"),
    ("SCORE_YEARS = (2022, 2023, 2024)", f"SCORE_YEARS = {SCORE!r}"),
    (
        'REC = OUT / (\n    "ks_t14slh_records.jsonl" if THIN >= 1 else '
        'f"ks_t14slh_records_thin{round(THIN * 100)}.jsonl"\n)',
        f"REC = Path({str(OUT)!r})",
    ),
):
    assert src.count(old) == 1, old
    src = src.replace(old, new)
OUT.parent.mkdir(parents=True, exist_ok=True)
if OUT.exists():
    OUT.unlink()  # never resume: the random streams must start at the first field
sys.argv = [str(SCRIPT), "2000", "100"]
exec(compile(src, str(SCRIPT), "exec"), {"__name__": "__main__", "__file__": str(SCRIPT)})
