"""Bbox reads of remote GeoParquet 1.1 files on Source Cooperative, with a download cap.

APIs verified from installed geopandas 1.2.0 / pyarrow 26.0.1 source (docs/api_notes.md).
Footer statistics of the `bbox` covering column give a byte estimate before any data read; a read
whose estimate exceeds the cap raises `OverCap` and nothing is fetched.
"""

import json
from dataclasses import dataclass

import fsspec
import geopandas as gpd
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from pyproj import CRS, Transformer

HTTPS = "https://data.source.coop/"
DEFAULT_CAP_MB = 200.0


class OverCap(RuntimeError):
    """The estimated download for a bbox read exceeds the cap. `info` holds the estimate."""

    def __init__(self, message: str, info: dict):
        super().__init__(message)
        self.info = info


@dataclass(frozen=True)
class Source:
    fs: object
    name: str

    def path(self, key: str) -> str:
        return key if isinstance(self.fs, pafs.FileSystem) else HTTPS + key


def open_source() -> Source:
    """Anonymous S3 on data.source.coop first; HTTPS via fsspec if S3 fails."""
    probe = "ftw/harmonized-field-data/fr/latest/fr.parquet"
    try:
        s3 = pafs.S3FileSystem(
            anonymous=True, endpoint_override="data.source.coop", scheme="https", region="us-east-1"
        )
        if s3.get_file_info(probe).type == pafs.FileType.File:
            return Source(s3, "pyarrow S3 (anonymous, data.source.coop)")
    except Exception:  # noqa: BLE001 - fall back to HTTPS
        pass
    return Source(fsspec.filesystem("https"), "fsspec HTTPS")


def footer(src: Source, key: str) -> pq.FileMetaData:
    """Read only the Parquet footer."""
    path = src.path(key)
    if isinstance(src.fs, pafs.FileSystem):
        return pq.ParquetFile(path, filesystem=src.fs).metadata
    return pq.ParquetFile(src.fs.open(path, "rb")).metadata


def file_crs(md: pq.FileMetaData) -> CRS:
    """CRS of the primary geometry column. GeoParquet: a missing `crs` key means OGC:CRS84."""
    geo = json.loads(md.metadata[b"geo"])
    col = geo["columns"][geo["primary_column"]]
    if "crs" not in col:
        return CRS("OGC:CRS84")
    if col["crs"] is None:
        raise ValueError("GeoParquet CRS is explicitly null (unknown)")
    return CRS.from_json_dict(col["crs"])


def estimate_bbox_read(
    md: pq.FileMetaData, box: tuple[float, float, float, float], columns: list[str] | None = None
):
    """Row groups whose `bbox` statistics intersect `box` (file CRS) and their compressed bytes.

    `columns`: top-level columns that will be read (the `bbox` column is always counted, since the
    filter reads it); None = all columns.
    """
    names = [md.schema.column(i).path for i in range(md.num_columns)]
    keep = None if columns is None else {*columns, "bbox"}
    read_idx = [i for i, n in enumerate(names) if keep is None or n.split(".")[0] in keep]
    idx = {k: names.index(f"bbox.{k}") for k in ("xmin", "ymin", "xmax", "ymax")}
    hit, nbytes = [], md.serialized_size
    for r in range(md.num_row_groups):
        rg = md.row_group(r)
        st = {k: rg.column(i).statistics for k, i in idx.items()}
        stats_ok = all(s is not None and s.has_min_max for s in st.values())
        if stats_ok and not (
            st["xmin"].min <= box[2]
            and st["xmax"].max >= box[0]
            and st["ymin"].min <= box[3]
            and st["ymax"].max >= box[1]
        ):
            continue
        hit.append(r)
        nbytes += sum(rg.column(c).total_compressed_size for c in read_idx)
    return hit, nbytes


def read_bbox(
    src: Source,
    key: str,
    lonlat_box: tuple[float, float, float, float],
    cap_mb: float = DEFAULT_CAP_MB,
    columns: list[str] | None = None,
) -> tuple[gpd.GeoDataFrame, dict]:
    """Read rows whose bbox intersects `lonlat_box` (EPSG:4326). Raises OverCap above the cap.

    `columns`: subset of top-level columns to read (must include the geometry column)."""
    md = footer(src, key)
    crs = file_crs(md)
    box = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform_bounds(*lonlat_box)
    hit, nbytes = estimate_bbox_read(md, box, columns)
    info = {
        "key": key,
        "rows": md.num_rows,
        "row_groups": md.num_row_groups,
        "row_groups_hit": len(hit),
        "estimated_mb": round(nbytes / 1e6, 1),
        "cap_mb": cap_mb,
        "crs": crs.name,
        "columns": columns or "all",
        "file_box": box,
    }
    if nbytes / 1e6 > cap_mb:
        raise OverCap(f"{key}: estimated {nbytes / 1e6:.1f} MB > cap {cap_mb:.0f} MB", info)
    gdf = gpd.read_parquet(src.path(key), bbox=box, filesystem=src.fs, columns=columns)
    return gdf, info
