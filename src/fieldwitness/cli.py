"""FieldWitness command-line entry point: `uv run python -m fieldwitness.cli <command>`."""

import argparse


def main() -> None:
    p = argparse.ArgumentParser(prog="fieldwitness")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("census", help="T0.5 data census for candidate regions")
    c.add_argument("--region", default="all", help="region id from config/regions.yaml, or 'all'")
    c.add_argument(
        "--compare", action="store_true", help="only rebuild comparison.md from existing results"
    )
    pf = sub.add_parser("pilot-fields", help="T1.4 select pilot fields for a region")
    pf.add_argument("--region", required=True)
    hs = sub.add_parser("hls-submit", help="T1.5 submit AppEEARS tasks for the pilot fields")
    hs.add_argument("--region", required=True)
    hw = sub.add_parser("hls-wait", help="T1.5 wait for AppEEARS tasks and download (1 GB cap)")
    hw.add_argument("--region", required=True)
    lb = sub.add_parser("labels", help="T1.6 crop labels per pilot field and year")
    lb.add_argument("--region", required=True)
    pw = sub.add_parser("power", help="T1.2 cache POWER daily weather for the pilot fields")
    pw.add_argument("--region", required=True)
    a = p.parse_args()

    if a.command == "labels":
        from fieldwitness.data import labels
        from fieldwitness.resolve.pilot import load_grid

        table = labels.build_labels(a.region, load_grid(a.region))
        print(labels.write_coverage(a.region, table), flush=True)
        return
    if a.command == "power":
        import geopandas as gpd

        from fieldwitness.data import power

        pilot = gpd.read_parquet(f"data/fields/{a.region}_pilot.parquet")
        keys = sorted(
            {(round(x, 2), round(y, 2)) for x, y in zip(pilot["lon"], pilot["lat"], strict=True)}
        )
        for i, (x, y) in enumerate(keys, 1):
            df, elev = power.cached(x, y)
            if i % 20 == 0 or i == len(keys):
                print(f"  {i}/{len(keys)} points cached ({len(df)} days)", flush=True)
        return

    if a.command in ("hls-submit", "hls-wait"):
        from fieldwitness.data import hls_series

        if a.command == "hls-submit":
            from fieldwitness.resolve.pilot import load_grid

            hls_series.submit_region(a.region, load_grid(a.region))
        else:
            hls_series.wait_and_download(a.region)
        return

    if a.command == "pilot-fields":
        from fieldwitness.resolve.pilot import build_pilot_fields

        _, summary = build_pilot_fields(a.region)
        print(summary, flush=True)
        return

    if a.command == "census":
        from fieldwitness import census

        regions = census.load_regions()
        ids = list(regions) if a.region == "all" else [a.region]
        if a.compare:
            print("wrote", census.write_comparison(list(regions)), flush=True)
            return
        for rid in ids:
            print(f"census {rid} ...", flush=True)
            res = census.run_region(rid, regions[rid])
            print("  wrote", census.write_region(res), flush=True)
        if a.region == "all":
            print("wrote", census.write_comparison(ids), flush=True)


if __name__ == "__main__":
    main()
