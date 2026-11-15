"""Evaluate Central Ukraine CropFormer (MAE + S2 Red-Edge/SWIR) vs TWDTW on WorldCereal OGH-GHLC10.

Enforces CLAUDE.md Rules 1, 6, 7, 9:
- Zero temporal leakage for MAE pretraining (`<= 2021` in temporal splits) and train/test splits.
- Strict 10 km spatial-block separation (`leave-2-blocks-out` 4-fold CV across 8 FTW blocks,
  400 fields total).
- Evaluates against independent ESA WorldCereal 10 m / OGH-GHLC10 v1.2 maize labels (2020-2024).
- Reports negative findings or remaining confusion honestly without post-hoc test tuning.

Writes `results/story/ua_cropformer_worldcereal.json` and `.md`.
Usage: uv run python -u scripts/eval_ua_cropformer_worldcereal.py
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from fieldwitness.story.phenology_algorithms import CropFormerNumPy
from fieldwitness.story.worldcereal_check import (
    _binary_metrics,
    fetch_ghlc_bbox,
    sample_fields_ghlc,
)

SEED = 20261114
REGION = "ua_central_t36uvu"
OUT_JSON = Path("results/story/ua_cropformer_worldcereal.json")
OUT_MD = Path("results/story/ua_cropformer_worldcereal.md")
MS_COLS = ("ndre1", "ndre2", "ndmi", "nbr2")


def _block_bootstrap_ci(
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    n_boot: int = 1000,
    seed: int = SEED,
) -> dict[str, list[float]]:
    blocks = sorted(df["block"].unique())
    by_block = {
        b: (
            df.loc[df["block"] == b, y_true_col].to_numpy(bool),
            df.loc[df["block"] == b, y_pred_col].to_numpy(bool),
        )
        for b in blocks
    }
    rng = np.random.default_rng(seed)
    accs, f1s, kappas = [], [], []
    nb = len(blocks)
    for _ in range(n_boot):
        pick = rng.integers(0, nb, size=nb)
        yt = np.concatenate([by_block[blocks[i]][0] for i in pick])
        yp = np.concatenate([by_block[blocks[i]][1] for i in pick])
        m = _binary_metrics(yt, yp)
        accs.append(m["accuracy"])
        f1s.append(m["f1"])
        kappas.append(m["kappa"])
    return {
        "accuracy_ci95": [
            round(float(np.percentile(accs, 2.5)), 4),
            round(float(np.percentile(accs, 97.5)), 4),
        ],
        "f1_ci95": [
            round(float(np.percentile(f1s, 2.5)), 4),
            round(float(np.percentile(f1s, 97.5)), 4),
        ],
        "kappa_ci95": [
            round(float(np.percentile(kappas, 2.5)), 4),
            round(float(np.percentile(kappas, 97.5)), 4),
        ],
    }


def _build_harvest_sequences(
    pilot: gpd.GeoDataFrame,
    hls_df: pd.DataFrame,
    ms_df: pd.DataFrame,
    years: list[int],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Build per-(field_id, year) irregular observation arrays cleanly."""
    hls = hls_df.copy()
    hls["date"] = pd.to_datetime(hls["date"])
    ms = ms_df.copy()
    ms["date"] = pd.to_datetime(ms["date"])

    merged = hls.merge(
        ms[["field_id", "date", *MS_COLS]],
        on=["field_id", "date"],
        how="left",
    )
    merged["has_ms"] = merged[list(MS_COLS)].notna().all(axis=1).astype(float)

    block_map = dict(zip(pilot["field_id"].astype(str), pilot["block"].astype(str), strict=True))
    merged["field_id"] = merged["field_id"].astype(str)
    grouped = {fid: grp.sort_values("date") for fid, grp in merged.groupby("field_id", sort=False)}

    records: dict[tuple[str, int], dict[str, Any]] = {}
    for fid, grp in grouped.items():
        dates = grp["date"]
        for yr in years:
            start = pd.Timestamp(year=yr - 1, month=9, day=1)
            end = pd.Timestamp(year=yr, month=12, day=31)
            sub = grp[(dates >= start) & (dates <= end)]
            if len(sub) < 6:
                continue
            doy = (sub["date"] - pd.Timestamp(year=yr, month=1, day=1)).dt.days.to_numpy(float)
            x3 = sub[["ndvi", "evi", "clear_fraction"]].to_numpy(float)
            ms_raw = sub[list(MS_COLS)].to_numpy(float)
            has_ms = sub["has_ms"].to_numpy(float)
            records[(fid, yr)] = {
                "field_id": fid,
                "block": block_map.get(fid, "unknown"),
                "year": int(yr),
                "doy": doy,
                "x3": x3,
                "ms_raw": ms_raw,
                "has_ms": has_ms,
            }
    return records


def _impute_ms_features(
    items: list[dict[str, Any]],
    ms_fill: np.ndarray,
) -> list[dict[str, Any]]:
    """Produce deep copies with `x` filled using training-fold channel means."""
    out = []
    for it in items:
        ms = it["ms_raw"].copy()
        for j in range(ms.shape[1]):
            bad = ~np.isfinite(ms[:, j])
            if bad.any():
                ms[bad, j] = ms_fill[j]
        x8 = np.column_stack([it["x3"], ms, it["has_ms"][:, None]])
        cp = dict(it)
        cp["x"] = x8
        out.append(cp)
    return out


def _fit_ms_fill(items: list[dict[str, Any]]) -> np.ndarray:
    """Compute column-wise means over finite MS values strictly inside training fold."""
    stacked = np.vstack([it["ms_raw"] for it in items])
    means = np.nanmean(stacked, axis=0)
    return np.where(np.isfinite(means), means, 0.0)


def _eval_fold_predictions(
    meta_df: pd.DataFrame,
    probs: np.ndarray,
    thresh: float = 0.50,
) -> tuple[dict[str, Any], pd.DataFrame]:
    res_df = meta_df.copy()
    res_df["p_maize"] = probs
    res_df["y_pred"] = res_df["p_maize"] >= thresh

    def _pack(sub: pd.DataFrame) -> dict[str, Any]:
        m = _binary_metrics(sub["ghlc_is_maize"].to_numpy(bool), sub["y_pred"].to_numpy(bool))
        m.update(_block_bootstrap_ci(sub, "ghlc_is_maize", "y_pred"))
        return m

    summary: dict[str, Any] = {"all_2020_2024": _pack(res_df)}
    for yr_lbl, yr_mask in (
        ("y2021_t24", res_df["year"] == 2021),
        ("post_2022_2024", res_df["year"].isin([2022, 2023, 2024])),
    ):
        if int(yr_mask.sum()) > 0:
            summary[yr_lbl] = _pack(res_df[yr_mask])
    return summary, res_df


def _fit_mae_cache(
    records: dict[tuple[str, int], dict[str, Any]],
    folds: list[list[str]],
    use_ms: bool,
    epochs: int = 12,
    seed: int = SEED,
) -> dict[int, dict[str, Any]]:
    """Pretrain strictly <= 2021 MAE encoders once per fold for reuse across evaluations."""
    d_in = 8 if use_ms else 3
    cache: dict[int, dict[str, Any]] = {}
    for fold_idx, test_blocks in enumerate(folds):
        test_set = set(test_blocks)
        train_raw = [
            v for (_fid, yr), v in records.items() if v["block"] not in test_set and yr <= 2021
        ]
        if use_ms:
            ms_fill = _fit_ms_fill(train_raw)
            pre_samples = _impute_ms_features(train_raw, ms_fill)
        else:
            ms_fill = np.zeros(len(MS_COLS), dtype=float)
            pre_samples = [dict(v, x=v["x3"]) for v in train_raw]

        model = CropFormerNumPy(
            d_in=d_in,
            d_model=32,
            n_heads=4,
            classes=("non_maize", "maize"),
            seed=seed + fold_idx * 17,
        )
        model.pretrain_mae(
            pre_samples,
            mask_ratio=0.30,
            epochs=epochs,
            lr=0.014,
            l2=1e-4,
            batch_size=48,
            seed=seed + fold_idx * 101 + 1,
        )
        cache[fold_idx] = {"model": model, "ms_fill": ms_fill, "pre_samples": pre_samples}
    return cache


def _run_spatial_cv(
    records: dict[tuple[str, int], dict[str, Any]],
    wc_df: pd.DataFrame,
    folds: list[list[str]],
    use_ms: bool,
    pretrain_mae: bool,
    mae_cache: dict[int, dict[str, Any]] | None = None,
    train_years_ft: tuple[int, ...] | None = None,
    test_years: tuple[int, ...] = (2020, 2021, 2022, 2023, 2024),
    seed: int = SEED,
) -> tuple[dict[str, Any], float, pd.DataFrame]:
    """Run leave-2-blocks-out 4-fold spatial CV with optional pre-cutoff temporal split."""
    d_in = 8 if use_ms else 3
    all_rows = []
    all_probs = []
    t_inf_total = 0.0
    n_inf = 0

    wc_map = {
        (str(r["field_id"]), int(r["year"])): bool(r["ghlc_is_maize"]) for _, r in wc_df.iterrows()
    }
    block_of = {k[0]: v["block"] for k, v in records.items()}

    for fold_idx, test_blocks in enumerate(folds):
        test_set = set(test_blocks)
        ft_years_set = (
            set(train_years_ft) if train_years_ft is not None else {2020, 2021, 2022, 2023, 2024}
        )
        ft_raw = []
        for (fid, yr), v in records.items():
            if v["block"] in test_set or yr not in ft_years_set:
                continue
            if (fid, yr) not in wc_map:
                continue
            item = dict(v)
            item["crop"] = "maize" if wc_map[(fid, yr)] else "non_maize"
            ft_raw.append(item)

        eval_raw = []
        for (fid, yr), v in sorted(records.items()):
            if v["block"] not in test_set or yr not in test_years:
                continue
            if (fid, yr) not in wc_map:
                continue
            item = dict(v)
            item["ghlc_is_maize"] = wc_map[(fid, yr)]
            eval_raw.append(item)

        if pretrain_mae and mae_cache is not None and fold_idx in mae_cache:
            model = copy.deepcopy(mae_cache[fold_idx]["model"])
            ms_fill = mae_cache[fold_idx]["ms_fill"]
            ft_samples = (
                _impute_ms_features(ft_raw, ms_fill)
                if use_ms
                else [dict(v, x=v["x3"]) for v in ft_raw]
            )
            eval_samples = (
                _impute_ms_features(eval_raw, ms_fill)
                if use_ms
                else [dict(v, x=v["x3"]) for v in eval_raw]
            )
        else:
            train_raw = [
                v for (_fid, yr), v in records.items() if v["block"] not in test_set and yr <= 2021
            ]
            if use_ms:
                ms_fill = _fit_ms_fill(train_raw)
                pre_samples = _impute_ms_features(train_raw, ms_fill)
                ft_samples = _impute_ms_features(ft_raw, ms_fill)
                eval_samples = _impute_ms_features(eval_raw, ms_fill)
            else:
                pre_samples = [dict(v, x=v["x3"]) for v in train_raw]
                ft_samples = [dict(v, x=v["x3"]) for v in ft_raw]
                eval_samples = [dict(v, x=v["x3"]) for v in eval_raw]

            model = CropFormerNumPy(
                d_in=d_in,
                d_model=32,
                n_heads=4,
                classes=("non_maize", "maize"),
                seed=seed + fold_idx * 17,
            )
            if pretrain_mae:
                model.pretrain_mae(
                    pre_samples,
                    mask_ratio=0.30,
                    epochs=12,
                    lr=0.014,
                    l2=1e-4,
                    batch_size=48,
                    seed=seed + fold_idx * 101 + 1,
                )
            else:
                model.fit_scaler(pre_samples + ft_samples)

        model.fine_tune(
            ft_samples,
            epochs=16,
            lr=0.014,
            l2=1e-3,
            batch_size=48,
            class_weighted=True,
            seed=seed + fold_idx * 101 + 2,
        )

        t_inf_start = time.perf_counter()
        for item in eval_samples:
            _, probs = model.predict(item["x"], item["doy"])
            all_probs.append(probs["maize"])
            all_rows.append(
                {
                    "field_id": item["field_id"],
                    "block": block_of[item["field_id"]],
                    "year": item["year"],
                    "ghlc_is_maize": item["ghlc_is_maize"],
                }
            )
        t_inf_total += time.perf_counter() - t_inf_start
        n_inf += len(eval_samples)

    meta_df = pd.DataFrame(all_rows)
    probs_arr = np.asarray(all_probs, float)
    # Use fixed 0.50 decision threshold (no test-set threshold tuning, CLAUDE.md Rule 9)
    summary, oof_df = _eval_fold_predictions(meta_df, probs_arr, thresh=0.50)
    ms_per_field = round((t_inf_total / max(1, n_inf)) * 1000.0, 3)
    return summary, ms_per_field, oof_df


def _clone_for_classes(
    base_model: CropFormerNumPy, classes: tuple[str, ...], seed: int
) -> CropFormerNumPy:
    """Clone an MAE-pretrained encoder while re-initializing the linear head for `classes`."""
    m = copy.deepcopy(base_model)
    m.classes = tuple(classes)
    rng = np.random.default_rng(seed)
    m.W_cls = rng.normal(0.0, 0.05, (m.d_model, len(m.classes)))
    m.b_cls = np.zeros(len(m.classes))
    return m


def _run_multiclass_phenology_holdout(
    records: dict[tuple[str, int], dict[str, Any]],
    labels_df: pd.DataFrame,
    folds: list[list[str]],
    use_ms: bool,
    mae_cache: dict[int, dict[str, Any]],
    seed: int = SEED,
) -> dict[str, Any]:
    """Evaluate 3-class phenology separation (<=2021 -> 2022-24 + spatial holdout)."""
    lbl_map = {
        (str(r["field_id"]), int(r["year"])): str(r["crop"])
        for _, r in labels_df.iterrows()
        if str(r["crop"]) in ("winter_wheat", "maize", "sunflower")
    }
    classes = ("winter_wheat", "maize", "sunflower")
    y_true_all, y_pred_all = [], []

    for fold_idx, test_blocks in enumerate(folds):
        test_set = set(test_blocks)
        tr_raw, te_raw = [], []
        for (fid, yr), v in sorted(records.items()):
            crop = lbl_map.get((fid, yr))
            if crop is None:
                continue
            item = dict(v)
            item["crop"] = crop
            if v["block"] not in test_set and yr <= 2021:
                tr_raw.append(item)
            elif v["block"] in test_set and yr >= 2022:
                te_raw.append(item)

        ms_fill = mae_cache[fold_idx]["ms_fill"]
        if use_ms:
            tr_samples = _impute_ms_features(tr_raw, ms_fill)
            te_samples = _impute_ms_features(te_raw, ms_fill)
        else:
            tr_samples = [dict(v, x=v["x3"]) for v in tr_raw]
            te_samples = [dict(v, x=v["x3"]) for v in te_raw]

        model = _clone_for_classes(
            mae_cache[fold_idx]["model"], classes, seed=seed + 500 + fold_idx
        )
        model.fine_tune(
            tr_samples,
            epochs=16,
            lr=0.014,
            batch_size=48,
            class_weighted=True,
            seed=seed + fold_idx,
        )
        for item in te_samples:
            pred, _ = model.predict(item["x"], item["doy"])
            y_true_all.append(item["crop"])
            y_pred_all.append(pred)

    yt = np.array(y_true_all)
    yp = np.array(y_pred_all)
    per_cls = {}
    for c in classes:
        m = yt == c
        per_cls[c] = {
            "n": int(m.sum()),
            "recall": round(float((yp[m] == c).mean()), 4) if m.any() else None,
        }
    return {
        "n_test": int(len(yt)),
        "exact_accuracy": round(float((yt == yp).mean()), 4) if len(yt) else None,
        "per_class": per_cls,
    }


def main() -> int:
    pilot = gpd.read_parquet(f"data/fields/{REGION}_pilot.parquet")
    pilot_4326 = pilot.to_crs("EPSG:4326") if pilot.crs and str(pilot.crs) != "EPSG:4326" else pilot
    hls_df = pd.read_parquet(f"data/fields/{REGION}_hls_series.parquet")
    ms_df = pd.read_parquet(f"data/fields/{REGION}_s2_multispectral.parquet")
    labels_df = pd.read_parquet(f"data/labels/{REGION}.parquet")

    # Assemble WorldCereal OGH-GHLC10 2020-2024 labels from local cache
    b = pilot_4326.total_bounds
    bbox = (float(b[0] - 0.01), float(b[1] - 0.01), float(b[2] + 0.01), float(b[3] + 0.01))
    wc_frames = []
    for yr in (2020, 2021, 2022, 2023, 2024):
        arr, meta, _ = fetch_ghlc_bbox(yr, bbox)
        wc_frames.append(sample_fields_ghlc(pilot_4326, arr, meta))
    wc_df = pd.concat(wc_frames, ignore_index=True)

    # Spatial 4-fold partitioning (2 of 8 10 km blocks held out per fold)
    blocks = sorted(pilot["block"].astype(str).unique())
    folds = [blocks[i : i + 2] for i in range(0, len(blocks), 2)]
    print(f"Folds (8 spatial blocks -> 4 folds): {folds}", flush=True)

    # Baseline: shipped NDVI-only TWDTW classifier against WorldCereal OGH-GHLC10
    tw_join = wc_df.merge(
        labels_df[["field_id", "year", "crop"]],
        on=["field_id", "year"],
        how="inner",
    )
    tw_join["twdtw_maize"] = tw_join["crop"] == "maize"
    tw_summary: dict[str, Any] = {}
    for key, mask in (
        ("all_2020_2024", slice(None)),
        ("y2021_t24", tw_join["year"] == 2021),
        ("post_2022_2024", tw_join["year"].isin([2022, 2023, 2024])),
    ):
        sub = tw_join[mask]
        m = _binary_metrics(sub["ghlc_is_maize"].to_numpy(bool), sub["twdtw_maize"].to_numpy(bool))
        m.update(_block_bootstrap_ci(sub, "ghlc_is_maize", "twdtw_maize"))
        tw_summary[key] = m
    print(f"TWDTW baseline kappa (2020-2024): {tw_summary['all_2020_2024']['kappa']}", flush=True)

    records = _build_harvest_sequences(pilot, hls_df, ms_df, list(range(2017, 2025)))
    print(f"Built {len(records)} harvest-year SITS records across 2017-2024", flush=True)

    # Pretrain MAE encoders strictly <= 2021 once per fold (3ch and 8ch)
    mae_3ch = _fit_mae_cache(records, folds, use_ms=False, epochs=12, seed=SEED)
    mae_8ch = _fit_mae_cache(records, folds, use_ms=True, epochs=12, seed=SEED)
    print("Pretrained <=2021 MAE fold encoders (3ch & 8ch)", flush=True)

    # Spatial 4-fold CV variants on 2020-2024
    cf_3ch_cv, ms_3ch, _ = _run_spatial_cv(
        records, wc_df, folds, use_ms=False, pretrain_mae=True, mae_cache=mae_3ch, seed=SEED
    )
    m3 = cf_3ch_cv["all_2020_2024"]
    print(
        f"CropFormer 3ch (MAE<=2021) CV kappa={m3['kappa']}, acc={m3['accuracy']} ({ms_3ch} ms)",
        flush=True,
    )

    cf_8ch_no_mae_cv, _, _ = _run_spatial_cv(
        records, wc_df, folds, use_ms=True, pretrain_mae=False, seed=SEED
    )
    m8n = cf_8ch_no_mae_cv["all_2020_2024"]
    print(
        f"CropFormer 8ch (no MAE) CV kappa={m8n['kappa']}, acc={m8n['accuracy']}",
        flush=True,
    )

    cf_8ch_cv, ms_8ch, _ = _run_spatial_cv(
        records, wc_df, folds, use_ms=True, pretrain_mae=True, mae_cache=mae_8ch, seed=SEED
    )
    m8 = cf_8ch_cv["all_2020_2024"]
    print(
        f"CropFormer 8ch (MAE<=2021) CV kappa={m8['kappa']}, acc={m8['accuracy']} ({ms_8ch} ms)",
        flush=True,
    )

    # Strict Spatio-Temporal Holdout (FT <= 2021 on 6 blocks -> eval 2022-2024 on 2 blocks)
    cf_3ch_st, _, _ = _run_spatial_cv(
        records,
        wc_df,
        folds,
        use_ms=False,
        pretrain_mae=True,
        mae_cache=mae_3ch,
        train_years_ft=(2020, 2021),
        test_years=(2022, 2023, 2024),
        seed=SEED + 33,
    )
    cf_8ch_st, _, _ = _run_spatial_cv(
        records,
        wc_df,
        folds,
        use_ms=True,
        pretrain_mae=True,
        mae_cache=mae_8ch,
        train_years_ft=(2020, 2021),
        test_years=(2022, 2023, 2024),
        seed=SEED + 33,
    )
    print(
        "Strict spatio-temporal holdout (<=2021 -> 2022-2024): "
        f"3ch kappa={cf_3ch_st['all_2020_2024']['kappa']}, "
        f"8ch kappa={cf_8ch_st['all_2020_2024']['kappa']}",
        flush=True,
    )

    # Multi-class phenology reproduction on causal TWDTW labels (<=2021 -> 2022-2024)
    mc_3ch = _run_multiclass_phenology_holdout(
        records, labels_df, folds, use_ms=False, mae_cache=mae_3ch, seed=SEED
    )
    mc_8ch = _run_multiclass_phenology_holdout(
        records, labels_df, folds, use_ms=True, mae_cache=mae_8ch, seed=SEED
    )
    print(
        f"3-class holdout exact_acc: 3ch={mc_3ch['exact_accuracy']}, "
        f"8ch={mc_8ch['exact_accuracy']}",
        flush=True,
    )

    doc = {
        "region_id": REGION,
        "reference_labels": (
            "OpenGeoHub OGH-GHLC10 v1.2 (class 3 = ESA WorldCereal 10 m main-season maize)"
        ),
        "spatial_validation": (
            "Leave-2-blocks-out 4-fold CV across all 8 10 km FTW blocks (400 fields, 100/fold)"
        ),
        "s2_multispectral_coverage": {
            "total_rows": int(len(ms_df)),
            "fields_with_obs": int(ms_df["field_id"].nunique()),
            "years": sorted(int(y) for y in ms_df["date"].dt.year.unique()),
            "channels": ["ndvi", "evi", "clear_fraction", *MS_COLS, "has_ms"],
        },
        "worldcereal_maize_vs_nonmaize": {
            "baseline_twdtw_ndvi": tw_summary,
            "cropformer_3ch_mae_cv": {**cf_3ch_cv, "ms_per_field": ms_3ch},
            "cropformer_8ch_no_mae_cv": cf_8ch_no_mae_cv,
            "cropformer_8ch_mae_cv": {**cf_8ch_cv, "ms_per_field": ms_8ch},
            "strict_spatiotemporal_le2021_to_2022_2024": {
                "cropformer_3ch_mae": cf_3ch_st["all_2020_2024"],
                "cropformer_8ch_mae": cf_8ch_st["all_2020_2024"],
            },
        },
        "multiclass_phenology_holdout": {
            "cropformer_3ch_mae": mc_3ch,
            "cropformer_8ch_mae": mc_8ch,
        },
        "notes": (
            "Maize vs non-maize targets independent ESA WorldCereal 10 m labels cached in "
            "data/worldcereal_ogh/. MAE self-supervised pretraining uses strictly <= 2021 SITS "
            "from the 6 training blocks of each fold."
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    def _row(name: str, m: dict[str, Any], lat: str = "-") -> str:
        ci0, ci1 = m["kappa_ci95"][0], m["kappa_ci95"][1]
        return (
            f"| {name} | {m['n']} | {m['accuracy'] * 100:.1f}% | "
            f"{m['precision'] * 100:.1f}% | {m['recall'] * 100:.1f}% | "
            f"{m['f1']:.3f} | {m['kappa']:.3f} [{ci0:.3f}, {ci1:.3f}] | {lat} |"
        )

    w3, m3_r, s3 = (
        mc_3ch["per_class"]["winter_wheat"]["recall"] * 100,
        mc_3ch["per_class"]["maize"]["recall"] * 100,
        mc_3ch["per_class"]["sunflower"]["recall"] * 100,
    )
    w8, m8_r, s8 = (
        mc_8ch["per_class"]["winter_wheat"]["recall"] * 100,
        mc_8ch["per_class"]["maize"]["recall"] * 100,
        mc_8ch["per_class"]["sunflower"]["recall"] * 100,
    )
    md_lines = [
        "# Central Ukraine (`ua_central_t36uvu`) — S2 Red-Edge/SWIR + MAE CropFormer (E2.2)",
        "",
        "Spatially blocked **4-fold Leave-2-Blocks-Out CV** across all **400 fields "
        "(8 x 10 km FTW blocks)** against independent **OGH-GHLC10 v1.2 (ESA WorldCereal 10 m "
        "maize, 2020-2024)** labels. MAE pretraining uses strictly `<= 2021` unlabeled SITS "
        "inside each fold's 6 training blocks.",
        "",
        "## 1. Maize vs Non-Maize Separation (Pooled `2020–2024`, n = 2,000)",
        "",
        "| Model / Features | n | Accuracy | Precision | Recall | F1 | κ [95% CI] | ms/field |",
        "|---|---|---|---|---|---|---|---|",
        _row("Baseline TWDTW (NDVI-only)", tw_summary["all_2020_2024"]),
        _row(
            "CropFormer 3ch (NDVI+EVI+Clear, MAE<=2021)",
            cf_3ch_cv["all_2020_2024"],
            f"{ms_3ch:.2f}",
        ),
        _row("CropFormer 8ch (+Red-Edge/SWIR, no MAE)", cf_8ch_no_mae_cv["all_2020_2024"]),
        _row(
            "CropFormer 8ch (+Red-Edge/SWIR, MAE<=2021)",
            cf_8ch_cv["all_2020_2024"],
            f"{ms_8ch:.2f}",
        ),
        "",
        "## 2. Year `2021` (T2.4 Cohort, n = 400) & Strict Holdout (`<=2021` -> `2022–2024`)",
        "",
        "| Cohort & Model | n | Accuracy | Precision | Recall | F1 | κ [95% CI] | ms |",
        "|---|---|---|---|---|---|---|---|",
        _row("2021: Baseline TWDTW", tw_summary["y2021_t24"]),
        _row("2021: CropFormer 3ch (MAE<=2021)", cf_3ch_cv["y2021_t24"]),
        _row("2021: CropFormer 8ch (MAE<=2021)", cf_8ch_cv["y2021_t24"]),
        _row("2022–2024 Holdout: CropFormer 3ch (FT<=2021)", cf_3ch_st["all_2020_2024"]),
        _row("2022–2024 Holdout: CropFormer 8ch (FT<=2021)", cf_8ch_st["all_2020_2024"]),
        "",
        "## 3. Multi-Class Phenology Consistency (`<=2021` -> `2022–2024`)",
        "",
        f"- **CropFormer 3ch (MAE):** {mc_3ch['exact_accuracy'] * 100:.1f}% exact match on "
        f"`{mc_3ch['n_test']}` held-out seasons "
        f"(wheat={w3:.1f}%, maize={m3_r:.1f}%, sunflower={s3:.1f}%)",
        f"- **CropFormer 8ch (+Red-Edge/SWIR, MAE):** {mc_8ch['exact_accuracy'] * 100:.1f}% exact "
        f"match (wheat={w8:.1f}%, maize={m8_r:.1f}%, sunflower={s8:.1f}%)",
    ]
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON} and {OUT_MD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
