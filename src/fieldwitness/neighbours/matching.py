"""T5.xa matching-history neighbour design (Kansas pilot fields).

Secondary analysis addressing the structural balance failure of T5.3:
conditioning on identical previous-2-year crop (`prev2_crop`) eliminates the
rotation-history imbalance by construction on that feature and restricts
comparisons to fields with identical two-year histories.

DoubleML PLR is fitted using the numeric confounders (soil, topography, climate, field size, year),
with spatial block cross-fitting (GroupKFold on `block`).
Diagnostics apply the four T5.3 checks:
1. Placebo: next season's crop as treatment (95% CI must include 0).
2. Negative control: same field's outcome 2 seasons earlier (95% CI must include 0).
3. Overlap: propensity clipping to [0.05, 0.95], share outside <= 0.10.
4. Balance: IPW-weighted standardised mean difference max |SMD| <= 0.25.
"""

from itertools import permutations

import numpy as np
import pandas as pd
from doubleml import DoubleMLPLR

from fieldwitness.neighbours.diagnostics import (
    OVERLAP_MAX_SHARE,
    PS_HIGH,
    PS_LOW,
    SMD_MAX,
    _ci_check,
    add_lags,
    balance_smd,
)
from fieldwitness.neighbours.dml import (
    CONFOUNDERS,
    MIN_BLOCKS,
    OUTCOMES,
    fit_plr,
)

MIN_ARM = 15


def matching_contrast_list(
    df: pd.DataFrame, min_arm: int = MIN_ARM
) -> list[tuple[str, str, str, str]]:
    """(crop, prev2_crop, treated_prev, ref_prev) with enough rows per arm on valid canopy data."""
    out = []
    valid = df.dropna(subset=["canopy_integral"])
    for (crop, prev2), g in valid.groupby(["crop", "prev2_crop"]):
        counts = g["prev_crop"].value_counts()
        for a, b in permutations(counts.index, 2):
            if counts[a] >= min_arm and counts[b] >= min_arm and a < b:
                out.append((str(crop), str(prev2), str(a), str(b)))
    return sorted(out)


def matching_design(df: pd.DataFrame) -> pd.DataFrame:
    """Confounder matrix: numeric columns only (prev2 is constant by construction)."""
    return df[list(CONFOUNDERS)].astype(float).copy()


def fit_matching_contrast(
    df: pd.DataFrame,
    crop: str,
    prev2: str,
    treated: str,
    ref: str,
    outcome: str,
    stratum: str,
    min_arm: int = MIN_ARM,
) -> tuple[dict, DoubleMLPLR | None]:
    """Fit DoubleML PLR for one matching contrast.

    Returns (result_dict, fitted_plr). Result dict has effect, SE, 95% CI
    (NaN with a `note` when skipped).
    """
    s = df[
        (df["crop"] == crop) & (df["prev2_crop"] == prev2) & df["prev_crop"].isin([treated, ref])
    ].copy()
    if stratum != "all":
        s = s[s["dry_season"] == (stratum == "dry")]
    s = s.dropna(subset=[outcome, *CONFOUNDERS])
    d = (s["prev_crop"] == treated).astype(float)
    row = {
        "crop": crop,
        "prev2_crop": prev2,
        "treated_prev": treated,
        "reference_prev": ref,
        "outcome": outcome,
        "stratum": stratum,
        "n": len(s),
        "n_treated": int(d.sum()),
        "n_reference": int(len(s) - d.sum()),
        "n_blocks": int(s["block"].nunique()),
        "outcome_sd": float(s[outcome].std()) if len(s) > 1 else np.nan,
        "effect": np.nan,
        "se": np.nan,
        "ci_low": np.nan,
        "ci_high": np.nan,
        "note": "",
        "tag": "D",
    }
    if row["n_treated"] < min_arm or row["n_reference"] < min_arm or row["n_blocks"] < MIN_BLOCKS:
        row["note"] = "too few rows or blocks"
        return row, None

    x = matching_design(s).reset_index(drop=True)
    data = pd.concat(
        [
            x,
            pd.Series(s[outcome].to_numpy(), name="y"),
            d.reset_index(drop=True).rename("d"),
        ],
        axis=1,
    )
    plr = fit_plr(data, x.columns, s["block"].to_numpy())
    ci = plr.confint(level=0.95)
    row.update(
        effect=float(plr.coef[0]),
        se=float(plr.se[0]),
        ci_low=float(ci.iloc[0, 0]),
        ci_high=float(ci.iloc[0, 1]),
    )
    return row, plr


def matching_overlap_balance(plr: DoubleMLPLR, s: pd.DataFrame, d: pd.Series) -> dict:
    """Overlap and weighted SMD balance on numeric confounders."""
    ps = np.asarray(plr.predictions["ml_m"])[:, 0, 0]
    share_out = float(np.mean((ps < PS_LOW) | (ps > PS_HIGH)))
    pc = np.clip(ps, PS_LOW, PS_HIGH)
    w = np.where(d.to_numpy() == 1, 1 / pc, 1 / (1 - pc))
    x = matching_design(s)
    raw = balance_smd(x, d.to_numpy())
    wtd = balance_smd(x, d.to_numpy(), w)
    return {
        "ps_min": float(ps.min()),
        "ps_max": float(ps.max()),
        "share_outside": share_out,
        "overlap_status": "pass" if share_out <= OVERLAP_MAX_SHARE else "fail",
        "smd_raw_max": raw,
        "smd_weighted_max": wtd,
        "balance_status": "pass" if wtd <= SMD_MAX else "fail",
    }


def diagnose_matching_contrast(
    df: pd.DataFrame,
    r: pd.Series | dict,
    min_arm: int = MIN_ARM,
    plr: DoubleMLPLR | None = None,
) -> dict:
    """Diagnostics for one matching contrast. `df` must come from `add_lags`."""
    crop = r["crop"]
    prev2 = r["prev2_crop"]
    a = r["treated_prev"]
    b = r["reference_prev"]
    y = r["outcome"]
    st = r["stratum"]

    out = {
        "overlap_status": "untested",
        "balance_status": "untested",
        "placebo_status": "untested",
        "negctrl_status": "untested",
        "n_failed": 0,
        "n_untested": 4,
        "show_as_evidence": False,
    }
    if pd.isna(r.get("effect", np.nan)):
        return out

    # 1 & 2: Overlap and Balance from main fit
    s = df[(df["crop"] == crop) & (df["prev2_crop"] == prev2) & df["prev_crop"].isin([a, b])]
    if st != "all":
        s = s[s["dry_season"] == (st == "dry")]
    s = s.dropna(subset=[y, *CONFOUNDERS]).reset_index(drop=True)
    d = (s["prev_crop"] == a).astype(float)
    if (
        int(d.sum()) >= min_arm
        and int(len(s) - d.sum()) >= min_arm
        and s["block"].nunique() >= MIN_BLOCKS
    ):
        if plr is None:
            x = matching_design(s).reset_index(drop=True)
            data = pd.concat([x, pd.Series(s[y].to_numpy(), name="y"), d.rename("d")], axis=1)
            plr = fit_plr(data, x.columns, s["block"].to_numpy())
        out.update(matching_overlap_balance(plr, s, d))

    # 3. Placebo: next season's crop as treatment
    s_p = df[(df["crop"] == crop) & (df["prev2_crop"] == prev2) & df["next_crop"].isin([a, b])]
    if st != "all":
        s_p = s_p[s_p["dry_season"] == (st == "dry")]
    s_p = s_p.dropna(subset=[y, *CONFOUNDERS]).reset_index(drop=True)
    d_p = (s_p["next_crop"] == a).astype(float)
    if (
        int(d_p.sum()) >= min_arm
        and int(len(s_p) - d_p.sum()) >= min_arm
        and s_p["block"].nunique() >= MIN_BLOCKS
    ):
        x_p = matching_design(s_p).reset_index(drop=True)
        data_p = pd.concat([x_p, pd.Series(s_p[y].to_numpy(), name="y"), d_p.rename("d")], axis=1)
        plr_p = fit_plr(data_p, x_p.columns, s_p["block"].to_numpy())
        c_p = _ci_check(plr_p)
        out.update(
            placebo_effect=c_p["effect"],
            placebo_ci_low=c_p["ci_low"],
            placebo_ci_high=c_p["ci_high"],
            placebo_status=c_p["status"],
            placebo_n=len(s_p),
        )

    # 4. Negative control: same field two seasons earlier
    lag_y = f"{y}_lag2"
    s_n = df[(df["crop"] == crop) & (df["prev2_crop"] == prev2) & df["prev_crop"].isin([a, b])]
    if st != "all":
        s_n = s_n[s_n["dry_season"] == (st == "dry")]
    s_n = s_n.dropna(subset=[lag_y, *CONFOUNDERS]).reset_index(drop=True)
    d_n = (s_n["prev_crop"] == a).astype(float)
    if (
        int(d_n.sum()) >= min_arm
        and int(len(s_n) - d_n.sum()) >= min_arm
        and s_n["block"].nunique() >= MIN_BLOCKS
    ):
        x_n = matching_design(s_n).reset_index(drop=True)
        data_n = pd.concat(
            [x_n, pd.Series(s_n[lag_y].to_numpy(), name="y"), d_n.rename("d")],
            axis=1,
        )
        plr_n = fit_plr(data_n, x_n.columns, s_n["block"].to_numpy())
        c_n = _ci_check(plr_n)
        out.update(
            negctrl_effect=c_n["effect"],
            negctrl_ci_low=c_n["ci_low"],
            negctrl_ci_high=c_n["ci_high"],
            negctrl_status=c_n["status"],
            negctrl_n=len(s_n),
        )

    checks = [
        out[k]
        for k in (
            "placebo_status",
            "negctrl_status",
            "overlap_status",
            "balance_status",
        )
    ]
    out["n_failed"] = sum(c == "fail" for c in checks)
    out["n_untested"] = sum(c == "untested" for c in checks)
    out["show_as_evidence"] = out["n_failed"] == 0 and out["n_untested"] == 0
    return out


def run_all_matching(df: pd.DataFrame, min_arm: int = MIN_ARM) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit all matching contrasts and run diagnostics.

    Returns (effects_df, diagnostics_df).
    """
    contrasts = matching_contrast_list(df, min_arm=min_arm)
    effect_rows = []
    diag_rows = []
    df_lags = add_lags(df)

    for crop, prev2, a, b in contrasts:
        for outcome in OUTCOMES:
            for stratum in ("all", "wet", "dry"):
                row, plr = fit_matching_contrast(
                    df,
                    crop,
                    prev2,
                    a,
                    b,
                    outcome,
                    stratum,
                    min_arm=min_arm,
                )
                effect_rows.append(row)
                diag = diagnose_matching_contrast(df_lags, row, min_arm=min_arm, plr=plr)
                diag_rows.append(diag)

    effects = pd.DataFrame(effect_rows)
    diag_df = pd.concat([effects, pd.DataFrame(diag_rows)], axis=1)
    return effects, diag_df
