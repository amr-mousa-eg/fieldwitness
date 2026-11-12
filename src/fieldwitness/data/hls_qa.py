"""T1.5 (finish): parse the downloaded AppEEARS HLS point-task CSVs, apply the QA rule, and expose
the field series through an `as_of`-guarded reader. Source tag O (HLS-VI, satellite observation).

QA rule (docs/api_notes.md, "Fmask"): a sampled pixel on a date is used only if
  - a VI granule and an Fmask record exist for that pixel and date (joined by date; an Fmask date
    without a VI granule is not evidence of a clear gap),
  - none of the decoded Fmask flags Cloud, Adjacent to cloud/shadow, Cloud shadow, Snow/ice, Water
    is set, and the Fmask value is not the fill value 255,
  - NDVI and EVI are not the fill value -19999. (The AppEEARS CSV values are already scaled by
    0.0001 and are in -1..1.)
Field value per date = median over its clear sampled pixels; clear_fraction = clear pixels / sampled
pixels of the field (a field is sampled at up to 12 seeded interior pixel centres).
"""

import json
from pathlib import Path

import pandas as pd

from fieldwitness.data.asof import guard, limit_end, register
from fieldwitness.data.hls_series import OUT

VI_FILL = -19999.0
FMASK_FILL = 255
BAD_FMASK = ("Cloud", "Adjacent_to_cloud/shadow", "Cloud_shadow", "Snow/ice", "Water")


def series_path(region_id: str) -> Path:
    return Path("data/fields") / f"{region_id}_hls_series.parquet"


def read_task(folder: Path) -> pd.DataFrame:
    """Pixel rows for one task folder: Category (field), ID, Date, NDVI, EVI, clear."""
    frames = []
    for sensor in ("HLSL30", "HLSS30"):
        vi_f = next(folder.glob(f"*-{sensor}-VI-020-results.csv"), None)
        fm_f = next(folder.glob(f"*-{sensor}-020-results.csv"), None)
        if vi_f is None or fm_f is None:
            continue
        vi = pd.read_csv(
            vi_f,
            usecols=["Category", "ID", "Date", f"{sensor}_VI_020_NDVI", f"{sensor}_VI_020_EVI"],
        ).rename(columns={f"{sensor}_VI_020_NDVI": "NDVI", f"{sensor}_VI_020_EVI": "EVI"})
        flags = [f"{sensor}_020_Fmask_{b}" for b in BAD_FMASK]
        fm = pd.read_csv(fm_f, usecols=["ID", "Date", f"{sensor}_020_Fmask", *flags])
        flagged = fm[flags].astype(str).apply(lambda c: c.str.strip() == "0b1").any(axis=1)
        fm["clear"] = ~flagged & (fm[f"{sensor}_020_Fmask"] != FMASK_FILL)
        frames.append(vi.merge(fm[["ID", "Date", "clear"]], on=["ID", "Date"], how="inner"))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_series(region_id: str, root: Path | None = None) -> pd.DataFrame:
    """Per field and date: median NDVI/EVI over clear pixels, n_clear, clear_fraction, tag O.

    `root` defaults to the T1.5 download folder; Experiment 3 passes the extra-year folder.
    """
    root = root or OUT / region_id
    pts = pd.DataFrame(json.loads((OUT / f"{region_id}_points.json").read_text(encoding="utf-8")))
    n_sampled = pts.groupby("category").size()
    px = pd.concat([read_task(p) for p in sorted(root.iterdir()) if p.is_dir()], ignore_index=True)
    ok = px["clear"] & (px["NDVI"] != VI_FILL) & (px["EVI"] != VI_FILL)
    px = px[ok].assign(Date=lambda d: pd.to_datetime(d["Date"]))
    # L30 and S30 (or two granules) can both see a pixel on one date: one value per pixel and date
    px = px.groupby(["Category", "ID", "Date"], as_index=False)[["NDVI", "EVI"]].mean()
    out = (
        px.groupby(["Category", "Date"])
        .agg(ndvi=("NDVI", "median"), evi=("EVI", "median"), n_clear=("ID", "size"))
        .reset_index()
        .rename(columns={"Category": "field_id", "Date": "date"})
    )
    out["clear_fraction"] = out["n_clear"] / out["field_id"].map(n_sampled)
    out["source_tag"] = "O"
    return out.sort_values(["field_id", "date"]).reset_index(drop=True)


@register("hls_series")
def read(region_id: str, start=None, end=None, table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Field HLS series clipped to the active `as_of` cut-off and guarded."""
    df = table if table is not None else pd.read_parquet(series_path(region_id))
    out = df
    hi = (
        limit_end(pd.Timestamp(end).date())
        if end is not None
        else limit_end(df["date"].max().date())
    )
    out = out[out["date"] <= pd.Timestamp(hi)]
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    guard((d.date() for d in out["date"]), "HLS series")
    return out
