"""Probe AppEEARS point-task limits with interior pixel centres of the pilot fields. Accepted probe
tasks are deleted immediately (DELETE /task/{id}).
Usage: uv run python -u scripts/probe_appeears_points.py
"""

import geopandas as gpd
import numpy as np

from fieldwitness.data import appeears as ae
from fieldwitness.data.hls_series import interior_points
from fieldwitness.resolve.pilot import load_grid


def body(name, coords, start, end):
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": ae.HLS_LAYERS,
            "coordinates": coords,
        },
    }


def main() -> None:
    pilot = gpd.read_parquet("data/fields/ks_t14slh_pilot.parquet")
    grid = load_grid("ks_t14slh")
    all_pts = interior_points(pilot, grid, max_per_field=None)
    pts25 = interior_points(pilot, grid, max_per_field=25)
    print("interior points: all", len(all_pts), "| max 25/field", len(pts25), flush=True)
    rng = np.random.default_rng(0)
    probes = [
        (
            "1000p_1y",
            [pts25[i] for i in rng.choice(len(pts25), 1000, replace=False)],
            "01-01-2023",
            "12-31-2023",
        ),
        ("25pf_9y", pts25, "01-01-2016", "12-31-2024"),
        ("allpx_9y", all_pts, "01-01-2016", "12-31-2024"),
    ]
    s = ae.login()
    try:
        for label, coords, start, end in probes:
            r = s.post(
                f"{ae.API}/task",
                json=body(f"fieldwitness-probe-{label}", coords, start, end),
                timeout=300,
            )
            if r.status_code < 400:
                tid = r.json()["task_id"]
                d = s.delete(f"{ae.API}/task/{tid}", timeout=60)
                print(
                    f"{label} ({len(coords)} pts): ACCEPTED (deleted, HTTP {d.status_code})",
                    flush=True,
                )
            else:
                print(
                    f"{label} ({len(coords)} pts): REJECTED HTTP {r.status_code}: {r.text[:200]}",
                    flush=True,
                )
    finally:
        print("logout HTTP", ae.logout(s), flush=True)


if __name__ == "__main__":
    main()
