"""T8.1 part 2: calendar, regional layers and region list (pure builders + small readers).

- `field_calendar`: observed bare months (T2.5, tag O), simulated bare share per month per option
  (tag D, `rotate.exposure.option_canopy`), crop vulnerability (T3.6, tag D).
- `region_layers`: GRACE and SMAP grids + region means + trend, and Current-option field colouring.
- `regions_list`: `packs/regions.json`.

Team choices (A, UNVERIFIED): `water_stress` uses a rainfed run with the median ABC world (TAW,
Kc scale) of the field; frost / water-stress colouring = mean over modelled Current crops of the
worst monthly share. The heat-wave layer is NOT built: the POWER grid size is not stated in the
POWER docs we read (see `data/power.py`), so no honest grid can be drawn. The SMAP cell box is
the point +-4.5 km (approximate; the AppEEARS point task returns one 9 km cell, no cell edges).
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import xarray as xr
import yaml

from fieldwitness.physics import waterbal
from fieldwitness.physics.kc import kc_curve
from fieldwitness.physics.vulnerability import HAZARDS, CropWindow, hazard_shares
from fieldwitness.rotate.exposure import COVER_FRAC, option_canopy
from fieldwitness.rotate.slots import SOW_DAY, _crops, _kc_ini
from fieldwitness.schemas import (
    BareMonth,
    CropVulnerability,
    FieldCalendar,
    GridCell,
    RegionalLayer,
    RegionEntry,
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
VULN_CROPS = tuple(SOW_DAY)  # crops with a sowing day: maize, sorghum, winter_wheat
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
    for crop in dict.fromkeys(c for c in crops if c in VULN_CROPS):
        w, p = _window(crop, region_id)
        heat = float(cfg["heat_tmax_c"][crop]["value"])
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


def field_calendar(
    fid: str,
    bare_obs: list[dict],
    obs_years: tuple[int, int],
    by_option: dict[str, TaggedSeries],
    vuln: list[CropVulnerability],
    as_of: date,
) -> FieldCalendar:
    return FieldCalendar(
        schema_version=SCHEMA_VERSION,
        field_id=fid,
        bare_observed=[BareMonth.model_validate(m) for m in bare_obs],
        bare_observed_years=obs_years,
        bare_by_option=by_option,
        vulnerability=vuln,
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
