# Bias diagnosis and per-crop centre recalibration (experiment, not adopted)

*12 Nov 2026. Pre-registered in `DECISIONS.md` (commit eb19a5b) before running. Branch `experiment/bias-diagnosis`; nothing here changes `main`, packs, the app or config. Tables, plots and the frozen corrections are in `results/hindcast/bias_diagnosis/`.*

**Question.** The 2022–2024 forecasts were biased (the conformal experiment found only about 31% of observed maize and wheat values above the predicted median). Is the bias already there in 2019–2021, and does a simple per-crop correction fitted on 2019–2021 remove it in 2022–2024?

**Data.** Fit: 432 out-of-sample pseudo-forecasts for 2019–2021 (cut-offs 2018–2020, copied from `experiment/conformal` commit c56a917). Test, read once after the corrections were frozen: the main hindcast, 463 field-seasons for 2022–2024. Signed error = predicted median − observed. CIs: 1,000 spatial-block (10 km) bootstrap resamples.

**1. The bias is not new, and its sign is mostly the same.** In forecast mode the model **over-predicts** the season's total greenness (canopy integral) for maize and winter wheat in every year, 2019 to 2023, by about 6 to 27 units (median). Examples: maize 2019 +8.44 [+5.39, +12.61], 2022 +14.61 [+5.45, +28.10]; winter wheat 2020 +27.12, 2022 +24.30, 2023 +23.51. Exceptions: winter wheat 2024 is −4.67 [−10.98, +0.53], and sorghum is near zero in 2019–2021 (for example −0.26 [−2.96, +2.13] in 2019) but +11.53 in 2022. Forced mode, which uses the real weather, shows the same pattern (for example winter wheat 2023 +26.08). So knowing the weather does not remove it.

**2. What it tracks** (Spearman rho of the canopy error, forecast mode):
- **Rain anomaly:** −0.11 [−0.22, −0.01] in 2019–2021 and −0.21 [−0.28, −0.13] in 2022–2024. Drier-than-usual seasons go with larger over-prediction, in both periods.
- **Temperature anomaly:** −0.31 [−0.38, −0.22] in 2022–2024 only. For 2019–2021, +0.10 [−0.01, +0.21]: cause not established.
- **Number of clear satellite observations:** cause not established in both periods.
- **Field size:** +0.12 [+0.02, +0.21] in 2019–2021 only. For 2022–2024: cause not established.

These are associations, not proof of a cause. A plausible reading, **not tested here**, is that the model's soil holds too little water (see the SSURGO check), or that its crop greenness does not drop enough in dry seasons.

**3. Corrections chosen on 2019–2021 only** (spatial-block cross-validation, simplest within one standard error):
- **Maize:** canopy × 0.855; peak shift +10 days.
- **Sorghum:** no canopy correction and no peak shift (neither beat "none").
- **Winter wheat:** an isotonic map for the canopy; peak shift −35 days.

**4. Gate on 2022–2024 (forecast mode): FAIL. Nothing is adopted.**

| Crop | n | Raw median error | Corrected median error | CRPS change (corrected − raw) | Gate |
|---|---|---|---|---|---|
| Maize | 124 | +11.25 [+3.73, +16.54] | +1.13 [−5.69, +7.18] (includes 0) | −1.24 [−2.92, +0.53] (does not exclude worse) | FAIL |
| Winter wheat | 197 | +16.30 [+12.04, +21.61] | +5.87 [+0.81, +8.80] (excludes 0) | −3.27 [−4.25, −2.25] (better) | FAIL |
| Sorghum | 142 | — | no correction selected | — | not applicable |

- **Maize:** the bias moved to about zero, but the CRPS improvement is not clear.
- **Winter wheat:** CRPS clearly improved and the bias shrank by about two thirds, but it did not reach zero.
- **Coverage (information only):** canopy 90% coverage was 27% raw against 25% corrected for maize, and 24% against 30% for winter wheat. The ranges stay far too narrow.
- **Peak timing (information only):** mean absolute error went from 14.9 to 14.9 days for maize and from 58.9 to 48.8 days for winter wheat.

**What this means.**
- A fixed per-crop correction removes part of the bias, but not enough to pass the pre-registered gate.
- The bias is partly tied to how dry and hot the season is, so a constant correction cannot track it.
- The over-prediction is not year-specific in sign (2019–2021 and 2022–2024 agree for maize and wheat). It is the size that varies with the weather.

**Limits.**
- CRPS here is a five-quantile approximation, used the same way before and after; it is not the stored sample CRPS.
- The season windows for the weather anomalies (Apr–Sep; Oct–Jun for wheat) are team choices (A).
- 2025 was not used.
- The analysis was re-run once after lint-only code edits, with identical output.
