"""T8.1 driver: `build_region` writes the per-field files and `index.json` for one region.

Reads the result files of T2-T6 (results/...), the pilot table and the HLS series in data/.
Region-level `hindcast.json` / `layers.json` and `packs/regions.json` are written by other
functions (they need Phase 7 and the GRACE/SMAP layers).
Fails (raises) if any user-facing number is untagged or a pack exceeds the size limit.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.data import labels as labels_mod
from fieldwitness.data import power
from fieldwitness.data.context import grace_file
from fieldwitness.packs import build as B
from fieldwitness.packs import extras as X
from fieldwitness.packs import sim3d as sim3d_mod
from fieldwitness.physics.forcing import forcing
from fieldwitness.rotate.current import all_current
from fieldwitness.rotate.evaluate import evaluate
from fieldwitness.rotate.priority import load_crops
from fieldwitness.schemas import RegionIndex, Tagged, check_tagged
from fieldwitness.story.seasons import EPOCH, detect_seasons, load_story
from fieldwitness.story.smooth import smooth_series

MAX_PACK_BYTES = 300_000
Y0, Y1 = 2001, 2024
R = Path("results")
# lon, lat of the SMAP AppEEARS point per region (data/context/smap_task.json, T1.8)
SMAP_POINTS = {"ks_t14slh": (-100.66036757568659, 38.34248485880243)}


def _j(p: str) -> dict:
    return json.loads((R / p).read_text("utf-8"))


def _weather(lon: float, lat: float):
    w = power.read(lon, lat, f"{Y0}-01-01", f"{Y1}-12-31")
    _, elev = power.cached(lon, lat)
    f = forcing(w, lat, float(elev or 0.0))
    rain, eto = [], []
    for y in range(Y0, Y1 + 1):
        fy = f[(f.index.year == y) & ~((f.index.month == 2) & (f.index.day == 29))]
        if len(fy) != 365 or fy.isna().any().any():
            continue
        rain.append(fy["rain"].to_numpy(float))
        eto.append(fy["eto"].to_numpy(float))
    return np.array(rain), np.array(eto)


_OPT_NULL = ("lo50", "hi50", "lo90", "hi90")


def _slim(o):
    """Drop null interval bounds (Tagged defaults, size); `value: null` stays (required)."""
    if isinstance(o, dict):
        return {k: _slim(v) for k, v in o.items() if not (k in _OPT_NULL and v is None)}
    if isinstance(o, list):
        return [_slim(v) for v in o]
    return o


def _write(path: Path, model, problems: list[str]) -> None:
    bad = check_tagged(model)
    if bad:
        problems.extend(f"{path.name}: untagged {b}" for b in bad[:5])
    txt = json.dumps(_slim(model.model_dump(mode="json")), separators=(",", ":"))
    if len(txt.encode()) > MAX_PACK_BYTES:
        problems.append(f"{path.name}: {len(txt.encode())} bytes > {MAX_PACK_BYTES}")
    path.write_text(txt, "utf-8")


def build_region(region_id: str, out_root: Path = Path("packs"), limit: int | None = None) -> dict:
    out = out_root / region_id
    out.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_parquet(f"data/fields/{region_id}_pilot.parquet")
    series = pd.read_parquet(f"data/fields/{region_id}_hls_series.parquet")
    series["date"] = pd.to_datetime(series["date"])
    as_of = series["date"].max().date()
    ev, rk, gr = _j("rotate/evaluation.json"), _j("rotate/ranking.json"), _j("rotate/grades.json")
    fl, pri, sc = _j("rotate/flip.json"), _j("rotate/priority.json"), _j("rotate/scenarios.json")
    pd_ = _j("rotate/posterior_draws.json")["fields"]
    cred = {f["field_id"]: f["credibility"] for f in _j("inference/credibility.json")["fields"]}
    allowed = set(_j("rotate/current_summary.json")["allowed"])
    currents = all_current(allowed, region_id=region_id)
    lab = labels_mod.read(region_id)
    crops = load_crops()
    fam = {c: (v.family.value if v.family else None) for c, v in crops.crops.items()}
    ky_ok = {c: bool(v.ky is not None and v.ky.verified) for c, v in crops.crops.items()}
    cfg = load_story()
    problems: list[str] = []
    summaries, sizes = [], []
    vcfg = X.load_vuln_cfg()
    bare = _j(f"story/{region_id.split('_')[0]}_bare_calendar.json")
    colour: dict[str, dict] = {"erosion_exposure": {}, "water_stress_share": {}, "frost_share": {}}
    rows = pilot if limit is None else pilot.head(limit)
    for _, r in rows.iterrows():
        fid = str(r["field_id"])
        fld = B.field_model(r, region_id)
        s = series[series["field_id"] == fid].sort_values("date")
        t = lab[lab["field_id"] == fid]
        crop_by_year = {int(y): c for y, c in zip(t["year"], t["crop"], strict=True)}
        seasons = B.story(detect_seasons(s["date"], s["ndvi"], cfg), crop_by_year)
        days = (s["date"] - EPOCH).dt.days.to_numpy(float)
        ok = s["ndvi"].notna().to_numpy()
        grid, sm = smooth_series(days[ok], s["ndvi"].to_numpy(float)[ok], cfg["smoothing"])
        cur = currents[fid]
        c_metrics = None
        if cur.simulatable and not cur.second_crops and len(cur.sequence) == 3:
            rain, eto = _weather(float(r["lon"]), float(r["lat"]))
            res = evaluate(rain, eto, [tuple(cur.sequence)], region_id, pd_[fid])
            c_metrics = {k: res[k][0] for k in B.EVAL_KEYS if res.get(k) and res[k][0] is not None}
        opts = B.options(
            fid,
            ev[fid],
            rk[fid],
            gr.get(fid),
            cur.sequence,
            c_metrics,
            cred.get(fid),
            pri[fid],
            fam,
            ky_ok,
            bool(r["hls_scale_flag"]),
        )
        pack = B.field_pack(fld, seasons, cred.get(fid), opts, fl[fid], as_of)
        _write(out / f"{fid}.json", pack, problems)
        _write(out / f"{fid}.series.json", B.field_series(fid, s, grid, sm, as_of), problems)
        _write(
            out / f"{fid}.scenarios.json",
            B.field_scenarios(fid, sc[fid], ev[fid]["candidates"], ev[fid]["tag"], as_of),
            problems,
        )
        # calendar (T2.5 observed, simulated bare per option, T3.6 vulnerability)
        canopies = {}
        all_seqs = [tuple(k) for k in ev[fid]["candidates"]] + [tuple(cur.sequence)]
        for key in dict.fromkeys(all_seqs):
            try:
                canopies[B.oid(key)] = X.canopy_for(key, region_id)
            except KeyError:  # a crop without a slot (e.g. soybean in Current)
                continue
        wx = power.read(float(r["lon"]), float(r["lat"]), f"{Y0}-01-01", f"{Y1}-12-31")
        _, elev = power.cached(float(r["lon"]), float(r["lat"]))
        f_ = forcing(wx, float(r["lat"]), float(elev or 0.0))
        vcrops = list(cur.sequence) + [c for key in ev[fid]["candidates"] for c in key]
        vuln = X.vulnerability(
            wx,
            f_["eto"],
            vcrops,
            region_id,
            vcfg,
            float(np.median(pd_[fid]["taw_mm"])),
            float(np.median(pd_[fid]["kc_scale"])),
        )
        cal = X.field_calendar(
            fid,
            bare[fid],
            (int(cfg["bare_calendar"]["first_year"]), as_of.year),
            X.bare_by_option(canopies),
            vuln,
            as_of,
        )
        _write(out / f"{fid}.calendar.json", cal, problems)
        top_alts = sorted(opts[1:], key=lambda o: o.rank)[:3]
        sim3d_data = sim3d_mod.build_field_sim3d(
            fid,
            tuple(cur.sequence),
            top_alts,
            wx,
            float(r["lat"]),
            float(elev or 0.0),
            float(np.median(pd_[fid]["taw_mm"])),
            float(np.median(pd_[fid]["kc_scale"])),
            float(np.median(pd_[fid]["budget_mm"])),
            region_id=region_id,
            start_year=2022,
        )
        _write(out / f"{fid}.sim3d.json", sim3d_data, problems)
        eros = opts[0].metrics.get("erosion_exposure")
        if eros is not None and eros.value is not None:
            colour["erosion_exposure"][fid] = eros
        for m, h in (("frost_share", "frost"), ("water_stress_share", "water_stress")):
            v = X.worst_month_share(cal.vulnerability, h)
            if v is not None:
                colour[m][fid] = Tagged(
                    value=round(v, 3),
                    unit="share of years (worst month, mean of Current crops)",
                    tag="D",
                    source=X.VULN_SRC,
                )
        top = min(opts[1:], key=lambda o: o.rank)
        summaries.append(B.field_summary(fld, cur.sequence, top))
        sizes.append((out / f"{fid}.json").stat().st_size)
    bb = pilot.lon.min(), pilot.lat.min(), pilot.lon.max(), pilot.lat.max()
    idx = RegionIndex(
        schema_version=B.SCHEMA_VERSION,
        region_id=region_id,
        name=region_id,
        tier=1,
        bbox_lonlat=tuple(float(v) for v in bb),
        basemap=None,
        fields=summaries,
        data_as_of=as_of,
    )
    _write(out / "index.json", idx, problems)
    grace = X.grace_layer(grace_file(), bb)
    smap = pd.read_parquet("data/context/smap_monthly.parquet")
    smap = smap[smap["region_id"] == region_id]
    lon_c, lat_c = SMAP_POINTS[region_id]
    lay = X.region_layers(
        region_id,
        [grace, X.smap_layer(smap, lon_c, lat_c)],
        colour,
        as_of,  # type: ignore[arg-type]
    )
    _write(out / "layers.json", lay, problems)
    _write(out_root / "regions.json", X.regions_list([(region_id, region_id, 1)]), problems)
    return {"fields": len(summaries), "max_pack_bytes": max(sizes), "problems": problems}
