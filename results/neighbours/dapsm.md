# Experiment 1 — distance-adjusted propensity score matching (DAPSM): negative result

Pre-registered in `DECISIONS.md` (2026-11-12, "Pre-registration: two algorithm experiments", commit `c6b82f7`) before any run.
Source: `scripts/x1_dapsm.py`, code `src/fieldwitness/neighbours/dapsm.py`, tests `tests/test_dapsm.py`.
Outputs: `dapsm.json` (summary), `dapsm_contrasts.csv` (every contrast row, old and new checks), `dapsm_w_grid.csv` (every contrast × every w), `field_centroids.csv`, `field_distance_km.npy`.
All statistics tag D. Thresholds are the T5.3 team choices (tag A, UNVERIFIED), not tuned.

## Setup

- Seasons used: 2018–2021 only (800 field-seasons; cut-off 2021-12-31). `dry_season` recomputed from each field's seasons ≤ 2021.
- Geometry: pilot field polygons (`data/fields/ks_t14slh_pilot.parquet`, CSB boundaries, WGS 84). Centroids computed in UTM 14N (EPSG:32614). Haversine distance matrix 200 × 200, Earth radius 6,371.0088 km (tag E).
- Distance scaling (fixed beforehand): divide by the largest pairwise centroid distance, 145.31 km (D).
- Design kept from T5.xa: same contrasts rule, confounders, outcomes, strata, propensity model (`fit_plr`, spatial block folds).

## Result

**Only 1 contrast pair has enough rows with data ≤ 2021**: maize after maize vs maize after winter wheat, with maize two seasons back (`prev2_crop` = maize). That gives 12 contrast rows (4 outcomes × 3 strata). The 8 wet/dry rows have 21 rows each, so at least one arm has fewer than the 15-row minimum, so they are not fitted. **4 rows fitted** (stratum "all", n = 42).

### Full w grid (median over the 4 fitted rows of the max |SMD| after matching)

| w | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| max \|SMD\| | **0.535** | 0.661 | 0.570 | 0.590 | 0.590 | 0.621 | 0.688 | 0.815 | 0.761 | 0.786 | 0.855 |
| pass (≤ 0.25) | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |

The 4 rows share one sample (same arms and confounders), so their balance values are equal. Chosen w by the pre-registered rule: **w = 0.0** (pure distance matching). The worst covariate is soil clay % at every row.

### Four diagnostics at w = 0.0, next to the old IPW double-ML design on the same rows

| Check | Old IPW (same ≤ 2021 rows) | DAPSM w = 0 | Old T5.xa as published (all years 2018–2024) |
|---|---|---|---|
| Overlap | 4 pass / 0 fail (Wilson 95 % 51–100 %) | 4 pass / 0 fail (51–100 %) | 32 / 0 |
| Balance (max \|SMD\| ≤ 0.25) | 0 pass / 4 fail (0–49 %); max \|SMD\| 0.47 | 0 pass / 4 fail (0–49 %); max \|SMD\| 0.54 | 8 / 24 |
| Placebo (next season's crop) | 4 untested | 4 untested | 7 / 5, 20 untested |
| Negative control (outcome 2 seasons earlier) | 4 untested | 4 untested | 23 / 5, 4 untested |
| Shown as evidence | **0** | **0** | **0** |

Why placebo and negative control are untested: the 2021 rows have no next-season crop before the cut-off, and the lag-2 outcome needs a season two years earlier, which exists only for 2020–2021 rows. Both samples fall below 15 rows per arm.

Matched effects (treated minus matched reference, 95 % block-bootstrap CI), for information only, not evidence: canopy integral −8.7 (−16.7 to 0.3), peak NDVI −0.05 (−0.11 to −0.01), cover days −11.0 (−20.8 to −1.7), canopy drop −0.07 (−0.11 to −0.02).

## Verdict

- **H1 not supported.** Balance passes in 0 of 4 rows under DAPSM and 0 of 4 under the old IPW design. On these rows distance matching is *worse* than IPW (max |SMD| 0.54 vs 0.47). Clay is the leading imbalance: nearby fields do not share the soil difference between the two arms.
- **Failed checks: balance (4 of 4). Placebo and negative control could not be run (too few rows before the cut-off).** No contrast passes all four checks.
- **The neighbour witness stays OFF.** `config/grading.yaml` and the app are not changed.
- The cut-off removes most of the old design's sample: 32 fitted rows with 2018–2024 data, 4 with 2018–2021. A neighbour design that obeys the cut-off needs more regions or more pre-2022 seasons, not a different matching rule. Not tried here: that would be a new design, and it would need its own pre-registration.
