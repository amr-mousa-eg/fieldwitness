"""T0.4 access check: read only a bbox from remote field-boundary GeoParquet files.

Usage:  uv run python -u scripts/check_fields.py

Uses fieldwitness.data.geoparquet: footer-based byte estimate first, read only if <= 200 MB.
"""

from shapely.geometry import box

from fieldwitness.data.geoparquet import OverCap, footer, open_source, read_bbox

# Query boxes in lon/lat (EPSG:4326).
# T14SLH footprint from CMR granule HLS-VI.S30.T14SLH.2023185T172901.v2.0 (docs/api_notes.md).
T14SLH = (-101.304, 37.837, -100.025, 38.845)
# ~20 km x 20 km test box in the Beauce (access check only; the French region is chosen in T0.5).
BEAUCE = (1.465, 48.16, 1.735, 48.34)
# ~10 km x 10 km test box in rural central Punjab near Jagraon (Tier 3 candidate; access test).
PUNJAB = (75.418, 30.745, 75.522, 30.835)

# FTW Kansas (US_KS.parquet) is not queried: the T14SLH box would read 204 MB (> cap) and CSB is the
# Tier 1 boundary source (DECISIONS.md). Punjab's file (992 MB, 159 row groups) was chosen over
# Ukraine.parquet (1,985 MB, 63 row groups) as the smaller Tier 3 candidate file.
FTW_PB = (
    "ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/"
    "admin:country_code=IN/IN_PB.parquet"
)
CSB = "ftw/harmonized-field-data/us_usda_cropland/year={y}/us_usda_cropland-{y}.parquet"
FR = "ftw/harmonized-field-data/fr/year={y}/fr-{y}.parquet"

QUERIES = [  # (label, key, lon/lat box)
    ("FTW global, Punjab (Tier 3 candidate)", FTW_PB, PUNJAB),
    ("USDA CSB 2024", CSB.format(y=2024), T14SLH),
    ("France RPG 2024", FR.format(y=2024), BEAUCE),
]


def main() -> None:
    src = open_source()
    print("filesystem:", src.name)
    for label, key, lonlat in QUERIES:
        print(f"\n== {label}\n   https://data.source.coop/{key}")
        try:
            gdf, info = read_bbox(src, key, lonlat)
        except OverCap as e:
            print("   OVER CAP: query not run —", e)
            continue
        n_exact = int(gdf.intersects(box(*info["file_box"])).sum())
        print(f"   {info}")
        print(f"   read {len(gdf):,} rows via bbox filter; {n_exact:,} polygons intersect the box")

    print("\n== France: harmonised crop columns per year (footers only)")
    for y in range(2015, 2025):
        md = footer(src, FR.format(y=y))
        names = [md.schema.column(i).path for i in range(md.num_columns)]
        nulls = {}
        for n in (n for n in names if n.startswith(("hcat:", "crop:"))):
            i = names.index(n)
            st = [md.row_group(r).column(i).statistics for r in range(md.num_row_groups)]
            nulls[n] = sum(s.null_count for s in st) if all(s is not None for s in st) else "n/a"
        print(f"   {y}: rows {md.num_rows:,} | null counts {nulls}")


if __name__ == "__main__":
    main()
