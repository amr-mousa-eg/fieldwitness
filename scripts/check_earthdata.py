"""T0.2 access check: Earthdata login + HLS-VI granule search for one small Kansas area.

Usage:
    uv run python scripts/check_earthdata.py                      # list granules in the window
    uv run python scripts/check_earthdata.py --granule-name "<pattern>"   # one tile, one date

Credentials: earthaccess reads %USERPROFILE%\\_netrc on Windows. This script never prints them.
Collection names/versions verified in CMR on 2026-11-04 (docs/api_notes.md).
"""

import argparse

import earthaccess

COLLECTIONS = [("HLSL30_VI", "2.0"), ("HLSS30_VI", "2.0")]
# Surface-reflectance parents (fallback source of VIs, and where Fmask lives). Verified in CMR.
SR_COLLECTIONS = [("HLSL30", "2.0"), ("HLSS30", "2.0")]


def archive_depth(tile: str, years: range) -> None:
    """Print granule counts per year for one MGRS tile (CMR hit counts only, no downloads)."""
    cols = COLLECTIONS + SR_COLLECTIONS
    print(f"\n== archive depth, tile {tile} (granule counts per year)")
    print("year  " + "  ".join(f"{sn:>10}" for sn, _ in cols))
    for y in years:
        counts = [
            earthaccess.DataGranules(earthaccess.__auth__)
            .parameters(
                short_name=sn,
                version=v,
                granule_name=f"*.{tile}.*",
                temporal=(f"{y}-01-01", f"{y}-12-31T23:59:59"),
            )
            .hits()
            for sn, v in cols
        ]
        print(f"{y}  " + "  ".join(f"{c:>10}" for c in counts))


# Small search box in SW Kansas near Garden City (lon/lat). An access-test area only.
BBOX = (-100.95, 37.95, -100.85, 38.05)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2023-07-01")
    p.add_argument("--end", default="2023-07-10")
    p.add_argument("--granule-name", default=None, help="CMR granule-name wildcard pattern")
    p.add_argument("--shape", action="store_true", help="print the structure of the first granule")
    p.add_argument("--archive-depth", metavar="TILE", help="count granules per year 2016-2024")
    a = p.parse_args()

    auth = earthaccess.login(strategy="netrc")
    print("authenticated:", bool(auth and auth.authenticated))

    if a.archive_depth:
        archive_depth(a.archive_depth, range(2016, 2025))
        return

    for short_name, version in COLLECTIONS:
        kw = dict(
            short_name=short_name, version=version, bounding_box=BBOX, temporal=(a.start, a.end)
        )
        if a.granule_name:
            kw["granule_name"] = a.granule_name
        granules = earthaccess.search_data(**kw)
        print(f"\n== {short_name} v{version}: {len(granules)} granules")
        for g in granules:
            umm = g["umm"]
            print(
                " ",
                umm["GranuleUR"],
                umm["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"],
            )
        if a.shape and granules:
            g = granules[0]
            print("\n  type:", type(g).__name__, "| top keys:", sorted(g.keys()))
            print("  meta keys:", sorted(g["meta"].keys()))
            print("  umm keys:", sorted(g["umm"].keys()))
            links = g.data_links()
            print(f"  data_links(): {len(links)} links, e.g.")
            for link in links[:20]:
                print("   ", link)


if __name__ == "__main__":
    main()
