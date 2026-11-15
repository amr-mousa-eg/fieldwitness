# Phase 4 Split-CQR Interval Recalibration Evaluation (Forecast Mode, 2022–2024)

Calibration: rolling-origin 2019–2021 (`n=3424` rows); Held-out Test: 2022–2024 (`n=3704` rows).
Spatial blocks: `109` (10 km grid), 1,000 block bootstrap resamples (`seed=42`). Point medians `q50` unchanged.

| Crop | Metric | n | Stored Cov90 | Sym CQR Cov90 | Asym CQR Cov90 | Stored Winkler | Sym Winkler | Asym Winkler | Gate (85–95%) | Gate (>=80%) |
|---|---|---|---|---|---|---|---|---|---|---|
| maize | canopy_integral | 124 | 23.4% | 79.0% | 78.2% | 279.8 | 114.7 | 114.6 | **fail** | **fail** |
| maize | cover_days | 124 | 10.5% | 81.5% | 77.4% | 585.7 | 196.8 | 210.7 | **fail** | **fail** |
| maize | peak | 124 | 91.1% | 96.0% | 96.8% | 89.4 | 95.5 | 104.4 | **fail** | **fail** |
| maize | sos | 124 | 33.1% | 91.1% | 91.1% | 246.7 | 139.4 | 147.7 | **pass** | **pass** |
| sorghum | canopy_integral | 142 | 37.3% | 71.8% | 69.7% | 182.1 | 117.2 | 119.7 | **fail** | **fail** |
| sorghum | cover_days | 142 | 5.6% | 88.7% | 79.6% | 559.7 | 226.6 | 213.2 | **fail** | **fail** |
| sorghum | peak | 142 | 84.5% | 86.6% | 88.0% | 112.3 | 106.8 | 130.6 | **fail** | **fail** |
| sorghum | sos | 142 | 64.1% | 89.4% | 89.4% | 351.3 | 283.8 | 234.5 | **pass** | **pass** |
| winter_wheat | canopy_integral | 197 | 25.4% | 76.1% | 69.5% | 319.0 | 121.8 | 114.9 | **fail** | **fail** |
| winter_wheat | cover_days | 197 | 3.0% | 95.9% | 88.8% | 831.8 | 242.4 | 246.2 | **pass** | **pass** |
| winter_wheat | peak | 197 | 34.5% | 78.2% | 78.2% | 670.4 | 427.8 | 432.2 | **fail** | **fail** |
| winter_wheat | sos | 197 | 18.8% | 86.3% | 80.2% | 1083.5 | 274.1 | 236.1 | **fail** | **pass** |

## Covariate-Stratified Split-CQR Comparison (SSURGO TAW & Pre-Cutoff Vigor, Hierarchical Fallback `n>=30`)

| Crop | Metric | Unstrat. Asym Cov90 | TAW-Strat. Asym Cov90 | Vigor-Strat. Asym Cov90 | Unstrat. Winkler | TAW-Strat. Winkler | Vigor-Strat. Winkler |
|---|---|---|---|---|---|---|---|
| maize | canopy_integral | 78.2% | 80.7% | 75.0% | 114.6 | 126.2 | 136.7 |
| maize | cover_days | 77.4% | 79.8% | 83.1% | 210.7 | 232.9 | 226.6 |
| maize | peak | 96.8% | 92.7% | 96.8% | 104.4 | 129.3 | 129.8 |
| maize | sos | 91.1% | 92.7% | 89.5% | 147.7 | 185.1 | 185.3 |
| sorghum | canopy_integral | 69.7% | 72.5% | 65.5% | 119.7 | 113.9 | 134.8 |
| sorghum | cover_days | 79.6% | 81.7% | 76.1% | 213.2 | 210.6 | 231.9 |
| sorghum | peak | 88.0% | 88.7% | 88.0% | 130.6 | 130.3 | 128.7 |
| sorghum | sos | 89.4% | 90.8% | 91.5% | 234.5 | 235.8 | 224.9 |
| winter_wheat | canopy_integral | 69.5% | 69.0% | 74.6% | 114.9 | 115.5 | 135.0 |
| winter_wheat | cover_days | 88.8% | 90.4% | 85.8% | 246.2 | 250.1 | 261.9 |
| winter_wheat | peak | 78.2% | 77.7% | 80.2% | 432.2 | 442.7 | 435.9 |
| winter_wheat | sos | 80.2% | 83.2% | 80.2% | 236.1 | 237.3 | 256.0 |
