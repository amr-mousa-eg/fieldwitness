"""Context datasets (PLAN.md T1.8): NASADEM slope per field, GRACE/GRACE-FO regional water
storage, SMAP L4 root-zone soil moisture. Collection ids verified in CMR on 2026-11-04
(docs/api_notes.md):
- NASADEM_HGT v001 (C2763264762-LPCLOUD), 1 arc-second; slope is derived on the HLS 30 m tile grid.
- TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 (C3195527175-POCLOUD): `lwe_thickness` (cm) on a
  0.5 degree grid, anomalies with the 2004.000-2009.999 mean removed (file attribute); the file
  says its `scale_factor` is "to be used with mascon solution that has the CRI filter applied",
  so values are multiplied by it. Native resolution is far coarser than a field: context only.
- SPL4SMGP v008 (C3480440870-NSIDC_CPRD) via AppEEARS point task, layer Geophysical_Data_sm_rootzone
  (m3/m3, fill -9999), 9 km: context only.
"""

import datetime as dt
import glob
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.warp import Resampling, reproject

from fieldwitness.data.asof import cutoff, guard, register
from fieldwitness.data.hls_series import interior_points

OUT = Path("data/context")
SMAP_LAYER = {"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone"}


# ---------------------------------------------------------------- (a) slope from NASADEM


def tile_dem(grid: dict, zips: list[str]) -> np.ndarray:
    """NASADEM heights (m) reprojected (bilinear) onto the HLS 30 m grid of the tile."""
    n = int(round(grid["size_m"] / 30.0))
    dst = np.full((n, n), np.nan, dtype="float32")
    transform = rasterio.transform.from_origin(grid["ulx"], grid["uly"], 30.0, 30.0)
    for z in zips:
        hgt = next(f for f in zipfile.ZipFile(z).namelist() if f.endswith(".hgt"))
        with rasterio.open(f"zip://{Path(z).resolve().as_posix()}!{hgt}") as src:
            tmp = np.full((n, n), np.nan, dtype="float32")
            reproject(
                rasterio.band(src, 1),
                tmp,
                dst_transform=transform,
                dst_crs=grid["epsg"],
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            dst = np.where(np.isnan(dst), tmp, dst)
    return dst


def slope_degrees(dem: np.ndarray, spacing_m: float = 30.0) -> np.ndarray:
    """Slope (degrees) from central differences: atan(sqrt((dz/dx)^2 + (dz/dy)^2))."""
    dzdy, dzdx = np.gradient(dem.astype("float64"), spacing_m)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def field_slopes(pilot: gpd.GeoDataFrame, grid: dict, slope: np.ndarray) -> pd.DataFrame:
    """Mean slope over every interior pixel (15 m rule) of each field."""
    pts = interior_points(pilot, grid, max_per_field=None)
    rows = []
    df = pd.DataFrame(
        [
            (p["category"], int(p["id"].rsplit("_", 2)[1]), int(p["id"].rsplit("_", 2)[2]))
            for p in pts
        ],
        columns=["field_id", "col", "row"],
    )
    ok = df["row"].between(0, slope.shape[0] - 1) & df["col"].between(0, slope.shape[1] - 1)
    df = df[ok].copy()  # fields crossing the tile edge: only pixels inside the tile
    df["slope"] = slope[df["row"], df["col"]]
    for fid, g in df.groupby("field_id"):
        rows.append(
            {
                "field_id": fid,
                "slope_deg_mean": round(float(np.nanmean(g["slope"])), 3),
                "n_pixels": int(g["slope"].notna().sum()),
                "tag": "D",
                "source": "NASADEM_HGT v001 (C2763264762-LPCLOUD), slope on the HLS 30 m grid",
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- (b) GRACE / GRACE-FO


def grace_region_series(nc: str, bbox) -> pd.DataFrame:
    """Monthly regional mean of scaled lwe_thickness (cm) over land cells whose centres fall in
    `bbox` (lon/lat), weighted by cos(latitude)."""
    ds = xr.open_dataset(nc, engine="h5netcdf")
    w, s, e, n = bbox
    lon360 = (w % 360, e % 360)
    sel = ds.sel(lat=slice(s, n), lon=slice(min(lon360), max(lon360)))
    if sel.sizes["lat"] == 0 or sel.sizes["lon"] == 0:  # bbox smaller than one cell: nearest cell
        sel = ds.sel(lat=[(s + n) / 2], lon=[((w + e) / 2) % 360], method="nearest")
    land = sel["land_mask"] == 1
    lwe = (sel["lwe_thickness"] * sel["scale_factor"]).where(land)
    wts = np.cos(np.deg2rad(sel["lat"])) * land
    series = (lwe * wts).sum(("lat", "lon")) / wts.sum()
    df = series.to_dataframe(name="lwe_cm").reset_index()[["time", "lwe_cm"]]
    df["n_cells"] = int(land.sum())
    return df


def trend_cm_per_year(df: pd.DataFrame) -> float:
    t = (pd.to_datetime(df["time"]) - pd.Timestamp("2002-01-01")).dt.days / 365.25
    return float(np.polyfit(t, df["lwe_cm"], 1)[0])


@register("grace")
def read_grace(region_id: str = "ks_t14slh", table: pd.DataFrame | None = None) -> pd.DataFrame:
    t = table if table is not None else pd.read_parquet(OUT / f"{region_id}_grace.parquet")
    c = cutoff()
    if c is not None:
        t = t[pd.to_datetime(t["time"]).dt.date <= c]
    guard((d.date() for d in pd.to_datetime(t["time"])), "grace")
    return t


# ---------------------------------------------------------------- (c) SMAP L4 via AppEEARS


def smap_task_body(points: dict[str, tuple[float, float]], start: str, end: str) -> dict:
    coords = [
        {"id": rid, "category": rid, "latitude": round(lat, 6), "longitude": round(lon, 6)}
        for rid, (lon, lat) in points.items()
    ]
    return {
        "task_type": "point",
        "task_name": "fieldwitness-T1.8-smap-rootzone",
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": [SMAP_LAYER],
            "coordinates": coords,
        },
    }


def smap_monthly_anomaly(series: pd.DataFrame, base_end: dt.date) -> pd.DataFrame:
    """Monthly mean root-zone moisture and anomaly vs the monthly climatology of months up to
    `base_end` (so a hindcast climatology never uses post-cut-off months)."""
    s = series.copy()
    s["month"] = pd.to_datetime(s["date"]).dt.to_period("M")
    m = s.groupby("month")["sm_rootzone"].mean().to_frame()
    m["moy"] = m.index.month
    base = m[m.index.to_timestamp() <= pd.Timestamp(base_end)]
    clim = base.groupby("moy")["sm_rootzone"].mean()
    m["anomaly"] = m["sm_rootzone"] - m["moy"].map(clim)
    return m.reset_index()


def smap_build(csv_path: str | Path, base_end: dt.date) -> pd.DataFrame:
    """AppEEARS SPL4SMGP results CSV (3-hourly, one 9 km cell per region) -> monthly mean and
    anomaly per region (tag D, context only, scale flag: 9 km >> field). Column names as
    returned by AppEEARS 2026-11-04 (see docs/api_notes.md)."""
    raw = pd.read_csv(csv_path)
    col = "SPL4SMGP_008_Geophysical_Data_sm_rootzone"
    raw["date"] = pd.to_datetime(raw["Date"].str.replace(" UTC", "", regex=False)).dt.date
    parts = []
    for rid, g in raw.groupby("ID"):
        m = smap_monthly_anomaly(g.rename(columns={col: "sm_rootzone"}), base_end)
        m.insert(0, "region_id", rid)
        parts.append(m)
    out = pd.concat(parts, ignore_index=True)
    out["month"] = out["month"].astype(str)
    return out


def nasadem_zips() -> list[str]:
    return sorted(glob.glob(str(OUT / "nasadem" / "*.zip")))


def grace_file() -> str:
    return glob.glob(str(OUT / "grace" / "*.nc"))[0]
