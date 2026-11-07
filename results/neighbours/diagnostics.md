# T5.3 diagnostics of the previous-crop contrasts (Kansas pilot fields)

Source: `scripts/t53_diagnostics.py` -> `diagnostics.csv`; code `src/fieldwitness/neighbours/diagnostics.py`.
Thresholds are team choices (tag A, UNVERIFIED rules of thumb), fixed before the run and not tuned:
propensity range [0.05, 0.95], at most 10 % of rows outside it, max weighted SMD <= 0.25.

## Result (negative)

- 92 contrasts fitted; **0 pass all four checks, so none is shown as evidence.**
- Placebo (next season's crop): 50 pass, 6 fail, 36 untested (too few rows).
- Negative-control outcome (same field, 2 seasons earlier): 23 pass, 5 fail, 64 untested.
- Overlap: 60 pass, 32 fail.
- Balance: **all 92 fail** (median raw max SMD 1.21, after weighting 0.97).
- Of the 20 contrasts whose CI excludes 0: none passes. 11 have an untested check, the rest fail one.

## Why balance fails

The imbalance is structural, not noise. In one example (sorghum after winter wheat vs after sorghum)
the largest SMDs are the crop two years back: fallow 2.08, sorghum 0.95, winter wheat 0.72. The
previous crop largely fixes the one before it (e.g. wheat-fallow), so the arms are different
rotation histories and propensity weighting cannot make them comparable. Other covariates
(climate, soil, position) have SMD 0.0-0.4.

## Consequence

The T5.2 effects are **not evidence**. The neighbour witness stays off in grading until a design
with real overlap exists (more fields/regions, or contrasts restricted to matching two-year
histories). Not tried here: it would be tuning after seeing the result.
