"""T0.3 access check: one AppEEARS area task (HLS-VI NDVI/EVI + Fmask) for one small polygon.

Usage:
    uv run python scripts/check_appeears.py                 # submit, wait, download, log out
    uv run python scripts/check_appeears.py --task-id <id>  # resume waiting/downloading a task

API verified from https://appeears.earthdatacloud.nasa.gov/api/ on 2026-11-04 (docs/api_notes.md).
Credentials (CLAUDE.md rule 12 exception): the urs.earthdata.nasa.gov entry of _netrc is read in
memory and passed only to POST /login. The password and the Bearer token are never printed,
logged or written to disk; the token is disposed with POST /logout at the end.
"""

import argparse
import hashlib
import json
import netrc
import time
from pathlib import Path

import requests
from earthaccess.auth import netrc_path

API = "https://appeears.earthdatacloud.nasa.gov/api"
EDL_HOST = "urs.earthdata.nasa.gov"
OUT_DIR = Path("data/appeears")  # gitignored

# ~500 m x 500 m access-test rectangle inside HLS tile T14SLH (SW Kansas). Not a field boundary.
POLYGON = [
    [-100.9029, 37.9978],
    [-100.8971, 37.9978],
    [-100.8971, 38.0022],
    [-100.9029, 38.0022],
    [-100.9029, 37.9978],
]

# VI layers carry no linked QA layer in AppEEARS, so Fmask comes from the SR products.
LAYERS = [
    {"product": "HLSL30_VI.020", "layer": "NDVI"},
    {"product": "HLSL30_VI.020", "layer": "EVI"},
    {"product": "HLSS30_VI.020", "layer": "NDVI"},
    {"product": "HLSS30_VI.020", "layer": "EVI"},
    {"product": "HLSL30.020", "layer": "Fmask"},
    {"product": "HLSS30.020", "layer": "Fmask"},
]


def task_body() -> dict:
    return {
        "task_type": "area",
        "task_name": "fieldwitness-T0.3-access-check",
        "params": {
            "dates": [{"startDate": "04-01-2023", "endDate": "10-31-2023"}],
            "layers": LAYERS,
            "geo": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": [POLYGON]},
                        "properties": {},
                    }
                ],
            },
            "output": {"format": {"type": "netcdf4"}, "projection": "native"},
        },
    }


def login(session: requests.Session) -> None:
    """POST /login with Earthdata credentials read in memory; keep the token only in the session."""
    entry = netrc.netrc(str(netrc_path())).authenticators(EDL_HOST)
    if entry is None:
        raise SystemExit(f"no {EDL_HOST} entry in _netrc")
    r = requests.post(f"{API}/login", auth=(entry[0], entry[2]), timeout=60)
    del entry
    if r.status_code != 200:
        raise SystemExit(f"login failed: HTTP {r.status_code}")
    body = r.json()
    session.headers["Authorization"] = f"Bearer {body['token']}"
    print(
        "login: HTTP 200, token_type:",
        body.get("token_type"),
        "| expiration:",
        body.get("expiration"),
    )


def logout(session: requests.Session) -> None:
    r = session.post(f"{API}/logout", timeout=60)
    session.headers.pop("Authorization", None)
    print("logout: HTTP", r.status_code)


def wait_until_done(session: requests.Session, task_id: str, poll_s: int) -> dict:
    while True:
        r = session.get(f"{API}/task/{task_id}", timeout=60)
        r.raise_for_status()
        task = r.json()
        print(time.strftime("%H:%M:%S"), "status:", task.get("status"), flush=True)
        if task.get("status") in ("done", "error"):
            return task
        time.sleep(poll_s)


def download_bundle(session: requests.Session, task_id: str) -> None:
    r = session.get(f"{API}/bundle/{task_id}", timeout=60)
    r.raise_for_status()
    files = r.json()["files"]
    out = OUT_DIR / task_id
    out.mkdir(parents=True, exist_ok=True)
    print(f"bundle: {len(files)} files")
    for f in files:
        path = out / f["file_name"]
        h = hashlib.sha256()
        with session.get(f"{API}/bundle/{task_id}/{f['file_id']}", stream=True, timeout=300) as d:
            d.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in d.iter_content(1 << 20):
                    fh.write(chunk)
                    h.update(chunk)
        ok = h.hexdigest() == f["sha256"]
        print(f"  {f['file_name']}  {f['file_type']}  {f['file_size']} B  sha256 ok: {ok}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task-id")
    p.add_argument("--poll", type=int, default=30, help="seconds between status checks")
    p.add_argument(
        "--list",
        action="store_true",
        help="print this project's recent tasks (no logout: avoids revoking a token that a "
        "running process may share; the token expires on its own after ~48 h)",
    )
    a = p.parse_args()

    session = requests.Session()
    login(session)
    if a.list:
        r = session.get(f"{API}/task", params={"limit": 20}, timeout=60)
        r.raise_for_status()
        for t in r.json():
            if t.get("task_name") == task_body()["task_name"]:
                print({k: t.get(k) for k in ("task_id", "status", "created", "completed")})
                print("params:", json.dumps(t.get("params")))
        return
    try:
        task_id = a.task_id
        if not task_id:
            r = session.post(f"{API}/task", json=task_body(), timeout=60)
            print("submit: HTTP", r.status_code, r.json())
            r.raise_for_status()
            task_id = r.json()["task_id"]
        t0 = time.time()
        task = wait_until_done(session, task_id, a.poll)
        print(f"waited {time.time() - t0:.0f} s in this run")
        print({k: task.get(k) for k in ("task_id", "status", "created", "completed", "error")})
        print("task keys:", sorted(task))
        if task.get("summary"):
            print("summary:", task["summary"])
        if task.get("status") == "done":
            download_bundle(session, task_id)
    finally:
        logout(session)


if __name__ == "__main__":
    main()
