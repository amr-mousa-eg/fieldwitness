# T7.4c Ablation (Kansas, forecast mode, cut-off 2021-12-31, n=266 field-seasons)

Forecast CRPS (days, or canopy units for canopy_integral); lower is better.
Reused from T7.3, no new run.

| Variant | sos | peak | canopy_integral | cover_days |
|---|---|---|---|---|
| Full model (3 witnesses, witness 3 off since T5.3) | 19.30 | 11.47 | 14.87 | 30.38 |
| Without witness 2 (= B2, uncalibrated physics) | 22.24 | 12.66 | 16.22 | 30.55 |
| Without witness 3 (= full model; witness 3 is already off) | 19.30 | 11.47 | 14.87 | 30.38 |

Notes:
- Witness 3 ablation equals the full model by construction: neighbour effects
  (T5.2) do not exist (Gate 5 failed).
- Table covers the 266 maize/sorghum field-seasons of T7.3; winter wheat (T7.1b)
  is not in the baselines file.
- Weak skill overall (T7.1/T7.2, T7.4b): differences here are not evidence that
  witness 2 helps or hurts.
