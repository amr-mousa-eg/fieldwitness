"""AppEEARS: API client for area tasks and helpers for their outputs.

API verified from https://appeears.earthdatacloud.nasa.gov/api/ (docs/api_notes.md). Credentials:
the urs.earthdata.nasa.gov entry of _netrc is read in memory and passed only to POST /login
(CLAUDE.md rule 12 exception); the Bearer token lives only in the requests.Session.
"""

import datetime as dt
import hashlib
import json
import netrc
import re
import time
from pathlib import Path

import numpy as np
import requests

_UNITS = re.compile(r"^days since (\d{4}-\d{2}-\d{2})(?:[ T]00:00:00(?:\.0+)?)?$")


def decode_time(values, units: str) -> list[dt.date]:
    """Decode the `time` variable of an AppEEARS HLS NetCDF file into calendar dates.

    AppEEARS writes `units = "days since <product start date> 00:00:00"` (2013-04-11 for HLSL30,
    2015-11-28 for HLSS30) together with `calendar = "julian"`. The values are plain day counts:
    read that way they match the dates in the task's Statistics CSV exactly, whereas a true Julian
    calendar (e.g. via cftime) would shift dates by ~13 days. So the calendar attribute is ignored.
    Source: AppEEARS task 09338e93-d3fa-493d-bc4a-476ac22a2b88, checked against its Statistics CSVs
    (docs/api_notes.md). Open the file with `decode_times=False` and pass `ds["time"].values` and
    `ds["time"].attrs["units"]`.
    """
    m = _UNITS.match(units.strip())
    if m is None:
        raise ValueError(f"unsupported AppEEARS time units: {units!r}")
    days = np.asarray(values)
    if days.size and not np.all(days == np.round(days)):
        raise ValueError("AppEEARS time values are expected to be whole days")
    base = dt.date.fromisoformat(m.group(1))
    return [base + dt.timedelta(days=int(d)) for d in days.ravel()]


# ---------------------------------------------------------------- API client (T1.5)

API = "https://appeears.earthdatacloud.nasa.gov/api"
EDL_HOST = "urs.earthdata.nasa.gov"
HLS_LAYERS = [
    {"product": "HLSL30_VI.020", "layer": "NDVI"},
    {"product": "HLSL30_VI.020", "layer": "EVI"},
    {"product": "HLSS30_VI.020", "layer": "NDVI"},
    {"product": "HLSS30_VI.020", "layer": "EVI"},
    {"product": "HLSL30.020", "layer": "Fmask"},
    {"product": "HLSS30.020", "layer": "Fmask"},
]

VIIRS_LAYERS = [
    {"product": "VNP13A1.002", "layer": "_500m_16_days_NDVI"},
    {"product": "VNP13A1.002", "layer": "_500m_16_days_EVI"},
]

ECOSTRESS_LAYERS = [
    {"product": "ECO_L3T_JET.003", "layer": "ET_PT_JPL_daily"},
    {"product": "ECO_L3T_JET.003", "layer": "ET_PT_JPL_quality"},
]

SRTM_LAYERS = [
    {"product": "SRTMGL1_NC.003", "layer": "DEM"},
]


def login() -> requests.Session:
    from earthaccess.auth import netrc_path

    entry = netrc.netrc(str(netrc_path())).authenticators(EDL_HOST)
    if entry is None:
        raise RuntimeError(f"no {EDL_HOST} entry in _netrc")
    r = requests.post(f"{API}/login", auth=(entry[0], entry[2]), timeout=60)
    del entry
    r.raise_for_status()
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


def _call(session: requests.Session, method: str, url: str, **kw) -> requests.Response:
    """Request with one re-login on HTTP 403. AppEEARS docs: "All programs should check for an HTTP
    403 Forbidden status code to successfully handle token expiration by acquiring a new token."
    (Observed 2026-11-04: a logout in another process revoked this session's token.)"""
    r = session.request(method, url, **kw)
    if r.status_code == 403:
        fresh = login()
        session.headers["Authorization"] = fresh.headers["Authorization"]
        r = session.request(method, url, **kw)
    return r


def logout(session: requests.Session) -> int:
    r = session.post(f"{API}/logout", timeout=60)
    session.headers.pop("Authorization", None)
    return r.status_code


def area_task(name: str, geojson: dict, start: str, end: str, layers=HLS_LAYERS) -> dict:
    """Area-task body; dates as MM-DD-YYYY (AppEEARS docs)."""
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": layers,
            "geo": geojson,
            "output": {"format": {"type": "netcdf4"}, "projection": "native"},
        },
    }


def submit(session: requests.Session, body: dict) -> str:
    r = _call(session, "POST", f"{API}/task", json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"submit failed: HTTP {r.status_code} {r.text[:500]}")
    return r.json()["task_id"]


def task(session: requests.Session, task_id: str) -> dict:
    r = _call(session, "GET", f"{API}/task/{task_id}", timeout=60)
    r.raise_for_status()
    return r.json()


def bundle(session: requests.Session, task_id: str) -> list[dict]:
    r = _call(session, "GET", f"{API}/bundle/{task_id}", timeout=60)
    r.raise_for_status()
    return r.json()["files"]


def download(session: requests.Session, task_id: str, files: list[dict], out: Path) -> int:
    """Download bundle files (sha256-checked); skip files already present with the right hash."""
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in files:
        path = out / f["file_name"]
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == f["sha256"]:
            continue
        h = hashlib.sha256()
        url = f"{API}/bundle/{task_id}/{f['file_id']}"
        with _call(session, "GET", url, stream=True, timeout=600) as d:
            d.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in d.iter_content(1 << 20):
                    fh.write(chunk)
                    h.update(chunk)
        if h.hexdigest() != f["sha256"]:
            raise RuntimeError(f"sha256 mismatch: {path}")
        n += f["file_size"]
    return n


def wait(session: requests.Session, task_ids: list[str], poll_s: int = 60) -> dict[str, dict]:
    """Poll until every task is done or error; prints status changes (unbuffered)."""
    last: dict[str, str] = {}
    while True:
        states = {t: task(session, t) for t in task_ids}
        for t, s in states.items():
            if s.get("status") != last.get(t):
                print(time.strftime("%H:%M:%S"), t, s.get("task_name"), s.get("status"), flush=True)
                last[t] = s.get("status")
        if all(s.get("status") in ("done", "error") for s in states.values()):
            return states
        time.sleep(poll_s)


def save_registry(path: Path, entries: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=1), encoding="utf-8")
