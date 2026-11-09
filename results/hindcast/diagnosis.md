# Diagnostic Breakdown of Hindcast Skill (Kansas Pilot T14SLH)

**Pre-registered in `DECISIONS.md` (commit `e021f3e`) before execution.**
- Total scored field-seasons: 463 across 200 Kansas pilot fields (2022–2024).
- Grades and credibility evaluated under cut-off `as_of(2021-12-31)` (no circularity).
- Statistical inference: 1,000 spatial block bootstrap resamples (10 km grid), seed=42.
- Decision rule: Primary test requires 95% CI of paired difference to strictly exclude 0. Cell $n < 20$ reported as 'too few to judge'.

## 1. Primary Pre-Registered Test: Baseline Comparisons

| Subset | n | FieldWitness CRPS (95% CI) | Baseline B1 CRPS | Diff vs B1 (95% CI) | Beats B1? | Baseline B2 CRPS | Diff vs B2 (95% CI) | Beats B2? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall (paired sample)** | 266 | 14.86 [13.20, 16.71] | 16.10 | +1.23 [0.48, 1.99] | **YES** | 16.22 | +1.35 [0.74, 1.90] | **YES** |
| Crop: maize | 124 | 17.68 [15.22, 20.38] | 19.45 | +1.77 [0.73, 2.89] | YES | 19.71 | +2.03 [1.17, 2.87] | YES |
| Crop: sorghum | 142 | 12.41 [10.01, 14.73] | 13.17 | +0.77 [-0.10, 1.64] | NO | 13.16 | +0.76 [-0.06, 1.53] | NO |
| Crop: winter_wheat | 197 | 21.15 [18.78, 23.42] | — | *Baseline omitted in T7.3* | — | — | *Baseline omitted in T7.3* | — |
| Crop: fallow | 0 | *Too few to judge (n < 20)* | — | — | — | — | — | — |

## 2. Exploratory Dimension Breakdowns

All cell comparisons below are designated **exploratory** per pre-registration protocol.

| Dimension | Cell | n | FW CRPS (95% CI) | Peak Timing Abs Err (d) | 90% Canopy Coverage | Verdict vs B1 | Verdict vs B2 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| Crop | maize | 124 | 17.68 [15.22, 20.38] | 14.9 d [12.3, 18.2] | 27.4% [19.8%, 35.1%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Crop | sorghum | 142 | 12.41 [10.01, 14.73] | 16.2 d [13.5, 18.7] | 43.7% [35.5%, 53.3%] | comparable within uncertainty (CI spans 0) | comparable within uncertainty (CI spans 0) |
| Crop | winter_wheat | 197 | 21.15 [18.78, 23.42] | 58.9 d [52.2, 66.3] | 23.9% [18.4%, 29.9%] | not evaluated (no baseline) | not evaluated (no baseline) |
| Crop | fallow | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Year | 2022 | 134 | 18.46 [16.39, 20.51] | 37.7 d [30.9, 46.1] | 26.9% [20.0%, 33.9%] | comparable within uncertainty (CI spans 0) | FieldWitness beats baseline (CI > 0) |
| Year | 2023 | 129 | 18.24 [15.71, 20.94] | 29.9 d [22.4, 38.0] | 29.5% [21.5%, 37.1%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Year | 2024 | 200 | 16.47 [14.26, 18.90] | 34.3 d [30.9, 38.5] | 34.5% [27.9%, 41.3%] | FieldWitness beats baseline (CI > 0) | comparable within uncertainty (CI spans 0) |
| Field Size | <10 ha | 115 | 19.83 [16.26, 23.48] | 36.7 d [29.1, 44.8] | 28.7% [20.9%, 37.2%] | comparable within uncertainty (CI spans 0) | comparable within uncertainty (CI spans 0) |
| Field Size | 10-50 ha | 176 | 16.27 [14.20, 18.53] | 33.3 d [27.9, 39.8] | 31.8% [25.6%, 39.0%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Field Size | >50 ha | 172 | 17.30 [15.53, 19.39] | 33.0 d [26.9, 39.8] | 31.4% [24.2%, 38.6%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | B | 170 | 16.96 [15.04, 18.98] | 29.2 d [24.5, 34.5] | 32.4% [25.3%, 39.4%] | comparable within uncertainty (CI spans 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | C | 268 | 17.30 [15.37, 19.46] | 37.1 d [32.2, 42.6] | 30.6% [25.0%, 35.9%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | D | 25 | 24.02 [15.95, 30.41] | 34.4 d [23.5, 45.1] | 24.0% [7.1%, 47.4%] | comparable within uncertainty (CI spans 0) | comparable within uncertainty (CI spans 0) |
| Clear HLS Obs | <10 | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Clear HLS Obs | 10-19 | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Clear HLS Obs | >=20 | 463 | 17.54 [15.93, 19.14] | 34.0 d [30.4, 37.9] | 30.9% [26.8%, 35.1%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |

## 3. Findings and Causal Statements

- **Crop**: Skill is highest (lowest CRPS) for sorghum (CRPS 12.41, 95% CI [10.01, 14.73]), followed by maize (CRPS 17.68, 95% CI [15.22, 20.38]), and lowest for winter wheat (CRPS 21.15, 95% CI [18.78, 23.42]).
  *Cause analysis*: cause not established

- **Crop timing anomaly**: Winter wheat displays a severe timing error (peak timing absolute error 58.9 d, 95% CI [52.2, 66.3] d; median signed timing error +36.0 d).
  *Cause analysis*: Proposed explanation (not tested): Predicted peak DOY is systematically ~36 days later than observed heading in Kansas (late May vs July model peak). Phenology prior stage lengths for winter wheat require calibration (proposed as a separate decision).

- **Year**: Skill is higher in 2024 (CRPS 16.47, 95% CI [14.26, 18.90]) than in 2023 (CRPS 18.24, 95% CI [15.71, 20.94]) and 2022 (CRPS 18.46, 95% CI [16.39, 20.51]), though intervals overlap.
  *Cause analysis*: cause not established

- **Field size**: Skill is comparable across all field size classes (<10 ha: CRPS 19.83, 95% CI [16.26, 23.48]; 10–50 ha: CRPS 16.27, 95% CI [14.20, 18.53]; >50 ha: CRPS 17.30, 95% CI [15.53, 19.39]).
  *Cause analysis*: cause not established

- **Grade**: Evidence Grade B exhibits average CRPS of 16.96 [15.04, 18.98] vs Grade C of 17.30 [15.37, 19.46] and Grade D of 24.02 [15.95, 30.41], but differences are within spatial bootstrap uncertainty.
  *Cause analysis*: cause not established

- **Hls observations**: All 463 Kansas field-seasons had >=20 clear HLS observations (bins <10 and 10–19 had n=0, too few to judge).
  *Cause analysis*: Semi-arid clear skies and dual Sentinel-2 / Landsat coverage over tile T14SLH produced dense time series across all fields.
