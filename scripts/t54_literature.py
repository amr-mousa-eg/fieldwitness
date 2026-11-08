"""T5.4: sign check of our Kansas previous-crop contrasts against published US findings.

Sources (opened 2026-11-08, see DECISIONS.md):
- Kluger, Di Tommaso & Lobell, "Precrop Payoffs: Causal machine learning reveals large but
  variable yield benefits of crop rotation in major breadbaskets", arXiv:2506.02384v2
  (14 Oct 2025; Environ. Res. Lett. 20 (2025) 114037), Table S9, column Eff_2-year, US rows.
  Effect of precrop A on crop B vs B after B, in % of mean US yield of B; stars = p < 0.05.
- NASA Earth Observatory, "How to Rotate Crops", A. Voiland, 28 Jul 2025,
  https://science.nasa.gov/earth/earth-observatory/how-to-rotate-crops-154601/
  (reports the same study: corn after winter wheat +0.9 %, soybean -> winter wheat about -12 %).

Only transitions among maize, winter wheat, sorghum and fallow (our Kansas crops) are compared.
Their outcome is a yield proxy (peak GCVI calibrated to yield); ours are canopy and season
outcomes from HLS NDVI. A sign match is not a yield claim.

Output: results/neighbours/literature_check.md
"""

from pathlib import Path

import pandas as pd

EFFECTS = Path("results/neighbours/effects.csv")
DIAG = Path("results/neighbours/diagnostics.csv")
OUT = Path("results/neighbours/literature_check.md")

# Table S9 (Eff_2-year), US rows used here: (treatment, control) -> effect in % of mean yield.
LIT = {
    ("fallow", "winter_wheat", "winter_wheat"): 8.3,  # F->WW vs WW->WW, n 84,845 / 151,613
    ("maize", "winter_wheat", "winter_wheat"): 4.0,  # C->WW vs WW->WW, n 22,417 / 151,613
    ("winter_wheat", "maize", "maize"): 0.9,  # WW->C vs C->C,   n 61,653 / 432,622
}

# Our contrast (crop, treated_prev, reference_prev) -> expected sign and how it is derived
# from LIT. Our effect = outcome after treated_prev minus outcome after reference_prev.
MAP = {
    ("winter_wheat", "fallow", "winter_wheat"): (+1, "F->WW +8.3 % (direct)"),
    ("winter_wheat", "maize", "winter_wheat"): (+1, "C->WW +4.0 % (direct)"),
    ("winter_wheat", "fallow", "maize"): (
        +1,
        "F->WW +8.3 % minus C->WW +4.0 % = +4.3 % "
        "(indirect, difference of two estimates, untested)",
    ),
    ("maize", "maize", "winter_wheat"): (
        -1,
        "WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct)",
    ),
}

HEADER = (
    "| crop | contrast (ours) | literature | outcome | stratum | n treated/ref | "
    "effect [95% CI] | expected sign | verdict | evidence (T5.3) |\n"
    "|---|---|---|---|---|---|---|---|---|---|"
)

# Outcomes where a higher value is the yield-like direction. canopy_drop is reversed (a larger
# drop is worse), so its expected sign is flipped.
OUTCOMES = {"peak_ndvi": +1, "canopy_integral": +1, "cover_days": +1, "canopy_drop": -1}


def verdict(effect: float, lo: float, hi: float, expected: int) -> str:
    if pd.isna(effect):
        return "not fitted"
    if lo > 0 or hi < 0:
        return "agree" if (effect > 0) == (expected > 0) else "DISAGREE"
    same = (effect > 0) == (expected > 0)
    return "inconclusive (CI includes 0), sign " + ("same" if same else "opposite")


def main() -> None:
    eff = pd.read_csv(EFFECTS)
    diag = pd.read_csv(DIAG)[
        ["crop", "treated_prev", "reference_prev", "outcome", "stratum", "show_as_evidence"]
    ]
    keys = ["crop", "treated_prev", "reference_prev", "outcome", "stratum"]
    df = eff.merge(diag, on=keys, how="left")

    rows, counts = [], {}
    for (crop, tr, ref), (sign, how) in MAP.items():
        for outcome, osign in OUTCOMES.items():
            for stratum in ("all", "wet", "dry"):
                r = df[
                    (df.crop == crop)
                    & (df.treated_prev == tr)
                    & (df.reference_prev == ref)
                    & (df.outcome == outcome)
                    & (df.stratum == stratum)
                ]
                if r.empty:
                    continue
                r = r.iloc[0]
                v = verdict(r.effect, r.ci_low, r.ci_high, sign * osign)
                kind = "not fitted" if v == "not fitted" else v.split(" ")[0]
                counts[(stratum, kind)] = counts.get((stratum, kind), 0) + 1
                ci = ""
                if not pd.isna(r.effect):
                    ci = f"{r.effect:.3g} [{r.ci_low:.3g}, {r.ci_high:.3g}]"
                rows.append(
                    f"| {crop} | {tr} vs {ref} | {how} | {outcome} | {stratum} | "
                    f"{int(r.n_treated)}/{int(r.n_reference)} | {ci} | "
                    f"{'+' if sign * osign > 0 else '-'} | {v} | {bool(r.show_as_evidence)} |"
                )

    not_compared = sorted(
        {
            f"{c}: {t} vs {r}"
            for c, t, r in eff[["crop", "treated_prev", "reference_prev"]].itertuples(index=False)
            if (c, t, r) not in MAP
        }
    )
    summary = "\n".join(
        f"- {s}: " + ", ".join(f"{v} {n}" for (s2, v), n in sorted(counts.items()) if s2 == s)
        for s in ("all", "wet", "dry")
    )
    text = f"""# T5.4 literature check: signs of previous-crop effects (Kansas pilot fields)

Source: `scripts/t54_literature.py` (reads `effects.csv`, `diagnostics.csv`).

## Sources

- Kluger, Di Tommaso & Lobell, *Precrop Payoffs: Causal machine learning reveals large but
  variable yield benefits of crop rotation in major breadbaskets*, arXiv:2506.02384v2 (14 Oct 2025),
  Environ. Res. Lett. 20 (2025) 114037. Table S9, column Eff_2-year, US rows (precrop A on crop B
  vs B after B, % of mean US yield of B, all significant at p < 0.05). v1 (3 Jun 2025) was titled
  *Evaluating crop rotations around the world using satellite imagery and causal machine learning*.
- NASA Earth Observatory, *How to Rotate Crops* (A. Voiland, 28 Jul 2025),
  <https://science.nasa.gov/earth/earth-observatory/how-to-rotate-crops-154601/>.
  It reports the same study (corn after winter wheat +0.9 %, soybean then winter wheat about
  -12 %, rotation helps more in rainier conditions). It does not mention sorghum or fallow.

Values were read from the arXiv HTML through a page-reading tool, twice, and the two corn rows match
the NASA article. They were not checked against the PDF.

## What is compared, and the caveats

- Only transitions among maize, winter wheat, sorghum and fallow (our Kansas crops). The paper
  has no sorghum and no fallow outcome; US rows used: F->WW +8.3 %, C->WW +4.0 %, WW->C +0.9 %.
- **Their outcome is yield** (a peak-GCVI proxy calibrated to county yields). **Ours are canopy
  and season outcomes** from HLS NDVI (peak NDVI, canopy integral, cover days, canopy drop).
  Peak NDVI is the closest analogue. A sign match is not a yield claim.
- Their control is the outcome crop after itself. Ours is a named reference previous crop; the
  F vs C contrast on wheat is an indirect comparison (difference of two published estimates).
- Their scope is US-wide (CDL masks, 2009-2021); ours is 200 fields in one HLS tile
  (T14SLH, Kansas).
- **None of our contrasts passes the T5.3 diagnostics** (`show_as_evidence` is False for all),
  so any agreement below is descriptive only and does not enter grading.
- Expected sign for `canopy_drop` is flipped (a larger drop is the worse direction).

## Summary (counts per stratum)

{summary}

## Comparisons

{HEADER}
{chr(10).join(rows)}

## Not compared (no literature counterpart among our crops)

{chr(10).join(f"- {x}" for x in not_compared)}
"""
    OUT.write_text(text, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
