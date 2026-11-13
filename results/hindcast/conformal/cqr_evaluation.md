# Phase 4 Split-CQR Interval Recalibration Evaluation (Forecast Mode, 2022–2024)

Calibration: rolling-origin 2019–2021 (`n=3424` rows); Held-out Test: 2022–2024 (`n=3704` rows).
Spatial blocks: `109` (10 km grid), 1,000 block bootstrap resamples (`seed=42`). Point medians `q50` unchanged.

| Crop | Metric | n | Stored Cov90 | Sym CQR Cov90 | Asym CQR Cov90 | Stored Winkler | Sym Winkler | Asym Winkler | Gate (85–95%) | Gate (>=80%) |
|---|---|---|---|---|---|---|---|---|---|---|
| maize | canopy_integral | 124 | 27.4% | 77.4% | 76.6% | 271.7 | 116.2 | 116.8 | **fail** | **fail** |
| maize | cover_days | 124 | 11.3% | 82.3% | 75.8% | 578.0 | 196.9 | 212.2 | **fail** | **fail** |
| maize | peak | 124 | 92.7% | 93.5% | 93.5% | 85.8 | 86.9 | 100.5 | **fail** | **fail** |
| maize | sos | 124 | 31.4% | 89.5% | 90.3% | 235.3 | 138.8 | 148.2 | **pass** | **pass** |
| sorghum | canopy_integral | 142 | 43.7% | 70.4% | 66.2% | 179.9 | 120.9 | 122.8 | **fail** | **fail** |
| sorghum | cover_days | 142 | 6.3% | 88.7% | 79.6% | 559.8 | 226.7 | 213.4 | **fail** | **fail** |
| sorghum | peak | 142 | 84.5% | 87.3% | 89.4% | 112.1 | 105.9 | 127.5 | **fail** | **fail** |
| sorghum | sos | 142 | 66.2% | 89.4% | 88.7% | 351.3 | 283.3 | 233.4 | **pass** | **pass** |
| winter_wheat | canopy_integral | 197 | 23.9% | 73.6% | 68.5% | 318.0 | 122.0 | 120.4 | **fail** | **fail** |
| winter_wheat | cover_days | 197 | 4.6% | 95.9% | 89.3% | 822.9 | 244.2 | 246.9 | **pass** | **pass** |
| winter_wheat | peak | 197 | 34.5% | 80.7% | 78.2% | 672.7 | 410.0 | 423.3 | **fail** | **fail** |
| winter_wheat | sos | 197 | 20.8% | 89.8% | 85.8% | 1083.0 | 274.9 | 231.3 | **pass** | **pass** |
