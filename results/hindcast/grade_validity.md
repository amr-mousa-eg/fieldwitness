# Grade & Credibility Empirical Validity Report (Kansas Pilot)

**Cut-off Date:** 2021-12-31 (Strict `as_of` guard; pre-registered in `DECISIONS.md`).  
**Scored Seasons:** 2022–2024 maize, sorghum, and winter wheat field-seasons.  
**Total Sample Size:** 463 field-seasons across 200 pilot fields.  
**Bootstrap:** 1000 resamples clustered by 10 km spatial grid blocks (seed=42).

## 1. Primary Pre-registered Test (Grade B vs Grade D)

- **Primary Metric:** Forecast-mode canopy integral CRPS.
- **Grade B Mean CRPS:** 16.9585 (95% CI: [15.0711, 18.9514], n = 170)
- **Grade D Mean CRPS:** 24.0243 (95% CI: [14.037, 31.251], n = 25)
- **Difference (D − B):** 7.0658 (95% CI: [-3.2777, 14.3151])
- **Primary Test Result:** **DID NOT PASS: Evidence grades did not show a statistically significant difference in predictive accuracy.**

## 2. Full Performance by Evidence Grade

| Evidence Grade | n | Mean Canopy Integral CRPS (95% CI) | Mean Peak Timing Error (days) | 90% Canopy Coverage | 90% Peak Coverage | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Grade B** | 170 | 16.9585 (15.0711 – 18.9514) | 29.15 d | 32.4% | 68.8% | Sufficient sample |
| **Grade C** | 268 | 17.3014 (15.2752 – 19.5556) | 37.09 d | 30.6% | 63.4% | Sufficient sample |
| **Grade D** | 25 | 24.0243 (14.037 – 31.251) | 34.38 d | 24.0% | 64.0% | Sufficient sample |

## 3. Continuous Credibility Score Rank Correlation (Exploratory)

- **Sample size:** 417 field-seasons with pre-cutoff credibility assessment.
- **Spearman $\rho$ vs Canopy Integral CRPS:** -0.0334 (p = 0.4969)
- **Spearman $\rho$ vs Peak Timing Error:** -0.0823 (p = 0.0931)
- *Interpretation:* A negative correlation indicates that higher physics credibility is associated with lower prediction errors.

## 4. Integrity and Model Invariance Statement

As pre-registered, FieldWitness evidence grades and threshold rules are **not altered** based on this check. The findings are reported transparently on the public Scoreboard and Methods pages to let reviewers and users judge the evidence system on empirical grounds.
