"""T2.2 acceptance check: detected season count vs the crop calendar on 30 labelled fields.

Pre-registered rule (written before the first run, not tuned afterwards):
- sample: 30 Kansas fields, seeded (SEED 20261114), drawn from fields whose labels are all in
  {winter_wheat, sorghum, maize, soybean, fallow}; stratified 10 winter_wheat-ever, 10 summer-crop,
  10 fallow-ever (a field joins the first stratum it qualifies for).
- expected seasons in harvest year Y from the label of year Y: winter_wheat / sorghum / maize /
  soybean -> 1 (+1 when double_crop_second is set); fallow -> 0.
- field-year matches when the detected count in harvest year Y equals the expected count.
- Years 2017..max label year (labels start 2017; the series covers 2015-09 on).
Run: uv run python -m fieldwitness.story.check_seasons
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.story.seasons import detect_seasons

SEED = 20261114
CROPS = {"winter_wheat": 1, "sorghum": 1, "maize": 1, "soybean": 1, "fallow": 0}
SERIES = Path("data/fields/ks_t14slh_hls_series.parquet")
LABELS = Path("data/labels/ks_t14slh.parquet")
OUT = Path("results/story/ks_seasons_check.json")


def expected(row: pd.Series) -> int:
    n = CROPS[row["crop"]]
    return n + (1 if n and isinstance(row["double_crop_second"], str) else 0)


def pick_fields(lab: pd.DataFrame, rng: np.random.Generator) -> dict[str, list[str]]:
    ok = lab.groupby("field_id")["crop"].apply(lambda s: set(s) <= set(CROPS))
    lab = lab[lab["field_id"].isin(ok[ok].index)]
    ever = lab.groupby("field_id")["crop"].apply(set)
    used: set[str] = set()
    out: dict[str, list[str]] = {}
    for name, test in [
        ("winter_wheat", lambda s: "winter_wheat" in s),
        ("summer_crop", lambda s: bool(s & {"sorghum", "maize", "soybean"})),
        ("fallow", lambda s: "fallow" in s),
    ]:
        pool = sorted(i for i, s in ever.items() if test(s) and i not in used)
        pick = sorted(rng.choice(pool, size=10, replace=False).tolist())
        used |= set(pick)
        out[name] = pick
    return out


def main() -> None:
    ser = pd.read_parquet(SERIES)
    lab = pd.read_parquet(LABELS)
    groups = pick_fields(lab, np.random.default_rng(SEED))
    rows = []
    for stratum, ids in groups.items():
        for fid in ids:
            s = ser[ser["field_id"] == fid].sort_values("date")
            det = detect_seasons(s["date"], s["ndvi"])
            for _, r in lab[lab["field_id"] == fid].iterrows():
                got = sum(1 for x in det if x.year == int(r["year"]))
                rows.append(
                    {
                        "stratum": stratum,
                        "field_id": fid,
                        "year": int(r["year"]),
                        "crop": r["crop"],
                        "expected": expected(r),
                        "detected": got,
                        "match": got == expected(r),
                    }
                )
    df = pd.DataFrame(rows)
    by = df.groupby("crop")["match"].agg(["mean", "count"]).round(3).to_dict("index")
    res = {
        "rule": "see module docstring (pre-registered)",
        "n_fields": 30,
        "n_field_years": len(df),
        "match_share": round(float(df["match"].mean()), 3),
        "target": 0.90,
        "passed": bool(df["match"].mean() >= 0.90),
        "by_crop": by,
        "fields": groups,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("n_field_years", "match_share", "passed", "by_crop")}))


if __name__ == "__main__":
    main()
