"""T8.1 part 2: calendar, regional layers and region list (pure builders + small readers).

- `field_calendar`: observed bare months (T2.5, tag O), simulated bare share per month per option
  (tag D, `rotate.exposure.option_canopy`), crop vulnerability (T3.6, tag D).
- `region_layers`: GRACE (JPL TELLUS or UT-CSR RL06.3), SMAP, and POWER heat-wave grids + region
  means + trend, and Current-option field colouring.
- `regions_list`: `packs/regions.json`.

Team choices (A, UNVERIFIED): `water_stress` uses a rainfed run with the median ABC world (TAW,
Kc scale) of the field; frost / water-stress colouring = mean over modelled Current crops of the
worst monthly share. Heat-wave days count days/year with `T2M_MAX >= 35.0 degC` (summer heat
threshold A from `config/vulnerability.yaml`) on the NASA POWER MERRA-2 native `0.5 x 0.625 deg`
grid verified in POWER API v2.10.3 headers and empirical cell boundaries (`T14SLH`/`T36UVU`).
The SMAP cell box is the point +-4.5 km (approximate; AppEEARS point task returns one 9 km cell).
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import xarray as xr
import yaml
from pydantic import BaseModel

from fieldwitness.data import power
from fieldwitness.physics import waterbal
from fieldwitness.physics.kc import kc_curve
from fieldwitness.physics.vulnerability import HAZARDS, CropWindow, hazard_shares
from fieldwitness.rotate.exposure import COVER_FRAC, option_canopy
from fieldwitness.rotate.slots import SOW_DAY, _crops, _kc_ini
from fieldwitness.schemas import (
    BareMonth,
    CropVulnerability,
    FieldCalendar,
    FieldPack,
    GridCell,
    RegionalLayer,
    RegionEntry,
    RegionIndex,
    RegionLayers,
    RegionList,
    Tagged,
    TaggedGrid,
    TaggedSeries,
)

SCHEMA_VERSION = "1.2"
MONTHS = list(range(1, 13))
_DIM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_MONTH_OF_DAY = np.repeat(MONTHS, _DIM)  # 365 days, no leap day (same as the timeline)
# crops with a sowing day (maize, sorghum, winter_wheat, sunflower, soybean)
VULN_CROPS = tuple(SOW_DAY)
VULN_SRC = "POWER daily weather x crop windows (crops.yaml); thresholds A, UNVERIFIED"


def _r(x: float | None, n: int = 3) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


def _share_series(vals, source: str) -> TaggedSeries:
    return TaggedSeries(
        x=MONTHS,
        values=[_r(v) for v in vals],
        unit="share of years",
        tag="D",
        source=source,
    )


def bare_by_option(canopies: dict[str, np.ndarray]) -> dict[str, TaggedSeries]:
    """option_id -> share of timeline-year days per calendar month with canopy proxy < 0.5."""
    out = {}
    for oid_, c in canopies.items():
        c = np.asarray(c, float).reshape(-1, 365)
        low = (c < COVER_FRAC).mean(axis=0)
        vals = [low[_MONTH_OF_DAY == m].mean() for m in MONTHS]
        out[oid_] = _share_series(vals, "simulated canopy proxy (Kc/Kc_mid) < 0.5, per option")
    return out


def canopy_for(seq: tuple[str, ...] | list[str], region_id: str) -> np.ndarray:
    from fieldwitness.rotate.slots import option_slots

    return option_canopy(option_slots(tuple(seq), region_id))


def _window(crop: str, region_id: str) -> tuple[CropWindow, float]:
    c = _crops().crops[crop]
    stages = tuple(int(x) for x in c.stage_lengths_days[region_id].value)
    sow = SOW_DAY[crop]
    doy = sow + 1 if sow >= 0 else 365 + sow + 1  # 1-based day of the sowing year
    kc_ini, kc_mid, kc_end = _kc_ini(c, region_id), float(c.kc_mid.value), float(c.kc_end.value)
    return CropWindow(stages, doy, kc_ini, kc_mid, kc_end), float(c.p.value)


def load_vuln_cfg(path: str = "config/vulnerability.yaml") -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _ks_series(
    w: CropWindow, p: float, weather: pd.DataFrame, eto: pd.Series, taw_mm: float, kc_scale: float
) -> pd.Series:
    """Rainfed Ks over the whole record; Kc = crop curve inside windows, 0.3 (fallow) outside."""
    idx = eto.index
    kc = pd.Series(0.3, index=idx)
    curve = kc_curve(w.stage_days, w.kc_ini, w.kc_mid, w.kc_end) * kc_scale
    for y in range(idx[0].year - 1, idx[-1].year + 1):
        start = pd.Timestamp(year=y, month=1, day=1) + pd.Timedelta(days=w.sow_doy - 1)
        days = pd.date_range(start, periods=len(curve), freq="D")
        keep = days.isin(idx)
        kc.loc[days[keep]] = curve[keep]
    res = waterbal.run(
        weather["PRECTOTCORR"].reindex(idx).fillna(0.0).to_numpy(float),
        (kc * eto).to_numpy(float),
        taw_mm,
        p,
    )
    return pd.Series(res["ks"], index=idx)


def vulnerability(
    weather: pd.DataFrame,
    eto: pd.Series,
    crops: list[str],
    region_id: str,
    cfg: dict,
    taw_mm: float,
    kc_scale: float,
) -> list[CropVulnerability]:
    out = []
    years = (int(weather.index[0].year), int(weather.index[-1].year))
    q = float(cfg["rain_quantile"]["value"])
    crops_cfg = _crops().crops
    heat_map = cfg.get("heat_tmax_c", {})
    for crop in dict.fromkeys(c for c in crops if c in VULN_CROPS and c in heat_map):
        st_map = crops_cfg[crop].stage_lengths_days
        if region_id not in st_map or st_map[region_id].value is None:
            continue
        w, p = _window(crop, region_id)
        heat = float(heat_map[crop]["value"])
        frost = float(cfg["frost_tmin_c"]["value"])
        ks = _ks_series(w, p, weather, eto, taw_mm, kc_scale)
        sh = hazard_shares(weather, w, heat, frost, ks, q, float(cfg["cover_frac"]["value"]))
        rain_thr = float(weather["PRECTOTCORR"].quantile(q))
        thr = {
            "heat": Tagged(value=heat, unit="degC Tmax", tag="A", source="team placeholder"),
            "frost": Tagged(value=frost, unit="degC Tmin", tag="A", source="PLAN.md T3.6 text"),
            "water_stress": Tagged(
                value=1.0, unit="Ks below this", tag="A", source="FAO-56 Eq. 84, Ks < 1"
            ),
            "extreme_rain_bare": Tagged(
                value=_r(rain_thr, 1), unit="mm/day", tag="D", source=f"POWER, {q:.0%} quantile"
            ),
        }
        notes = {
            "heat": "Tmax above threshold in the mid-season stage; placeholder, UNVERIFIED",
            "frost": "Tmin <= 0 degC after green-up (end of initial stage); not a damage threshold",
            "water_stress": f"rainfed run, median ABC world (TAW {taw_mm:.0f} mm); Ks < 1 days",
            "extreme_rain_bare": "rain above the local quantile on a day with no crop cover",
        }
        out.append(
            CropVulnerability(
                crop=crop,
                years=years,
                thresholds=thr,
                threshold_notes=notes,
                shares={h: _share_series(sh[h], VULN_SRC) for h in HAZARDS},
            )
        )
    return out


def obs_checks_series(
    field_lst: pd.DataFrame | None = None,
    era5_df: pd.DataFrame | None = None,
    heat_threshold_c: float = 35.0,
    rain_quantile: float = 0.99,
) -> dict[str, TaggedSeries] | None:
    """Build observed satellite thermal [O] & ERA5 extreme-rain [E] monthly check rows."""
    out: dict[str, TaggedSeries] = {}
    if field_lst is not None and not field_lst.empty:
        fl = field_lst.copy()
        fl["date"] = pd.to_datetime(fl["date"])
        fl = fl[fl["lst_c"].notna()]
        fl["year"] = fl["date"].dt.year
        fl["month"] = fl["date"].dt.month
        lst_vals: list[float | None] = []
        for m in MONTHS:
            sm = fl[fl["month"] == m]
            if sm["year"].nunique() < 2:
                lst_vals.append(None)
            else:
                yr_hot = sm.groupby("year")["lst_c"].max() > heat_threshold_c
                lst_vals.append(_r(float(yr_hot.mean())))
        if any(v is not None for v in lst_vals):
            out["lst_heat"] = TaggedSeries(
                x=MONTHS,
                values=lst_vals,
                unit="share of years",
                tag="O",
                source=(
                    f"USGS/NASA Landsat 8-9 C2 L2 ST_B10 (100 m TIRS / 30 m COG), "
                    f"LST > {heat_threshold_c:.0f} degC"
                ),
            )

    if era5_df is not None and not era5_df.empty:
        er = era5_df.copy()
        er["date"] = pd.to_datetime(er["date"])
        er = er[er["rain_mm"].notna()]
        if not er.empty:
            q_thr = float(er["rain_mm"].quantile(rain_quantile))
            er["year"] = er["date"].dt.year
            er["month"] = er["date"].dt.month
            years = sorted(er["year"].unique())
            n_yr = max(len(years), 1)
            er_vals: list[float | None] = []
            ext = er[er["rain_mm"] > q_thr]
            for m in MONTHS:
                n_hit = int(ext[ext["month"] == m]["year"].nunique())
                er_vals.append(_r(n_hit / n_yr))
            out["extreme_rain_era5"] = TaggedSeries(
                x=MONTHS,
                values=er_vals,
                unit="share of years",
                tag="E",
                source=(
                    f"ECMWF ERA5 0.25 deg daily rain > {q_thr:.1f} mm/d "
                    f"(local q{int(round(rain_quantile * 100))}, coarse context)"
                ),
            )
    return out or None


def load_obs_checks_inputs(
    region_id: str,
    cutoff_date: date | None = None,
    data_dir: Path | str = "data",
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Load cached field Landsat LST [O] and ERA5 daily rain [E] tables clipped to `cutoff_date`."""
    base = Path(data_dir)
    lst_path = base / "context" / "landsat_lst" / f"{region_id}_lst.parquet"
    era_path = base / "weather" / "era5" / f"{region_id}_era5_daily.parquet"

    lst_df: pd.DataFrame | None = None
    if lst_path.exists():
        tmp = pd.read_parquet(lst_path)
        if cutoff_date is not None and not tmp.empty:
            tmp = tmp[pd.to_datetime(tmp["date"]).dt.date <= cutoff_date].copy()
        lst_df = tmp

    era_df: pd.DataFrame | None = None
    if era_path.exists():
        tmp = pd.read_parquet(era_path)
        if cutoff_date is not None and not tmp.empty:
            tmp = tmp[pd.to_datetime(tmp["date"]).dt.date <= cutoff_date].copy()
        era_df = tmp

    return lst_df, era_df


def field_calendar(
    fid: str,
    bare_obs: list[dict],
    obs_years: tuple[int, int],
    by_option: dict[str, TaggedSeries],
    vuln: list[CropVulnerability],
    as_of: date,
    obs_checks: dict[str, TaggedSeries] | None = None,
) -> FieldCalendar:
    return FieldCalendar(
        schema_version=SCHEMA_VERSION,
        field_id=fid,
        bare_observed=[BareMonth.model_validate(m) for m in bare_obs],
        bare_observed_years=obs_years,
        bare_by_option=by_option,
        vulnerability=vuln,
        obs_checks=obs_checks,
        data_as_of=as_of,
    )


def worst_month_share(vuln: list[CropVulnerability], hazard: str) -> float | None:
    """Mean over crops of the worst monthly share for `hazard`; None if nothing computable."""
    vals = []
    for v in vuln:
        s = [x for x in v.shares[hazard].values if x is not None]
        if s:
            vals.append(max(s))
    return float(np.mean(vals)) if vals else None


# ---------------------------------------------------------------- regional layers


def _slope_per_year(x: list[int], y: list[float | None]) -> float | None:
    pts = [(a, b) for a, b in zip(x, y, strict=True) if b is not None]
    if len(pts) < 3:
        return None
    return float(np.polyfit([a for a, _ in pts], [b for _, b in pts], 1)[0])


def _layer(
    layer_id: str,
    res_km: float,
    res_src: str,
    years: list[int],
    cells: list[GridCell],
    unit: str,
    source: str,
    mean: list[float | None],
    tag: str = "D",
) -> RegionalLayer:
    slope = _slope_per_year(years, mean)
    return RegionalLayer(
        layer_id=layer_id,  # type: ignore[arg-type]
        resolution_km=res_km,
        resolution_source=res_src,
        scale_flag=True,
        grid=TaggedGrid(years=years, cells=cells, unit=unit, tag=tag, source=source),  # type: ignore[arg-type]
        region_mean=TaggedSeries(
            x=years,
            values=[_r(v, 4) for v in mean],
            unit=unit,
            tag=tag,
            source=source,  # type: ignore[arg-type]
        ),
        trend=Tagged(
            value=_r(slope, 4),
            unit=f"{unit} per year",
            tag="D",
            source="least-squares slope of the annual region mean",
        ),
    )


def grace_layer(nc: str, bbox, cutoff_date: date | None = None) -> RegionalLayer:
    """Annual mean of scaled lwe_thickness (cm) per 0.5 degree land cell inside `bbox`."""
    ds = xr.open_dataset(nc, engine="h5netcdf")
    w, s, e, n = bbox
    lon360 = sorted((w % 360, e % 360))
    sel = ds.sel(lat=slice(s, n), lon=slice(*lon360))
    land = sel["land_mask"] == 1
    lwe = (sel["lwe_thickness"] * sel["scale_factor"]).where(land)
    t = pd.to_datetime(lwe["time"].values)
    keep = np.ones(len(t), bool) if cutoff_date is None else t.date <= cutoff_date
    lwe = lwe.isel(time=np.where(keep)[0])
    t = t[keep]
    last = t.max()
    years = [y for y in range(t.min().year + 1, last.year + (1 if last.month == 12 else 0))]
    dlat = float(abs(np.diff(sel["lat"].values)).mean()) if sel.sizes["lat"] > 1 else 0.5
    dlon = float(abs(np.diff(sel["lon"].values)).mean()) if sel.sizes["lon"] > 1 else 0.5
    cells, wts, per_cell = [], [], []
    for i, la in enumerate(sel["lat"].values):
        for j, lo in enumerate(sel["lon"].values):
            if not bool(land.isel(lat=i, lon=j).values):
                continue
            ser = pd.Series(lwe.isel(lat=i, lon=j).values, index=t)
            ann = ser.groupby(ser.index.year).agg(["mean", "count"])
            vals = [
                _r(ann.loc[y, "mean"], 3) if y in ann.index and ann.loc[y, "count"] >= 6 else None
                for y in years
            ]
            lo180 = float(lo) - 360.0 if lo > 180 else float(lo)
            cells.append(
                GridCell(
                    bbox_lonlat=(lo180 - dlon / 2, la - dlat / 2, lo180 + dlon / 2, la + dlat / 2),
                    values=vals,
                )
            )
            wts.append(math.cos(math.radians(la)))
            per_cell.append(vals)
    mean = []
    for k in range(len(years)):
        v = [(c[k], wt) for c, wt in zip(per_cell, wts, strict=True) if c[k] is not None]
        mean.append(sum(a * b for a, b in v) / sum(b for _, b in v) if v else None)
    km = dlat * 111.0
    return _layer(
        "grace_tws",
        round(km, 1),
        f"GRACE/GRACE-FO mascon CRI grid spacing {dlat:g} deg (file); effective resolution "
        "is coarser than the grid spacing",
        years,
        cells,
        "cm water-equivalent anomaly (vs 2004-2009 mean)",
        "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4, annual mean of monthly values",
        mean,
    )


def smap_layer(smap: pd.DataFrame, lon: float, lat: float) -> RegionalLayer:
    m = smap.copy()
    m["year"] = m["month"].str[:4].astype(int)
    cnt = m.groupby("year")["anomaly"].count()
    years = [int(y) for y in cnt.index if cnt[y] == 12]
    ann = m.groupby("year")["anomaly"].mean()
    vals = [_r(ann[y], 4) for y in years]
    dlat = 4.5 / 110.57
    dlon = 4.5 / (111.32 * math.cos(math.radians(lat)))
    cell = GridCell(bbox_lonlat=(lon - dlon, lat - dlat, lon + dlon, lat + dlat), values=vals)
    return _layer(
        "smap_anomaly",
        9.0,
        "SPL4SMGP v008 9 km (AppEEARS point task); cell box = point +-4.5 km, approximate",
        years,
        [cell],
        "m3/m3 anomaly vs monthly climatology",
        "SPL4SMGP.008 root-zone soil moisture, annual mean of monthly anomalies",
        vals,
    )


def grace_csr_layer(
    nc: str,
    mask_nc: str,
    bbox: tuple[float, float, float, float],
    cutoff_date: date | None = None,
) -> RegionalLayer:
    """Annual mean of UT-CSR GRACE/GRACE-FO RL06.3 lwe_thickness (cm) per 0.25 deg land cell.

    CSR RL06.3M mascons ship with GIA and ellipsoidal corrections already applied (unlike JPL
    TELLUS CRI, there is no separate scale_factor array). Native solution uses 1 deg equal-area
    mascons represented on a 0.25 deg grid (`time` in days since 2002-01-01).
    """
    w, s, e, n = bbox
    lon360 = sorted((w % 360, e % 360))
    with (
        xr.open_dataset(nc, engine="h5netcdf") as ds,
        xr.open_dataset(mask_nc, engine="h5netcdf") as mk,
    ):
        sel = ds.sel(lat=slice(s, n), lon=slice(*lon360))
        msel = mk.sel(lat=slice(s, n), lon=slice(*lon360))
        land = msel["LO_val"] == 1
        lwe = sel["lwe_thickness"].where(land)
        raw_t = lwe["time"].values
        t = (
            pd.to_datetime(raw_t, unit="D", origin="2002-01-01")
            if np.issubdtype(raw_t.dtype, np.number)
            else pd.to_datetime(raw_t)
        )
        keep = np.ones(len(t), bool) if cutoff_date is None else t.date <= cutoff_date
        lwe = lwe.isel(time=np.where(keep)[0])
        t = t[keep]
        last = t.max()
        years = [y for y in range(t.min().year + 1, last.year + (1 if last.month == 12 else 0))]
        lats = sel["lat"].values
        lons = sel["lon"].values
        dlat = float(abs(np.diff(lats)).mean()) if len(lats) > 1 else 0.25
        dlon = float(abs(np.diff(lons)).mean()) if len(lons) > 1 else 0.25
        cells, wts, per_cell = [], [], []
        for i, la in enumerate(lats):
            for j, lo in enumerate(lons):
                if not bool(land.isel(lat=i, lon=j).values):
                    continue
                ser = pd.Series(lwe.isel(lat=i, lon=j).values, index=t)
                ann = ser.groupby(ser.index.year).agg(["mean", "count"])
                vals = [
                    _r(ann.loc[y, "mean"], 3)
                    if y in ann.index and ann.loc[y, "count"] >= 6
                    else None
                    for y in years
                ]
                lo180 = float(lo) - 360.0 if lo > 180 else float(lo)
                cells.append(
                    GridCell(
                        bbox_lonlat=(
                            lo180 - dlon / 2,
                            float(la) - dlat / 2,
                            lo180 + dlon / 2,
                            float(la) + dlat / 2,
                        ),
                        values=vals,
                    )
                )
                wts.append(math.cos(math.radians(float(la))))
                per_cell.append(vals)
    mean = []
    for k in range(len(years)):
        v = [(c[k], wt) for c, wt in zip(per_cell, wts, strict=True) if c[k] is not None]
        mean.append(sum(a * b for a, b in v) / sum(b for _, b in v) if v else None)
    km = dlat * 111.0
    return _layer(
        "grace_tws",
        round(km, 1),
        f"UT-CSR GRACE/GRACE-FO RL06.3 mascons on {dlat:g} deg grid (1 deg equal-area mascons, "
        "Save 2024); effective resolution is coarser than grid spacing",
        years,
        cells,
        "cm water-equivalent anomaly (vs 2004-2009 mean)",
        "CSR_GRACE_GRACE-FO_RL0603_Mascons (all-corrections, DOI 10.15781/cgq9-nh24), "
        "annual mean of monthly values",
        mean,
    )


def merra2_cells(
    bbox: tuple[float, float, float, float],
) -> list[tuple[float, float, tuple[float, float, float, float]]]:
    """Intersecting MERRA-2 0.5 deg lat x 0.625 deg lon cell centres and bounds for `bbox`."""
    w, s, e, n = bbox
    dlat, dlon = 0.5, 0.625
    j0 = math.floor((w + 180.0) / dlon + 0.5)
    j1 = math.ceil((e + 180.0) / dlon - 0.5)
    i0 = math.floor((s + 90.0) / dlat + 0.5)
    i1 = math.ceil((n + 90.0) / dlat - 0.5)
    out: list[tuple[float, float, tuple[float, float, float, float]]] = []
    for i in range(i0, i1 + 1):
        lat_c = round(-90.0 + dlat * i, 4)
        for j in range(j0, j1 + 1):
            lon_c = round(-180.0 + dlon * j, 4)
            cell_box = (lon_c - dlon / 2, lat_c - dlat / 2, lon_c + dlon / 2, lat_c + dlat / 2)
            if cell_box[2] > w and cell_box[0] < e and cell_box[3] > s and cell_box[1] < n:
                out.append((lon_c, lat_c, cell_box))
    return out


def heatwave_layer(
    bbox: tuple[float, float, float, float],
    threshold_c: float = 35.0,
    cutoff_date: date | None = None,
    loader=None,
) -> RegionalLayer:
    """Annual days with NASA POWER T2M_MAX >= `threshold_c` on intersecting MERRA-2 cells."""
    fn = loader or power.cached
    grid = merra2_cells(bbox)
    per_cell_maps: list[dict[int, float]] = []
    wts: list[float] = []
    year_set: set[int] = set()
    for lon_c, lat_c, _ in grid:
        df, _ = fn(lon_c, lat_c)
        if cutoff_date is not None:
            df = df[df.index.date <= cutoff_date]
        ser = df["T2M_MAX"].dropna()
        ann_cnt = ser.groupby(ser.index.year).count()
        ann_hot = (ser >= threshold_c).groupby(ser.index.year).sum()
        cell_yr = {int(y): float(ann_hot[y]) for y, cnt in ann_cnt.items() if int(cnt) >= 330}
        per_cell_maps.append(cell_yr)
        wts.append(math.cos(math.radians(lat_c)))
        year_set.update(cell_yr.keys())
    years = sorted(year_set)
    cells = [
        GridCell(bbox_lonlat=box, values=[cmap.get(y) for y in years])
        for (_, _, box), cmap in zip(grid, per_cell_maps, strict=True)
    ]
    mean: list[float | None] = []
    for y in years:
        v = [(cmap[y], wt) for cmap, wt in zip(per_cell_maps, wts, strict=True) if y in cmap]
        mean.append(sum(a * b for a, b in v) / sum(b for _, b in v) if v else None)
    return _layer(
        "heatwave_days",
        55.5,
        "NASA POWER Daily API (MERRA-2 native 0.5 deg lat x 0.625 deg lon grid, ~55.5 km lat); "
        "regional context only",
        years,
        cells,
        "days/year",
        f"NASA POWER T2M_MAX >= {threshold_c:.1f} degC (summer threshold A, vulnerability.yaml), "
        "annual count",
        mean,
    )


def region_layers(
    region_id: str,
    layers: list[RegionalLayer],
    colouring: dict[str, dict[str, Tagged]],
    as_of: date,
) -> RegionLayers:
    return RegionLayers(
        schema_version=SCHEMA_VERSION,
        region_id=region_id,
        layers=layers,
        field_colouring={k: v for k, v in colouring.items() if v},  # type: ignore[misc]
        data_as_of=as_of,
    )


def regions_list(entries: list[tuple[str, str, int]]) -> RegionList:
    return RegionList(regions=[RegionEntry(region_id=a, name=b, tier=c) for a, b, c in entries])  # type: ignore[arg-type]


# ---------------------------------------------------------------- S7 Rank-1 option deltas

OptionDeltaMetric = Literal[
    "delta_water_use_mm",
    "delta_bad_year_water_mm",
    "delta_bare_months",
    "delta_ryi",
    "delta_erosion_exposure",
]

_DELTA_SPECS: tuple[tuple[OptionDeltaMetric, str, str, int, bool], ...] = (
    ("delta_water_use_mm", "water_use_mm", "mm per rotation", 1, False),
    (
        "delta_bad_year_water_mm",
        "bad_year_water_mm",
        "mm per rotation (CVaR10, upper tail)",
        1,
        False,
    ),
    ("delta_bare_months", "cover_days", "months", 1, False),
    ("delta_ryi", "ryi", "0-1", 3, True),
    (
        "delta_erosion_exposure",
        "erosion_exposure",
        "relative, within-field comparison only",
        3,
        False,
    ),
)


class FieldOptionDelta(BaseModel):
    field_id: str
    current_sequence: list[str]
    current_grade: Literal["A", "B", "C", "D"]
    alt_option_id: str
    alt_sequence: list[str]
    alt_grade: Literal["A", "B", "C", "D"]
    deltas: dict[OptionDeltaMetric, Tagged]


class OptionDeltaSummary(BaseModel):
    mean: Tagged
    improved_count: int
    valid_count: int


class RegionOptionDeltas(BaseModel):
    schema_version: str
    region_id: str
    data_as_of: date
    n_fields: int
    fields: dict[str, FieldOptionDelta]
    summary: dict[OptionDeltaMetric, OptionDeltaSummary]


def _bare_months_from_cover(cover_days: float) -> float:
    bare_days = max(0.0, 1095.0 - float(cover_days))
    return round(bare_days / 30.4375, 1)


def build_option_deltas_for_region(region_dir: Path) -> RegionOptionDeltas:
    """Compute Rank-1 Alternative minus Current deltas for every field in a region pack dir."""
    idx = RegionIndex.model_validate_json((region_dir / "index.json").read_bytes())
    fields_out: dict[str, FieldOptionDelta] = {}
    collected: dict[OptionDeltaMetric, list[float]] = {k: [] for k, *_ in _DELTA_SPECS}

    for summary in idx.fields:
        fid = summary.field_id
        pack = FieldPack.model_validate_json((region_dir / f"{fid}.json").read_bytes())
        cur = next((o for o in pack.options if o.option_id == "current"), None)
        alts = [o for o in pack.options if o.option_id != "current"]
        if cur is None or not alts:
            continue
        alt = min(alts, key=lambda o: (o.rank if o.rank > 0 else 9999, o.option_id))

        deltas: dict[OptionDeltaMetric, Tagged] = {}
        for delta_key, src_metric, unit, digits, _higher_better in _DELTA_SPECS:
            cm = cur.metrics.get(src_metric)
            am = alt.metrics.get(src_metric)
            cv = cm.value if cm is not None else None
            av = am.value if am is not None else None
            if cv is None or av is None:
                val: float | None = None
            elif delta_key == "delta_bare_months":
                val = _r(_bare_months_from_cover(av) - _bare_months_from_cover(cv), digits)
            else:
                val = _r(float(av) - float(cv), digits)

            if val is not None:
                collected[delta_key].append(val)

            tag = am.tag if am is not None else "D"
            src = f"Rank-1 {alt.option_id} vs Current ({src_metric})"
            deltas[delta_key] = Tagged(value=val, unit=unit, tag=tag, source=src)

        fields_out[fid] = FieldOptionDelta(
            field_id=fid,
            current_sequence=list(cur.sequence),
            current_grade=cur.grade,
            alt_option_id=alt.option_id,
            alt_sequence=list(alt.sequence),
            alt_grade=alt.grade,
            deltas=deltas,
        )

    summary_out: dict[OptionDeltaMetric, OptionDeltaSummary] = {}
    for delta_key, src_metric, unit, digits, higher_better in _DELTA_SPECS:
        vals = collected[delta_key]
        mean_val = _r(float(np.mean(vals)), digits) if vals else None
        improved = sum(1 for v in vals if (v > 0 if higher_better else v < 0))
        summary_out[delta_key] = OptionDeltaSummary(
            mean=Tagged(
                value=mean_val,
                unit=unit,
                tag="D",
                source=(
                    f"Mean Rank-1 minus Current across {len(vals)} comparable fields ({src_metric})"
                ),
            ),
            improved_count=improved,
            valid_count=len(vals),
        )

    return RegionOptionDeltas(
        schema_version=SCHEMA_VERSION,
        region_id=idx.region_id,
        data_as_of=idx.data_as_of,
        n_fields=len(idx.fields),
        fields=fields_out,
        summary=summary_out,
    )
