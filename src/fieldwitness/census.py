"""T0.5 data census per candidate region (PLAN.md T0.5).

Inputs are metadata and small bbox reads only:
- HLS-VI observation and cloud counts from CMR granule metadata (`CLOUD_COVERAGE`,
  `SPATIAL_COVERAGE` AdditionalAttributes; tile-level, not field-level clear observations).
- ECOSTRESS ECO_L3T_JET overpass counts (CMR hit counts at the region point), v002 and v003.
- Field sizes and interior HLS pixels from boundary GeoParquet, bbox reads under the 200 MB cap.
- Label years from the boundary/label files available.
No imagery is downloaded. Raw CMR granule metadata is cached under data/census/ (gitignored).
"""

import calendar
import datetime as dt
import json
import statistics
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import yaml
from pyproj import Transformer
from shapely.geometry import box

from fieldwitness.data.geoparquet import DEFAULT_CAP_MB, OverCap, open_source, read_bbox
from fieldwitness.data.hcat import is_annual_arable, normalise
from fieldwitness.resolve.pixels import interior_pixel_counts

CMR = "https://cmr.earthdata.nasa.gov/search/granules"
HLS_PRODUCTS = [("HLSL30_VI", "2.0", "L30"), ("HLSS30_VI", "2.0", "S30")]
ECO_VERSIONS = ["002", "003"]
HLS_YEARS = range(2016, 2025)
ECO_YEARS = range(2018, 2025)
SAMPLE_KM = 20.0
HLS_PIXEL_M2 = 900.0
SCALE_FLAG_HA = 4 * HLS_PIXEL_M2 / 1e4  # CLAUDE.md rule 5: pixel area > field area / 4
CACHE = Path("data/census")
OUT = Path("docs/census")


def load_regions(path: str = "config/regions.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["regions"]


# ---------------------------------------------------------------- seasons


def season_window(start: int, end: int, year: int) -> tuple[dt.date, dt.date]:
    """Inclusive date window of the season whose harvest year (end month) is `year`."""
    y0 = year - 1 if start > end else year
    return dt.date(y0, start, 1), dt.date(year, end, calendar.monthrange(year, end)[1])


# ---------------------------------------------------------------- CMR


def _cmr_get(url: str, params: dict, headers: dict | None = None) -> requests.Response:
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=120)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def hls_granules(tile: str, short_name: str, version: str, sensor: str) -> list[dict]:
    """All granules of one HLS-VI product on one tile, Sep 2015 - Dec 2024 (cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{tile}_{short_name}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "short_name": short_name,
        "version": version,
        "readable_granule_name": f"HLS-VI.{sensor}.{tile}.*",
        "options[readable_granule_name][pattern]": "true",
        "temporal": "2015-09-01T00:00:00Z,2024-12-31T23:59:59Z",
        "page_size": 500,
    }
    out, after = [], None
    while True:
        headers = {"CMR-Search-After": after} if after else {}
        r = _cmr_get(f"{CMR}.umm_json", params, headers)
        items = r.json()["items"]
        for it in items:
            u = it["umm"]
            aa = {a["Name"]: a["Values"][0] for a in u.get("AdditionalAttributes", [])}
            out.append(
                {
                    "date": u["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10],
                    "cloud": float(aa["CLOUD_COVERAGE"]),
                    "spatial": float(aa["SPATIAL_COVERAGE"]),
                    "sensor": sensor,
                }
            )
        after = r.headers.get("CMR-Search-After")
        if not items or not after:
            break
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def cmr_hits(params: dict) -> int:
    r = _cmr_get(f"{CMR}.json", {**params, "page_size": 0})
    return int(r.headers["CMR-Hits"])


# ---------------------------------------------------------------- summaries


def hls_season_table(granules: list[dict], seasons: dict) -> pd.DataFrame:
    df = pd.DataFrame(granules)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    rows = []
    for name, s in seasons.items():
        for y in HLS_YEARS:
            a, b = season_window(s["start"], s["end"], y)
            g = df[(df["date"] >= a) & (df["date"] <= b)]
            rows.append(
                {
                    "season": name,
                    "year": y,
                    "granules": len(g),
                    "L30": int((g["sensor"] == "L30").sum()),
                    "S30": int((g["sensor"] == "S30").sum()),
                    "cloud_le20": int((g["cloud"] <= 20).sum()),
                    "cloud_le50": int((g["cloud"] <= 50).sum()),
                    "cloud_le20_spatial_ge50": int(
                        ((g["cloud"] <= 20) & (g["spatial"] >= 50)).sum()
                    ),
                    "median_cloud_pct": round(float(g["cloud"].median()), 1) if len(g) else None,
                    "median_spatial_pct": round(float(g["spatial"].median()), 1)
                    if len(g)
                    else None,
                }
            )
    return pd.DataFrame(rows)


def hls_monthly(granules: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(granules)
    d = pd.to_datetime(df["date"])
    df = df[(d.dt.year >= HLS_YEARS.start) & (d.dt.year < HLS_YEARS.stop)]
    d = pd.to_datetime(df["date"])
    n_years = len(HLS_YEARS)
    g = df.groupby(d.dt.month)
    return pd.DataFrame(
        {
            "mean_granules": (g.size() / n_years).round(1),
            "mean_cloud_le20": (g["cloud"].apply(lambda c: (c <= 20).sum()) / n_years).round(1),
        }
    ).reindex(range(1, 13), fill_value=0.0)


def ecostress_table(point: list[float], seasons: dict) -> pd.DataFrame:
    rows = []
    for name, s in seasons.items():
        for y in ECO_YEARS:
            a, b = season_window(s["start"], s["end"], y)
            row = {"season": name, "year": y}
            for v in ECO_VERSIONS:
                row[f"v{v}"] = cmr_hits(
                    {
                        "short_name": "ECO_L3T_JET",
                        "version": v,
                        "point": f"{point[0]},{point[1]}",
                        "temporal": f"{a}T00:00:00Z,{b}T23:59:59Z",
                    }
                )
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- boundaries


def tile_grid(tile: str) -> dict:
    """UTM EPSG code and grid origin of an HLS tile, from one granule's CMR metadata."""
    r = _cmr_get(
        f"{CMR}.umm_json",
        {
            "short_name": "HLSS30_VI",
            "version": "2.0",
            "readable_granule_name": f"HLS-VI.S30.{tile}.*",
            "options[readable_granule_name][pattern]": "true",
            "page_size": 1,
        },
    )
    aa = {a["Name"]: a["Values"][0] for a in r.json()["items"][0]["umm"]["AdditionalAttributes"]}
    ncols = int(aa["NCOLS"])
    return {
        "epsg": aa["HORIZONTAL_CS_CODE"],
        "ulx": float(aa["ULX"]),
        "uly": float(aa["ULY"]),
        "size_m": ncols * 30.0,
    }


def box_around(lon: float, lat: float, km: float) -> tuple[float, float, float, float]:
    dlat = km / 2 / 111.32
    dlon = km / 2 / (111.32 * np.cos(np.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def tile_centre_lonlat(grid: dict) -> tuple[float, float]:
    t = Transformer.from_crs(grid["epsg"], "EPSG:4326", always_xy=True)
    return t.transform(grid["ulx"] + grid["size_m"] / 2, grid["uly"] - grid["size_m"] / 2)


def tile_lonlat_bounds(grid: dict) -> tuple[float, float, float, float]:
    t = Transformer.from_crs(grid["epsg"], "EPSG:4326", always_xy=True)
    x0, y1 = grid["ulx"], grid["uly"]
    return t.transform_bounds(x0, y1 - grid["size_m"], x0 + grid["size_m"], y1)


def _read_boundary(src, region: dict, lonlat_box) -> tuple:
    """Capped bbox read; with `boundary.cache_as` the result is cached under data/census/."""
    b = region["boundary"]
    cache = CACHE / b["cache_as"] if b.get("cache_as") else None
    if cache is not None and cache.exists():
        gdf = gpd.read_parquet(cache)
        return gdf, json.loads(cache.with_suffix(".json").read_text(encoding="utf-8"))
    gdf, info = read_bbox(
        src, b["key"], lonlat_box, cap_mb=b.get("cap_mb", DEFAULT_CAP_MB), columns=b.get("columns")
    )
    if cache is not None:
        CACHE.mkdir(parents=True, exist_ok=True)
        gdf.to_parquet(cache)
        info = {k: v for k, v in info.items() if k != "file_box"} | {
            "file_box": list(info["file_box"])
        }
        cache.with_suffix(".json").write_text(json.dumps(info), encoding="utf-8")
    return gdf, info


def boundary_stats(src, region: dict, lonlat_box, grid: dict) -> dict:
    gdf, info = _read_boundary(src, region, lonlat_box)
    year = region["boundary"].get("year")
    if year is not None and "determination:datetime" in gdf.columns:
        gdf = gdf[pd.to_datetime(gdf["determination:datetime"]).dt.year == year]
    utm = gdf.to_crs(grid["epsg"])
    to_utm = Transformer.from_crs("EPSG:4326", grid["epsg"], always_xy=True)
    sample = box(*to_utm.transform_bounds(*lonlat_box))
    utm = utm[utm.geometry.centroid.within(sample)]  # count each field once, by centroid
    arable = None
    if region["boundary"].get("arable_only"):
        codes = utm["hcat:code"].map(normalise)
        keep = codes.map(is_annual_arable)
        groups = codes.where(~keep).dropna().str[:4].value_counts().to_dict()
        arable = {
            "parcels_all": int(len(utm)),
            "parcels_kept": int(keep.sum()),
            "excluded_by_hcat_group": {k: int(v) for k, v in sorted(groups.items())},
            "excluded_missing_code": int(codes.isna().sum()),
        }
        utm = utm[keep.to_numpy()]
    area_ha = utm.geometry.area.to_numpy() / 1e4
    geoms = list(utm.geometry)
    n30 = interior_pixel_counts(geoms, grid["ulx"], grid["uly"], buffer_m=30)
    n15 = interior_pixel_counts(geoms, grid["ulx"], grid["uly"], buffer_m=15)
    n = len(area_ha)
    pct = np.percentile(area_ha, [10, 25, 50, 75, 90]) if n else [None] * 5
    return {
        "read": {k: v for k, v in info.items() if k != "file_box"},
        "sample_box_lonlat": [round(v, 4) for v in lonlat_box],
        "sample_area_km2": round(sample.area / 1e6, 1),
        "fields": n,
        "area_ha_p10_p25_p50_p75_p90": [round(float(v), 2) for v in pct] if n else None,
        "area_ha_mean": round(float(area_ha.mean()), 2) if n else None,
        "field_cover_fraction": round(float(area_ha.sum() * 1e4 / sample.area), 3),
        "share_scale_flag_lt_0p36ha": round(float((area_ha < SCALE_FLAG_HA).mean()), 3)
        if n
        else None,
        "share_ge4_interior_px_buf30": round(float((n30 >= 4).mean()), 3) if n else None,
        "share_ge4_interior_px_buf15": round(float((n15 >= 4).mean()), 3) if n else None,
        "median_interior_px_buf30": float(np.median(n30)) if n else None,
        "field_definition": "annual arable (HCAT3, fieldwitness.data.hcat)" if arable else "all",
        "arable_filter": arable,
    }


def sample_stats(src, region: dict, lonlat_box, grid: dict) -> dict:
    """boundary_stats, or an over-cap record (read not run) if the estimate exceeds the cap."""
    try:
        return boundary_stats(src, region, lonlat_box, grid)
    except OverCap as e:
        info = {k: v for k, v in e.info.items() if k != "file_box"}
        return {
            "over_cap": True,
            "read": info,
            "sample_box_lonlat": [round(v, 4) for v in lonlat_box],
        }


def label_years(src, region: dict) -> list[int]:
    lab = region.get("labels") or {}
    if not lab.get("years"):
        return []
    y0, y1 = lab["years"]
    found = []
    for y in range(y0, y1 + 1):
        info = src.fs.get_file_info(src.path(lab["key_pattern"].format(y=y)))
        if getattr(info, "type", None) is not None and info.type.name == "File":
            found.append(y)
    return found


# ---------------------------------------------------------------- run + write


def run_region(region_id: str, region: dict) -> dict:
    src = open_source()
    res: dict = {"region_id": region_id, "tier": region["tier"], "name": region["name"]}
    res["hls"] = {}
    for tile in region["tiles"]:
        gran = []
        for sn, v, sensor in HLS_PRODUCTS:
            gran += hls_granules(tile, sn, v, sensor)
        res["hls"][tile] = {
            "seasons": hls_season_table(gran, region["seasons"]).to_dict("records"),
            "monthly": hls_monthly(gran).reset_index(names="month").to_dict("records"),
        }
    res["ecostress"] = ecostress_table(region["point"], region["seasons"]).to_dict("records")

    grids = {t: tile_grid(t) for t in region["tiles"]}
    km = region.get("sample_km", SAMPLE_KM)
    if not region.get("boundary"):
        chosen = region["tiles"][0]
        res["tile"] = chosen
        res["boundary"] = {}
    elif len(region["tiles"]) > 1:
        cover = {}
        for t, g in grids.items():
            lon, lat = tile_centre_lonlat(g)
            cover[t] = sample_stats(src, region, box_around(lon, lat, km), g)
        ok = [t for t in cover if not cover[t].get("over_cap")] or list(cover)
        chosen = max(ok, key=lambda t: cover[t].get("field_cover_fraction", -1))
        res["tile_choice"] = {
            t: c.get("field_cover_fraction", f"over cap ({c['read']['estimated_mb']} MB)")
            for t, c in cover.items()
        }
        res["tile"] = chosen
        res["boundary"] = {f"box{km:g}km_tile_centre": cover[chosen]}
    else:
        chosen = region["tiles"][0]
        res["tile"] = chosen
        g = grids[chosen]
        res["boundary"] = {
            f"box{km:g}km": sample_stats(src, region, box_around(*region["point"], km), g)
        }
        if region.get("full_tile_sample"):
            res["boundary"]["full_tile"] = sample_stats(src, region, tile_lonlat_bounds(g), g)
    res["grid"] = grids[chosen]
    res["label_years"] = label_years(src, region)
    res["seasons_def"] = region["seasons"]
    res["boundary_source"] = (region.get("boundary") or {}).get("source", "none (CMR-only)")
    res["generated"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    return res


def _md_table(rows: list[dict], cols: list[str]) -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)


def season_summary(res: dict, tile: str | None = None) -> dict:
    """Median over harvest years, per season, of observation counts on the chosen tile."""
    rows = res["hls"][tile or res["tile"]]["seasons"]
    out = {}
    for s in res["seasons_def"]:
        r = [x for x in rows if x["season"] == s]
        keys = ("granules", "cloud_le20", "cloud_le50", "cloud_le20_spatial_ge50", "L30", "S30")
        out[s] = {k: statistics.median(x[k] for x in r) for k in keys}
        out[s]["min_cloud_le20"] = min(x["cloud_le20"] for x in r)
        out[s]["min_cloud_le20_spatial_ge50"] = min(x["cloud_le20_spatial_ge50"] for x in r)
    eco = res["ecostress"]
    for s in res["seasons_def"]:
        e = [x for x in eco if x["season"] == s and x["year"] >= 2019]
        for v in ECO_VERSIONS:
            out[s][f"eco_v{v}"] = statistics.median(x[f"v{v}"] for x in e)
    return out


def write_region(res: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{res['region_id']}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    s = res["seasons_def"]
    lines = [
        f"# Census — {res['name']} (`{res['region_id']}`, Tier {res['tier']})",
        "",
        f"Generated {res['generated']} by `fieldwitness.cli census`. Tile **{res['tile']}** "
        f"({res['grid']['epsg']}). Numbers are counts from CMR metadata and bbox reads; "
        "no imagery downloaded.",
        "",
        "Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by "
        "harvest year): " + "; ".join(f"{k} months {v['start']}–{v['end']}" for k, v in s.items()),
        "",
    ]
    if "tile_choice" in res:
        lines += [
            "Tile choice (field cover fraction of FTW 2024 polygons in a 20 km box at each tile "
            f"centre): {res['tile_choice']} → **{res['tile']}**.",
            "",
        ]
    lines += ["## Summary (medians over harvest years)", ""]
    summ = season_summary(res)
    lines.append(
        _md_table(
            [{"season": k, **v} for k, v in summ.items()],
            [
                "season",
                "granules",
                "L30",
                "S30",
                "cloud_le50",
                "cloud_le20",
                "min_cloud_le20",
                "cloud_le20_spatial_ge50",
                "min_cloud_le20_spatial_ge50",
                "eco_v002",
                "eco_v003",
            ],
        )
    )
    lines += [
        "`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / "
        "≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. "
        "`eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a "
        "partial archive).",
        "",
    ]
    for tile, h in res["hls"].items():
        lines += [f"## HLS-VI observations per season and year — {tile}", ""]
        lines.append(
            _md_table(
                h["seasons"],
                [
                    "season",
                    "year",
                    "granules",
                    "L30",
                    "S30",
                    "cloud_le50",
                    "cloud_le20",
                    "cloud_le20_spatial_ge50",
                    "median_cloud_pct",
                    "median_spatial_pct",
                ],
            )
        )
        lines += ["", f"Monthly means 2016–2024 ({tile}):", ""]
        lines.append(_md_table(h["monthly"], ["month", "mean_granules", "mean_cloud_le20"]))
        lines.append("")
    lines += ["## ECOSTRESS ECO_L3T_JET overpasses at the region point", ""]
    lines.append(_md_table(res["ecostress"], ["season", "year", "v002", "v003"]))
    lines += ["", f"## Field sizes and interior pixels ({res['boundary_source']})", ""]
    for name, b in res["boundary"].items():
        lines += [f"### Sample `{name}`", "", "```json", json.dumps(b, indent=1), "```", ""]
    lines += [
        "Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer "
        "of 30 m (old rule) or 15 m (PLAN.md T1.4 since 2026-11-04), on the tile grid (ULX/ULY "
        "from CMR). Scale flag: field "
        f"< {SCALE_FLAG_HA} ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are "
        "counted once, by centroid inside the sample box.",
        "",
        "## Label years",
        "",
        f"{res['label_years'] or 'none (no crop labels; Tier 3 crops are inferred)'}",
        "",
    ]
    p = OUT / f"{res['region_id']}.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def write_comparison(region_ids: list[str]) -> Path:
    rows = []
    for rid in region_ids:
        res = json.loads((OUT / f"{rid}.json").read_text(encoding="utf-8"))
        gran = [
            g for sn, v, sensor in HLS_PRODUCTS for g in hls_granules(res["tile"], sn, v, sensor)
        ]
        res["hls"][res["tile"]]["seasons"] = hls_season_table(gran, res["seasons_def"]).to_dict(
            "records"
        )
        summ = season_summary(res)
        b = next(iter(res["boundary"].values()), None)
        if b is None:
            over = "n/a (CMR-only)"
        elif b.get("over_cap"):
            over = f"over cap ({b['read']['estimated_mb']} MB)"
        else:
            over = None
        for s, v in summ.items():
            rows.append(
                {
                    "region": rid,
                    "tier": res["tier"],
                    "tile": res["tile"],
                    "season": s,
                    "obs": v["granules"],
                    "obs_cloud<=20": v["cloud_le20"],
                    "worst_year_cloud<=20": v["min_cloud_le20"],
                    "obs_cloud<=20_cov>=50": v["cloud_le20_spatial_ge50"],
                    "worst_year_cloud<=20_cov>=50": v["min_cloud_le20_spatial_ge50"],
                    "eco_v002": v["eco_v002"],
                    "eco_v003": v["eco_v003"],
                    "median_field_ha": over or b["area_ha_p10_p25_p50_p75_p90"][2],
                    "share>=4px_buf30": over or b["share_ge4_interior_px_buf30"],
                    "share>=4px_buf15": over or b["share_ge4_interior_px_buf15"],
                    "share_scale_flag": over or b["share_scale_flag_lt_0p36ha"],
                    "label_years": len(res["label_years"]),
                }
            )
    cols = list(rows[0])
    text = [
        "# Census comparison (T0.5)",
        "",
        "One row per region and season. Observation counts are medians over harvest years "
        "2016–2024 of HLS-VI granules (L30 + S30) on the region tile, from CMR metadata; "
        "`obs_cloud<=20` counts granules with tile-level cloud ≤ 20 %; `_cov>=50` additionally "
        "requires `SPATIAL_COVERAGE` ≥ 50 % of the tile (many granules cover only part of a tile, "
        "so raw counts overstate observations at a given field). ECOSTRESS: median "
        "overpasses per season 2019–2024 at the region point. Field statistics: first sample "
        "box per region (20 km; Ukraine 10 km; FTW: 2024 layer only). Season windows: tag **A**. "
        "Per-region details: `docs/census/<region>.md`. Region status (user decision): "
        + "; ".join(f"`{rid}` {load_regions()[rid].get('status')}" for rid in region_ids)
        + ".",
        "",
        _md_table(rows, cols),
    ]
    rec = OUT / "_recommendation.md"
    if rec.exists():
        text += ["", rec.read_text(encoding="utf-8")]
    p = OUT / "comparison.md"
    p.write_text("\n".join(text), encoding="utf-8")
    return p
