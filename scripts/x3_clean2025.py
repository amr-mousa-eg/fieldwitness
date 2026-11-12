"""Experiment 3 (pre-registered in DECISIONS.md 2026-11-12): clean 2025 test, both modes.

Usage: uv run python -u scripts/x3_clean2025.py <calendar|gdd>
Runs scripts/x2_gdd_hindcast.py with only these in-memory changes (asserted, printed below):
  - scored season 2025 only (SCORE_YEARS = (2025,));
  - the 2025 HLS series (data/fields/ks_t14slh_hls_series_2025.parquet) is appended to the
    series; fitting still uses only seasons <= 2021 (`as_of` 2021-12-31, unchanged);
  - 2025 crop labels (data/labels/ks_t14slh_2025.parquet, CSB 2018-2025 edition) are appended
    to the scoring labels only (read outside the guard, as before);
  - POWER 2025 daily weather (separate cache data/power_2025/) is added for the forced run only;
  - records go to results/hindcast/clean2025/records_<mode>.jsonl.
Calibration, priors, seeds, n_ref (2000) and k (100) are unchanged.
"""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

from fieldwitness.data import power

MODE = sys.argv[1]
assert MODE in ("calendar", "gdd")
SCRIPT = Path("scripts/x2_gdd_hindcast.py")
P2025 = Path("data/power_2025")


def loader_2025(lon: float, lat: float):
    """Cached 2001-2024 POWER series plus 2025 from a separate cache (one API call per point)."""
    df, elev = power.cached(lon, lat)
    P2025.mkdir(parents=True, exist_ok=True)
    f = P2025 / f"{power._key(lon, lat)}.parquet"
    if f.exists():
        extra = pd.read_parquet(f)
    else:
        extra, _ = power.parse(power.fetch(lon, lat, dt.date(2025, 1, 1), dt.date(2025, 12, 31)))
        extra.to_parquet(f)
    return pd.concat([df, extra[extra.index.year == 2025]]).sort_index(), elev


src = SCRIPT.read_text("utf-8")
CHANGES = [
    ("SCORE_YEARS = (2022, 2023, 2024)", "SCORE_YEARS = (2025,)"),
    (
        'series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")',
        'series = pd.concat([pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet"), '
        'pd.read_parquet("data/fields/ks_t14slh_hls_series_2025.parquet")], ignore_index=True)',
    ),
    (
        "    lab_all = labels.read(region)",
        "    lab_all = pd.concat([labels.read(region), "
        'pd.read_parquet("data/labels/ks_t14slh_2025.parquet")])',
    ),
    (
        "    w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31))",
        "    w = power.read(lon, lat, dt.date(min(years), 1, 1), dt.date(max(years), 12, 31), "
        "loader=LOADER_2025)",
    ),
    ('OUT = OUT / "gdd"', 'OUT = OUT / "clean2025"'),
]
for old, new in CHANGES:
    assert src.count(old) == 1, old
    src = src.replace(old, new)
    print("change:", new[:110], flush=True)
sys.argv = [str(SCRIPT), "2000", "100", "1000000000", MODE]
ns = {"__name__": "__main__", "__file__": str(SCRIPT), "LOADER_2025": loader_2025}
exec(compile(src, str(SCRIPT), "exec"), ns)
