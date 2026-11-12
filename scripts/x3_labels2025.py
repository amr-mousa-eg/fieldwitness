"""Experiment 3: 2025 crop labels for the pilot fields from the CSB 2018-2025 edition.

Usage: uv run python -u scripts/x3_labels2025.py
Input : data/fields/ks_t14slh_csb1825.parquet (T14SLH tile extract of NASS
        NationalCSB_2018-2025_rev23.zip, layer national1825; columns CDL2018..CDL2025 = CDL class
        codes), data/labels/ks_t14slh.parquet (labels 2017-2024 from the 2017-2024 edition).
Output: data/labels/ks_t14slh_2025.parquet, results/hindcast/clean2025/labels_2025_crosswalk.json

The CDL code -> crop key crosswalk is NOT typed in from memory (CLAUDE.md rule 1). It is learned
from the data: for every pilot field and year 2018-2024, the CDL code of this edition at the
field's representative point is paired with the existing label of that field and year; a code
maps to the label it agrees with in most pairs. Agreement is reported. A 2025 code that never
occurs in 2018-2024, or whose agreement is below 90 % (team threshold, tag A), gets the label
"unknown" and is not scored. Join rule as `labels.build_labels`: representative point, first hit.
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

CSB = Path("data/fields/ks_t14slh_csb1825.parquet")
PILOT = Path("data/fields/ks_t14slh_pilot.parquet")
LABELS = Path("data/labels/ks_t14slh.parquet")
OUT = Path("data/labels/ks_t14slh_2025.parquet")
REPORT = Path("results/hindcast/clean2025/labels_2025_crosswalk.json")
MIN_AGREE = 0.90  # tag A


def main() -> None:
    csb = gpd.read_parquet(CSB)
    pilot = gpd.read_parquet(PILOT)
    pts = gpd.GeoDataFrame(
        pilot[["field_id"]], geometry=pilot.geometry.representative_point(), crs=pilot.crs
    )
    cols = [f"CDL{y}" for y in range(2018, 2026)]
    j = gpd.sjoin(pts.to_crs(csb.crs), csb[["geometry", "CSBID", *cols]], how="left")
    j = j[~j.index.duplicated(keep="first")]
    lab = pd.read_parquet(LABELS).set_index(["field_id", "year"])["crop"]
    pairs = []
    for y in range(2018, 2025):
        for fid, code in zip(j["field_id"], j[f"CDL{y}"], strict=True):
            if pd.notna(code) and (fid, y) in lab.index:
                pairs.append({"code": int(code), "label": lab[(fid, y)], "year": y})
    pairs = pd.DataFrame(pairs)
    xw = {}
    for code, g in pairs.groupby("code"):
        vc = g["label"].value_counts()
        xw[int(code)] = {
            "label": str(vc.index[0]),
            "agreement": float(vc.iloc[0] / len(g)),
            "n_pairs": len(g),
            "all_labels": {str(k): int(v) for k, v in vc.items()},
        }
    overall = float(
        sum(int((pairs["code"] == c).sum() * v["agreement"]) for c, v in xw.items()) / len(pairs)
    )
    rows = []
    for fid, code, csbid in zip(j["field_id"], j["CDL2025"], j["CSBID"], strict=True):
        c = None if pd.isna(code) else int(code)
        x = xw.get(c)
        crop = x["label"] if (x and x["agreement"] >= MIN_AGREE) else "unknown"
        rows.append(
            {
                "field_id": fid,
                "year": 2025,
                "crop": crop,
                "double_crop_second": None,
                "crop_name_raw": None,
                "hcat_code": None,
                "crop_source": "label",
                "cdl_code": c,
                "csb_id": None if pd.isna(csbid) else str(csbid),
            }
        )
    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rep = {
        "source": "NASS NationalCSB_2018-2025_rev23.zip (3,758,023,527 bytes), layer national1825",
        "pairs_2018_2024": len(pairs),
        "overall_agreement_2018_2024": overall,
        "min_agreement_to_use_code": MIN_AGREE,
        "crosswalk": xw,
        "fields_without_polygon": int(j["CDL2025"].isna().sum()),
        "labels_2025": out["crop"].value_counts().to_dict(),
        "tag": "E (NASS CSB/CDL), crosswalk D (learned from 2018-2024 agreement)",
    }
    REPORT.write_text(json.dumps(rep, indent=1), "utf-8")
    print(
        json.dumps(
            {
                k: rep[k]
                for k in (
                    "pairs_2018_2024",
                    "overall_agreement_2018_2024",
                    "labels_2025",
                    "fields_without_polygon",
                )
            },
            indent=1,
        )
    )
    print({c: (v["label"], round(v["agreement"], 3), v["n_pairs"]) for c, v in xw.items()})


if __name__ == "__main__":
    main()
