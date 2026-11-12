"""Bias diagnosis and per-crop centre recalibration (experiment; see DECISIONS.md pre-registration
of 2026-11-12). Usage:

    uv run python scripts/x4_bias_diagnosis.py --data <folder with power/ and fields/>

Reads the fit inputs copied into results/hindcast/bias_diagnosis/fit_input/ (from branch
experiment/conformal, commit c56a917) and, only after freezing the corrections, the test records
results/hindcast/ks_t14slh_records.jsonl. Writes results/hindcast/bias_diagnosis/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fieldwitness.data import power  # noqa: E402
from fieldwitness.data.asof import as_of, forcing_weather  # noqa: E402
from fieldwitness.experimental import bias  # noqa: E402

OUT = Path("results/hindcast/bias_diagnosis")
FIT_FILES = [OUT / "fit_input" / f"pseudo_cut{c}.jsonl" for c in (2018, 2019, 2020)]
TEST_FILE = Path("results/hindcast/ks_t14slh_records.jsonl")
FIELDS = Path("results/pilot_fields/ks_t14slh.csv")
CROPS = ("maize", "sorghum", "winter_wheat")
MIN_N = 20


def load(path: Path, fields: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for line in path.read_text().splitlines():
        r = json.loads(line)
        for s in r["seasons"]:
            for mode in ("forecast", "forced"):
                m = s[mode]
                rows.append(
                    {
                        "field_id": r["field_id"],
                        "year": s["year"],
                        "crop": s["crop"],
                        "mode": mode,
                        "ci_q": m["canopy_integral"]["q"],
                        "ci_obs": s["observed"]["canopy_integral"],
                        "ci_err": m["canopy_integral"]["err_median"],
                        "pk_q": m["peak"]["q"],
                        "pk_obs": s["observed"]["peak"],
                        "pk_err": m["peak"]["err_median"],
                        "cov50": m["canopy_integral"]["covered50"],
                        "cov90": m["canopy_integral"]["covered90"],
                    }
                )
    df = pd.DataFrame(rows).merge(fields, on="field_id", how="left")
    return df.dropna(subset=["ci_obs", "ci_err"])


# --- Part A ---------------------------------------------------------------------------------


def window(crop: str, year: int) -> tuple[dt.date, dt.date]:
    if crop == "winter_wheat":
        return dt.date(year - 1, 10, 1), dt.date(year, 6, 30)
    return dt.date(year, 4, 1), dt.date(year, 9, 30)


def weather_anomaly(lon, lat, crop, year, data: Path):
    key = power._key(lon, lat)
    loader = lambda lo, la: (pd.read_parquet(data / "power" / f"{key}.parquet"), None)  # noqa: E731
    cut = dt.date(year - 1, 12, 31) if year <= 2021 else dt.date(2021, 12, 31)
    a, b = window(crop, year)
    with as_of(cut):
        clim = power.read(lon, lat, loader=loader)
        with forcing_weather():
            season = power.read(lon, lat, start=a, end=b, loader=loader)
    if season.empty:
        return np.nan, np.nan
    rains, temps = [], []
    for y in sorted({d.year for d in clim.index}):
        lo, hi = window(crop, y)
        if hi > cut or lo < dt.date(2001, 1, 1):
            continue
        w = clim.loc[pd.Timestamp(lo) : pd.Timestamp(hi)]
        rains.append(w["PRECTOTCORR"].sum())
        temps.append(((w["T2M_MAX"] + w["T2M_MIN"]) / 2).mean())
    rain = 100.0 * (season["PRECTOTCORR"].sum() / np.mean(rains) - 1.0)
    temp = ((season["T2M_MAX"] + season["T2M_MIN"]) / 2).mean() - np.mean(temps)
    return rain, temp


def add_drivers(df: pd.DataFrame, data: Path) -> pd.DataFrame:
    hls = pd.read_parquet(
        data / "fields" / "ks_t14slh_hls_series.parquet", columns=["field_id", "date", "n_clear"]
    )
    hls = hls[hls["n_clear"] > 0]
    hls["date"] = pd.to_datetime(hls["date"]).dt.date
    by_field = {f: g["date"].to_numpy() for f, g in hls.groupby("field_id")}
    keys = df[["field_id", "crop", "year", "lon", "lat"]].drop_duplicates()
    rec = []
    for k in keys.itertuples():
        rain, temp = weather_anomaly(k.lon, k.lat, k.crop, k.year, data)
        a, b = window(k.crop, k.year)
        d = by_field.get(k.field_id, np.array([]))
        rec.append((k.field_id, k.crop, k.year, rain, temp, int(((d >= a) & (d <= b)).sum())))
    drv = pd.DataFrame(
        rec, columns=["field_id", "crop", "year", "rain_anom_pct", "temp_anom_c", "n_clear_obs"]
    )
    return df.merge(drv, on=["field_id", "crop", "year"], how="left")


def part_a(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (mode, crop, year), g in df.groupby(["mode", "crop", "year"]):
        for var in ("ci", "pk"):
            s = bias.summarize(g[f"{var}_err"].to_numpy(), g["block"].to_numpy(), MIN_N)
            out.append(
                {
                    "mode": mode,
                    "crop": crop,
                    "year": year,
                    "metric": {"ci": "canopy_integral", "pk": "peak_doy"}[var],
                    **s,
                }
            )
    return pd.DataFrame(out)


def drivers_table(df: pd.DataFrame) -> pd.DataFrame:
    f = df[df["mode"] == "forecast"].copy()
    f["period"] = np.where(f["year"] <= 2021, "2019-2021", "2022-2024")
    out = []
    for period, g in f.groupby("period"):
        for drv in ("rain_anom_pct", "temp_anom_c", "n_clear_obs", "area_ha"):
            h = g.dropna(subset=[drv])
            rho, lo, hi = bias.block_bootstrap_spearman(h[drv], h["ci_err"], h["block"])
            out.append(
                {
                    "period": period,
                    "driver": drv,
                    "n": len(h),
                    "rho": rho,
                    "lo": lo,
                    "hi": hi,
                    "verdict": "tracks the bias" if (lo > 0 or hi < 0) else "cause not established",
                }
            )
    return pd.DataFrame(out)


def plot(tab: pd.DataFrame) -> None:
    for metric in ("canopy_integral", "peak_doy"):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
        for ax, mode in zip(axes, ("forecast", "forced"), strict=False):
            for i, crop in enumerate(CROPS):
                t = tab[(tab.metric == metric) & (tab["mode"] == mode) & (tab.crop == crop)].dropna(
                    subset=["median"]
                )
                x = t["year"] + (i - 1) * 0.15
                ax.errorbar(
                    x,
                    t["median"],
                    yerr=[t["median"] - t["median_lo"], t["median_hi"] - t["median"]],
                    fmt="o",
                    capsize=3,
                    label=crop,
                )
            ax.axhline(0, color="grey", lw=0.8)
            ax.axvline(2021.5, color="grey", ls=":", lw=0.8)
            ax.set_title(f"{mode} mode")
            ax.set_xlabel("season year")
        axes[0].set_ylabel(f"median signed error, {metric} (pred - obs)")
        axes[0].legend()
        fig.suptitle(
            "Signed error by crop and year, 95% spatial-block bootstrap CI (n < 20 omitted)"
        )
        fig.tight_layout()
        fig.savefig(OUT / f"signed_error_{metric}.png", dpi=110)
        plt.close(fig)


# --- Part B ---------------------------------------------------------------------------------


def crps_of(qs, obs) -> np.ndarray:
    return np.array([bias.pinball_crps(q, y) for q, y in zip(qs, obs, strict=False)])


def canopy_candidates(train: pd.DataFrame):
    med = np.array([q[2] for q in train["ci_q"]])
    m = bias.fit_multiplier(med, train["ci_obs"].to_numpy())
    iso = bias.fit_isotonic(med, train["ci_obs"].to_numpy())
    return {
        "none": lambda q: np.asarray(q, float),
        "multiplier": lambda q, m=m: bias.apply_multiplier(q, m),
        "isotonic": lambda q, iso=iso: bias.apply_isotonic(np.atleast_2d(q), iso)[0],
    }, m


def cv_select(fit: pd.DataFrame, seed: int = bias.SEED):
    blocks = np.array(sorted(fit["block"].unique()))
    rng = np.random.default_rng(seed)
    fold_of = dict(zip(blocks, rng.permutation(len(blocks)) % 5, strict=False))
    folds = fit["block"].map(fold_of).to_numpy()
    scores = {k: [] for k in ("none", "multiplier", "isotonic")}
    pk = {"none": [], "shift": []}
    for k in range(5):
        tr, te = fit[folds != k], fit[folds == k]
        cands, _ = canopy_candidates(tr)
        for name, f in cands.items():
            scores[name].append(crps_of([f(q) for q in te["ci_q"]], te["ci_obs"]).mean())
        s = bias.fit_shift(tr["pk_err"])
        pk["none"].append(np.abs(te["pk_err"]).mean())
        pk["shift"].append(np.abs(te["pk_err"] + s).mean())
    stat = {k: (np.mean(v), np.std(v, ddof=1) / np.sqrt(len(v))) for k, v in scores.items()}
    best = min(stat, key=lambda k: stat[k][0])
    chosen = next(
        k for k in ("none", "multiplier", "isotonic") if stat[k][0] <= stat[best][0] + stat[best][1]
    )
    d = np.array(pk["none"]) - np.array(pk["shift"])
    use_shift = d.mean() > d.std(ddof=1) / np.sqrt(len(d))
    return chosen, stat, use_shift, (float(np.mean(pk["none"])), float(np.mean(pk["shift"])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data"))
    args = ap.parse_args()
    fields = pd.read_csv(FIELDS)[["field_id", "block", "area_ha", "lon", "lat"]]

    # ---- fit period only: Part A (2019-2021) and frozen corrections -------------------------
    fit = pd.concat([load(p, fields) for p in FIT_FILES], ignore_index=True)
    frozen = {"source": "experiment/conformal c56a917 pseudo_cut2018-2020", "crops": {}}
    for crop in CROPS:
        g = fit[(fit["mode"] == "forecast") & (fit.crop == crop)]
        if len(g) < MIN_N:
            frozen["crops"][crop] = {
                "n_fit": len(g),
                "canopy": "none (n < 20)",
                "peak_shift_days": None,
            }
            continue
        chosen, stat, use_shift, pk = cv_select(g)
        med = np.array([q[2] for q in g["ci_q"]])
        entry = {
            "n_fit": len(g),
            "canopy": chosen,
            "cv_crps": {k: [round(v[0], 4), round(v[1], 4)] for k, v in stat.items()},
            "cv_peak_mae_none_vs_shift": [round(pk[0], 2), round(pk[1], 2)],
        }
        if chosen == "multiplier":
            entry["multiplier"] = bias.fit_multiplier(med, g["ci_obs"])
        if chosen == "isotonic":
            iso = bias.fit_isotonic(med, g["ci_obs"])
            entry["isotonic_x"], entry["isotonic_y"] = (
                iso.X_thresholds_.tolist(),
                iso.y_thresholds_.tolist(),
            )
        entry["peak_shift_days"] = bias.fit_shift(g["pk_err"]) if use_shift else None
        frozen["crops"][crop] = entry
    (OUT / "frozen_corrections.json").write_text(json.dumps(frozen, indent=2))
    print(
        "frozen:",
        json.dumps(
            {
                c: {k: v for k, v in e.items() if k in ("canopy", "peak_shift_days", "n_fit")}
                for c, e in frozen["crops"].items()
            }
        ),
    )

    # ---- test period, read once ----------------------------------------------------------
    test = load(TEST_FILE, fields)
    both = add_drivers(pd.concat([fit, test], ignore_index=True), args.data)
    tab = part_a(both)
    tab.to_csv(OUT / "signed_error_by_crop_year.csv", index=False)
    drv = drivers_table(both)
    drv.to_csv(OUT / "drivers.csv", index=False)
    plot(tab)

    gate = []
    tf = test[test["mode"] == "forecast"]
    for crop, e in frozen["crops"].items():
        g = tf[tf.crop == crop]
        if e["canopy"] == "none" or e["canopy"].startswith("none") or len(g) < MIN_N:
            gate.append(
                {
                    "crop": crop,
                    "n_test": len(g),
                    "canopy_correction": e["canopy"],
                    "gate": "not applicable",
                }
            )
            continue
        if e["canopy"] == "multiplier":
            f = lambda q, m=e["multiplier"]: bias.apply_multiplier(q, m)  # noqa: E731
        else:
            from sklearn.isotonic import IsotonicRegression

            iso = IsotonicRegression(out_of_bounds="clip").fit(e["isotonic_x"], e["isotonic_y"])
            f = lambda q, iso=iso: bias.apply_isotonic(np.atleast_2d(q), iso)[0]  # noqa: E731
        qc = [f(q) for q in g["ci_q"]]
        raw_err = g["ci_err"].to_numpy()
        cor_err = np.array([q[2] for q in qc]) - g["ci_obs"].to_numpy()
        b = g["block"].to_numpy()
        r_med = bias.block_bootstrap(raw_err, b)
        c_med = bias.block_bootstrap(cor_err, b)
        dcrps = crps_of(qc, g["ci_obs"]) - crps_of(g["ci_q"], g["ci_obs"])
        d = bias.block_bootstrap(dcrps, b, np.mean)
        fit_g = fit[(fit["mode"] == "forecast") & (fit.crop == crop)]
        f_med = bias.block_bootstrap(fit_g["ci_err"].to_numpy(), fit_g["block"].to_numpy())
        year_specific = (np.sign(f_med[0]) != np.sign(r_med[0])) or (f_med[1] <= 0 <= f_med[2])

        def cov(qs, y, lo, hi):
            return float(np.mean([(q[lo] <= v <= q[hi]) for q, v in zip(qs, y, strict=True)]))

        ok = abs(c_med[0]) < abs(r_med[0]) and c_med[1] <= 0 <= c_med[2] and d[2] <= 0
        gate.append(
            {
                "crop": crop,
                "n_test": len(g),
                "canopy_correction": e["canopy"],
                "fit_median_err": f_med,
                "raw_median_err": r_med,
                "corrected_median_err": c_med,
                "crps_diff_mean": d,
                "cov50_raw": cov(g["ci_q"], g["ci_obs"], 1, 3),
                "cov50_corr": cov(qc, g["ci_obs"], 1, 3),
                "cov90_raw": cov(g["ci_q"], g["ci_obs"], 0, 4),
                "cov90_corr": cov(qc, g["ci_obs"], 0, 4),
                "year_specific": bool(year_specific),
                "gate": "PASS" if ok and not year_specific else "FAIL",
            }
        )
        if e.get("peak_shift_days") is not None:
            gate[-1]["peak_mae_raw_vs_shift"] = [
                float(np.abs(g["pk_err"]).mean()),
                float(np.abs(g["pk_err"] + e["peak_shift_days"]).mean()),
            ]
    (OUT / "gate.json").write_text(json.dumps(gate, indent=2, default=float))
    print(json.dumps(gate, indent=1, default=lambda x: round(float(x), 3)))
    write_md(tab, drv, gate)


def fmt(r, k="median"):
    if r.get("verdict") == "too few to judge":
        return "too few to judge"
    return f"{r[k]:+.2f} [{r[k + '_lo']:+.2f}, {r[k + '_hi']:+.2f}]"


def write_md(tab, drv, gate) -> None:
    L = [
        "# Bias diagnosis: signed error by crop and year",
        "",
        "Signed error = predicted median − observed. 95% CI: 1,000 spatial-block (10 km) bootstrap resamples, seed 20261114. Years 2019–2021: pseudo-forecasts (cut-off = previous 31 Dec); 2022–2024: main hindcast (cut-off 31 Dec 2021).",  # noqa: E501
        "",
    ]
    for metric in ("canopy_integral", "peak_doy"):
        L += [
            f"## {metric}",
            "",
            "| mode | crop | year | n | median signed error [CI] | MAE [CI] |",
            "|---|---|---|---|---|---|",
        ]
        for r in tab[tab.metric == metric].sort_values(["mode", "crop", "year"]).to_dict("records"):
            L.append(
                f"| {r['mode']} | {r['crop']} | {r['year']} | {r['n']} | {fmt(r)} | {fmt(r, 'mae') if r.get('verdict') != 'too few to judge' else ''} |"  # noqa: E501
            )
        L.append("")
    L += [
        "## Drivers (forecast mode, canopy signed error, Spearman rho [CI])",
        "",
        "| period | driver | n | rho [CI] | verdict |",
        "|---|---|---|---|---|",
    ]
    for r in drv.to_dict("records"):
        L.append(
            f"| {r['period']} | {r['driver']} | {r['n']} | {r['rho']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] | {r['verdict']} |"  # noqa: E501
        )
    L += [
        "",
        "## Gate (forecast mode, 2022–2024)",
        "",
        "```json",
        json.dumps(gate, indent=1, default=lambda x: round(float(x), 3)),
        "```",
        "",
    ]
    (OUT / "tables.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
