"""Probe how the AppEEARS area-task file limit scales (features x dates). Accepted probe tasks are
deleted immediately (DELETE /task/{id}, AppEEARS API docs).
Usage: uv run python -u scripts/probe_appeears_limit.py
"""

import re

import geopandas as gpd

from fieldwitness.data import appeears as ae
from fieldwitness.data.hls_series import feature_collection

PROBES = [  # (label, n features, start, end)
    ("200f_4mo", 200, "09-01-2015", "12-31-2015"),
    ("20f_4mo", 20, "09-01-2015", "12-31-2015"),
    ("20f_1mo", 20, "06-01-2023", "06-30-2023"),
    ("1f_12mo", 1, "01-01-2023", "12-31-2023"),
    ("5f_12mo", 5, "01-01-2023", "12-31-2023"),
]


def main() -> None:
    pilot = gpd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    s = ae.login()
    try:
        for label, n, start, end in PROBES:
            fc = feature_collection(pilot.iloc[:n])
            body = ae.area_task(f"fieldwitness-probe-{label}", fc, start, end)
            r = s.post(f"{ae.API}/task", json=body, timeout=120)
            if r.status_code < 400:
                tid = r.json()["task_id"]
                d = s.delete(f"{ae.API}/task/{tid}", timeout=60)
                print(f"{label}: ACCEPTED (deleted, HTTP {d.status_code})", flush=True)
            else:
                m = re.search(r"by ([\d.]+)%", r.text)
                over = m.group(1) if m else "?"
                print(f"{label}: REJECTED HTTP {r.status_code}, over by {over}%", flush=True)
    finally:
        print("logout HTTP", ae.logout(s), flush=True)


if __name__ == "__main__":
    main()
