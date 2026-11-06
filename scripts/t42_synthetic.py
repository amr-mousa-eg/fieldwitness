"""T4.2: census from the Kansas HLS series, weather, and a seeded batch of synthetic fields.

Writes results/inference/synthetic_summary.json (small) and data/synthetic/ks_synth.npz
(gitignored with data/). Usage: uv run python -u scripts/t42_synthetic.py [n_fields]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.infer import forward, synthetic

n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
cfg = forward.load_cfg()
series = pd.read_parquet("data/fields/ks_t14slh_hls_series.parquet")
cen = synthetic.census(series)
wx = synthetic.weather_years(cfg)
f = synthetic.make_fields(n, cen, wx, cfg=cfg)
peak = f["true_ndvi"].max(0)
summary = {
    "n_fields": n,
    "weather_years_used": sorted(wx),
    "n_gap_templates": cen["n_templates"],
    "median_obs_per_year": cen["median_obs_per_year"],
    "noise_sd_ndvi": round(cen["noise_sd"], 4),
    "true_peak_ndvi_quantiles_5_50_95": [
        round(float(x), 3) for x in np.quantile(peak, [0.05, 0.5, 0.95])
    ],
    "eta_mm_quantiles_5_50_95": [
        round(float(x), 1) for x in np.quantile(f["eta_mm"], [0.05, 0.5, 0.95])
    ],
    "tags": {"noise_sd_ndvi": "D", "gaps": "D", "truth": "A (priors)", "ndvi_map": "A"},
}
Path("results/inference").mkdir(parents=True, exist_ok=True)
Path("results/inference/synthetic_summary.json").write_text(json.dumps(summary, indent=2), "utf-8")
Path("data/synthetic").mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    "data/synthetic/ks_synth.npz",
    true_ndvi=f["true_ndvi"],
    eta_mm=f["eta_mm"],
    year=f["year"],
    **{f"truth_{k}": v for k, v in f["truth"].items()},
)
print(json.dumps(summary))
