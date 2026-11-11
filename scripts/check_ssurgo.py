"""Phase 12: independent soil check of the 200 Kansas pilot fields against USDA SSURGO.

Usage: uv run --frozen python -u scripts/check_ssurgo.py [--soilgrids PATH]
Read-only: changes no simulation input, pack or result. Writes
results/validation/soil_ssurgo_check.{json,csv,md,png}; raw SDA replies are cached per field in
data/ssurgo/ks_t14slh/ (gitignored), so reruns do not query SDA again.

What is compared (all over the same root zone, Zr):
  A. The TAW the simulation actually uses: per field, the median of the 30 posterior worlds in
     results/rotate/posterior_draws.json (= taw_base_mm 150 x ABC taw_scale; tag D, or tag A for
     the prior-fallback fields), vs SSURGO available water storage AWS = sum(awc_r * dz) (tag E).
     The pipeline does NOT derive TAW from SoilGrids: config/synthetic.yaml `taw_base_mm` is a
     fixed 150 mm placeholder (tag A) for every field, so a "SoilGrids TAW" does not exist.
  B. That 150 mm base itself vs SSURGO AWS (bias and MAE only; it is a constant).
  C. SoilGrids 2.0 clay and sand (mean, the values the pipeline stores, tag E) vs SSURGO
     claytotal_r / sandtotal_r, both thickness-weighted over the root zone, in percent.
Zr = mean of the FAO-56 Table 22 maize range in config/crops.yaml (1.0-1.7 m -> 1.35 m), the
value packs/sim3d.py uses for maize roots; 1.0 m is reported as a sensitivity.
Point = field polygon centroid (representative point if the centroid falls outside).
SSURGO weighting = component-percent weighted mean over components with a complete root-zone
awc_r profile (NRCS's 'weighted average of all components' convention, which lets us check our
sum against NRCS's own aws0100wta); the dominant component is reported as a sensitivity.
"""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import shapely

from fieldwitness.config import load_crops
from fieldwitness.data import ssurgo

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REGION = "ks_t14slh"
OUT = Path("results/validation")
CACHE = Path("data/ssurgo") / REGION
SG_DEPTHS = {"0-5cm": (0, 5), "5-15cm": (5, 15), "15-30cm": (15, 30), "30-60cm": (30, 60)}
SG_DEPTHS |= {"60-100cm": (60, 100), "100-200cm": (100, 200)}
TAW_BASE_MM = 150.0  # config/synthetic.yaml taw_base_mm (tag A placeholder)


def stats(x, y, units: str) -> dict:
    """x minus y. Pearson, Spearman, bias (mean, median), MAE, n."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    diff = d["x"] - d["y"]
    const = d["x"].nunique() < 2 or d["y"].nunique() < 2
    return {
        "n": int(len(d)),
        "pearson_r": None if const else round(float(d["x"].corr(d["y"])), 3),
        "spearman_rho": None if const else round(float(d["x"].corr(d["y"], "spearman")), 3),
        "bias_mean": round(float(diff.mean()), 2),
        "bias_median": round(float(diff.median()), 2),
        "mae": round(float(diff.abs().mean()), 2),
        "units": units,
    }


def soilgrids_root_zone(path: Path, zr_cm: float) -> pd.DataFrame | None:
    if not path.exists():
        return None
    t = pd.read_parquet(path)
    t = t[(t["stat"] == "mean") & t["property"].isin(["clay", "sand"])]
    t = t.assign(w=[ssurgo.overlap_cm(*SG_DEPTHS[d], zr_cm) for d in t["depth"]])
    t = t[(t["w"] > 0) & t["value"].notna()]
    t = t.assign(vw=t["value"] * t["w"])
    g = t.groupby(["field_id", "property"])[["vw", "w"]].sum()
    return (g["vw"] / g["w"]).unstack("property").add_prefix("sg_").add_suffix("_pct")


def main(soilgrids: Path) -> None:
    roots = load_crops().crops["maize"].root_depth_m.range
    zr_cm = 100.0 * float(np.mean(roots))
    index = json.loads(Path(f"packs/demo/{REGION}/index.json").read_text("utf-8"))
    draws = json.loads(Path("results/rotate/posterior_draws.json").read_text("utf-8"))["fields"]
    rows = []
    for i, f in enumerate(index["fields"], 1):
        fid = f["field_id"]
        geom = shapely.from_wkt(f["geometry_wkt"])
        pt = geom.centroid if geom.contains(geom.centroid) else geom.representative_point()
        sda = ssurgo.query_point(pt.x, pt.y, CACHE / f"{fid}.json")
        p = ssurgo.field_profile(sda, zr_cm)
        p100 = ssurgo.field_profile(sda, 100.0)
        d = draws[fid]
        rows.append(
            {
                "field_id": fid,
                "lon": round(pt.x, 6),
                "lat": round(pt.y, 6),
                "ssurgo_status": p["status"],
                "mukey": p.get("mukey"),
                "muname": p.get("muname"),
                "dominant_component": p.get("dominant"),
                "dominant_pct": p.get("dominant_pct"),
                "ssurgo_aws_mm": p.get("aws_mm"),
                "ssurgo_aws_dominant_mm": p.get("dominant_aws_mm"),
                "ssurgo_aws_100cm_mm": p100.get("aws_mm"),
                "ssurgo_clay_pct": p.get("clay_pct"),
                "ssurgo_sand_pct": p.get("sand_pct"),
                "sim_taw_median_mm": float(np.median(d["taw_mm"])),
                "sim_taw_source": d["source"],
            }
        )
        if i % 25 == 0:
            print(f"  {i}/{len(index['fields'])} fields", flush=True)
    df = pd.DataFrame(rows).set_index("field_id")
    sg = soilgrids_root_zone(soilgrids, zr_cm)
    if sg is not None:
        df = df.join(sg)
    ok = df[df["ssurgo_status"] == "ok"]
    post = ok[ok["sim_taw_source"] == "posterior"]
    aws = ok["ssurgo_aws_mm"]
    res = {
        "check": "Independent soil check vs USDA SSURGO (Soil Data Access), Phase 12",
        "tags": {"ssurgo": "E", "soilgrids": "E", "sim_taw_posterior": "D", "taw_base": "A"},
        "root_zone_cm": zr_cm,
        "root_zone_source": "mean of FAO-56 Table 22 maize root depth range (config/crops.yaml)",
        "point": "field centroid (representative point if outside the polygon)",
        "ssurgo_weighting": "component-percent weighted over components with complete awc_r",
        "conversion": "AWS_mm = 10 * sum(awc_r [cm/cm] * horizon thickness inside root zone [cm])",
        "difference_sign": "pipeline/SoilGrids minus SSURGO",
        "n_fields": int(len(df)),
        "n_ssurgo_ok": int(len(ok)),
        "no_match": {
            s: sorted(df.index[df["ssurgo_status"] == s].tolist())
            for s in sorted(set(df["ssurgo_status"]) - {"ok"})
        },
        "ssurgo_aws_mm_summary": {
            k: round(float(v), 1)
            for k, v in aws.describe(percentiles=[0.1, 0.5, 0.9]).items()
            if k != "count"
        },
        "sim_taw_vs_ssurgo_aws": {
            "all_fields": stats(ok["sim_taw_median_mm"], aws, "mm"),
            "posterior_fields_only": stats(post["sim_taw_median_mm"], post["ssurgo_aws_mm"], "mm"),
            "sensitivity_dominant_component": stats(
                ok["sim_taw_median_mm"], ok["ssurgo_aws_dominant_mm"], "mm"
            ),
            "sensitivity_zr_100cm": stats(ok["sim_taw_median_mm"], ok["ssurgo_aws_100cm_mm"], "mm"),
        },
        "taw_base_150mm_vs_ssurgo_aws": stats(pd.Series(TAW_BASE_MM, index=ok.index), aws, "mm"),
    }
    if sg is not None:
        res["soilgrids_vs_ssurgo_texture"] = {
            "clay": stats(ok["sg_clay_pct"], ok["ssurgo_clay_pct"], "% (weight, < 2 mm)"),
            "sand": stats(ok["sg_sand_pct"], ok["ssurgo_sand_pct"], "% (weight, < 2 mm)"),
        }
    else:
        res["soilgrids_vs_ssurgo_texture"] = f"skipped: {soilgrids} not on disk"
    OUT.mkdir(parents=True, exist_ok=True)
    df.round(2).to_csv(OUT / "soil_ssurgo_check.csv")
    (OUT / "soil_ssurgo_check.json").write_text(json.dumps(res, indent=2) + "\n", "utf-8")
    plot(ok, sg is not None, zr_cm)
    (OUT / "soil_ssurgo_check.md").write_text(report(res), "utf-8")
    print(json.dumps(res, indent=2))


def plot(ok: pd.DataFrame, texture: bool, zr_cm: float) -> None:
    n = 3 if texture else 1
    fig, axes = plt.subplots(1, n, figsize=(4.6 * n, 4.6), squeeze=False)
    ink, mute, a1, a2 = "#1f2937", "#6b7280", "#2563eb", "#d97706"

    def panel(ax, x, y, xl, yl, title, groups=None):
        lo = float(np.nanmin([x.min(), y.min()])) * 0.9
        hi = float(np.nanmax([x.max(), y.max()])) * 1.05
        ax.plot([lo, hi], [lo, hi], color=mute, lw=1, ls="--", label="1:1")
        if groups is None:
            ax.scatter(x, y, s=14, color=a1, alpha=0.7, lw=0)
        else:
            for g, c in groups:
                m = ok["sim_taw_source"] == g
                ax.scatter(x[m], y[m], s=14, color=c, alpha=0.7, lw=0, label=f"{g} ({m.sum()})")
        ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel=xl, ylabel=yl)
        ax.set_title(title, fontsize=10, color=ink, loc="left")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    ax = axes[0][0]
    panel(
        ax,
        ok["ssurgo_aws_mm"],
        ok["sim_taw_median_mm"],
        f"SSURGO available water, 0-{zr_cm:.0f} cm (mm) [E]",
        "Simulation TAW, posterior median (mm) [D/A]",
        "Root-zone water capacity",
        groups=[("posterior", a1), ("prior", a2)],
    )
    ax.axhline(TAW_BASE_MM, color=mute, lw=0.8, ls=":")
    ax.text(ax.get_xlim()[1], TAW_BASE_MM, " base 150 mm [A]", va="bottom", ha="right", fontsize=7)
    if texture:
        for j, prop in ((1, "clay"), (2, "sand")):
            panel(
                axes[0][j],
                ok[f"ssurgo_{prop}_pct"],
                ok[f"sg_{prop}_pct"],
                f"SSURGO {prop}, 0-{zr_cm:.0f} cm (%) [E]",
                f"SoilGrids {prop}, 0-{zr_cm:.0f} cm (%) [E]",
                f"{prop.capitalize()} content",
            )
    fig.suptitle(
        f"Kansas pilot fields vs USDA SSURGO (n = {len(ok)})", x=0.01, ha="left", fontsize=11
    )
    fig.tight_layout()
    fig.savefig(OUT / "soil_ssurgo_check.png", dpi=150)
    plt.close(fig)


def report(r: dict) -> str:
    def line(name, s):
        if isinstance(s, str):
            return f"| {name} | {s} | | | | | |"
        return (
            f"| {name} | {s['n']} | {s['pearson_r']} | {s['spearman_rho']} | "
            f"{s['bias_mean']} | {s['bias_median']} | {s['mae']} ({s['units']}) |"
        )

    t = r["sim_taw_vs_ssurgo_aws"]
    out = [
        "# Independent soil check: Kansas pilot fields vs USDA SSURGO",
        "",
        "Generated by `scripts/check_ssurgo.py`. Read-only check; no simulation input changed.",
        f"Root zone 0-{r['root_zone_cm']:.0f} cm ({r['root_zone_source']}). "
        f"Point: {r['point']}. SSURGO: {r['ssurgo_weighting']}. {r['conversion']}. "
        f"Differences are {r['difference_sign']}.",
        "",
        f"Fields: {r['n_fields']}; SSURGO value found: {r['n_ssurgo_ok']}.",
        "",
        "| Comparison | n | Pearson r | Spearman rho | Mean bias | Median bias | MAE |",
        "|---|---|---|---|---|---|---|",
        line("Simulation TAW (all fields) vs SSURGO AWS", t["all_fields"]),
        line("Simulation TAW (posterior fields only)", t["posterior_fields_only"]),
        line("  sensitivity: dominant component", t["sensitivity_dominant_component"]),
        line("  sensitivity: root zone 100 cm", t["sensitivity_zr_100cm"]),
        line("Base TAW 150 mm (constant) vs SSURGO AWS", r["taw_base_150mm_vs_ssurgo_aws"]),
    ]
    tex = r["soilgrids_vs_ssurgo_texture"]
    if isinstance(tex, dict):
        out += [line("SoilGrids clay vs SSURGO clay", tex["clay"])]
        out += [line("SoilGrids sand vs SSURGO sand", tex["sand"])]
    else:
        out += [line("SoilGrids texture", tex)]
    out += ["", f"SSURGO AWS over the root zone (mm): {r['ssurgo_aws_mm_summary']}", ""]
    if r["no_match"]:
        out += ["Fields with no SSURGO value:", ""]
        out += [f"- {s}: {len(ids)} ({', '.join(ids)})" for s, ids in r["no_match"].items()]
    else:
        out += ["Fields with no SSURGO value: none."]
    out += ["", "![scatter](soil_ssurgo_check.png)", ""]
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--soilgrids", type=Path, default=Path(f"data/soil/{REGION}_fields.parquet"))
    main(ap.parse_args().soilgrids)
