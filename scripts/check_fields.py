"""T0.4 access check: read only a bbox from remote field-boundary GeoParquet files.

Usage:  uv run python -u scripts/check_fields.py

For each source: read the footer, find row groups whose `bbox` statistics intersect the query box,
estimate the bytes a bbox read would fetch, and only if the estimate is <= CAP_MB run
`geopandas.read_parquet(..., bbox=...)` and count polygons that truly intersect the box.

Filesystem: anonymous S3 on Source Cooperative (endpoint data.source.coop) first; HTTPS via fsspec
if S3 fails. APIs verified from installed geopandas 1.2.0 / pyarrow 26.0.1 source
(docs/api_notes.md).
"""

import json

import fsspec
import geopandas as gpd
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from pyproj import CRS, Transformer
from shapely.geometry import box

CAP_MB = 200.0
HTTPS = "https://data.source.coop/"

# Query boxes in lon/lat (EPSG:4326).
# T14SLH footprint from CMR granule HLS-VI.S30.T14SLH.2023185T172901.v2.0 (docs/api_notes.md).
T14SLH = (-101.304, 37.837, -100.025, 38.845)
# ~20 km x 20 km test box in the Beauce (access check only; the French region is chosen in T0.5).
BEAUCE = (1.465, 48.16, 1.735, 48.34)
# ~10 km x 10 km test box in rural central Punjab near Jagraon (Tier 3 candidate; access test).
PUNJAB = (75.418, 30.745, 75.522, 30.835)

# NASS CSB 2024 metadata: Albers Conical Equal Area (NLCD), NAD83/GRS80, standard parallels
# 29.5 and 45.5, central meridian -96, latitude of origin 23, false E/N 0, metres.
# Used only if the file's GeoParquet metadata carries no CRS (the mirror README says "None").
CSB_ALBERS = (
    "+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0 +datum=NAD83 +units=m"
)

# FTW Kansas (US_KS.parquet) is not queried: the T14SLH box would read 204 MB (> cap) and CSB is the
# Tier 1 boundary source (DECISIONS.md). Punjab's file (992 MB, 159 row groups) was chosen over
# Ukraine.parquet (1,985 MB, 63 row groups) as the smaller Tier 3 candidate file.
FTW_PB = (
    "ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/"
    "admin:country_code=IN/IN_PB.parquet"
)
CSB = "ftw/harmonized-field-data/us_usda_cropland/year={y}/us_usda_cropland-{y}.parquet"
FR = "ftw/harmonized-field-data/fr/year={y}/fr-{y}.parquet"

QUERIES = [  # (label, key, lon/lat box, fallback CRS)
    ("FTW global, Punjab (Tier 3 candidate)", FTW_PB, PUNJAB, None),
    ("USDA CSB 2024", CSB.format(y=2024), T14SLH, CSB_ALBERS),
    ("France RPG 2024", FR.format(y=2024), BEAUCE, None),
]


def open_filesystem():
    """Return (name, filesystem, path_for_key). Tries anonymous S3, then HTTPS."""
    try:
        s3 = pafs.S3FileSystem(
            anonymous=True, endpoint_override="data.source.coop", scheme="https", region="us-east-1"
        )
        info = s3.get_file_info(CSB.format(y=2024))
        if info.type == pafs.FileType.File:
            return "pyarrow S3 (anonymous, data.source.coop)", s3, lambda k: k
        print("S3 probe: file not found via S3:", info)
    except Exception as e:  # noqa: BLE001 - report and fall back
        print(f"S3 probe failed: {type(e).__name__}: {str(e)[:200]}")
    return "fsspec HTTPS", fsspec.filesystem("https"), lambda k: HTTPS + k


def footer(fs, path):
    pf = pq.ParquetFile(path, filesystem=fs) if isinstance(fs, pafs.FileSystem) else None
    if pf is None:
        pf = pq.ParquetFile(fs.open(path, "rb"))
    return pf


def file_crs(md, fallback):
    geo = json.loads(md.metadata[b"geo"])
    col = geo["columns"][geo["primary_column"]]
    crs = col.get("crs", "absent")
    if crs is None or crs == "absent":
        # GeoParquet: a missing "crs" key means OGC:CRS84; an explicit null means unknown.
        if crs is None and fallback is None:
            raise SystemExit("file CRS is null and no fallback CRS given")
        return (CRS.from_user_input(fallback) if crs is None else CRS("OGC:CRS84")), geo, crs
    return CRS.from_json_dict(crs), geo, "projjson"


def estimate(md, qbox):
    """Row groups whose bbox statistics intersect qbox, and their compressed bytes."""
    names = [md.schema.column(i).path for i in range(md.num_columns)]
    idx = {k: names.index(f"bbox.{k}") for k in ("xmin", "ymin", "xmax", "ymax")}
    hit, nbytes = [], 0
    for r in range(md.num_row_groups):
        rg = md.row_group(r)
        st = {k: rg.column(i).statistics for k, i in idx.items()}
        if any(s is None or not s.has_min_max for s in st.values()):
            hit.append(r)  # no stats: must assume it is read
        elif (
            st["xmin"].min <= qbox[2]
            and st["xmax"].max >= qbox[0]
            and st["ymin"].min <= qbox[3]
            and st["ymax"].max >= qbox[1]
        ):
            hit.append(r)
        else:
            continue
        nbytes += sum(rg.column(c).total_compressed_size for c in range(rg.num_columns))
    return hit, nbytes + md.serialized_size


def main() -> None:
    fs_name, fs, path_for = open_filesystem()
    print("filesystem:", fs_name)

    for label, key, lonlat, fallback in QUERIES:
        path = path_for(key)
        md = footer(fs, path).metadata
        crs, geo, crs_src = file_crs(md, fallback)
        to_file = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        qbox = to_file.transform_bounds(*lonlat)
        total = sum(
            md.row_group(r).column(c).total_compressed_size
            for r in range(md.num_row_groups)
            for c in range(md.num_columns)
        )
        hit, est = estimate(md, qbox)
        print(f"\n== {label}\n   {HTTPS}{key}")
        print(
            f"   geoparquet {geo.get('version')} | crs from {crs_src}: {crs.name} | "
            f"covering: {geo['columns'][geo['primary_column']].get('covering')}"
        )
        print(
            f"   rows {md.num_rows:,} | row groups {md.num_row_groups} | file {total / 1e6:.0f} MB"
        )
        print(f"   query box (file CRS): {tuple(round(v, 1) for v in qbox)}")
        print(
            f"   row groups hit {len(hit)} | estimated read {est / 1e6:.1f} MB (cap {CAP_MB:.0f})"
        )
        if est / 1e6 > CAP_MB:
            print("   OVER CAP: query not run")
            continue
        gdf = gpd.read_parquet(path, bbox=qbox, filesystem=fs)
        n_bbox = len(gdf)
        n_exact = int(gdf.intersects(box(*qbox)).sum())
        print(f"   read {n_bbox:,} rows via bbox filter; {n_exact:,} polygons intersect the box")
        print(f"   columns: {list(gdf.columns)}")

    print("\n== France: harmonised crop columns per year (footers only)")
    for y in range(2015, 2025):
        md = footer(fs, path_for(FR.format(y=y))).metadata
        names = [md.schema.column(i).path for i in range(md.num_columns)]
        crop_cols = [n for n in names if n.startswith(("hcat:", "crop:"))]
        nulls = {}
        for n in crop_cols:
            i = names.index(n)
            stats = [md.row_group(r).column(i).statistics for r in range(md.num_row_groups)]
            nulls[n] = (
                sum(s.null_count for s in stats) if all(s is not None for s in stats) else "n/a"
            )
        print(f"   {y}: rows {md.num_rows:,} | null counts {nulls}")


if __name__ == "__main__":
    main()
