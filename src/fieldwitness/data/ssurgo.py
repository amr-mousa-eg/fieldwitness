"""USDA-NRCS SSURGO via Soil Data Access (SDA): independent soil check only (Phase 12).

Not a simulation input: nothing in the pipeline, packs or results reads this module. Request
and response shapes were verified on 2026-11-11 (docs/api_notes.md, "Soil Data Access"):
POST JSON {"query": <SQL>, "format": "JSON+COLUMNNAME"} to `URL`; the reply is
{"Table": [[column names], [row], ...]} with every value as a string (or null), and `{}` when
the query returns no rows. The table function SDA_Get_Mukey_from_intersection_with_WktWgs84
takes a WKT geometry in WGS84, longitude first (SDA "Advanced Queries" page).

Units (SDM "Table Column Descriptions" report and a cross-check against NRCS's own muaggatt
value, docs/api_notes.md): `awc_r` is a volume fraction (cm water / cm soil); `hzdept_r`,
`hzdepb_r` are cm below the surface; `comppct_r` is percent of the map unit; `claytotal_r`,
`sandtotal_r` are weight percent of the < 2 mm fraction. Values are tag E.

SSURGO is an undated current snapshot, not a time series, so the `as_of` guard has nothing to
clip; this check is never used in hindcast mode.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"
USER_AGENT = "fieldwitness-soil-check"


def point_sql(lon: float, lat: float) -> str:
    """Map unit, components and horizons under one WGS84 point (lon first)."""
    return (
        "SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.majcompflag, "
        "h.hzdept_r, h.hzdepb_r, h.awc_r, h.claytotal_r, h.sandtotal_r "
        "FROM mapunit mu INNER JOIN component c ON c.mukey = mu.mukey "
        "LEFT JOIN chorizon h ON h.cokey = c.cokey "
        "WHERE mu.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84("
        f"'point({lon:.6f} {lat:.6f})')) "
        "ORDER BY c.comppct_r DESC, c.cokey, h.hzdept_r"
    )


def parse(payload: dict) -> list[dict]:
    """SDA JSON+COLUMNNAME reply -> list of row dicts (numbers as float, null as None)."""
    table = payload.get("Table") or []
    if not table:
        return []
    names, rows = table[0], table[1:]
    out = []
    for r in rows:
        d = dict(zip(names, r, strict=True))
        for k in ("comppct_r", "hzdept_r", "hzdepb_r", "awc_r", "claytotal_r", "sandtotal_r"):
            d[k] = None if d.get(k) in (None, "") else float(d[k])
        d["majcompflag"] = (d.get("majcompflag") or "").strip()
        out.append(d)
    return out


def query_point(lon: float, lat: float, cache: Path, pause_s: float = 1.0) -> list[dict]:
    """One point per request, cached as the raw reply in `cache` (reruns never re-query)."""
    if cache.exists():
        return parse(json.loads(cache.read_text("utf-8")))
    body = json.dumps({"query": point_sql(lon, lat), "format": "JSON+COLUMNNAME"}).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json", "User-Agent": USER_AGENT}
    )
    for attempt in range(3):  # network timeouts only; HTTP errors (e.g. 400) are raised at once
        try:
            with urllib.request.urlopen(req, timeout=120) as f:
                text = f.read().decode("utf-8")
            break
        except (TimeoutError, urllib.error.URLError) as e:
            if isinstance(e, urllib.error.HTTPError) or attempt == 2:
                raise
            time.sleep(30 * (attempt + 1))
    payload = json.loads(text) if text.strip() else {}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload), "utf-8")
    time.sleep(pause_s)  # polite: sequential requests with a pause
    return parse(payload)


def overlap_cm(top: float, bottom: float, zr_cm: float) -> float:
    """Thickness (cm) of horizon [top, bottom) that lies inside the root zone [0, zr_cm)."""
    return max(0.0, min(bottom, zr_cm) - max(top, 0.0))


def component_profile(horizons: list[dict], zr_cm: float) -> dict | None:
    """Depth-weighted root-zone values for one component.

    Water: AWS_mm = sum(awc_r [cm/cm] * overlap [cm]) * 10 [mm/cm] (the same sum NRCS uses for
    muaggatt aws0100wta, which is in cm of water). FAO-56 Eq. 82 TAW = 1000 (theta_FC - theta_WP)
    Zr [mm] is the same quantity, since awc_r ~ theta_FC - theta_WP (SDM column description).
    Clay and sand: thickness-weighted mean percent over the same zone.
    Returns None if the horizons do not cover the whole root zone or any horizon inside it has
    a null awc_r (no partial profiles)."""
    hz = [h for h in horizons if h["hzdept_r"] is not None and h["hzdepb_r"] is not None]
    parts = [(h, overlap_cm(h["hzdept_r"], h["hzdepb_r"], zr_cm)) for h in hz]
    parts = [(h, t) for h, t in parts if t > 0]
    covered = sum(t for _, t in parts)
    if not parts or abs(covered - zr_cm) > 1e-6 or any(h["awc_r"] is None for h, _ in parts):
        return None
    aws_mm = 10.0 * sum(h["awc_r"] * t for h, t in parts)

    def wmean(key):
        if any(h[key] is None for h, _ in parts):
            return None
        return sum(h[key] * t for h, t in parts) / covered

    return {"aws_mm": aws_mm, "clay_pct": wmean("claytotal_r"), "sand_pct": wmean("sandtotal_r")}


def field_profile(rows: list[dict], zr_cm: float) -> dict:
    """Map-unit value at one point: component-percent weighted mean over components with a
    complete root-zone profile (NRCS's 'weighted average of all components' convention), plus
    the dominant (largest comppct_r) component for sensitivity. `status` explains a miss."""
    if not rows:
        return {"status": "no map unit"}
    comps: dict[str, dict] = {}
    for r in rows:
        c = comps.setdefault(r["cokey"], {"pct": r["comppct_r"], "name": r["compname"], "hz": []})
        if r["hzdept_r"] is not None:
            c["hz"].append(r)
    profiles = []
    for c in comps.values():
        p = component_profile(c["hz"], zr_cm)
        if p is not None and c["pct"]:
            profiles.append((c["pct"], c["name"], p))
    base = {"mukey": rows[0]["mukey"], "muname": rows[0]["muname"], "n_components": len(comps)}
    if not profiles:
        return {
            **base,
            "status": "no awc_r over the full root zone (profile too shallow or null awc_r)",
        }
    w = sum(pct for pct, _, _ in profiles)

    def wavg(key):
        vals = [(pct, p[key]) for pct, _, p in profiles if p[key] is not None]
        sw = sum(pct for pct, _ in vals)
        return sum(pct * v for pct, v in vals) / sw if vals else None

    dom_pct, dom_name, dom = max(profiles, key=lambda t: t[0])
    return {
        **base,
        "status": "ok",
        "aws_mm": wavg("aws_mm"),
        "clay_pct": wavg("clay_pct"),
        "sand_pct": wavg("sand_pct"),
        "pct_used": w,
        "dominant": dom_name,
        "dominant_pct": dom_pct,
        "dominant_aws_mm": dom["aws_mm"],
    }
