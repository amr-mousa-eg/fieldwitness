# Central Ukraine (`ua_central_t36uvu`) — S2 Red-Edge/SWIR + MAE CropFormer (E2.2)

Spatially blocked **4-fold Leave-2-Blocks-Out CV** across all **400 fields (8 x 10 km FTW blocks)** against independent **OGH-GHLC10 v1.2 (ESA WorldCereal 10 m maize, 2020-2024)** labels. MAE pretraining uses strictly `<= 2021` unlabeled SITS inside each fold's 6 training blocks.

## 1. Maize vs Non-Maize Separation (Pooled `2020–2024`, n = 2,000)

| Model / Features | n | Accuracy | Precision | Recall | F1 | κ [95% CI] | ms/field |
|---|---|---|---|---|---|---|---|
| Baseline TWDTW (NDVI-only) | 2000 | 66.0% | 5.1% | 45.3% | 0.091 | 0.025 [0.002, 0.045] | - |
| CropFormer 3ch (NDVI+EVI+Clear, MAE<=2021) | 2000 | 92.2% | 13.5% | 20.0% | 0.161 | 0.122 [0.050, 0.232] | 0.24 |
| CropFormer 8ch (+Red-Edge/SWIR, no MAE) | 2000 | 94.8% | 12.5% | 6.7% | 0.087 | 0.062 [0.011, 0.132] | - |
| CropFormer 8ch (+Red-Edge/SWIR, MAE<=2021) | 2000 | 94.0% | 12.9% | 10.7% | 0.117 | 0.086 [-0.002, 0.234] | 0.24 |

## 2. Year `2021` (T2.4 Cohort, n = 400) & Strict Holdout (`<=2021` -> `2022–2024`)

| Cohort & Model | n | Accuracy | Precision | Recall | F1 | κ [95% CI] | ms |
|---|---|---|---|---|---|---|---|
| 2021: Baseline TWDTW | 400 | 35.2% | 5.5% | 100.0% | 0.104 | 0.035 [0.017, 0.056] | - |
| 2021: CropFormer 3ch (MAE<=2021) | 400 | 91.0% | 11.1% | 20.0% | 0.143 | 0.099 [-0.043, 0.409] | - |
| 2021: CropFormer 8ch (MAE<=2021) | 400 | 94.2% | 21.4% | 20.0% | 0.207 | 0.177 [-0.037, 0.501] | - |
| 2022–2024 Holdout: CropFormer 3ch (FT<=2021) | 1200 | 70.1% | 5.1% | 40.0% | 0.091 | 0.026 [-0.019, 0.076] | - |
| 2022–2024 Holdout: CropFormer 8ch (FT<=2021) | 1200 | 75.0% | 5.3% | 33.3% | 0.091 | 0.028 [-0.013, 0.073] | - |

## 3. Multi-Class Phenology Consistency (`<=2021` -> `2022–2024`)

- **CropFormer 3ch (MAE):** 82.4% exact match on `1199` held-out seasons (wheat=93.8%, maize=91.7%, sunflower=69.8%)
- **CropFormer 8ch (+Red-Edge/SWIR, MAE):** 85.9% exact match (wheat=96.4%, maize=93.5%, sunflower=75.0%)
