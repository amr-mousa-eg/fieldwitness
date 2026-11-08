"""T7.4a: skill vs field size. Joins hindcast records with field area / interior pixels.

Bins on area_ha fixed before looking at results (tag A): <10, 10-30, 30-60, >=60.
Per bin and mode (forecast/forced), metric canopy_integral and peak: n, mean CRPS,
covered50, covered90. Output results/hindcast/ks_t14slh_size_curve.json + .svg.
"""

import json
from pathlib import Path

import pandas as pd

BINS = [(0, 10), (10, 30), (30, 60), (60, float("inf"))]
METRICS = ("canopy_integral", "peak")
fields = pd.read_parquet("data/fields/ks_t14slh_pilot.parquet")[
    ["field_id", "area_ha", "interior_px"]
].set_index("field_id")
recs = [
    json.loads(x)
    for x in Path("results/hindcast/ks_t14slh_records.jsonl").read_text("utf-8").splitlines()
    if x
]
rows = []
for r in recs:
    if r["field_id"] not in fields.index:
        continue
    f = fields.loc[r["field_id"]]
    for s in r["seasons"]:
        for mode in ("forecast", "forced"):
            for m in METRICS:
                if mode in s:
                    a = s[mode][m]
                    rows.append(
                        dict(
                            area=f.area_ha,
                            px=f.interior_px,
                            mode=mode,
                            metric=m,
                            crps=a["crps"],
                            c50=a["covered50"],
                            c90=a["covered90"],
                            obs=s["observed"][m],
                        )
                    )
df = pd.DataFrame(rows)
out = []
for lo, hi in BINS:
    for mode in ("forecast", "forced"):
        for m in METRICS:
            g = df[(df.area >= lo) & (df.area < hi) & (df["mode"] == mode) & (df.metric == m)]
            if len(g):
                out.append(
                    dict(
                        bin=f"{lo}-{'inf' if hi == float('inf') else hi} ha",
                        mode=mode,
                        metric=m,
                        n=len(g),
                        n_fields_px_median=float(g.px.median()),
                        crps=float(g.crps.mean()),
                        # relative to observed spread so metrics of different units are comparable
                        crps_over_obs_mean=float((g.crps / g.obs.abs().clip(lower=1)).mean()),
                        covered50=float(g.c50.mean()),
                        covered90=float(g.c90.mean()),
                    )
                )
doc = dict(
    bins_ha=[[lo, None if hi == float("inf") else hi] for lo, hi in BINS],
    bins_note="fixed before looking at results (tag A)",
    rows=out,
    tag="D (model) vs O (HLS); area E",
    caveats="small n in some bins; crop mix differs by bin; no significance test",
)
Path("results/hindcast/ks_t14slh_size_curve.json").write_text(json.dumps(doc, indent=1), "utf-8")

# SVG: canopy_integral forecast, CRPS and covered90 per bin
sel = [o for o in out if o["metric"] == "canopy_integral" and o["mode"] == "forecast"]
W, H, P = 480, 260, 40
mx = max(o["crps"] for o in sel) * 1.1
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-size="11">']
parts.append(
    '<text x="40" y="16">Canopy-integral CRPS (bars) and 90% coverage (dots) by field size</text>'
)
bw = (W - 2 * P) / len(sel)
for i, o in enumerate(sel):
    x = P + i * bw + 8
    h = (H - 2 * P) * o["crps"] / mx
    parts.append(
        f'<rect x="{x:.0f}" y="{H - P - h:.0f}" width="{bw - 16:.0f}" '
        f'height="{h:.0f}" fill="#4477aa"/>'
    )
    cy = H - P - (H - 2 * P) * o["covered90"]
    parts.append(f'<circle cx="{x + (bw - 16) / 2:.0f}" cy="{cy:.0f}" r="5" fill="#cc6677"/>')
    parts.append(f'<text x="{x:.0f}" y="{H - P + 14}">{o["bin"]}</text>')
    parts.append(f'<text x="{x:.0f}" y="{H - P + 27}">n={o["n"]}</text>')
parts.append("</svg>")
Path("results/hindcast/ks_t14slh_size_curve.svg").write_text("\n".join(parts), "utf-8")
for o in sel:
    print(o["bin"], o["n"], round(o["crps"], 2), round(o["covered50"], 2), round(o["covered90"], 2))
