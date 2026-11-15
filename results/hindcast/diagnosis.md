# Diagnostic Breakdown of Hindcast Skill (Kansas Pilot T14SLH)

**Pre-registered in `DECISIONS.md` (commit `e021f3e`) before execution.**
- Total scored field-seasons: 463 across 200 Kansas pilot fields (2022–2024).
- Grades and credibility evaluated under cut-off `as_of(2021-12-31)` (no circularity).
- Statistical inference: 1,000 spatial block bootstrap resamples (10 km grid), seed=42.
- Decision rule: Primary test requires 95% CI of paired difference to strictly exclude 0. Cell $n < 20$ reported as 'too few to judge'.

## 1. Primary Pre-Registered Test: Baseline Comparisons

| Subset | n | FieldWitness CRPS (95% CI) | Baseline B1 CRPS | Diff vs B1 (95% CI) | Beats B1? | Baseline B2 CRPS | Diff vs B2 (95% CI) | Beats B2? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall (paired sample)** | 463 | 17.86 [16.42, 19.35] | 19.67 | +1.81 [1.39, 2.22] | **YES** | 20.45 | +2.59 [2.04, 3.10] | **YES** |
| Crop: maize | 124 | 18.23 [15.99, 20.72] | 20.68 | +2.45 [1.59, 3.32] | YES | 21.24 | +3.01 [1.91, 4.04] | YES |
| Crop: sorghum | 142 | 12.70 [10.58, 15.16] | 14.07 | +1.37 [0.56, 2.18] | YES | 14.50 | +1.80 [0.97, 2.56] | YES |
| Crop: winter_wheat | 197 | 21.36 [19.39, 23.50] | 23.08 | +1.73 [1.22, 2.14] | YES | 24.24 | +2.89 [2.06, 3.64] | YES |
| Crop: fallow | 0 | *Too few to judge (n < 20)* | — | — | — | — | — | — |

## 2. Exploratory Dimension Breakdowns

All cell comparisons below are designated **exploratory** per pre-registration protocol.

| Dimension | Cell | n | FW CRPS (95% CI) | Peak Timing Abs Err (d) | 90% Canopy Coverage | Verdict vs B1 | Verdict vs B2 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| Crop | maize | 124 | 18.23 [15.99, 20.72] | 17.2 d [14.1, 21.1] | 23.4% [15.1%, 32.1%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Crop | sorghum | 142 | 12.70 [10.58, 15.16] | 16.3 d [13.7, 19.5] | 37.3% [28.0%, 46.5%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Crop | winter_wheat | 197 | 21.36 [19.39, 23.50] | 56.0 d [48.6, 63.9] | 25.4% [19.4%, 31.8%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Crop | fallow | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Year | 2022 | 134 | 19.31 [16.87, 21.73] | 37.7 d [30.0, 46.4] | 22.4% [15.7%, 29.6%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Year | 2023 | 129 | 18.75 [16.25, 21.63] | 30.6 d [22.6, 40.0] | 27.9% [20.7%, 35.2%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Year | 2024 | 200 | 16.32 [14.21, 18.49] | 32.5 d [28.0, 37.2] | 33.0% [26.2%, 40.0%] | FieldWitness beats baseline (CI > 0) | comparable within uncertainty (CI spans 0) |
| Field Size | <10 ha | 115 | 20.28 [16.95, 23.93] | 37.1 d [30.3, 45.2] | 23.5% [15.9%, 31.1%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Field Size | 10-50 ha | 176 | 16.45 [14.44, 18.30] | 31.5 d [25.8, 37.9] | 31.8% [25.4%, 38.7%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Field Size | >50 ha | 172 | 17.69 [15.78, 19.72] | 33.0 d [27.0, 39.9] | 28.5% [22.3%, 34.7%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | B | 139 | 17.93 [15.55, 20.43] | 28.7 d [22.5, 35.4] | 25.9% [18.5%, 32.7%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | C | 299 | 17.25 [15.62, 18.76] | 35.6 d [30.3, 41.4] | 30.1% [25.3%, 34.7%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |
| Cut-off Grade | D | 25 | 24.81 [16.80, 30.85] | 34.9 d [23.4, 45.9] | 24.0% [7.1%, 47.4%] | comparable within uncertainty (CI spans 0) | comparable within uncertainty (CI spans 0) |
| Clear HLS Obs | <10 | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Clear HLS Obs | 10-19 | 0 | *Too few to judge (n < 20)* | — | — | — | — |
| Clear HLS Obs | >=20 | 463 | 17.86 [16.42, 19.35] | 33.5 d [29.3, 38.0] | 28.5% [24.5%, 32.3%] | FieldWitness beats baseline (CI > 0) | FieldWitness beats baseline (CI > 0) |

## 3. Findings and Causal Statements

- **Crop**: Skill is highest (lowest CRPS) for sorghum (CRPS 12.70, 95% CI [10.58, 15.16]), followed by maize (CRPS 18.23, 95% CI [15.99, 20.72]), and lowest for winter wheat (CRPS 21.36, 95% CI [19.39, 23.50]).
  *Cause analysis*: cause not established

- **Crop timing anomaly**: Winter wheat displays a severe timing error (peak timing absolute error 56.0 d, 95% CI [48.6, 63.9] d; median signed timing error +30.0 d).
  *Cause analysis*: Proposed explanation (not tested): Predicted peak DOY is systematically ~30 days later than observed heading in Kansas (late May vs July model peak). Phenology prior stage lengths for winter wheat require calibration (proposed as a separate decision).

- **Year**: By year: 2024 (CRPS 16.32, 95% CI [14.21, 18.49]), 2023 (CRPS 18.75, 95% CI [16.25, 21.63]), and 2022 (CRPS 19.31, 95% CI [16.87, 21.73]), with overlapping bootstrap intervals.
  *Cause analysis*: cause not established

- **Field size**: Skill is comparable across all field size classes (<10 ha: CRPS 20.28, 95% CI [16.95, 23.93]; 10-50 ha: CRPS 16.45, 95% CI [14.44, 18.30]; >50 ha: CRPS 17.69, 95% CI [15.78, 19.72]).
  *Cause analysis*: cause not established

- **Grade**: Evidence Grade B exhibits average CRPS of 17.93 [15.55, 20.43], Grade C exhibits average CRPS of 17.25 [15.62, 18.76], Grade D exhibits average CRPS of 24.81 [16.80, 30.85], with overlapping spatial bootstrap uncertainty.
  *Cause analysis*: cause not established

- **Hls observations**: 463 of 463 Kansas field-seasons had >=20 clear HLS observations (bins <10 and 10-19 had n<20, too few to judge).
  *Cause analysis*: Semi-arid clear skies and dual Sentinel-2 / Landsat coverage over tile T14SLH produced dense time series across all fields.
