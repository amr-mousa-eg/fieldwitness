# FieldWitness — Consistency Audit (AG-1)

Audit conducted on 12 Nov 2026 by Google Antigravity across project documentation, submission drafts, and frontend copy.

---

## 1. Audit Table of Numbers, Limits, and Citations

Columns: `claim | where stated (file:line) | source value | file:line | status (match / mismatch / cannot verify) | suggested wording`

| Claim | Where Stated (file:line) | Source Value | Source (file:line) | Status | Suggested Wording |
|---|---|---|---|---|---|
| 200 pilot fields in Kansas | `README.md:11`, `submission.md:12`, `app/src/strings/en.json:7` | 200 pilot fields selected across tile T14SLH | `results/pilot_fields/ks_t14slh_summary.json:3`, `results/resolver_check.json:2` | match | Keep as stated ("Kansas, USA (HLS tile T14SLH), 200 pilot fields"). |
| Season detection 78.3% accuracy vs 90% target | `README.md:100`, `submission.md:67`, `app/src/strings/en.json:441,635` | 78.3% (`match_share: 0.783`) on test set vs target 0.90 | `results/story/ks_seasons_test.json:70,94` | match | Keep percentage ("78.3% on held-out test data against a 90% target"). |
| Season detection sample denominator (155/198 field-seasons) | `README.md:113`, `app/src/strings/en.json:441,461,473` | 240 held-out field-years (188/240 matches) | `results/story/ks_seasons_test.json:69` (`n_field_years: 240`) | mismatch | Replace "155 of 198 field seasons" with "188 of 240 field-years" (or "78.3% across 240 held-out field-years"). |
| Season detection citation to `kansas_season_eval.json` | `README.md:113`, `app/src/strings/en.json:441,461` | File does not exist; test results live in `ks_seasons_test.json` | `results/story/ks_seasons_test.json` | mismatch | Replace `results/story/kansas_season_eval.json` with `results/story/ks_seasons_test.json`. |
| Neighbour diagnostics: 0 of 32 contrasts passed | `submission.md:53`, `app/src/strings/en.json:442,462` | 0 of 32 fitted contrasts passed all checks in matched-history secondary design (T5.xa) | `results/neighbours/matching_diagnostics.md:14,29` | match (secondary) | Clarify that 0/32 refers to the secondary matching-history analysis (T5.xa): "0 of 32 matched-history contrasts (T5.xa)". |
| Neighbour diagnostics: 0 of 92 contrasts passed | `docs/gates/gate-5.md:9`, `results/neighbours/diagnostics.md:9` | 0 of 92 fitted contrasts passed all checks in unconditional primary design (T5.3) | `results/neighbours/diagnostics.md:9` | match (primary) | State explicitly in overview texts: "0 of 92 primary contrasts (T5.3) and 0 of 32 matched-history contrasts (T5.xa) passed diagnostics". |
| Neighbour diagnostics file citation for 0/32 contrasts | `README.md:114`, `app/src/strings/en.json:442,462` | 0/32 is from `matching_diagnostics.md`, not `diagnostics.md` | `results/neighbours/matching_diagnostics.md:14`, `results/neighbours/diagnostics.md:9` | mismatch | Replace citation `results/neighbours/diagnostics.md` with `results/neighbours/matching_diagnostics.md` when citing the 32 contrasts. |
| Evidence grade ceiling B (Grade A disabled) | `README.md:68,130`, `submission.md:53`, `app/src/strings/en.json:8,56,442` | Highest grade in Kansas is B because Witness 3 is OFF | `config/grading.yaml:26` (A requires 3 witnesses) | match | Keep as stated ("evidence grades top out at B because the neighbour witness is kept OFF"). |
| Scored hindcast sample size (n = 463 field-seasons) | `README.md:106`, `submission.md:65`, `app/src/strings/en.json:263,445` | Total scored field-seasons = 463 (197 winter wheat, 142 sorghum, 124 maize) | `results/hindcast/ks_t14slh.json:114,121-123`, `results/hindcast/grade_validity.json:5` | match | Keep as stated ("n = 463 field-seasons across 2022–2024"). |
| Baseline comparison sample size (n = 266 field-seasons) | `README.md:75`, `submission.md:61`, `DiagnosisSection.tsx:60` | Baselines B0, B1, B2 evaluated on 266 maize and sorghum field-seasons (winter wheat omitted) | `results/hindcast/ks_t14slh_baselines.json:5`, `results/hindcast/diagnosis.md:13` | match | Keep as stated ("266 labelled maize and sorghum field-seasons; winter wheat omitted from baselines"). |
| Winter wheat peak timing error description | `submission.md:66`, `app/src/strings/en.json:446` | Peak timing absolute error is 58.9 d [52.2, 66.3] d; signed median offset is +36.0 d | `results/hindcast/diagnosis.md:47-48`, `results/hindcast/diagnosis.json:18` | mismatch / incomplete | Update text to distinguish: "peak timing mean absolute error of 58.9 days and a median signed offset of +36.0 days late". |
| Winter wheat timing in README | `README.md:107` | Mean absolute error 58.9 d, signed median offset +36.0 d | `results/hindcast/diagnosis.md:47-48` | match | Keep as stated in README.md ("absolute error 58.9 d [52.2, 66.3] d; signed median offset +36.0 d"). |
| Hindcast CRPS vs baselines: Green-up date (19.3 vs 20.7 B0, 52% in 90% range) | `README.md:81`, `submission.md:62` | FW CRPS 19.30, covered90 52.3%; B0 CRPS 20.67 | `results/hindcast/ks_t14slh_baselines.json:17-19,54` | match | Keep as stated ("19.3 vs 20.7, 52% inside 90% range"). |
| Hindcast CRPS vs baselines: Peak date (11.5 vs 12.7 B2, 89% in 90% range) | `README.md:82`, `submission.md:62` | FW CRPS 11.47, covered90 88.7%; B2 CRPS 12.66 | `results/hindcast/ks_t14slh_baselines.json:26-28,137` | match | Keep as stated ("11.5 vs 12.7, 89% inside 90% range"). |
| Hindcast CRPS vs baselines: Season greenness (14.9 vs 15.1 B0, 35% in 90% range) | `README.md:83`, `submission.md:62` | FW CRPS 14.87, covered90 35.0%; B0 CRPS 15.13 | `results/hindcast/ks_t14slh_baselines.json:35-37,72` | match | Keep as stated ("14.9 vs 15.1, 35% inside 90% range"). |
| Hindcast CRPS vs baselines: Cover days (30.4 vs 25.3 B0, 9% in 90% range) | `README.md:84`, `submission.md:63` | FW CRPS 30.38, covered90 9.0%; B0 CRPS 25.30 | `results/hindcast/ks_t14slh_baselines.json:45-47,82` | match | Keep as stated ("30.4 vs 25.3, 9% inside 90% range"). |
| Grade validity verdict: Grade B vs Grade D difference | `README.md:106`, `submission.md:65`, `app/src/strings/en.json:263,445` | Diff (D - B) = 7.07, 95% CI [-3.28, 14.32]; B CRPS 16.96, D CRPS 24.02 (n=25) | `results/hindcast/grade_validity.json:10-14,22,46` | match | Keep as stated ("Grade B 17.0 vs Grade D 24.0; 95% CI of diff -3.3 to 14.3; n=25 for Grade D"). |
| Correlation metric in Roadmap Gate 3 (Pearson vs Spearman) | `app/src/strings/en.json:474` ("Pearson r = 0.264") | Spearman rank correlation rho = 0.2641 | `results/hindcast/ks_t14slh_baselines.json:39` (`"spearman": 0.26415`) | mismatch | Replace "Pearson r = 0.264" with "Spearman rho = 0.264". |
| Correlation metric in README Roadmap Gate 3 | `README.md:128` ("Spearman r = 0.264") | Spearman rank correlation rho = 0.2641 | `results/hindcast/ks_t14slh_baselines.json:39` | mismatch (notation) | Replace "Spearman r" with "Spearman rho" or "Spearman rank correlation = 0.264". |
| Diagnostic Diff vs B1 (+1.23 [0.48, 1.99]) & B2 (+1.35 [0.74, 1.90]) | `README.md:107`, `submission.md:66`, `DiagnosisSection.tsx:68,78` | Diff vs B1 = +1.23 [0.48, 1.99]; Diff vs B2 = +1.35 [0.74, 1.90] | `results/hindcast/diagnosis.md:13` | match | Keep as stated. |
| Diagnostic Sorghum Diff vs B1 (+0.77 [-0.10, 1.64]) | `README.md:107`, `submission.md:66`, `app/src/strings/en.json:446` | Sorghum diff vs B1 = +0.77 [-0.10, 1.64], 95% CI spans 0 | `results/hindcast/diagnosis.md:15` | match | Keep as stated. |
| 3D simulation parity check (max difference 0.0000057 mm) | `README.md:38-39`, `submission.md:42`, `app/src/strings/en.json:457` | 20 fields × 36 rotations × 3 weathers = 2160 runs, max difference 5.7e-6 mm | `results/validation/sim3d_parity.json:4` | match | Keep as stated ("max difference 0.0000057 mm"). |
| SSURGO check: simulation TAW median 142 mm vs SSURGO 282 mm (n = 198) | `README.md:567`, `app/src/strings/en.json:449` | Simulation median 142.1 mm vs SSURGO 281.8 mm, n = 198 | `results/validation/soil_ssurgo_check.md:14,24` | match | Keep as stated. |
| SoilGrids role in water balance | `submission.md:104-105` ("AWC at 250 m... Establishes baseline TEW and REW for soil water modeling") | SoilGrids not used for water balance; fixed 150 mm base placeholder (A) is used | `DECISIONS.md:565`, `app/src/strings/en.json:451,503` | mismatch | Correct submission.md: SoilGrids is used as coarse context/covariates; simulation starts from 150 mm baseline (A). |
| POWER terms and citation confirmation status | `app/src/strings/en.json:492` ("Terms and citation still to be confirmed...") | POWER citation verified: Sparks (2018), DOI: 10.21105/joss.01035; open data policy | `DATA.md:73-75` | mismatch (outdated string) | Update string: "NASA Open Data Policy (public domain); citation: Sparks (2018)". |
| Taxonomy licence confirmation status | `app/src/strings/en.json:528` ("Licence and citation still to be confirmed...") | GBIF Backbone (CC-BY 4.0, DOI: 10.15468/39omei) & USDA PLANTS verified | `DATA.md:84-87` | mismatch (outdated string) | Update string: "GBIF Backbone (CC-BY 4.0) & USDA NRCS PLANTS (public domain)". |
| HLS DOIs: `HLSL30.002` & `HLSS30.002` | `DATA.md:51`, `submission.md:76` | `10.5067/HLS/HLSL30.002` and `10.5067/HLS/HLSS30.002` | LP DAAC official DOIs (`DATA.md:51`) | match | Keep as stated. |
| SMAP L4 DOI: `SPL4SMGP` v008 | `DATA.md:96`, `submission.md:85` | `10.5067/T5RUATAQREF8` | NSIDC DAAC official DOI (`DATA.md:96`) | match | Keep as stated. |
| NASADEM DOI: `NASADEM_HGT` v001 | `DATA.md:89`, `submission.md:91` | `10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001` | LP DAAC official DOI (`DATA.md:89`) | match | Keep as stated. |
| SoilGrids 2.0 DOI | `DATA.md:78`, `submission.md:104` | `10.5194/soil-7-217-2021` | ISRIC publication DOI (`DATA.md:78`) | match | Keep as stated. |
| Test counts in README vs DECISIONS | `README.md:26` ("251 pytest tests") | 255 passed / 7 skipped pytest tests; 163 vitest tests | `DECISIONS.md:604` | mismatch (outdated) | Update README: "255 pytest tests passed (7 skipped), 163 vitest tests passed". |
| Repository tag name | `CLAUDE.md:28`, `DECISIONS.md:606` | `v1.0-spaceapps` (created by repository owner only) | `DECISIONS.md:606` | match | Keep untouched. |
| Sole live deployment URL | `README.md:10`, `submission.md:10`, `CLAUDE.md:23` | `https://amr-mousa-eg.github.io/fieldwitness/` | `README.md:10` | match | Sole canonical public URL. |

---

## 2. Forbidden Claims Audit

| Target | Rule | Finding / Status |
|---|---|---|
| Crop yield in tonnes / bushels | Forbidden (Rule 4) | **Clean.** Explicitly disclaimed in `README.md:173`, `submission.md:68`, `app/src/strings/en.json:433`. App outputs only dimensionless 0–1 Relative Yield Index (RYI). |
| Crop prices, revenues, or profits | Forbidden (Rule 4) | **Clean.** Explicitly disclaimed in `README.md:173`, `submission.md:68`, `app/src/strings/en.json:435`. No monetary units exist in packs or app strings. |
| "Measuring soil fertility / carbon from space" | Forbidden (Rule 4) | **Clean.** Explicitly disclaimed in `README.md:173`, `submission.md:68`, `app/src/strings/en.json:434`. Residue proxy is strictly marked as a proxy in `en.json:181`. |
| LLM / generative AI making recommendations | Forbidden (Rule 4) | **Clean.** Explicitly disclaimed in `AI_USE.md:7`, `README.md:174`, `submission.md:131`, `app/src/strings/en.json:436`. Explanations are deterministic template strings. |
| Misuse of "forecast" vs "hindcast" | Terminology precision | **Mostly clean.** Historical simulations without post-cut-off data are accurately defined as "forecast mode hindcasts". In `app/src/strings/en.json:619`, Field in 3D explicitly warns: "Simulated with the weather of {year}; not a forecast." |
| Misuse of "predicts" | Honesty guideline | **Monitored.** Where used (e.g. `en.json:431` "Every recommendation is a prediction"), it describes falsifiable empirical hypotheses evaluated against future satellite data, not prophetic assertions. |

---

## 3. Statements Overstating Evidence

1. **Winter Wheat Phenology Offset Presentation:**
   - In `submission.md:66` and `app/src/strings/en.json:446`, winter wheat timing error is described as an "offset of about 36 days late". This quotes only the signed median timing error (+36.0 d) while obscuring the larger mean absolute error of 58.9 d [52.2, 66.3] d (`results/hindcast/diagnosis.md:47`). The README (`README.md:107`) correctly quotes both.
2. **Correlation Metric Precision:**
   - `app/src/strings/en.json:474` states: "Pearson r = 0.264". The metric in `results/hindcast/ks_t14slh_baselines.json:39` is Spearman rank correlation rho = 0.264. Calling a rank correlation Pearson r overstates linear association.
3. **SoilGrids Water Capacity Role in Submission Draft:**
   - `submission.md:104-105` states that SoilGrids provides "available water capacity at 250 m resolution" to establish "baseline total evaporable water (TEW) and readily evaporable water (REW)". This contradicts `DECISIONS.md:565` and `app/src/strings/en.json:503`, which clarify that the simulation uses an assumed 150 mm base placeholder (A) and does NOT derive TAW from SoilGrids.

---

## 4. Status of Netlify, OpenET, POLARIS, and SSURGO

| Dataset / Host | Stated Status | Actual Status in Repository | Verdict |
|---|---|---|---|
| **Netlify** | Mirror URL removed from README per D3; sole URL is GitHub Pages | Present in `PLAN.md:465`, `DECISIONS.md:422`, `app/deploy/README.md`, `HOW_WE_BUILT_FIELDWITNESS.md`. | **Accurate.** Not presented as active live URL in user documentation. Configs in `app/netlify.toml` are explicitly marked "PREPARED, NOT DEPLOYED". |
| **OpenET** | Excluded from MVP; moved to stretch S6 | Never accessed; documented as excluded due to unverified commercial license terms in `DATA.md:83` and `submission.md:116`. | **Clean.** Accurately documented as unused. |
| **POLARIS** | Purged in Gate 0 as unverified/invented | Recorded in `README.md:118`, `en.json:466`, and `HOW_WE_BUILT_FIELDWITNESS.md:160` as a purged dataset. | **Clean.** Accurately documented as discarded historical exploration. |
| **SSURGO** | Re-introduced on 11 Nov for read-only independent check | Accurately documented in `DATA.md:79` and `en.json:448,504` as an independent validation check only (never a simulation input). However, `README.md:118` and `en.json:466` still lump SSURGO with POLARIS as "invented datasets removed", which creates an apparent contradiction unless qualified. | **Minor ambiguity.** `README.md:118` and `en.json:466` should clarify: "(purged in Gate 0; SSURGO re-verified in Phase 12 for an independent check only)". |

---

## 5. Audit Against the Feature Freeze

| Feature / Artifact | Freeze Status | Repository Reality | Verdict |
|---|---|---|---|
| **Rotation Builder** | Implemented 11 Nov behind `?builder=1`; enabled by default on 12 Nov | `app/src/featureFlags.ts:13-16` has builder enabled by default; kill switch is `?builder=0`. Outdated comments in `RotationBuilder.tsx:1` and `rotationBuilder.test.ts:1` still refer to `?builder=1`. | **Compliant.** Active by default; comments are harmless leftovers. |
| **Farm View** | Implemented 11 Nov behind `feature/farm-view`; enabled by default on 12 Nov | `app/src/featureFlags.ts:27-32` activates Farm view whenever builder is enabled; kill switch is `?farm=0`. Merged in PR #11 (`a3524f9`). | **Compliant.** Live and functional. |
| **Code Freeze Adherence** | Building frozen end of 12 Nov 2026; documentation and bug fixes only | No feature code added on `main` post-freeze. PRs #13, #14, #15 remain unmerged draft experiments by Claude Code. | **Compliant.** |
| **Tag `v1.0-spaceapps`** | Must not be created or touched by AI agents | Tag does not exist in local or remote repository. Awaiting owner creation. | **Compliant.** |

---

## 6. Top 5 Most Important Mismatches

1. **Season Detection Denominator & Non-Existent File Citation:**
   `README.md:113` and `app/src/strings/en.json:441,461,473` cite "155 of 198 field seasons" and reference `results/story/kansas_season_eval.json`. The source file does not exist; the actual evaluation is in `results/story/ks_seasons_test.json`, which evaluated **240 held-out field-years** (188/240 = 78.33%).
2. **SoilGrids Water Capacity Claim in Submission Draft:**
   `submission.md:104-105` claims ISRIC SoilGrids 2.0 provides "available water capacity at 250 m resolution" to establish "baseline total evaporable water (TEW) and readily evaporable water (REW)". In reality (`DECISIONS.md:565`, `en.json:503`), SoilGrids AWC is not used; the simulation uses a fixed 150 mm base placeholder (tag A).
3. **Correlation Metric Mislabeling (Pearson vs Spearman):**
   `app/src/strings/en.json:474` states "Pearson r = 0.264" for canopy integral hindcast evaluation, whereas `results/hindcast/ks_t14slh_baselines.json:39` and `README.md:128` confirm this is a **Spearman rank correlation** (rho = 0.264).
4. **Neighbour Diagnostics Citation Mismatch:**
   `README.md:114` and `app/src/strings/en.json:442,462` state "0 of 32 contrasts passed" (the matched-history secondary design, T5.xa) but cite `results/neighbours/diagnostics.md` (which documents the 92-contrast primary design, T5.3) instead of `results/neighbours/matching_diagnostics.md`.
5. **Incomplete Winter Wheat Timing Reporting in Frontend Strings:**
   `submission.md:66` and `app/src/strings/en.json:446` report only that winter wheat has a "peak timing offset of about 36 days late" (the signed median), omitting the mean absolute error of 58.9 d [52.2, 66.3] d documented in `results/hindcast/diagnosis.md:47`.
