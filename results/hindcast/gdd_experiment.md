# Experiment 2 — thermal-time (GDD) phenology: mixed result, H2 not supported

This experiment was pre-registered in `DECISIONS.md` (2026-11-12, commit `c6b82f7`) before any run. The user approved the amendment on dormancy and stage mapping (commit `17bc5cd`) before any Experiment 2 code ran.

- Sources and table locations: `docs/gdd_sources.md`.
- Code: `physics/phenology.py`, `infer/forward.py` (`phenology_mode`), and `scripts/x2_gdd_hindcast.py`, `x2_gdd_baselines.py`, `x2_gdd_compare.py`.
- Numbers: `gdd_experiment.json`; per-season records in `gdd/`.
- Statistics are tag D (model) scored against O (HLS). Crop labels are tag E.
- The published hindcast, baseline and diagnosis files were not changed.

## Setup (same as the published hindcast)

- Same cut-off (2021-12-31; ABC fit only on seasons ≤ 2021), priors, seeds, n_ref 2,000 and k 100.
- Same 463 scored field-seasons in 2022–2024 (maize 124, sorghum 142, winter wheat 197).
- Same statistics and CRPS, and the same baselines: B0, B1 and B2, which cover maize and sorghum only, as published.
- Same bootstrap: 10 km blocks, 1,000 resamples, seed 42.
- **Reproduction check:** in calendar mode the new runner reproduces the published records exactly, for all 200 fields. The baseline runner also reproduces the published baselines exactly (266 of 266). Unit tests show that calendar mode is bit-identical to the code on main.

## Before vs after: forecast mode (decides the verdict)

Numbers are means with 95 % CIs. Differences are gdd − calendar on the same field-seasons. For an error, a negative difference means gdd is better.

| Crop (n) | Metric | Calendar | GDD | Difference |
|---|---|---|---|---|
| Winter wheat (197) | Peak timing absolute error (days) | 58.9 [52.2, 66.3] | 49.4 [41.8, 57.0] | **−9.6 [−13.9, −5.6]** |
| | Peak timing signed error (days, + = model late) | +25.6 [17.0, 34.6] | −7.4 [−16.1, 1.5] | −33.1 [−35.0, −31.0] |
| | Canopy-integral CRPS | 21.15 [18.78, 23.42] | 21.48 [18.94, 24.17] | +0.34 [−2.62, 3.55] |
| | 90 % coverage, canopy / peak | 24 % / 35 % | 28 % / 39 % | +4 / +4 pts (CIs span 0) |
| Maize (124) | Peak timing absolute error | 14.9 [12.3, 18.2] | 12.8 [10.5, 15.4] | **−2.2 [−3.6, −0.8]** |
| | Canopy-integral CRPS | 17.68 [15.22, 20.38] | 18.11 [14.89, 21.79] | +0.43 [−2.73, 3.67] |
| | 90 % coverage, canopy / peak | 27 % / 93 % | 29 % / 74 % | +2 / **−19** pts |
| Sorghum (142) | Peak timing absolute error | 16.2 [13.5, 18.7] | 16.0 [13.4, 18.5] | −0.2 [−1.4, 1.2] |
| | Canopy-integral CRPS | 12.41 [10.01, 14.73] | 19.15 [15.83, 22.56] | **+6.74 [4.13, 9.42] (worse)** |
| | 90 % coverage, canopy / peak | 44 % / 85 % | 19 % / 68 % | **−25 / −17** pts |
| All (463) | Peak timing absolute error | 34.0 [30.4, 37.9] | 29.3 [26.0, 33.2] | −4.7 [−6.6, −3.0] |
| | Canopy-integral CRPS | 17.54 [15.93, 19.14] | 19.87 [17.88, 22.06] | **+2.33 [0.29, 4.51] (worse)** |

Winter wheat's median signed peak error falls from +36.0 to +8.0 days. The +36.0 matches `diagnosis.md`.

## Forced mode (real weather of the scored year; reported, not used for the verdict)

| Crop (n) | Peak timing absolute error: calendar → gdd (diff) | Canopy-integral CRPS: calendar → gdd (diff) |
|---|---|---|
| Winter wheat (197) | 71.8 → 44.4 (−27.4 [−33.6, −21.2]) | 21.88 → 22.87 (+0.99 [−2.02, 4.24]) |
| Maize (124) | 13.2 → 12.2 (−1.0 [−2.3, 0.2]) | 17.79 → 18.63 (+0.84 [−2.19, 4.03]) |
| Sorghum (142) | 16.8 → 16.4 (−0.5 [−1.9, 1.1]) | 12.16 → 20.57 (**+8.41 [5.76, 10.89]**) |

## Against the baselines (forecast canopy-integral CRPS, maize + sorghum, n = 266; baseline − FieldWitness, positive = FieldWitness better)

| Mode | FieldWitness | B1 − FW | B2 − FW | B0 − FW |
|---|---|---|---|---|
| Calendar (as published) | 14.86 | +1.23 [0.48, 1.99] | +1.35 [0.74, 1.90] | +0.26 [−0.83, 1.51] |
| GDD (physics baselines also in gdd) | 18.67 | +1.84 [1.37, 2.33] | +0.34 [0.10, 0.56] | **−3.54 [−5.76, −1.39]** |

In gdd mode, the field-mean baseline B0 (no physics) beats FieldWitness on canopy CRPS, both overall and for sorghum (−4.54 [−7.31, −1.83]).

## Verdict (pre-registered rule, forecast mode)

- **Winter wheat improves:** yes. Peak-timing absolute error falls by 9.6 days, and the CI lies entirely below 0. The systematic lateness almost disappears.
- **Maize gets worse:** no. Peak timing improves (−2.2 d). Canopy CRPS does not change significantly. Peak 90 % coverage falls from 93 % to 74 %; this is not part of the rule, but it is reported here.
- **Sorghum gets worse:** **yes.** Canopy-integral CRPS rises by 6.7 (CI 4.1 to 9.4), and canopy 90 % coverage falls from 44 % to 19 %.
- **H2 does not hold.** Thermal time is not adopted, and `phenology_mode` stays `calendar` by default.

Possible cause for sorghum, not tested: with the short-season thresholds the simulated season is shorter, so the canopy integral changes. The tag A mapping and the hybrid column are the obvious suspects. Re-choosing them now would be tuning on the test years, so this was not done. A new attempt needs a new pre-registration, with any choice made only on seasons ≤ 2021.

## What adoption would require (not done)

Adoption would need a new pre-registered run that passes the rule. Then:

1. Rebuild every field pack and the 3D packs, with new weather inputs: Tmax and Tmin are not in `sim3d_inputs` today.
2. Port `phenology.py` and the per-draw stage lengths to the TypeScript replay used by the Rotation Builder.
3. Regenerate the parity references, and re-run the parity test (2,160 runs).
4. Re-run the hindcast, baselines, diagnosis and grade-validity outputs, and update the Scoreboard.
5. Update the Methods text (the stage length source and the dormancy rule).
