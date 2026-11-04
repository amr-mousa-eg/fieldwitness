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
    a = p.parse_args()

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
