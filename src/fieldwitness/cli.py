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
    so = sub.add_parser("soil", help="T1.3 SoilGrids values for the pilot fields (WCS)")
    so.add_argument("--region", required=True)
    cx = sub.add_parser("context", help="T1.8 slope (pilot fields), GRACE and SMAP context")
    cx.add_argument("--region", required=True, help="region for the slope step")
    a = p.parse_args()

    if a.command == "context":
        import json
        from pathlib import Path

        import geopandas as gpd

        from fieldwitness.census import tile_centre_lonlat
        from fieldwitness.config import load_regions
        from fieldwitness.data import appeears as ae
        from fieldwitness.data import context as cx_
        from fieldwitness.resolve.pilot import load_grid

        grid = load_grid(a.region)
        pilot = gpd.read_parquet(f"data/fields/{a.region}_pilot.parquet")
        slope = cx_.slope_degrees(cx_.tile_dem(grid, cx_.nasadem_zips()))
        sl = cx_.field_slopes(pilot, grid, slope)
        sl.to_parquet(cx_.OUT / f"{a.region}_slope.parquet")
        print("slope:", sl["slope_deg_mean"].describe().round(3).to_dict(), flush=True)
        regions = [r for r, v in load_regions().items() if v.status == "selected"]
        summary, points = {}, {}
        for rid in regions:
            g = load_grid(rid)
            bbox = load_regions()[rid].bbox_lonlat
            df = cx_.grace_region_series(cx_.grace_file(), bbox)
            df.to_parquet(cx_.OUT / f"{rid}_grace.parquet")
            summary[rid] = {
                "grace_months": len(df),
                "grace_cells": int(df["n_cells"].iloc[0]),
                "grace_trend_cm_per_year_2002_on": round(cx_.trend_cm_per_year(df), 3),
            }
            points[rid] = tile_centre_lonlat(g)
        reg = cx_.OUT / "smap_task.json"
        if not reg.exists():
            s_ = ae.login()
            try:
                body = cx_.smap_task_body(points, "04-01-2015", "12-31-2024")
                tid = ae.submit(s_, body)
                reg.write_text(json.dumps({"task_id": tid, "points": points}), encoding="utf-8")
            finally:
                ae.logout(s_)
        summary["smap_task"] = json.loads(reg.read_text(encoding="utf-8"))["task_id"]
        Path("results/context").mkdir(parents=True, exist_ok=True)
        Path("results/context/summary.json").write_text(
            json.dumps(summary, indent=1), encoding="utf-8"
        )
        print(summary, flush=True)
        return

    if a.command == "soil":
        from fieldwitness.census import tile_lonlat_bounds
        from fieldwitness.data import soilgrids
        from fieldwitness.resolve.pilot import load_grid

        t = soilgrids.build(a.region, tile_lonlat_bounds(load_grid(a.region)))
        print(f"rows {len(t)}, missing values {int(t['value'].isna().sum())}", flush=True)
        return

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
