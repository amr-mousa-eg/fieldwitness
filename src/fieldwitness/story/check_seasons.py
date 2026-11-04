"""T2.2 acceptance check: detected season count vs the crop calendar on 30 labelled fields.

Three field sets, drawn from DIFFERENT 10 km blocks (pilot `block` column; no block is shared by
any two sets; SEED 20261114):
- orig: the first pre-registered 30 (result on record in results/story/ks_seasons_check.json,
  74.6 %; never overwritten: `orig` refuses to run if that file exists).
- dev / test: the remaining blocks are split in two random halves (seeded); each half supplies 30
  fields (10 winter_wheat-ever, 10 summer-crop, 10 fallow-ever; first stratum a field qualifies
  for). Tune on dev only; run test ONCE.
Rule (unchanged): expected seasons in harvest year Y from the label of year Y: winter_wheat /
sorghum / maize / soybean -> 1 (+1 when double_crop_second is set); fallow -> 0 ("no crop-like
season"); a field-year matches when the detected count equals the expected count. Years 2017..max
label year.
Dev grid for seasons.min_crop_amplitude (fixed before the dev run): 0, .10, .15, .20, .25, .30,
.35, .40, .45, .50; pick the highest dev match share, ties -> smallest value.
Run: uv run python -m fieldwitness.story.check_seasons dev|grid|test|orig
"""

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fieldwitness.story.seasons import detect_seasons
from fieldwitness.story.smooth import load_story

SEED = 20261114
CROPS = {"winter_wheat": 1, "sorghum": 1, "maize": 1, "soybean": 1, "fallow": 0}
SERIES = Path("data/fields/ks_t14slh_hls_series.parquet")
LABELS = Path("data/labels/ks_t14slh.parquet")
PILOT = Path("data/fields/ks_t14slh_pilot.parquet")
RES = Path("results/story")
ORIG = RES / "ks_seasons_check.json"
GRID = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def expected(row: pd.Series) -> int:
    n = CROPS[row["crop"]]
    return n + (1 if n and isinstance(row["double_crop_second"], str) else 0)


def pick_fields(
    lab: pd.DataFrame, rng: np.random.Generator, allowed: set[str] | None = None
) -> dict[str, list[str]]:
    ok = lab.groupby("field_id")["crop"].apply(lambda s: set(s) <= set(CROPS))
    lab = lab[lab["field_id"].isin(ok[ok].index)]
    if allowed is not None:
        lab = lab[lab["field_id"].isin(allowed)]
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


def draw_sets() -> dict:
    """orig (from the record), dev and test (disjoint unused 10 km blocks)."""
    lab, pil = pd.read_parquet(LABELS), pd.read_parquet(PILOT)[["field_id", "block"]]
    orig = json.loads(ORIG.read_text())["fields"]
    ob = set(pil[pil.field_id.isin([f for v in orig.values() for f in v])].block)
    blocks = sorted(set(pil.block) - ob)
    rng = np.random.default_rng(SEED)
    rng.shuffle(blocks)
    half = len(blocks) // 2
    sets, used_blocks = {"orig": orig}, {"orig": sorted(ob)}
    for name, bl in (("dev", blocks[:half]), ("test", blocks[half:])):
        allowed = set(pil[pil.block.isin(bl)].field_id)
        sets[name] = pick_fields(lab, np.random.default_rng(SEED + (name == "test")), allowed)
        ids = [f for v in sets[name].values() for f in v]
        used_blocks[name] = sorted(set(pil[pil.field_id.isin(ids)].block))
    for a in used_blocks:
        for b in used_blocks:
            assert a >= b or not set(used_blocks[a]) & set(used_blocks[b]), (a, b)
    return {"sets": sets, "blocks": used_blocks}


def evaluate(groups: dict[str, list[str]], cfg: dict) -> pd.DataFrame:
    ser, lab = pd.read_parquet(SERIES), pd.read_parquet(LABELS)
    rows = []
    for stratum, ids in groups.items():
        for fid in ids:
            s = ser[ser["field_id"] == fid].sort_values("date")
            det = detect_seasons(s["date"], s["ndvi"], cfg)
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
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> dict:
    by = df.groupby("crop")["match"].agg(["mean", "count"]).round(3).to_dict("index")
    return {
        "n_field_years": len(df),
        "match_share": round(float(df["match"].mean()), 3),
        "passed": bool(df["match"].mean() >= 0.90),
        "by_crop": by,
    }


def _cfg(amp: float) -> dict:
    cfg = copy.deepcopy(load_story())
    cfg["seasons"]["min_crop_amplitude"] = amp
    return cfg


def main(mode: str) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    drawn = draw_sets()
    if mode == "sets":
        (RES / "ks_seasons_sets.json").write_text(json.dumps(drawn, indent=1))
        print({k: len(v) for k, v in drawn["blocks"].items()})
    elif mode == "grid":  # dev only
        tab = {}
        for amp in GRID:
            tab[str(amp)] = summary(evaluate(drawn["sets"]["dev"], _cfg(amp)))
        (RES / "ks_seasons_dev_grid.json").write_text(json.dumps(tab, indent=1))
        print({k: (v["match_share"], v["by_crop"]["fallow"]["mean"]) for k, v in tab.items()})
    elif mode in ("dev", "test"):
        amp = load_story()["seasons"]["min_crop_amplitude"]
        out = RES / f"ks_seasons_{mode}.json"
        if mode == "test" and out.exists():
            sys.exit("test set already run once; refusing to overwrite (no further tuning)")
        df = evaluate(drawn["sets"][mode], _cfg(amp))
        res = {
            "min_crop_amplitude": amp,
            "fields": drawn["sets"][mode],
            "blocks": drawn["blocks"][mode],
            **summary(df),
            "target": 0.90,
            "rows": df.to_dict("records"),
        }
        out.write_text(json.dumps(res, indent=1))
        print(
            json.dumps({k: res[k] for k in ("n_field_years", "match_share", "passed", "by_crop")})
        )
    else:
        sys.exit("usage: sets|grid|dev|test")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
