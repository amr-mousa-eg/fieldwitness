"""Build the GDD before/after tables and charts (pre-registered in DECISIONS.md 2026-11-12).

Usage: uv run python -u results/hindcast/gdd_before_after/code/build.py
Reads only existing Experiment 2 outputs (records, baselines, curves from rerun_with_curves.py)
and local field data; writes only into results/hindcast/gdd_before_after/.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate as ag  # noqa: E402

H = Path("results/hindcast")
G = H / "gdd"
OUT = H / "gdd_before_after"
FIG = OUT / "figures"
PILOT = Path("data/fields/ks_t14slh_pilot.parquet")
SERIES = Path("data/fields/ks_t14slh_hls_series.parquet")
CAL_C, GDD_C = "#0072B2", "#D55E00"  # Okabe-Ito blue, vermillion
CROP_LABEL = {"maize": "Maize", "sorghum": "Sorghum", "winter_wheat": "Winter wheat"}
SOURCES = [
    "results/hindcast/gdd/records_calendar.jsonl",
    "results/hindcast/gdd/records_gdd.jsonl",
    "results/hindcast/gdd/baselines_calendar.jsonl",
    "results/hindcast/gdd/baselines_gdd.jsonl",
    "results/hindcast/ks_t14slh_records.jsonl",
    "results/hindcast/ks_t14slh_baselines.jsonl",
    "results/hindcast/gdd_before_after/curves_calendar.npz",
    "results/hindcast/gdd_before_after/curves_gdd.npz",
    "results/hindcast/gdd_before_after/rerun_check_calendar.json",
    "results/hindcast/gdd_before_after/rerun_check_gdd.json",
    "data/fields/ks_t14slh_pilot.parquet (blocks, field area; local, not in git)",
    "data/fields/ks_t14slh_hls_series.parquet (observed NDVI points; local, not in git)",
]


def fmt(c: dict, nd: int = 2, pct: bool = False) -> str:
    k = 100.0 if pct else 1.0
    s = "%" if pct else ""
    v, lo, hi = c["value"] * k, c["ci_low"] * k, c["ci_high"] * k
    d = 0 if pct else nd
    return f"{v:.{d}f}{s} [{lo:.{d}f}, {hi:.{d}f}]"


def identical(a, b, key) -> dict:
    ra = {key(r): r for r in ag.read_jsonl(a)}
    rb = {key(r): r for r in ag.read_jsonl(b)}
    n = sum(ra[k] == rb.get(k) for k in ra)
    return {"n": len(ra), "n_reference": len(rb), "n_identical": n, "all": n == len(ra) == len(rb)}


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_parquet(PILOT)
    blocks = dict(zip(pilot["field_id"], pilot["block"], strict=True))
    area = dict(zip(pilot["field_id"], pilot["area_ha"], strict=True))
    cal = ag.season_rows(ag.read_jsonl(G / "records_calendar.jsonl"), blocks, "calendar")
    gdd = ag.season_rows(ag.read_jsonl(G / "records_gdd.jsonl"), blocks, "gdd")
    base = pd.concat(
        [
            ag.baseline_rows(ag.read_jsonl(G / f"baselines_{m}.jsonl"), blocks, m)
            for m in ("calendar", "gdd")
        ]
    )
    m = ag.paired(cal, gdd)
    doc: dict = {"pre_registration": "DECISIONS.md 2026-11-12 (commit 6f62874)"}

    # 7. sanity
    doc["sanity"] = {
        "calendar_records_vs_published": identical(
            G / "records_calendar.jsonl", H / "ks_t14slh_records.jsonl", lambda r: r["field_id"]
        ),
        "calendar_baselines_vs_published": identical(
            G / "baselines_calendar.jsonl",
            H / "ks_t14slh_baselines.jsonl",
            lambda r: (r["field_id"], r["year"]),
        ),
        "curve_reruns": {
            mo: json.loads((OUT / f"rerun_check_{mo}.json").read_text("utf-8"))
            for mo in ("calendar", "gdd")
        },
        "source_files": SOURCES,
    }

    # 1. summary table
    rows = []
    for run in ag.RUN_TYPES:
        for crop in ag.CROPS:
            for mode, df in (("calendar", cal), ("gdd", gdd)):
                c = ag.cell(df[(df["run"] == run) & (df["crop"] == crop)])
                rows.append({"run": run, "crop": crop, "method": "FieldWitness", "mode": mode, **c})
            c = ag.diff_cell(m[(m["run"] == run) & (m["crop"] == crop)])
            rows.append(
                {"run": run, "crop": crop, "method": "FieldWitness", "mode": "gdd - calendar", **c}
            )
            for b in ("B0", "B1", "B2"):
                if run == "forced":
                    rows.append(
                        {
                            "run": run,
                            "crop": crop,
                            "method": b,
                            "mode": "-",
                            "note": "no baseline (baselines use past weather)",
                        }
                    )
                    continue
                if crop == "winter_wheat":
                    rows.append(
                        {"run": run, "crop": crop, "method": b, "mode": "-", "note": "no baseline"}
                    )
                    continue
                for mode in ("calendar", "gdd"):
                    sub = base[
                        (base["mode"] == mode) & (base["method"] == b) & (base["crop"] == crop)
                    ]
                    rows.append(
                        {"run": run, "crop": crop, "method": b, "mode": mode, **ag.cell(sub)}
                    )
    flat = []
    for r in rows:
        f = {
            k: r.get(k) for k in ("run", "crop", "method", "mode", "n", "too_few_to_judge", "note")
        }
        for met in ag.METRICS:
            if isinstance(r.get(met), dict):
                f[met] = r[met]["value"]
                f[f"{met}_ci_low"] = r[met]["ci_low"]
                f[f"{met}_ci_high"] = r[met]["ci_high"]
        flat.append(f)
    pd.DataFrame(flat).to_csv(OUT / "summary_table.csv", index=False)
    doc["summary_table"] = rows

    beats = {}
    for crop in ("maize", "sorghum"):
        beats[crop] = {}
        for mode, df in (("calendar", cal), ("gdd", gdd)):
            fw = df[(df["run"] == "forecast") & (df["crop"] == crop)]
            bs = base[(base["mode"] == mode) & (base["crop"] == crop)]
            beats[crop][mode] = ag.beats(fw, bs)
        beats[crop]["fieldwitness_beats_in_both_modes"] = {
            b: beats[crop]["calendar"][b]["fieldwitness_beats"]
            and beats[crop]["gdd"][b]["fieldwitness_beats"]
            for b in ("B0", "B1", "B2")
        }
    beats["winter_wheat"] = "no baseline"
    doc["fieldwitness_vs_baselines_forecast_canopy_crps"] = beats

    # 2. per-field view
    mf = m[m["run"] == "forecast"]
    cal_mean = {
        c: cal[(cal["run"] == "forecast") & (cal["crop"] == c)]["ci_crps"].mean() for c in ag.CROPS
    }
    pf = ag.per_field(mf, cal_mean)
    pf.to_csv(OUT / "per_field.csv", index=False)
    counts = {}
    for c in ag.CROPS:
        g = pf[pf["crop"] == c]
        counts[c] = {
            "fields": len(g),
            "timing": g["timing_class"].value_counts().to_dict(),
            "crps": g["crps_class"].value_counts().to_dict(),
            "crps_band": float(g["crps_band"].iloc[0]),
        }
    doc["per_field_counts"] = counts
    doc["noise_bands"] = {
        "timing_days": ag.TIMING_BAND_DAYS,
        "crps_share_of_calendar_mean": ag.CRPS_BAND_SHARE,
    }
    fig, ax = plt.subplots(2, 3, figsize=(12, 6.5), constrained_layout=True)
    for j, c in enumerate(ag.CROPS):
        g = pf[pf["crop"] == c]
        for i, (col, band, lab) in enumerate(
            (
                ("d_peak_abs_err", ag.TIMING_BAND_DAYS, "Change in peak-timing error (days)"),
                ("d_ci_crps", counts[c]["crps_band"], "Change in canopy CRPS"),
            )
        ):
            a = ax[i, j]
            a.hist(g[col], bins=25, color="#999999", edgecolor="white")
            a.axvspan(-band, band, color="#F0E442", alpha=0.35, label="within noise")
            a.axvline(0, color="black", lw=0.8)
            a.set_xlabel(lab + "\n(negative = heat clock better)")
            a.set_ylabel("Fields")
            a.set_title(f"{CROP_LABEL[c]} (n = {len(g)} fields)")
            if i == 0 and j == 0:
                a.legend(frameon=False)
    fig.suptitle("Per-field change, heat clock (GDD) minus calendar, forecast run")
    fig.savefig(FIG / "per_field_histograms.png", dpi=110)
    plt.close(fig)

    # 3. year by year
    yr = []
    for run in ag.RUN_TYPES:
        for c in ag.CROPS:
            for y in (2022, 2023, 2024):
                d = ag.diff_cell(m[(m["run"] == run) & (m["crop"] == c) & (m["year"] == y)])
                yr.append({"run": run, "crop": c, "year": y, **d})
    doc["by_year_difference"] = yr
    pd.DataFrame(
        [
            {
                "run": r["run"],
                "crop": r["crop"],
                "year": r["year"],
                "n": r["n"],
                "too_few_to_judge": r["too_few_to_judge"],
                **{f"d_{k}": r[k]["value"] for k in ag.METRICS if k in r},
                **{f"d_{k}_ci_low": r[k]["ci_low"] for k in ag.METRICS if k in r},
                **{f"d_{k}_ci_high": r[k]["ci_high"] for k in ag.METRICS if k in r},
            }
            for r in yr
        ]
    ).to_csv(OUT / "by_year.csv", index=False)

    # 5. winter wheat split by pre-registered diagnosis dimensions (computable here)
    series = pd.read_parquet(SERIES)
    nobs = series.groupby(["field_id", series["date"].dt.year])["date"].count().to_dict()
    w = mf[mf["crop"] == "winter_wheat"].copy()
    w["size_class"] = [
        "<10 ha" if area[f] < 10 else ("10-50 ha" if area[f] <= 50 else ">50 ha")
        for f in w["field_id"]
    ]
    w["hls_bin"] = [
        (lambda n: "<10" if n < 10 else ("10-19" if n <= 19 else ">=20"))(nobs.get((f, y), 0))
        for f, y in zip(w["field_id"], w["year"], strict=True)
    ]
    split = {}
    for dim in ("year", "size_class", "hls_bin"):
        split[dim] = {}
        for k, g in w.groupby(dim):
            d = ag.diff_cell(g)
            split[dim][str(k)] = {
                "n": d["n"],
                "too_few_to_judge": d["too_few_to_judge"],
                **({"d_peak_abs_err": d["peak_abs_err"]} if not d["too_few_to_judge"] else {}),
            }
    doc["winter_wheat_timing_split"] = split

    # 4. example fields
    curves = {}
    for mo in ("calendar", "gdd"):
        z = np.load(OUT / f"curves_{mo}.npz")
        curves[mo] = dict(zip(z["keys"].tolist(), z["q"], strict=True))
    ser = series.dropna(subset=["ndvi"]).copy()
    ser["year"] = ser["date"].dt.year
    ser["doy"] = ser["date"].dt.day_of_year
    eligible = {c: sorted(set(mf.loc[mf["crop"] == c, "field_id"])) for c in ag.CROPS}
    picks = ag.pick_examples(eligible, {"winter_wheat": 3, "maize": 2, "sorghum": 3})
    doc["example_fields_random_seed42"] = picks
    after = {}
    for c in ag.CROPS:
        g = pf[pf["crop"] == c].sort_values(["d_peak_abs_err", "field_id"])
        after[c] = {
            "largest_decrease": g["field_id"].head(3).tolist(),
            "largest_increase": g["field_id"].tail(3).tolist()[::-1],
        }
    doc["after_the_fact_fields"] = after

    def chart(fid, crop, path, title_note):
        seasons = sorted(mf.loc[(mf["field_id"] == fid) & (mf["crop"] == crop), "year"])
        fig, axes = plt.subplots(
            1,
            len(seasons),
            figsize=(4.6 * len(seasons), 3.6),
            squeeze=False,
            constrained_layout=True,
        )
        t = np.arange(1, 366)
        for a, y in zip(axes[0], seasons, strict=True):
            key = f"{fid}|{y}|{crop}|forecast"
            for mo, col, ls, lab in (
                ("calendar", CAL_C, "-", "Calendar clock"),
                ("gdd", GDD_C, "--", "Heat clock (GDD)"),
            ):
                q = curves[mo][key]
                a.fill_between(t, q[0], q[2], color=col, alpha=0.18, lw=0)
                a.plot(t, q[1], color=col, ls=ls, lw=2, label=f"{lab}: median, 5-95 % band")
            o = ser[(ser["field_id"] == fid) & (ser["year"] == y)].drop_duplicates("doy")
            a.scatter(
                o["doy"],
                o["ndvi"],
                s=12,
                color="black",
                zorder=3,
                label="Satellite (HLS) observations",
            )
            row = mf[(mf["field_id"] == fid) & (mf["year"] == y) & (mf["crop"] == crop)].iloc[0]
            a.set_title(
                f"{y}: peak error {row['peak_abs_err_cal']:.0f} d (calendar), "
                f"{row['peak_abs_err_gdd']:.0f} d (heat)"
            )
            a.set_xlabel("Day of year" + (" (harvest year)" if crop == "winter_wheat" else ""))
            a.set_ylabel("Canopy greenness (NDVI)")
            a.set_ylim(0, 1)
            a.set_xlim(1, 365)
        axes[0][0].legend(fontsize=7, frameon=False, loc="upper left")
        fig.suptitle(f"{CROP_LABEL[crop]} field {fid[:8]} (forecast run)\n{title_note}", fontsize=9)
        fig.savefig(path, dpi=100)
        plt.close(fig)

    figs = {"examples": [], "after_the_fact": []}
    for c, ids in picks.items():
        for fid in ids:
            p = FIG / f"example_{c}_{fid[:8]}.png"
            chart(fid, c, p, "Randomly drawn (seed 42, rule fixed beforehand).")
            figs["examples"].append(str(p))
    for c, d in after.items():
        for kind, ids in d.items():
            for fid in ids:
                p = FIG / f"after_the_fact_{c}_{kind}_{fid[:8]}.png"
                chart(fid, c, p, "Selected after the fact: for illustration, not evidence.")
                figs["after_the_fact"].append(str(p))
    doc["figures"] = figs

    (OUT / "summary.json").write_text(json.dumps(doc, indent=1, default=str), "utf-8")
    print(json.dumps({"sanity": doc["sanity"], "per_field_counts": counts}, indent=1, default=str))


if __name__ == "__main__":
    main()
