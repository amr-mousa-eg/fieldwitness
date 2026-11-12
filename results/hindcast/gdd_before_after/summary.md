# GDD before/after: tables (calendar = before, heat clock gdd = after)

Pre-registration: DECISIONS.md 2026-11-12 (commit 6f62874). All numbers come from the Experiment 2 run outputs; 95 % CI = spatial block bootstrap (10 km blocks, 1,000 resamples, seed 42). Statistics tag D (model) scored against O (HLS); crop labels E. Plain-language summary: `docs/GDD_BEFORE_AFTER.md`.

## 1. Summary table

CRPS = canopy-integral CRPS (lower is better). Peak error = mean absolute peak-timing error (days). Signed = median signed peak-timing error (days, + = model late). Coverage = share of seasons where the observation fell inside the 90 % interval (canopy integral / peak day).

### Forecast run

| Crop | Method | Mode | n | CRPS | Peak error (d) | Signed (d) | 90 % cov. canopy | 90 % cov. peak |
|---|---|---|---|---|---|---|---|---|
| Maize | FieldWitness | calendar | 124 | 17.68 [15.22, 20.38] | 14.9 [12.3, 18.2] | -6.0 [-9.5, 0.0] | 27% [20, 35] | 93% [88, 97] |
| Maize | FieldWitness | gdd | 124 | 18.11 [14.89, 21.79] | 12.8 [10.5, 15.4] | 0.0 [-3.0, 2.0] | 29% [21, 37] | 74% [67, 81] |
| Maize | FieldWitness | **gdd - calendar** | 124 | 0.43 [-2.73, 3.67] | -2.2 [-3.6, -0.8] | 4.9 [3.7, 6.2] | 0.02 [-0.10, 0.14] | -0.19 [-0.25, -0.12] |
| Maize | B0 | calendar | 124 | 15.71 [13.12, 18.97] | 17.4 [13.9, 21.6] | 6.2 [2.0, 9.5] | 33% [24, 42] | 40% [30, 49] |
| Maize | B0 | gdd | 124 | 15.71 [13.12, 18.97] | 17.4 [13.9, 21.6] | 6.2 [2.0, 9.5] | 33% [24, 42] | 40% [30, 49] |
| Maize | B1 | calendar | 124 | 19.45 [17.00, 22.21] | 28.6 [25.6, 32.1] | -26.5 [-31.0, -23.0] | 20% [13, 29] | 92% [87, 96] |
| Maize | B1 | gdd | 124 | 19.99 [16.39, 24.15] | 16.1 [13.5, 19.3] | -10.5 [-15.0, -8.0] | 26% [19, 34] | 77% [69, 84] |
| Maize | B2 | calendar | 124 | 19.71 [17.17, 22.36] | 20.7 [17.5, 24.3] | -18.0 [-23.0, -13.0] | 28% [21, 36] | 92% [87, 96] |
| Maize | B2 | gdd | 124 | 18.33 [15.05, 22.14] | 14.5 [11.9, 17.7] | -7.0 [-13.0, -3.0] | 28% [21, 36] | 81% [74, 89] |
| Sorghum | FieldWitness | calendar | 142 | 12.41 [10.01, 14.73] | 16.2 [13.5, 18.7] | 2.0 [0.0, 5.0] | 44% [36, 53] | 85% [79, 90] |
| Sorghum | FieldWitness | gdd | 142 | 19.15 [15.83, 22.56] | 16.0 [13.4, 18.5] | -1.0 [-7.0, 0.0] | 19% [13, 25] | 68% [59, 75] |
| Sorghum | FieldWitness | **gdd - calendar** | 142 | 6.74 [4.13, 9.42] | -0.2 [-1.4, 1.2] | -4.8 [-5.9, -3.6] | -0.25 [-0.38, -0.13] | -0.17 [-0.24, -0.11] |
| Sorghum | B0 | calendar | 142 | 14.61 [12.04, 17.20] | 18.4 [14.8, 22.6] | -1.5 [-4.5, 3.5] | 32% [25, 41] | 43% [34, 53] |
| Sorghum | B0 | gdd | 142 | 14.61 [12.04, 17.20] | 18.4 [14.8, 22.6] | -1.5 [-4.5, 3.5] | 32% [25, 41] | 43% [34, 53] |
| Sorghum | B1 | calendar | 142 | 13.17 [10.61, 15.66] | 15.4 [12.9, 17.9] | -7.5 [-12.0, -2.0] | 37% [30, 46] | 79% [73, 85] |
| Sorghum | B1 | gdd | 142 | 20.95 [17.52, 24.39] | 18.2 [15.3, 21.2] | -15.5 [-17.0, -10.0] | 18% [12, 24] | 39% [30, 48] |
| Sorghum | B2 | calendar | 142 | 13.16 [11.00, 15.30] | 14.5 [12.1, 17.0] | 0.0 [-5.0, 2.0] | 44% [35, 52] | 92% [87, 96] |
| Sorghum | B2 | gdd | 142 | 19.59 [16.30, 22.94] | 17.1 [14.4, 19.9] | -13.5 [-16.0, -8.0] | 19% [13, 25] | 75% [67, 82] |
| Winter wheat | FieldWitness | calendar | 197 | 21.15 [18.78, 23.42] | 58.9 [52.2, 66.3] | 36.0 [31.0, 42.0] | 24% [18, 30] | 35% [28, 42] |
| Winter wheat | FieldWitness | gdd | 197 | 21.48 [18.94, 24.17] | 49.4 [41.8, 57.0] | 8.0 [1.0, 10.0] | 28% [22, 34] | 39% [32, 46] |
| Winter wheat | FieldWitness | **gdd - calendar** | 197 | 0.34 [-2.62, 3.55] | -9.6 [-13.9, -5.6] | -33.0 [-35.0, -31.0] | 0.04 [-0.06, 0.14] | 0.04 [-0.05, 0.14] |
| Winter wheat | B0 | | | no baseline | | | | |
| Winter wheat | B1 | | | no baseline | | | | |
| Winter wheat | B2 | | | no baseline | | | | |

### Forced run

| Crop | Method | Mode | n | CRPS | Peak error (d) | Signed (d) | 90 % cov. canopy | 90 % cov. peak |
|---|---|---|---|---|---|---|---|---|
| Maize | FieldWitness | calendar | 124 | 17.79 [15.46, 20.50] | 13.2 [10.2, 16.7] | -1.5 [-8.0, 0.0] | 21% [13, 28] | 68% [59, 76] |
| Maize | FieldWitness | gdd | 124 | 18.63 [15.36, 22.40] | 12.1 [9.8, 15.2] | 0.0 [-2.5, 0.0] | 19% [13, 27] | 66% [59, 74] |
| Maize | FieldWitness | **gdd - calendar** | 124 | 0.84 [-2.19, 4.03] | -1.0 [-2.3, 0.2] | 3.1 [1.8, 4.2] | -0.02 [-0.13, 0.11] | -0.02 [-0.10, 0.07] |
| Maize | B0 | | | no baseline (baselines use past weather) | | | | |
| Maize | B1 | | | no baseline (baselines use past weather) | | | | |
| Maize | B2 | | | no baseline (baselines use past weather) | | | | |
| Sorghum | FieldWitness | calendar | 142 | 12.16 [9.84, 14.54] | 16.8 [13.8, 19.9] | -2.0 [-8.0, 0.0] | 35% [27, 45] | 72% [63, 80] |
| Sorghum | FieldWitness | gdd | 142 | 20.57 [17.16, 23.99] | 16.4 [13.7, 19.0] | -4.5 [-9.0, 0.0] | 13% [7, 19] | 58% [49, 66] |
| Sorghum | FieldWitness | **gdd - calendar** | 142 | 8.41 [5.76, 10.89] | -0.5 [-1.9, 1.1] | -1.2 [-2.8, 0.5] | -0.23 [-0.35, -0.11] | -0.14 [-0.21, -0.07] |
| Sorghum | B0 | | | no baseline (baselines use past weather) | | | | |
| Sorghum | B1 | | | no baseline (baselines use past weather) | | | | |
| Sorghum | B2 | | | no baseline (baselines use past weather) | | | | |
| Winter wheat | FieldWitness | calendar | 197 | 21.88 [19.61, 24.21] | 71.8 [63.9, 80.6] | 56.0 [39.5, 65.0] | 14% [10, 19] | 21% [16, 27] |
| Winter wheat | FieldWitness | gdd | 197 | 22.87 [20.35, 25.68] | 44.4 [37.3, 52.0] | 0.0 [-2.0, 5.0] | 21% [15, 27] | 36% [30, 43] |
| Winter wheat | FieldWitness | **gdd - calendar** | 197 | 0.99 [-2.02, 4.24] | -27.4 [-33.6, -21.2] | -50.7 [-54.1, -47.8] | 0.07 [-0.03, 0.15] | 0.15 [0.06, 0.24] |
| Winter wheat | B0 | | | no baseline (baselines use past weather) | | | | |
| Winter wheat | B1 | | | no baseline (baselines use past weather) | | | | |
| Winter wheat | B2 | | | no baseline (baselines use past weather) | | | | |

In the gdd − calendar rows the coverage differences are shares (0.10 = 10 points); the signed-error row is the mean of per-season differences.

### Does FieldWitness beat the baselines? (forecast canopy CRPS, baseline − FieldWitness; beats = CI entirely > 0)

| Crop | Baseline | Calendar mode | Gdd mode | Beats in both modes |
|---|---|---|---|---|
| Maize | B0 | -1.97 [-3.93, 0.05] no clear difference | -2.40 [-5.23, 0.24] no clear difference | no |
| Maize | B1 | 1.77 [0.73, 2.89] FW beats | 1.88 [0.89, 2.83] FW beats | yes |
| Maize | B2 | 2.03 [1.17, 2.87] FW beats | 0.22 [-0.26, 0.66] no clear difference | no |
| Sorghum | B0 | 2.21 [0.98, 3.46] FW beats | -4.54 [-7.31, -1.83] baseline beats FW | no |
| Sorghum | B1 | 0.77 [-0.10, 1.64] no clear difference | 1.80 [1.46, 2.10] FW beats | no |
| Sorghum | B2 | 0.76 [-0.06, 1.53] no clear difference | 0.44 [0.20, 0.65] FW beats | no |
| Winter wheat | B0-B2 | no baseline | no baseline | - |

## 2. Per-field view (forecast run; field mean over its scored seasons of the crop)

Noise bands fixed beforehand (tag A): timing ±5 days; CRPS ±10 % of the crop's calendar mean forecast CRPS. Histograms: `figures/per_field_histograms.png`; values: `per_field.csv`.

| Crop | Fields | Timing: improved / within noise / worse | CRPS band | CRPS: improved / within noise / worse |
|---|---|---|---|---|
| Maize | 88 | 29 / 48 / 11 | ±1.77 | 42 / 7 / 39 |
| Sorghum | 112 | 22 / 68 / 22 | ±1.24 | 33 / 3 / 76 |
| Winter wheat | 160 | 95 / 15 / 50 | ±2.11 | 77 / 11 / 72 |

## 3. Year by year (gdd − calendar; `by_year.csv`)

| Run | Crop | Year | n | Δ CRPS | Δ peak error (d) |
|---|---|---|---|---|---|
| forecast | Maize | 2022 | 36 | -1.00 [-5.85, 4.18] | -4.0 [-6.6, -1.3] |
| forecast | Maize | 2023 | 34 | 1.26 [-4.16, 6.57] | -1.7 [-3.4, -0.0] |
| forecast | Maize | 2024 | 54 | 0.87 [-3.90, 5.40] | -1.3 [-3.9, 1.0] |
| forecast | Sorghum | 2022 | 51 | -1.09 [-5.33, 3.30] | -0.3 [-2.2, 1.7] |
| forecast | Sorghum | 2023 | 34 | 9.26 [4.96, 13.45] | -0.4 [-2.9, 1.9] |
| forecast | Sorghum | 2024 | 57 | 12.25 [9.23, 15.05] | 0.0 [-2.0, 2.0] |
| forecast | Winter wheat | 2022 | 47 | -12.27 [-17.74, -6.37] | -25.9 [-32.8, -18.3] |
| forecast | Winter wheat | 2023 | 61 | -13.04 [-18.14, -7.32] | 21.3 [16.6, 25.6] |
| forecast | Winter wheat | 2024 | 89 | 16.16 [11.79, 20.28] | -22.1 [-26.9, -17.2] |
| forced | Maize | 2022 | 36 | 0.91 [-4.04, 5.52] | 0.1 [-0.9, 1.2] |
| forced | Maize | 2023 | 34 | -0.56 [-5.98, 5.16] | -2.4 [-5.2, 0.1] |
| forced | Maize | 2024 | 54 | 1.67 [-2.72, 5.84] | -0.9 [-2.9, 1.2] |
| forced | Sorghum | 2022 | 51 | 1.88 [-2.03, 6.01] | 1.3 [-0.4, 3.2] |
| forced | Sorghum | 2023 | 34 | 10.16 [5.63, 14.39] | -1.5 [-4.4, 1.3] |
| forced | Sorghum | 2024 | 57 | 13.22 [10.44, 15.82] | -1.4 [-3.8, 1.0] |
| forced | Winter wheat | 2022 | 47 | -6.19 [-12.23, -0.32] | -62.1 [-72.9, -48.8] |
| forced | Winter wheat | 2023 | 61 | -15.29 [-21.30, -8.84] | 14.2 [9.3, 19.5] |
| forced | Winter wheat | 2024 | 89 | 15.94 [12.12, 19.51] | -37.5 [-44.9, -29.5] |

## 5. Winter wheat timing change by pre-registered diagnosis dimensions (forecast)

| Dimension | Cell | n | Δ peak error (d) |
|---|---|---|---|
| year | 2022 | 47 | -25.9 [-32.8, -18.3] |
| year | 2023 | 61 | 21.3 [16.6, 25.6] |
| year | 2024 | 89 | -22.1 [-26.9, -17.2] |
| size_class | 10-50 ha | 75 | -7.7 [-14.7, -1.0] |
| size_class | <10 ha | 48 | -8.5 [-17.7, 1.1] |
| size_class | >50 ha | 74 | -12.2 [-18.5, -6.3] |
| hls_bin | >=20 | 197 | -9.6 [-13.9, -5.6] |

Early- vs late-season fields is not a pre-registered dimension and was not computed. **Cause of the timing change: not established.**

## 4. Example fields

Random draw (seed 42, rule fixed beforehand): Winter wheat a80d3a32, 1c41850d, c41b7f43; Maize 13c9aa10, ce244a1b; Sorghum b7bc5e58, 11aae63d, d11fd9d2. Charts: `figures/example_*.png`. Selected after the fact (for illustration, not evidence): `figures/after_the_fact_*.png`.

## 7. Sanity

- Calendar records vs published: 200 of 200 fields identical.
- Calendar baselines vs published: 266 of 266 field-seasons identical.
- Curve re-runs (identical code plus a read-only hook): records identical in both modes (926 predictions each).
- Source files: `results/hindcast/gdd/records_calendar.jsonl`; `results/hindcast/gdd/records_gdd.jsonl`; `results/hindcast/gdd/baselines_calendar.jsonl`; `results/hindcast/gdd/baselines_gdd.jsonl`; `results/hindcast/ks_t14slh_records.jsonl`; `results/hindcast/ks_t14slh_baselines.jsonl`; `results/hindcast/gdd_before_after/curves_calendar.npz`; `results/hindcast/gdd_before_after/curves_gdd.npz`; `results/hindcast/gdd_before_after/rerun_check_calendar.json`; `results/hindcast/gdd_before_after/rerun_check_gdd.json`; `data/fields/ks_t14slh_pilot.parquet (blocks, field area; local, not in git)`; `data/fields/ks_t14slh_hls_series.parquet (observed NDVI points; local, not in git)`.

## 6. 2025 clean test

Not possible from local data: HLS ends 2024-12-31 and crop labels end 2024. Estimated download about 175–185 MB (3 AppEEARS point tasks, by analogy with 2022–2024); not downloaded. Details: `feasibility_2025.json`.
