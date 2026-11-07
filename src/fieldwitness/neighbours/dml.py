"""T5.2 double machine learning for previous-crop effects (partially linear model).

Model: Y = theta * D + g(X) + e, D = m(X) + v (Chernozhukov et al. 2018, partialling-out score),
fitted with `doubleml.DoubleMLPLR` (API checked in docs/api_notes.md). D = 1 if the previous crop
is the treated crop, 0 if it is the reference crop; the sample is restricted to the two arms.
theta is the average change of the outcome (NDVI-based, tag D) caused by the previous crop, given
the confounders.
Nuisance learners: random forests (team choice, tag A, UNVERIFIED hyper-parameters, not tuned).
Cross-fitting folds are spatial blocks (CLAUDE.md rule 7): whole 10 km blocks are held out together
(GroupKFold on the `block` column), so neighbouring fields never sit in train and test at once.
"""

from itertools import permutations

import numpy as np
import pandas as pd
from doubleml import DoubleMLData, DoubleMLPLR
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import GroupKFold

SEED = 20261114
OUTCOMES = ("canopy_integral", "peak_ndvi", "cover_days", "canopy_drop")
CONFOUNDERS = (
    "area_ha",
    "lon",
    "lat",
    "clay_pct",
    "sand_pct",
    "soc_g_kg",
    "season_precip_mm",
    "season_tmax_c",
    "year",
)
MIN_ARM = {"all": 30, "wet": 20, "dry": 20}
MIN_BLOCKS = 5


def design(df: pd.DataFrame) -> pd.DataFrame:
    """Confounder matrix: numeric columns plus one-hot of the crop two years back."""
    x = df[list(CONFOUNDERS)].astype(float).copy()
    prev2 = df["prev2_crop"].fillna("unknown")
    for level in ("winter_wheat", "maize", "sorghum", "fallow", "unknown"):
        x[f"prev2_{level}"] = (prev2 == level).astype(float)
    return x


def contrast_list(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """(outcome crop, treated previous crop, reference previous crop) with enough rows per arm."""
    out = []
    for crop, g in df.groupby("crop"):
        counts = g["prev_crop"].value_counts()
        for a, b in permutations(counts.index, 2):
            if counts[a] >= MIN_ARM["all"] and counts[b] >= MIN_ARM["all"] and a < b:
                out.append((crop, a, b))
    return out


def fit_contrast(
    df: pd.DataFrame, crop: str, treated: str, ref: str, outcome: str, stratum: str
) -> dict:
    """One DoubleML PLR fit. Returns a result row (effect NaN with a `note` when skipped)."""
    s = df[(df["crop"] == crop) & df["prev_crop"].isin([treated, ref])].copy()
    if stratum != "all":
        s = s[s["dry_season"] == (stratum == "dry")]
    s = s.dropna(subset=[outcome, *CONFOUNDERS])
    d = (s["prev_crop"] == treated).astype(float)
    row = {
        "crop": crop,
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
    need = MIN_ARM[stratum]
    if row["n_treated"] < need or row["n_reference"] < need or row["n_blocks"] < MIN_BLOCKS:
        row["note"] = "too few rows or blocks"
        return row
    x = design(s).reset_index(drop=True)
    data = pd.concat(
        [x, pd.Series(s[outcome].to_numpy(), name="y"), d.reset_index(drop=True).rename("d")],
        axis=1,
    )
    groups = s["block"].to_numpy()
    n_folds = min(5, row["n_blocks"])
    folds = list(GroupKFold(n_splits=n_folds).split(x, groups=groups))
    obj = DoubleMLData(data, y_col="y", d_cols="d", x_cols=list(x.columns))
    ml_l = RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=SEED, n_jobs=1)
    ml_m = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=SEED, n_jobs=1)
    plr = DoubleMLPLR(obj, ml_l, ml_m, n_folds=n_folds, draw_sample_splitting=False)
    plr.set_sample_splitting([folds])
    plr.fit()
    ci = plr.confint(level=0.95)
    row.update(
        effect=float(plr.coef[0]),
        se=float(plr.se[0]),
        ci_low=float(ci.iloc[0, 0]),
        ci_high=float(ci.iloc[0, 1]),
    )
    return row


def run_all(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for crop, a, b in contrast_list(df):
        for outcome in OUTCOMES:
            for stratum in ("all", "wet", "dry"):
                rows.append(fit_contrast(df, crop, a, b, outcome, stratum))
    return pd.DataFrame(rows)
