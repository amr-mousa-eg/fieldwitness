"""Gate 1 check (a): how often the tag-A no-data rule (mean coverage == 0) fires.

Counts zero cells per property/depth in the Kansas tile soil rasters. Read-only;
writes results/gate1_soil_nodata.json.
"""

import json
from pathlib import Path

import numpy as np
import rasterio

SOIL = Path("data/soil/ks_t14slh")
PROPS = ["bdod", "clay", "sand", "silt", "soc"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]

out = {}
for p in PROPS:
    for dp in DEPTHS:
        f = SOIL / f"{p}_{dp}_mean.tif"
        if not f.exists():
            out[f"{p}_{dp}"] = "missing file"
            continue
        with rasterio.open(f) as r:
            a = r.read(1)
        nz = a[a != 0]
        out[f"{p}_{dp}"] = {
            "cells": int(a.size),
            "zero_cells": int((a == 0).sum()),
            "zero_share": round(float((a == 0).mean()), 4),
            "median_raw_nonzero": float(np.median(nz)) if nz.size else None,
        }
Path("results").mkdir(exist_ok=True)
Path("results/gate1_soil_nodata.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, v if isinstance(v, str) else (v["zero_cells"], v["cells"], v["median_raw_nonzero"]))
