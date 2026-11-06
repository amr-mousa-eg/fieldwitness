"""T4.4: simulation-based calibration of the ABC posterior -> results/inference/sbc.json + SVG.

Usage: uv run python -u scripts/t44_sbc.py [n_test] [n_ref_per_year] [k]
Per test field (truth drawn from the prior by make_fields, test seed differs from the reference
tables) the rank of the truth among the k posterior draws is recorded (ties broken at random, so
the binary variable is also valid). If the posterior is calibrated the ranks are uniform.
Uniformity: chi-square statistic over B bins (reported, not tuned). ABC with tolerance k/N is
approximate, so non-uniformity is a result to report, not to hide.
Shapes: U = flat; hump (centre high) = posterior too wide; ends high = too narrow.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.infer import abc, forward, priors, synthetic

n_test = int(sys.argv[1]) if len(sys.argv) > 1 else 500
n_ref = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
k = int(sys.argv[3]) if len(sys.argv) > 3 else 300
SEED = priors.SEED
B = 10

cfg = forward.load_cfg()
crop = forward.crop_params(cfg["crop"], cfg["region"])
cen = synthetic.census(pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet"))
wx = synthetic.weather_years(cfg)
f = synthetic.make_fields(n_test, cen, wx, cfg=cfg)
refs = {
    y: abc.reference_table(wx[y][0], wx[y][1], n_ref, crop, cfg, seed=SEED + 1000 + y)
    for y in sorted(wx)
}
rng = np.random.default_rng(SEED + 11)
VARS = priors.VARIABLES
ranks = {v: [] for v in VARS}
for j in range(n_test):
    r = refs[int(f["year"][j])]
    p = abc.posterior(f["obs_doy"][j], f["obs_ndvi"][j], r, cen["noise_sd"], k, rng)
    for v in VARS:
        if v == "irrigation_mm" and not bool(f["truth"]["irrigated"][j]):
            continue
        d = np.asarray(r["hidden"][v], float)[p["idx"]]
        t = float(f["truth"][v][j])
        lo, eq = int((d < t).sum()), int((d == t).sum())
        ranks[v].append(lo + int(rng.integers(0, eq + 1)))  # rank in 0..k

rows, hist = {}, {}
for v in VARS:
    rk = np.asarray(ranks[v])
    h = np.histogram(rk, bins=B, range=(0, k + 1))[0]
    exp = len(rk) / B
    chi2 = float(((h - exp) ** 2 / exp).sum())
    hist[v] = h.tolist()
    # chi-square 95 % critical value for 9 d.o.f. = 16.92 (standard table value)
    rows[v] = {
        "n_fields": int(len(rk)),
        "hist": h.tolist(),
        "chi2_uniform_9dof": round(chi2, 2),
        "uniform_at_5pct": bool(chi2 < 16.92),
        "ends_share": round(float((h[0] + h[-1]) / len(rk)), 3),
        "centre_share": round(float((h[4] + h[5]) / len(rk)), 3),
    }
    rows[v]["shape"] = (
        "flat"
        if rows[v]["uniform_at_5pct"]
        else "hump (posterior too wide)"
        if rows[v]["centre_share"] > 0.24
        else "U (posterior too narrow)"
        if rows[v]["ends_share"] > 0.24
        else "skewed (bias)"
    )
out = {
    "n_test": n_test,
    "n_ref_per_year": n_ref,
    "k": k,
    "bins": B,
    "variables": rows,
    "tag": "D",
    "note": "ABC tolerance k/N makes the posterior approximate; one shared forward model",
}
Path("results/inference").mkdir(parents=True, exist_ok=True)
Path("results/inference/sbc.json").write_text(json.dumps(out, indent=2), "utf-8")


def hist_svg(v: str) -> str:
    h = np.asarray(hist[v])
    w, ht, m = 360, 220, 30
    bw = (w - 2 * m) / B
    top = max(h.max(), 1) * 1.15
    exp = h.sum() / B
    bars = "".join(
        f'<rect x="{m + i * bw:.1f}" y="{ht - m - (c / top) * (ht - 2 * m):.1f}" '
        f'width="{bw - 2:.1f}" height="{(c / top) * (ht - 2 * m):.1f}" fill="#4477aa"/>'
        for i, c in enumerate(h)
    )
    ey = ht - m - (exp / top) * (ht - 2 * m)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{ht}" '
        f'font-family="sans-serif" font-size="11">'
        f'<text x="{m}" y="16">SBC rank histogram: {v} (n={h.sum()}, tag D)</text>{bars}'
        f'<line x1="{m}" x2="{w - m}" y1="{ey:.1f}" y2="{ey:.1f}" stroke="#cc3311" '
        f'stroke-dasharray="4"/><text x="{m}" y="{ht - 10}">rank of truth among {k} draws '
        f"(red = uniform expectation)</text></svg>"
    )


for v in VARS:
    Path(f"results/inference/sbc_{v}.svg").write_text(hist_svg(v), "utf-8")
print(json.dumps({v: {x: rows[v][x] for x in ("chi2_uniform_9dof", "shape")} for v in VARS}))
