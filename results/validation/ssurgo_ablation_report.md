# SSURGO AWS vs Fixed 150 mm TAW Prior — Error Stratification Report

Fields matched with valid SSURGO profiles: **198**; Mean SSURGO AWS `[E]`: **265.8 mm** vs mean shipped sim TAW `[A/D]`: **146.6 mm**.

| Metric | Climate Regime | TAW Deficit Tercile | n | Mean TAW Gap (mm) | Mean Signed Error (y - q50) | MAE | 90% Cov |
|---|---|---|---|---|---|---|---|
| canopy_integral | drought_2022_2023 | low_gap | 87 | 63.1 | -7.44 | 19.62 | 29.9% |
| canopy_integral | drought_2022_2023 | mid_gap | 87 | 129.3 | -22.03 | 24.39 | 27.6% |
| canopy_integral | drought_2022_2023 | high_gap | 88 | 164.3 | -17.63 | 19.77 | 27.3% |
| canopy_integral | wet_2024 | low_gap | 67 | 66.8 | +9.63 | 19.49 | 34.3% |
| canopy_integral | wet_2024 | mid_gap | 67 | 128.4 | -1.29 | 16.81 | 35.8% |
| canopy_integral | wet_2024 | high_gap | 64 | 164.6 | +0.72 | 20.02 | 34.4% |
| cover_days | drought_2022_2023 | low_gap | 87 | 63.1 | +12.86 | 38.52 | 12.6% |
| cover_days | drought_2022_2023 | mid_gap | 87 | 129.3 | -13.98 | 40.43 | 6.9% |
| cover_days | drought_2022_2023 | high_gap | 88 | 164.3 | -3.35 | 29.93 | 9.1% |
| cover_days | wet_2024 | low_gap | 67 | 66.8 | +35.10 | 39.61 | 3.0% |
| cover_days | wet_2024 | mid_gap | 67 | 128.4 | +20.75 | 35.78 | 6.0% |
| cover_days | wet_2024 | high_gap | 64 | 164.6 | +21.08 | 38.75 | 1.6% |
