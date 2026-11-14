# T2.4 WorldCereal / OGH-GHLC10 Independent Cross-Check — Central Ukraine (`ua_central_t36uvu`)

- **Reference product:** OpenGeoHub Global Harmonized Land Cover (`ogh-ghlc10` v1.2, 30 m annual COGs 2020–2024, DOI `10.5194/egusphere-2026-5540`, CC BY 4.0). Class `3` (`2.2 Annual crops - maize`) comes directly from ESA WorldCereal 10 m main-season maize; class `5` is other annual crops (winter wheat, sunflower, barley).
- **Sampling protocol:** 15 m inward polygon buffer (`CLAUDE.md` Rule 5) over all 400 FTW pilot fields across 8 disjoint 10 km spatial blocks; 95% CIs via 1,000 spatial-block bootstrap replicates.
- **Download footprint:** 3.77 MB across 2020–2024 BigTIFF range requests.

## Agreement Summary

| Horizon | Sample `n` | Annual Cropland Agreement | Maize TP / FP / FN / TN | Maize Acc [95% CI] | Precision | Recall | F1 [95% CI] | Cohen's $\kappa$ |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| **2021 (T2.4 target year)** | 400 | **98.25%** | 15 / 259 / 0 / 126 | 35.2% [29.2%, 44.8%] | 5.5% | 100.0% | 0.104 [0.053, 0.149] | 0.035 |
| **2020–2024 (all years)** | 2000 | **98.35%** | 34 / 639 / 41 / 1286 | 66.0% [60.6%, 72.0%] | 5.1% | 45.3% | 0.091 [0.047, 0.119] | 0.025 |
| **2020–2024 (`conf >= 0.70`)** | 1574 | **98.48%** | 28 / 472 / 31 / 1043 | 68.0% [62.7%, 74.4%] | 5.6% | 47.5% | 0.100 [0.048, 0.135] | 0.035 |

## Breakdown by Classified Crop (2021 / 2020–2024)

- **Winter cereals (`winter_wheat`):** 2021 `n = 118`: **0.0%** labelled as WorldCereal maize (`95.8%` OGH class 5 other annual crops). Across 2020–2024 (`n = 474`): `1.7%` maize, `93.5%` class 5 other annual crops. Spring-vs-summer cohort separation is reliable.
- **Cropland mask integrity:** `98.25%` (2021) and `98.35%` (2020–2024) of FTW pilot fields are confirmed annual cropland in `ogh-ghlc10`.
- **Negative finding on Maize vs Sunflower separation:** In 2021, NDVI TWDTW classified `274/400` fields as `maize` vs only `15/400` mapped by ESA WorldCereal inside `ogh-ghlc10` (`tp=15, fp=259, fn=0, kappa=0.035`). Across 2017–2024, TWDTW maize-vs-sunflower ratios swing strongly across wet/dry years (e.g. `13 maize / 306 sunflower` in dry 2020 vs `274 maize / 8 sunflower` in wet 2021), showing that NDVI-only TWDTW with fixed FAO-56 stage lengths confuses late-senescing sunflower and maize. Accordingly, Tier 3 crop states carry uncertainty **tag D** and **must be disclosed as unvalidated at the species level** between summer crops (maize vs sunflower), whereas **winter cereal vs summer crop** separation is well-supported.
