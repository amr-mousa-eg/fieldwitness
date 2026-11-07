"""T5.3 diagnostics for the previous-crop contrasts of T5.2.

Four checks per fitted contrast (same sample, learners and spatial folds as `dml.fit_contrast`):
1. Placebo: treatment = the crop grown the NEXT season (cannot cause this season's outcome).
   Fails if its 95 % CI excludes 0.
2. Negative-control outcome: the same field's outcome two seasons earlier (before the treatment
   season; the crop of that season is among the confounders). Fails if the CI excludes 0.
3. Overlap: cross-fitted propensity P(D=1|X). Fails if more than OVERLAP_MAX_SHARE of rows lie
   outside [PS_LOW, PS_HIGH].
4. Balance: standardised mean difference (SMD) of every confounder after inverse-propensity
   weighting (propensity clipped to the same range). Fails if max |SMD| > SMD_MAX.
A check that cannot be run (too few rows) is "untested". A contrast is shown as evidence only
if all four pass. Thresholds are team choices (tag A, UNVERIFIED rules of thumb, not tuned).
With ~90 contrasts, a few placebo/control failures are expected by chance (5 % level).
"""

import numpy as np
import pandas as pd

from fieldwitness.neighbours.dml import CONFOUNDERS, MIN_ARM, MIN_BLOCKS, design, fit_plr

PS_LOW, PS_HIGH = 0.05, 0.95
OVERLAP_MAX_SHARE = 0.10
SMD_MAX = 0.25


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add `next_crop` (crop of year+1) and `<outcome>_lag2` (outcome of year-2), same field."""
    out = df.copy()
    key = out[["field_id", "year"]]
    look = out.set_index(["field_id", "year"])
    nxt = pd.MultiIndex.from_arrays([key["field_id"], key["year"] + 1])
    out["next_crop"] = look["crop"].reindex(nxt).to_numpy()
    lag = pd.MultiIndex.from_arrays([key["field_id"], key["year"] - 2])
    for col in ("canopy_integral", "peak_ndvi", "cover_days", "canopy_drop"):
        out[f"{col}_lag2"] = look[col].reindex(lag).to_numpy()
    return out


def _sample(df, crop, treated, ref, stratum, arm_col, outcome):
    s = df[(df["crop"] == crop) & df[arm_col].isin([treated, ref])]
    if stratum != "all":
        s = s[s["dry_season"] == (stratum == "dry")]
    return s.dropna(subset=[outcome, *CONFOUNDERS]).reset_index(drop=True)


def _fit(s, outcome, arm_col, treated, stratum):
    """Returns (plr, d) or (None, d) when the sample is too small."""
    d = (s[arm_col] == treated).astype(float)
    need = MIN_ARM[stratum]
    n1 = int(d.sum())
    if n1 < need or len(s) - n1 < need or s["block"].nunique() < MIN_BLOCKS:
        return None, d
    x = design(s)
    data = pd.concat([x, s[outcome].rename("y"), d.rename("d")], axis=1)
    return fit_plr(data, x.columns, s["block"].to_numpy()), d


def _ci_check(plr) -> dict:
    ci = plr.confint(level=0.95)
    lo, hi = float(ci.iloc[0, 0]), float(ci.iloc[0, 1])
    return {
        "effect": float(plr.coef[0]),
        "ci_low": lo,
        "ci_high": hi,
        "status": "fail" if (lo > 0 or hi < 0) else "pass",
    }


def balance_smd(x: pd.DataFrame, d: np.ndarray, w: np.ndarray | None = None) -> float:
    """Max absolute SMD over columns; weighted if `w` is given. Pooled SD is unweighted."""
    d = np.asarray(d) == 1
    w = np.ones(len(d)) if w is None else np.asarray(w, dtype=float)
    worst = 0.0
    for c in x.columns:
        v = x[c].to_numpy(dtype=float)
        sd = np.sqrt((v[d].var(ddof=1) + v[~d].var(ddof=1)) / 2) if d.sum() > 1 else 0.0
        if sd == 0 or not np.isfinite(sd):
            continue
        m1 = np.average(v[d], weights=w[d])
        m0 = np.average(v[~d], weights=w[~d])
        worst = max(worst, abs(m1 - m0) / sd)
    return float(worst)


def overlap_balance(plr, s: pd.DataFrame, d: pd.Series) -> dict:
    ps = np.asarray(plr.predictions["ml_m"])[:, 0, 0]
    share_out = float(np.mean((ps < PS_LOW) | (ps > PS_HIGH)))
    pc = np.clip(ps, PS_LOW, PS_HIGH)
    w = np.where(d.to_numpy() == 1, 1 / pc, 1 / (1 - pc))
    x = design(s)
    raw, wtd = balance_smd(x, d.to_numpy()), balance_smd(x, d.to_numpy(), w)
    return {
        "ps_min": float(ps.min()),
        "ps_max": float(ps.max()),
        "share_outside": share_out,
        "overlap_status": "pass" if share_out <= OVERLAP_MAX_SHARE else "fail",
        "smd_raw_max": raw,
        "smd_weighted_max": wtd,
        "balance_status": "pass" if wtd <= SMD_MAX else "fail",
    }


def diagnose_row(df: pd.DataFrame, r: pd.Series) -> dict:
    """Diagnostics for one fitted row of effects.csv. `df` must come from `add_lags`."""
    crop, a, b, y, st = (
        r["crop"],
        r["treated_prev"],
        r["reference_prev"],
        r["outcome"],
        r["stratum"],
    )
    out = {"overlap_status": "untested", "balance_status": "untested"}
    # main fit -> overlap and balance
    s = _sample(df, crop, a, b, st, "prev_crop", y)
    plr, d = _fit(s, y, "prev_crop", a, st)
    if plr is not None:
        out.update(overlap_balance(plr, s, d))
    # placebo: next season's crop as treatment
    s = _sample(df, crop, a, b, st, "next_crop", y)
    plr, _ = _fit(s, y, "next_crop", a, st)
    out["placebo_status"] = "untested"
    if plr is not None:
        c = _ci_check(plr)
        out.update(
            placebo_effect=c["effect"],
            placebo_ci_low=c["ci_low"],
            placebo_ci_high=c["ci_high"],
            placebo_status=c["status"],
            placebo_n=len(s),
        )
    # negative-control outcome: same field two seasons earlier
    lag = f"{y}_lag2"
    s = _sample(df, crop, a, b, st, "prev_crop", lag)
    plr, _ = _fit(s, lag, "prev_crop", a, st)
    out["negctrl_status"] = "untested"
    if plr is not None:
        c = _ci_check(plr)
        out.update(
            negctrl_effect=c["effect"],
            negctrl_ci_low=c["ci_low"],
            negctrl_ci_high=c["ci_high"],
            negctrl_status=c["status"],
            negctrl_n=len(s),
        )
    checks = [
        out[k] for k in ("placebo_status", "negctrl_status", "overlap_status", "balance_status")
    ]
    out["n_failed"] = sum(c == "fail" for c in checks)
    out["n_untested"] = sum(c == "untested" for c in checks)
    out["show_as_evidence"] = out["n_failed"] == 0 and out["n_untested"] == 0
    return out


def run_diagnostics(df: pd.DataFrame, effects: pd.DataFrame) -> pd.DataFrame:
    """Merge diagnostics onto the fitted rows of effects; unfitted rows are never evidence."""
    d2 = add_lags(df)
    keys = ["crop", "treated_prev", "reference_prev", "outcome", "stratum"]
    rows = []
    for _, r in effects.iterrows():
        if np.isnan(r["effect"]):
            rows.append({"show_as_evidence": False, "n_failed": 0, "n_untested": 4})
        else:
            rows.append(diagnose_row(d2, r))
    return pd.concat([effects[keys + ["effect", "ci_low", "ci_high"]], pd.DataFrame(rows)], axis=1)
