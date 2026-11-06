"""T4.3: ABC recovery on synthetic fields -> results/inference/abc_recovery.json + SVG plots.

Usage: uv run python -u scripts/t43_abc.py [n_test] [n_ref_per_year] [k]
Test fields: infer.synthetic.make_fields (seed SEED). Reference tables use other seeds, so test
truth is never in the table. No test-set tuning: k, N, thresholds are fixed before the run.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.infer import abc, forward, priors, synthetic

n_test = int(sys.argv[1]) if len(sys.argv) > 1 else 300
n_ref = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
k = int(sys.argv[3]) if len(sys.argv) > 3 else 300
SEED = priors.SEED

cfg = forward.load_cfg()
crop = forward.crop_params(cfg["crop"], cfg["region"])
cen = synthetic.census(pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet"))
wx = synthetic.weather_years(cfg)
f = synthetic.make_fields(n_test, cen, wx, cfg=cfg)
refs = {
    y: abc.reference_table(wx[y][0], wx[y][1], n_ref, crop, cfg, seed=SEED + 1000 + y)
    for y in sorted(wx)
}
rng = np.random.default_rng(SEED + 7)
VARS = priors.VARIABLES
post = {v: np.zeros((k, n_test)) for v in VARS}
for j in range(n_test):
    r = refs[int(f["year"][j])]
    p = abc.posterior(f["obs_doy"][j], f["obs_ndvi"][j], r, cen["noise_sd"], k, rng)
    for v in VARS:
        post[v][:, j] = np.asarray(r["hidden"][v], float)[p["idx"]]

prior = priors.sample(20000, seed=SEED + 99)
rows = {}
for v in VARS:
    truth = np.asarray(f["truth"][v], float)
    m = truth > 0 if v == "irrigation_mm" else np.ones(n_test, bool)
    pv, tv = post[v][:, m], truth[m]
    c50, c90 = abc.interval_coverage(pv, tv, 0.5), abc.interval_coverage(pv, tv, 0.9)
    shrink = float(np.mean(pv.std(0)) / np.asarray(prior[v], float).std())
    rows[v] = {
        "n_fields": int(m.sum()),
        "coverage_50": round(c50, 3),
        "coverage_90": round(c90, 3),
        "posterior_sd_over_prior_sd": round(shrink, 3),
        "corr_truth_post_mean": round(float(np.corrcoef(pv.mean(0), tv)[0, 1]), 3),
        "within_5pts": bool(abs(c50 - 0.5) <= 0.05 and abs(c90 - 0.9) <= 0.05),
    }
    rows[v]["identifiable"] = bool(rows[v]["within_5pts"] and shrink < 0.9)
irr = (post["irrigated"].mean(0) > 0.5) == np.asarray(f["truth"]["irrigated"], bool)
# Binary variable: central-interval coverage is degenerate, judge by accuracy (prior = 0.5).
rows["irrigated"]["accuracy_at_0.5"] = round(float(irr.mean()), 3)
rows["irrigated"]["identifiable"] = bool(irr.mean() >= 0.65)
rows["irrigated"]["note"] = "coverage not meaningful for a 0/1 variable; accuracy used"
for v in VARS:
    rows[v]["direction"] = (
        "over-covers (conservative)"
        if rows[v]["coverage_90"] > 0.95 or rows[v]["coverage_50"] > 0.55
        else "under-covers (overconfident)"
        if rows[v]["coverage_90"] < 0.85 or rows[v]["coverage_50"] < 0.45
        else "calibrated"
    )
out = {
    "n_test": n_test,
    "n_ref_per_year": n_ref,
    "k": k,
    "years": sorted(wx),
    "variables": rows,
    "tag": "D",
    "note": "truth and ABC share one forward model: identifiability under a perfect model only",
}
Path("results/inference").mkdir(parents=True, exist_ok=True)
Path("results/inference/abc_recovery.json").write_text(json.dumps(out, indent=2), "utf-8")


def scatter_svg(v: str) -> str:
    t = np.asarray(f["truth"][v], float)
    m = post[v].mean(0)
    lo, hi = np.quantile(post[v], [0.05, 0.95], axis=0)
    a, b = float(min(t.min(), lo.min())), float(max(t.max(), hi.max()))
    s = 300.0 / (b - a if b > a else 1.0)
    X = lambda x: 40 + (x - a) * s  # noqa: E731
    Y = lambda y: 340 - (y - a) * s  # noqa: E731
    el = [f'<line x1="{X(a)}" y1="{Y(a)}" x2="{X(b)}" y2="{Y(b)}" stroke="#999"/>']
    for i in range(len(t)):
        el.append(
            f'<line x1="{X(t[i]):.1f}" x2="{X(t[i]):.1f}" y1="{Y(lo[i]):.1f}" '
            f'y2="{Y(hi[i]):.1f}" stroke="#9ecae1" stroke-width="1"/>'
        )
        el.append(f'<circle cx="{X(t[i]):.1f}" cy="{Y(m[i]):.1f}" r="2" fill="#08519c"/>')
    r = rows[v]
    el.append(
        f'<text x="40" y="18" font-size="12">{v}: truth (x) vs posterior mean, 90% band (y); '
        f"cov50={r['coverage_50']} cov90={r['coverage_90']}</text>"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="370">' + "".join(el) + "</svg>"
    )


for v in VARS:
    Path(f"results/inference/abc_recovery_{v}.svg").write_text(scatter_svg(v), "utf-8")
print(
    json.dumps(
        {
            v: {
                x: rows[v][x]
                for x in (
                    "coverage_50",
                    "coverage_90",
                    "posterior_sd_over_prior_sd",
                    "identifiable",
                )
            }
            for v in VARS
        }
    )
)
