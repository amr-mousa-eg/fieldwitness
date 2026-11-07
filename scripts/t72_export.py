# ruff: noqa: E501
"""T7.2/T7.3 export: packs/<region>/hindcast.json, story-field ledger, SVG figure.

Reads results/hindcast/<region>*.json(l). Quantiles q = [5, 25, 50, 75, 95] % (t71_hindcast QS).
Predictions tag D, observed tag D, labels E.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from fieldwitness.schemas import HindcastRow, LedgerEntry, RegionHindcast, Tagged

REGION = sys.argv[1] if len(sys.argv) > 1 else "ks_t14slh"
R = Path("results/hindcast")
P = Path("packs") / REGION
METRICS = ("sos", "peak", "canopy_integral", "cover_days")
UNIT = {
    "sos": "day of year",
    "peak": "day of year",
    "canopy_integral": "NDVI-days/10",
    "cover_days": "days",
}
VERSION = "hindcast-v1"


def _t(v, unit, lo50=None, hi50=None, lo90=None, hi90=None, tag="D", src="hindcast"):
    return Tagged(
        value=v, lo50=lo50, hi50=hi50, lo90=lo90, hi90=hi90, unit=unit, tag=tag, source=src
    )


def main() -> None:
    base = json.loads((R / f"{REGION}.json").read_text("utf-8"))
    bl = json.loads((R / f"{REGION}_baselines.json").read_text("utf-8"))
    rows = [HindcastRow.model_validate(r) for r in base["rows"]]
    for r in bl["table"]:
        if r["method"] == "fieldwitness":
            continue
        sc = {k: v for k, v in r.items() if k not in ("method", "metric", "n")}
        rows.append(
            HindcastRow(
                method=r["method"], mode="forecast", metric=r["metric"], n=r["n"], scores=sc
            )
        )
    recs = [json.loads(x) for x in (R / f"{REGION}_records.jsonl").read_text("utf-8").splitlines()]
    story = sorted((r for r in recs if len(r["seasons"]) == 3), key=lambda r: r["field_id"])
    story = story[0] if story else sorted(recs, key=lambda r: -len(r["seasons"]))[0]
    hc = RegionHindcast(
        schema_version=base["schema_version"],
        region_id=REGION,
        cutoff=date.fromisoformat(base["cutoff"]),
        scored_years=base["scored_years"],
        crop_observed_source="label",
        rows=rows,
        story_field_id=story["field_id"],
        data_as_of=date.fromisoformat(base["cutoff"]),
    )
    (P / "hindcast.json").write_text(hc.model_dump_json(exclude_none=True), "utf-8")

    entries = []
    for s in story["seasons"]:
        for mode in ("forecast", "forced"):
            f = s[mode]
            pred, obs, sc = {}, {}, {}
            for m in METRICS:
                q = f[m]["q"]
                assert q == sorted(q)
                pred[m] = _t(q[2], UNIT[m], q[1], q[3], q[0], q[4], src=f"abc-{mode}")
                obs[m] = _t(s["observed"][m], UNIT[m], src="HLS smoothed series")
                sc[f"crps_{m}"] = f[m]["crps"]
            entries.append(
                LedgerEntry(
                    field_id=story["field_id"],
                    as_of=date.fromisoformat(base["cutoff"]),
                    model_version=VERSION,
                    mode=mode,
                    season_year=s["year"],
                    crop=s["crop"],
                    crop_observed_source="label",
                    predicted=pred,
                    observed=obs,
                    scores=sc,
                )
            )
    pk = P / f"{story['field_id']}.json"
    d = json.loads(pk.read_text("utf-8"))
    d["ledger"] = [json.loads(e.model_dump_json(exclude_none=True)) for e in entries]
    from fieldwitness.schemas import FieldPack

    FieldPack.model_validate(d)
    pk.write_text(json.dumps(d, separators=(",", ":")), "utf-8")
    print("hindcast.json rows", len(rows), "ledger", len(entries), "kb", pk.stat().st_size // 1024)

    # --- figure: CRPS per metric, fieldwitness vs baselines (forecast), hand-written SVG ---
    meths = ["fieldwitness", "B0", "B1", "B2"]
    col = {"fieldwitness": "#1b6ca8", "B0": "#888", "B1": "#c77d1a", "B2": "#7a4fa3"}
    crps = {(r.method, r.metric): r.scores.get("crps") for r in rows if r.mode == "forecast"}
    W, H = 760, 360
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
        '<text x="40" y="22" font-size="14">Kansas hindcast 2022-24 (cut-off 2021-12-31), forecast mode: CRPS, lower is better</text>',
    ]
    for i, m in enumerate(METRICS):
        vals = [crps.get((k, m)) for k in meths]
        mx = max(v for v in vals if v is not None)
        x0 = 40 + i * 180
        out.append(f'<text x="{x0}" y="{H - 14}">{m}</text>')
        for j, (k, v) in enumerate(zip(meths, vals, strict=True)):
            if v is None:
                continue
            h = 260 * v / mx
            x = x0 + j * 38
            out.append(
                f'<rect x="{x}" y="{H - 34 - h:.1f}" width="32" height="{h:.1f}" fill="{col[k]}"/>'
            )
            out.append(f'<text x="{x}" y="{H - 38 - h:.1f}" font-size="10">{v:.1f}</text>')
    for j, k in enumerate(meths):
        out.append(
            f'<rect x="{560 + j * 50}" y="30" width="10" height="10" fill="{col[k]}"/>'
            f'<text x="{574 + j * 50}" y="40" font-size="10">{k}</text>'
        )
    out.append("</svg>")
    (R / f"{REGION}_crps.svg").write_text("\n".join(out), "utf-8")
    print("figure written")


if __name__ == "__main__":
    main()
