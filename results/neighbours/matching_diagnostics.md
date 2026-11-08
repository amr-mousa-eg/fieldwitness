# T5.xa Matching-history neighbour design diagnostics (Kansas pilot fields)

Source: `scripts/t5xa_matching.py` -> `matching_effects.csv`,
`matching_diagnostics.csv`; code `src/fieldwitness/neighbours/matching.py`.
Design: Secondary analysis conditioning on identical two-year crop history
(`prev2_crop`) to eliminate the two-year rotation imbalance identified in T5.3.
DoubleML PLR fitted with numeric confounders (soil, topography, climate,
field size, year) using spatial block cross-fitting (10 km blocks).
Thresholds are identical to T5.3 (tag A, UNVERIFIED rules of thumb, not tuned):
propensity range [0.05, 0.95], max share outside 10%, max weighted SMD <= 0.25.

## Results Summary

- Total contrast rows: 72; **32 fitted** across 6 pairs.
- Contrasts whose 95% CI excludes 0: **10**.
- Contrasts passing all four checks: **0 shown as evidence**.

### Check-by-check breakdown (fitted contrasts)

- **Overlap:** {'pass': 32}
- **Balance:** {'fail': 24, 'pass': 8}
- **Placebo (next_crop):** {'untested': 20, 'pass': 7, 'fail': 5}
- **Negative control (lag2):** {'pass': 23, 'fail': 5, 'untested': 4}

## Comparison with T5.3 (Unconditional Precrop)

| Metric | T5.3 Unconditional | T5.xa Matching History |
| :--- | :--- | :--- |
| Fitted contrasts | 92 | 32 |
| Overlap pass rate | 65.2% (60/92) | 100.0% (32/32) |
| Balance pass rate (SMD <= 0.25) | 0.0% (0/92) | 25.0% (8/32) |
| CI excludes 0 | 20 | 10 |
| Shown as evidence | 0 | 0 |

## Why evidence remains 0

Matching on `prev2_crop` successfully resolves the structural covariate balance
failure on rotation history (SMD dropped substantially; 8 contrasts pass balance
with smd_weighted_max <= 0.25, and all 32 pass overlap).
However, none of the 8 balance-passing contrasts passes all four checks:
- Placebo check (`next_crop`) either fails (future crop predicts current outcome,
  indicating persistent field unobservables) or is untested due to small sample size.
- Negative-control outcome (`outcome_lag2`) similarly fails or is untested.

## Consequence for FieldWitness

The T5.3 primary negative result remains unchanged: **neighbour witness stays OFF**.
T5.xa serves as a documented, honest secondary analysis confirming that while
conditioning on history fixes rotation balance, pilot-scale sample size and
unobserved field-level confounding prevent causal claims from satisfying our
preregistered evidence criteria.