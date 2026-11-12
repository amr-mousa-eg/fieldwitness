# Reliability tiers: the one test on 2022–2024 (result: not shown)

Pre-registered in `DECISIONS.md` (commit `c28cf32`). Model and tier boundaries were frozen from the 2019–2021 pseudo-forecasts only (commit `52b95de`) before this test ran.

- Metric: forecast-mode canopy-integral CRPS (lower is better), n = 463.
- 95 % CI: spatial block bootstrap (10 km blocks, 1,000 resamples, seed 42).
- Tags: D (model) vs O (HLS).
- R1–R4 are relative reliability tiers. They are **not** evidence grades, and they do not use the neighbour witness.

Sources: `results.json`, `breakdowns.json`, `cv_results.csv`, `model_and_tiers.json`.

## Training (2019–2021 seasons, cut-offs 2018–2020)

- Rows: 428 field-seasons: maize 127 (84 fields), sorghum 134 (107 fields), winter wheat 167 (145 fields).
- Leave-one-block-out CV loss (MSE of log scaled CRPS ± SE):

| Model | CV loss |
|---|---|
| null | 1.201 ± 0.065 |
| **crop** | **1.083 ± 0.061** |
| grade | 1.204 ± 0.065 |
| credibility | 1.187 ± 0.065 |
| gbm | 1.136 ± 0.066 |

- **Chosen: crop only.** It has the best loss outright, so it is also the simplest model within one SE.
- Frozen boundaries (log scaled CRPS): −2.584, −1.859, −1.788.
- The crop model gives only 3 distinct predictions, so R4 is empty by construction.

## Test by tier (2022–2024)

| Tier | n | Mean CRPS [95 % CI] | Crop in tier |
|---|---|---|---|
| R1 | 142 | 12.41 [10.13, 14.66] | all sorghum |
| R2 | 124 | 17.68 [15.13, 20.33] | all maize |
| R3 | 197 | 21.15 [18.67, 23.62] | all winter wheat |
| R4 | 0 | empty | — |
| Current grade B | 170 | 16.96 [15.07, 18.95] | |
| Current grade C | 268 | 17.30 [15.28, 19.56] | |
| Current grade D | 25 | 24.02 [14.04, 31.25] | |

Mean absolute peak-timing error by tier (secondary target): R1 16.2 d, R2 14.9 d, R3 58.9 d.

## Gate

| Condition | Result |
|---|---|
| (i) R1 < R2 < R3 < R4 | **fail** (R4 empty; R1 < R2 < R3 holds) |
| (ii) CI of R4 − R1 excludes 0 | **fail** (R4 empty, not computable) |
| (iii) Spearman CI excludes 0 | pass: ρ 0.212 [0.113, 0.306] |
| (iv) gbm beats crop and grade | **fail**: ρ(gbm) − ρ(crop) −0.043 [−0.119, 0.036]; ρ(gbm) − ρ(grade) +0.144 [0.021, 0.274] |
| **Verdict** | **not shown** |

Test Spearman for every model: null 0, crop 0.212 [0.113, 0.306], grade 0.025 [−0.068, 0.110], credibility 0.019 [−0.064, 0.097], gbm 0.169 [0.067, 0.275].

## Stability

- **By crop (inside one crop the chosen tiers are constant).** gbm ρ: maize 0.033 [−0.153, 0.223], sorghum −0.046 [−0.204, 0.105], winter wheat 0.028 [−0.131, 0.175]. Nothing ranks fields within a crop.
- **By year:**

| Year | R1 / R2 / R3 mean CRPS | Spearman |
|---|---|---|
| 2022 | 13.07 / 18.41 / 24.36 | 0.233 [0.058, 0.388] |
| 2023 | 10.84 / 13.91 / 24.78 | 0.440 [0.281, 0.575] |
| 2024 | 12.75 / 19.57 / 16.97 (R3 below R2) | 0.072 [−0.068, 0.214] |

## Honesty checks

- **How much is just crop:** all of it. The chosen tiers *are* the crop. Crop-only tiers and the chosen tiers are identical.
- **Error level shift:** mean CRPS was 11.74 in the training seasons and 17.54 in the test years. By crop, training → test: maize 12.80 → 17.68, sorghum 6.50 → 12.41, winter wheat 15.13 → 21.15. Any tier is relative reliability, not a promised error size.
- **Grade reproduction check:** grades recomputed at the 2021 cut-off give B 170, C 268, D 25, the same as `grade_validity.json`.
