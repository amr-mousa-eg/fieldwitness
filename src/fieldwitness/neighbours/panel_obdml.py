"""Panel Overlap-Balanced Double Machine Learning (Panel-OBDML / AOW-ATO).

Pre-registered in `DECISIONS.md` to resolve the structural identification,
balance, placebo, and negative-control flaws identified in `diagnostics.py` and `matching.py`:

1. Estimand alignment (Li, Morgan & Zaslavsky 2018 JASA; Mao, Li & Greene 2019 Biometrics):
   `DoubleMLPLR` estimates the conditional-variance / overlap-weighted ATO effect, yet legacy
   diagnostics weighted covariates by inverse propensity (1/e, 1/(1-e)), magnifying extreme RF
   propensities 20x. Here we estimate the Augmented Overlap-Weighted (AOW) ATO effect directly
   using overlap weights w_1 = 1 - e(X), w_0 = e(X) in [0, 1], with zero propensity division.

2. Causal cross-fitted nuisance learners (Chernozhukov et al. 2018; 10 km GroupKFold):
   - Propensity ml_m: StandardScaler + L2-regularized LogisticRegressionCV inside each spatial
     block fold, eliminating tree-leaf propensity overfitting.
   - Outcomes mu_0, mu_1: StandardScaler + RidgeCV blended with shallow regularized
     HistGradientBoostingRegressor (when sample permits).

3. Explicit time-indexed controls & strictly causal pre-(t-2) history (`<= t-3`):
   - Main contrasts include explicit calendar `year` indicators, numeric confounders,
     `prev2_crop`, and leave-own-block-out crop-year productivity residual computed solely from
     years <= t - 3 (never touching Y_{t-2}, preventing negative-control circularity).
   - Placebo (`next_crop`) explicitly conditions on `prev_crop` and `prev2_crop`, blocking
     2-year alternation backdoors (A -> M -> A).
   - Negative-control outcome (`Y_{t-2}`) conditions on year-(t-2) weather (`precip_lag2`,
     `tmax_lag2`), `year_lag2`, `crop_lag2`, `prev_crop_lag2` (t-3), soil/spatial covariates,
     and the <= t-3 baseline residual.

4. Inference: 10 km spatial-block cluster-robust variance (Cameron, Gelbach & Miller 2011) with
   t_{G-1} critical values for both 90% and 95% confidence intervals. All outputs tag D.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV, RidgeCV
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fieldwitness.neighbours.diagnostics import (
    OVERLAP_MAX_SHARE,
    PS_HIGH,
    PS_LOW,
    SMD_MAX,
    balance_smd,
)
from fieldwitness.neighbours.dml import (
    CONFOUNDERS,
    MIN_ARM,
    MIN_BLOCKS,
    OUTCOMES,
    SEED,
    contrast_list,
)
from fieldwitness.neighbours.matching import MIN_ARM as MATCH_MIN_ARM
from fieldwitness.neighbours.matching import matching_contrast_list

NUMERIC_CONFOUNDERS = tuple(c for c in CONFOUNDERS if c != "year")
STATIC_CONFOUNDERS = ("area_ha", "lon", "lat", "clay_pct", "sand_pct", "soc_g_kg")
NEGCTRL_ESS_FLOOR = 10.0


def add_panel_history(
    df: pd.DataFrame,
    extra_rows: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach strictly causal lags and <= (t-3) field productivity anomaly.

    `extra_rows` may supply earlier single-year records (e.g. 2017 where `prev_crop` is absent so
    those rows are excluded from `df`) to populate `crop_lag2`, `prev_crop_lag2`, `Y_{t-2}`, and
    `hist_anom_<y>` strictly backward in time without adding unlabelled rows to `df`.
    """
    out = df.copy().reset_index(drop=True)
    if extra_rows is not None and not extra_rows.empty:
        pool = pd.concat([extra_rows, out], ignore_index=True)
        pool = pool.drop_duplicates(subset=["field_id", "year"], keep="last").reset_index(drop=True)
    else:
        pool = out.copy()

    look = pool.set_index(["field_id", "year"])
    key_df = out[["field_id", "year"]]
    nxt_idx = pd.MultiIndex.from_arrays([key_df["field_id"], key_df["year"] + 1])
    lag2_idx = pd.MultiIndex.from_arrays([key_df["field_id"], key_df["year"] - 2])
    lag3_idx = pd.MultiIndex.from_arrays([key_df["field_id"], key_df["year"] - 3])

    out["next_crop"] = look["crop"].reindex(nxt_idx).to_numpy()
    out["crop_lag2"] = look["crop"].reindex(lag2_idx).fillna("unknown").to_numpy()
    # Preceding crop of year (t-2) is crop(t-3), or prev_crop(t-2) when t-3 crop row is absent
    p3 = look["crop"].reindex(lag3_idx).to_numpy()
    if "prev_crop" in look.columns:
        p2_prev = look["prev_crop"].reindex(lag2_idx).to_numpy()
        p3 = np.where(pd.notna(p3), p3, p2_prev)
    out["prev_crop_lag2"] = pd.Series(p3).fillna("unknown").to_numpy()
    out["precip_lag2"] = pd.to_numeric(
        look["season_precip_mm"].reindex(lag2_idx), errors="coerce"
    ).to_numpy()
    out["tmax_lag2"] = pd.to_numeric(
        look["season_tmax_c"].reindex(lag2_idx), errors="coerce"
    ).to_numpy()
    out["year_lag2"] = out["year"] - 2

    for col in OUTCOMES:
        out[f"{col}_lag2"] = (
            pd.to_numeric(look[col].reindex(lag2_idx), errors="coerce").to_numpy()
            if col in look.columns
            else np.nan
        )

    # Strictly causal pre-(t-2) anomaly residual (using ONLY years s <= year - 3)
    for col in OUTCOMES:
        anom_vals = np.zeros(len(out), dtype=float)
        has_hist = np.zeros(len(out), dtype=float)
        if col not in pool.columns or "block" not in pool.columns:
            out[f"hist_anom_{col}"] = anom_vals
            out[f"has_hist_{col}"] = has_hist
            continue

        valid = pool.dropna(subset=[col, "crop", "block", "year"])[
            ["field_id", "year", "crop", "block", col]
        ].copy()
        if valid.empty:
            out[f"hist_anom_{col}"] = anom_vals
            out[f"has_hist_{col}"] = has_hist
            continue

        # Leave-own-block-out crop-year baseline mean:
        # mu_{-b}(s, c) = (sum_{s,c} - sum_{s,c,b}) / (n_{s,c} - n_{s,c,b})
        sc_sum = valid.groupby(["year", "crop"])[col].transform("sum")
        sc_cnt = valid.groupby(["year", "crop"])[col].transform("count")
        scb_sum = valid.groupby(["year", "crop", "block"])[col].transform("sum")
        scb_cnt = valid.groupby(["year", "crop", "block"])[col].transform("count")
        other_cnt = sc_cnt - scb_cnt
        loo_mean = np.where(
            other_cnt > 0,
            (sc_sum - scb_sum) / np.maximum(other_cnt, 1),
            sc_sum / np.maximum(sc_cnt, 1),
        )
        valid["anom"] = valid[col].to_numpy(dtype=float) - loo_mean

        # Group by field_id -> sorted arrays of (year_s, anom_s)
        hist_by_field: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for fid, g in valid.groupby("field_id", sort=False):
            gs = g.sort_values("year")
            hist_by_field[str(fid)] = (
                gs["year"].to_numpy(dtype=int),
                gs["anom"].to_numpy(dtype=float),
            )

        for idx, (fid, yr) in enumerate(zip(out["field_id"], out["year"], strict=True)):
            rec = hist_by_field.get(str(fid))
            if rec is None:
                continue
            yrs, anoms = rec
            mask = yrs <= (int(yr) - 3)
            if mask.any():
                anom_vals[idx] = float(np.mean(anoms[mask]))
                has_hist[idx] = 1.0

        out[f"hist_anom_{col}"] = anom_vals
        out[f"has_hist_{col}"] = has_hist

    return out


def _one_hot(series: pd.Series, prefix: str) -> pd.DataFrame:
    vals = series.fillna("unknown").astype(str)
    levels = sorted(vals.unique())
    cols = {f"{prefix}_{lv}": (vals == lv).astype(float).to_numpy() for lv in levels}
    return pd.DataFrame(cols, index=series.index)


def design_main(
    s: pd.DataFrame,
    outcome: str,
    include_prev2: bool = True,
) -> pd.DataFrame:
    """Design matrix for main contrast: numeric confounders + year dummies + prev2 + <=t-3 anom."""
    parts = [s[list(NUMERIC_CONFOUNDERS)].astype(float)]
    parts.append(_one_hot(s["year"].astype(int).astype(str), "yr"))
    if include_prev2 and "prev2_crop" in s.columns:
        parts.append(_one_hot(s["prev2_crop"], "prev2"))
    hist_col, has_col = f"hist_anom_{outcome}", f"has_hist_{outcome}"
    if hist_col in s.columns and has_col in s.columns:
        parts.append(s[[hist_col, has_col]].astype(float))
    return pd.concat(parts, axis=1).reset_index(drop=True)


def design_placebo(
    s: pd.DataFrame,
    outcome: str,
    include_prev2: bool = True,
) -> pd.DataFrame:
    """Design matrix for placebo (`next_crop`): includes `prev_crop` & `prev2_crop` histories."""
    parts = [s[list(NUMERIC_CONFOUNDERS)].astype(float)]
    parts.append(_one_hot(s["year"].astype(int).astype(str), "yr"))
    parts.append(_one_hot(s["prev_crop"], "prev"))
    if include_prev2 and "prev2_crop" in s.columns:
        parts.append(_one_hot(s["prev2_crop"], "prev2"))
    hist_col, has_col = f"hist_anom_{outcome}", f"has_hist_{outcome}"
    if hist_col in s.columns and has_col in s.columns:
        parts.append(s[[hist_col, has_col]].astype(float))
    return pd.concat(parts, axis=1).reset_index(drop=True)


def design_negctrl(s: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Design matrix for negative control (`Y_{t-2}`): year-(t-2) climate, crops, and <=t-3 anom."""
    parts = [
        s[list(STATIC_CONFOUNDERS)].astype(float),
        s[["precip_lag2", "tmax_lag2"]].astype(float),
        _one_hot(s["year_lag2"].astype(int).astype(str), "yr_lag2"),
        _one_hot(s["crop_lag2"], "crop_lag2"),
        _one_hot(s["prev_crop_lag2"], "prev_lag2"),
    ]
    hist_col, has_col = f"hist_anom_{outcome}", f"has_hist_{outcome}"
    if hist_col in s.columns and has_col in s.columns:
        parts.append(s[[hist_col, has_col]].astype(float))
    return pd.concat(parts, axis=1).reset_index(drop=True)


def _fit_propensity_fold(x_tr: np.ndarray, d_tr: np.ndarray, seed: int) -> object:
    n_pos = int((d_tr == 1).sum())
    n_neg = int((d_tr == 0).sum())
    min_arm = min(n_pos, n_neg)
    if min_arm >= 6:
        cv = StratifiedKFold(n_splits=min(3, min_arm // 2), shuffle=True, random_state=seed)
        clf = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "logit",
                    LogisticRegressionCV(
                        Cs=np.logspace(-2, 2, 9),
                        cv=cv,
                        l1_ratios=(0,),
                        scoring="neg_log_loss",
                        use_legacy_attributes=False,
                        max_iter=1000,
                        random_state=seed,
                    ),
                ),
            ]
        )
    else:
        clf = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("logit", LogisticRegression(C=1.0, max_iter=1000, random_state=seed)),
            ]
        )
    clf.fit(x_tr, d_tr)
    return clf


def _fit_outcome_fold(
    x_tr: np.ndarray, y_tr: np.ndarray, seed: int
) -> tuple[object, object | None]:
    ridge = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=np.logspace(-1, 3, 13))),
        ]
    )
    ridge.fit(x_tr, y_tr)
    hgb = None
    if len(y_tr) >= 35:
        leaf = max(8, len(y_tr) // 10)
        hgb = HistGradientBoostingRegressor(
            max_iter=60,
            max_depth=3,
            min_samples_leaf=leaf,
            l2_regularization=5.0,
            random_state=seed,
        )
        hgb.fit(x_tr, y_tr)
    return ridge, hgb


def _predict_outcome_fold(models: tuple[object, object | None], x_te: np.ndarray) -> np.ndarray:
    ridge, hgb = models
    pred = ridge.predict(x_te)
    if hgb is not None:
        pred = 0.5 * pred + 0.5 * hgb.predict(x_te)
    return pred


def fit_aow(
    x: pd.DataFrame,
    y: np.ndarray,
    d: np.ndarray,
    blocks: np.ndarray,
    seed: int = SEED,
) -> dict:
    """Fit cross-fitted Augmented Overlap-Weighted (AOW / ATO) estimator.

    Returns point estimate, block-clustered SE, 95% and 90% t_{G-1} CIs, cross-fitted
    propensities `e_hat`, overlap weights `w`, ESS per arm, overlap/balance metrics, and n_blocks.
    """
    x_arr = x.to_numpy(dtype=float)
    y_arr = np.asarray(y, dtype=float)
    d_arr = np.asarray(d, dtype=float)
    blk_arr = np.asarray(blocks)
    n = len(y_arr)
    uniq_blocks = np.unique(blk_arr)
    n_blocks = len(uniq_blocks)

    e_hat = np.empty(n, dtype=float)
    mu0 = np.empty(n, dtype=float)
    mu1 = np.empty(n, dtype=float)

    n_folds = min(5, n_blocks)
    gkf = GroupKFold(n_splits=n_folds)
    for tr_idx, te_idx in gkf.split(x_arr, y_arr, groups=blk_arr):
        x_tr, x_te = x_arr[tr_idx], x_arr[te_idx]
        d_tr, y_tr = d_arr[tr_idx], y_arr[tr_idx]

        # Propensity model
        if (d_tr == 1).sum() < 2 or (d_tr == 0).sum() < 2:
            e_hat[te_idx] = float(np.clip(d_tr.mean(), 0.01, 0.99))
        else:
            m_fit = _fit_propensity_fold(x_tr, d_tr.astype(int), seed)
            e_hat[te_idx] = m_fit.predict_proba(x_te)[:, 1]

        # Outcome models on control and treated arms separately
        m0_mask = d_tr == 0
        m1_mask = d_tr == 1
        if m0_mask.sum() >= 5:
            mod0 = _fit_outcome_fold(x_tr[m0_mask], y_tr[m0_mask], seed)
            mu0[te_idx] = _predict_outcome_fold(mod0, x_te)
        else:
            mu0[te_idx] = float(y_tr[m0_mask].mean()) if m0_mask.any() else float(y_tr.mean())

        if m1_mask.sum() >= 5:
            mod1 = _fit_outcome_fold(x_tr[m1_mask], y_tr[m1_mask], seed + 1)
            mu1[te_idx] = _predict_outcome_fold(mod1, x_te)
        else:
            mu1[te_idx] = float(y_tr[m1_mask].mean()) if m1_mask.any() else float(y_tr.mean())

    e_num = np.clip(e_hat, 1e-4, 1.0 - 1e-4)
    h = e_num * (1.0 - e_num)
    w = np.where(d_arr == 1, 1.0 - e_num, e_num)

    # Mao, Li & Greene (2019) Augmented Overlap Weighting score
    psi = (
        h * (mu1 - mu0)
        + d_arr * (1.0 - e_num) * (y_arr - mu1)
        - (1.0 - d_arr) * e_num * (y_arr - mu0)
    )
    h_bar = float(np.mean(h))
    theta = float(np.sum(psi) / max(np.sum(h), 1e-12))

    # 10 km spatial-block cluster-robust variance (Cameron, Gelbach & Miller 2011) with CR1 df
    phi = (psi - theta * h) / max(h_bar, 1e-12)
    cluster_sums = np.array([phi[blk_arr == b].sum() for b in uniq_blocks], dtype=float)
    cr1 = n_blocks / max(n_blocks - 1, 1)
    var_hat = float(cr1 * np.sum(cluster_sums**2) / (n * n))
    se = float(np.sqrt(max(var_hat, 1e-18)))

    df_t = max(n_blocks - 1, 1)
    t95 = float(student_t.ppf(0.975, df=df_t))
    t90 = float(student_t.ppf(0.95, df=df_t))

    # Effective Sample Size per arm under overlap weights
    w1 = w[d_arr == 1]
    w0 = w[d_arr == 0]
    ess1 = float((w1.sum() ** 2) / max((w1**2).sum(), 1e-12)) if len(w1) else 0.0
    ess0 = float((w0.sum() ** 2) / max((w0**2).sum(), 1e-12)) if len(w0) else 0.0

    share_out = float(np.mean((e_hat < PS_LOW) | (e_hat > PS_HIGH)))
    e_ipw = np.clip(e_hat, PS_LOW, PS_HIGH)
    w_ipw = np.where(d_arr == 1, 1.0 / e_ipw, 1.0 / (1.0 - e_ipw))
    smd_raw = balance_smd(x, d_arr)
    smd_ipw = balance_smd(x, d_arr, w_ipw)
    smd_ow = balance_smd(x, d_arr, w)

    return {
        "effect": theta,
        "se": se,
        "ci_low": theta - t95 * se,
        "ci_high": theta + t95 * se,
        "lo90": theta - t90 * se,
        "hi90": theta + t90 * se,
        "n": n,
        "n_treated": int((d_arr == 1).sum()),
        "n_reference": int((d_arr == 0).sum()),
        "n_blocks": n_blocks,
        "ps_min": float(e_hat.min()),
        "ps_max": float(e_hat.max()),
        "share_outside": share_out,
        "ess_treated": ess1,
        "ess_reference": ess0,
        "ess_min": min(ess1, ess0),
        "smd_raw_max": smd_raw,
        "smd_ipw_max": smd_ipw,
        "smd_weighted_max": smd_ow,
        "overlap_weights": w,
        "e_hat": e_hat,
    }


def _check_overlap_and_balance(fit: dict, ess_floor: float) -> dict:
    ov_pass = fit["share_outside"] <= OVERLAP_MAX_SHARE and fit["ess_min"] >= ess_floor
    bal_pass = fit["smd_weighted_max"] <= SMD_MAX
    return {
        "overlap_status": "pass" if ov_pass else "fail",
        "balance_status": "pass" if bal_pass else "fail",
    }


def fit_and_diagnose_contrast(
    df_hist: pd.DataFrame,
    crop: str,
    treated: str,
    ref: str,
    outcome: str,
    stratum: str,
    prev2_crop: str | None = None,
    min_arm: int | None = None,
    seed: int = SEED,
) -> dict:
    """Fit Panel-OBDML (AOW/ATO) + all 4 pre-registered diagnostics for one contrast.

    If `prev2_crop` is None, runs a pooled contrast matching Primary DML's contrast space; if
    provided, restricts both arms to identical `prev2_crop` (matching-history).
    """
    need = (
        min_arm
        if min_arm is not None
        else (MATCH_MIN_ARM if prev2_crop is not None else MIN_ARM[stratum])
    )
    ess_floor = max(12.0, 0.5 * need)

    row: dict = {
        "crop": crop,
        **({"prev2_crop": prev2_crop} if prev2_crop is not None else {}),
        "treated_prev": treated,
        "reference_prev": ref,
        "outcome": outcome,
        "stratum": stratum,
        "n": 0,
        "n_treated": 0,
        "n_reference": 0,
        "n_blocks": 0,
        "outcome_sd": np.nan,
        "effect": np.nan,
        "se": np.nan,
        "ci_low": np.nan,
        "ci_high": np.nan,
        "lo90": np.nan,
        "hi90": np.nan,
        "ps_min": np.nan,
        "ps_max": np.nan,
        "share_outside": np.nan,
        "ess_min": np.nan,
        "smd_raw_max": np.nan,
        "smd_ipw_max": np.nan,
        "smd_weighted_max": np.nan,
        "overlap_status": "untested",
        "balance_status": "untested",
        "placebo_effect": np.nan,
        "placebo_ci_low": np.nan,
        "placebo_ci_high": np.nan,
        "placebo_n": 0,
        "placebo_status": "untested",
        "negctrl_effect": np.nan,
        "negctrl_ci_low": np.nan,
        "negctrl_ci_high": np.nan,
        "negctrl_n": 0,
        "negctrl_status": "untested",
        "n_failed": 0,
        "n_untested": 4,
        "show_as_evidence": False,
        "note": "",
        "tag": "D",
    }

    def _filter(arm_col: str, req_cols: tuple[str, ...]) -> pd.DataFrame:
        sub = df_hist[(df_hist["crop"] == crop) & df_hist[arm_col].isin([treated, ref])]
        if prev2_crop is not None:
            sub = sub[sub["prev2_crop"] == prev2_crop]
        if stratum != "all":
            sub = sub[sub["dry_season"] == (stratum == "dry")]
        return sub.dropna(subset=list(req_cols)).reset_index(drop=True)

    # 1. Main fit
    s_main = _filter("prev_crop", (outcome, *CONFOUNDERS))
    d_main = (s_main["prev_crop"] == treated).to_numpy(dtype=float)
    row["n"] = len(s_main)
    row["n_treated"] = int(d_main.sum())
    row["n_reference"] = int(len(s_main) - d_main.sum())
    row["n_blocks"] = int(s_main["block"].nunique()) if len(s_main) else 0
    row["outcome_sd"] = float(s_main[outcome].std()) if len(s_main) > 1 else np.nan
    if row["n_treated"] < need or row["n_reference"] < need or row["n_blocks"] < MIN_BLOCKS:
        row["note"] = "too few rows or blocks"
        return row

    x_main = design_main(s_main, outcome, include_prev2=(prev2_crop is None))
    m_fit = fit_aow(x_main, s_main[outcome].to_numpy(), d_main, s_main["block"].to_numpy(), seed)
    ov_bal = _check_overlap_and_balance(m_fit, ess_floor)
    row.update(
        effect=m_fit["effect"],
        se=m_fit["se"],
        ci_low=m_fit["ci_low"],
        ci_high=m_fit["ci_high"],
        lo90=m_fit["lo90"],
        hi90=m_fit["hi90"],
        ps_min=m_fit["ps_min"],
        ps_max=m_fit["ps_max"],
        share_outside=m_fit["share_outside"],
        ess_min=m_fit["ess_min"],
        smd_raw_max=m_fit["smd_raw_max"],
        smd_ipw_max=m_fit["smd_ipw_max"],
        smd_weighted_max=m_fit["smd_weighted_max"],
        **ov_bal,
    )

    # 2. De-confounded placebo: next crop as treatment, holding prev_crop & prev2_crop fixed
    s_pla = _filter("next_crop", (outcome, *CONFOUNDERS))
    d_pla = (s_pla["next_crop"] == treated).to_numpy(dtype=float)
    if (
        int(d_pla.sum()) >= need
        and int(len(s_pla) - d_pla.sum()) >= need
        and s_pla["block"].nunique() >= MIN_BLOCKS
    ):
        x_pla = design_placebo(s_pla, outcome, include_prev2=(prev2_crop is None))
        p_fit = fit_aow(x_pla, s_pla[outcome].to_numpy(), d_pla, s_pla["block"].to_numpy(), seed)
        pla_pass = not (p_fit["ci_low"] > 0.0 or p_fit["ci_high"] < 0.0)
        row.update(
            placebo_effect=p_fit["effect"],
            placebo_ci_low=p_fit["ci_low"],
            placebo_ci_high=p_fit["ci_high"],
            placebo_n=len(s_pla),
            placebo_status="pass" if pla_pass else "fail",
        )

    # 3. Year-aligned negative-control: Y_{t-2} adjusted for (t-2) weather, crops, <=t-3 anom
    lag_col = f"{outcome}_lag2"
    s_neg = _filter("prev_crop", (lag_col, "precip_lag2", "tmax_lag2", *STATIC_CONFOUNDERS))
    d_neg = (s_neg["prev_crop"] == treated).to_numpy(dtype=float)
    if (
        int(d_neg.sum()) >= need
        and int(len(s_neg) - d_neg.sum()) >= need
        and s_neg["block"].nunique() >= MIN_BLOCKS
    ):
        x_neg = design_negctrl(s_neg, outcome)
        n_fit = fit_aow(x_neg, s_neg[lag_col].to_numpy(), d_neg, s_neg["block"].to_numpy(), seed)
        neg_pass = not (n_fit["ci_low"] > 0.0 or n_fit["ci_high"] < 0.0)
        row.update(
            negctrl_effect=n_fit["effect"],
            negctrl_ci_low=n_fit["ci_low"],
            negctrl_ci_high=n_fit["ci_high"],
            negctrl_n=len(s_neg),
            negctrl_status="pass" if neg_pass else "fail",
        )

    checks = [
        row["overlap_status"],
        row["balance_status"],
        row["placebo_status"],
        row["negctrl_status"],
    ]
    row["n_failed"] = sum(c == "fail" for c in checks)
    row["n_untested"] = sum(c == "untested" for c in checks)
    row["show_as_evidence"] = row["n_failed"] == 0 and row["n_untested"] == 0
    return row


def run_all(
    df: pd.DataFrame,
    extra_rows: pd.DataFrame | None = None,
    match_prev2: bool = False,
    seed: int = SEED,
) -> pd.DataFrame:
    """Run Panel-OBDML + all 4 diagnostics across pooled or prev2-matched contrasts."""
    df_hist = add_panel_history(df, extra_rows=extra_rows)
    rows: list[dict] = []
    if match_prev2:
        contrasts = matching_contrast_list(df)
        for crop, prev2, a, b in contrasts:
            for outcome in OUTCOMES:
                for stratum in ("all", "wet", "dry"):
                    rows.append(
                        fit_and_diagnose_contrast(
                            df_hist,
                            crop,
                            a,
                            b,
                            outcome,
                            stratum,
                            prev2_crop=prev2,
                            seed=seed,
                        )
                    )
    else:
        contrasts = contrast_list(df)
        for crop, a, b in contrasts:
            for outcome in OUTCOMES:
                for stratum in ("all", "wet", "dry"):
                    rows.append(
                        fit_and_diagnose_contrast(
                            df_hist,
                            crop,
                            a,
                            b,
                            outcome,
                            stratum,
                            prev2_crop=None,
                            seed=seed,
                        )
                    )
    return pd.DataFrame(rows)
