<!-- DRAFT: FieldWitness Space Apps 2026 Submission
     NOTE: Field names and length limits to verify against the official 2026 Submission and Judging Guide on 13 Nov.
     Submission window: 14 Nov 09:00 to 15 Nov 23:59 local time (spaceappschallenge.org).
     Verification status: All claims, numbers, and limitations grounded in repository results/ and verified datasets. -->

# Space Apps 2026 Submission: FieldWitness

Challenge: **Field Shift: Adapting Farms with NASA Data**

- **Live Application:** https://amr-mousa-eg.github.io/fieldwitness/
- **Repository:** https://github.com/amr-mousa-eg/fieldwitness
- **Pilot Region:** Kansas, USA (HLS tile T14SLH, 200 pilot fields)

---

## 1. Project Summary
*(Field names and length limits to verify against the 2026 guide on 13 Nov)*

FieldWitness is a public, no-login, offline-capable decision support web application that helps farmers evaluate crop rotation alternatives for their own fields. For every rotation option, the system evaluates:
- Water consumption, dry-year drought risk, and bare-soil exposure windows;
- Erosion exposure on local slopes and a non-monetary 0–1 Relative Yield Index;
- Transparent A–D evidence grades backed by three independent witnesses.

The evidence comes from:
1. **Physics:** An FAO-56 root-zone water balance forced by NASA POWER daily surface meteorology;
2. **The Field's Own Past:** 30 m satellite history from NASA's Harmonized Landsat Sentinel-2 (HLS) back to 2013, calibrating physics via approximate Bayesian computation;
3. **Neighbours:** Natural experiments across nearby fields evaluated with causal double machine learning (currently kept OFF in Kansas grading because structural rotation history imbalance and placebo/control tests failed pre-registered diagnostics).

Every recommendation is saved as an empirical prediction that next season's satellite observation will verify. The tool transparently supports human judgment without replacing local agricultural experience.

---

## 2. Detailed Description
*(Field names and length limits to verify against the 2026 guide on 13 Nov)*

### What it does
A farmer or advisor selects a field from the map or searchable list. The interface provides synchronized views:
- **Field Story:** Satellite vegetation history at 30 m resolution since 2013, tracking green-up, peak canopy, senescence, and historical harvest years.
- **Rotation Options & "Why this ranking?" explainer:** Compares the field's current rotation against 3-season alternatives. Users can adjust priority sliders (water conservation, soil cover, drought resilience, erosion risk, nitrogen fixation, organic matter), apply operational constraints (banned crops, irrigation status, water caps, marketable crops), and simulate weather what-if scenarios (temperature and rainfall shifts applied to historical weather). A transparent score contribution table and bar chart explains why the top-ranked option ranks first over the next-best alternative.
- **Calendar View:** Shows observed and simulated bare-soil months to target cover crop placement, alongside seasonal vulnerability windows when crops face elevated heat stress, frost risk, water deficit, or extreme precipitation.
- **Field in 3D:** Interactive procedural 3D root-zone soil water balance, crop canopy progression, and water-stress visualization (Ks) driven by FAO-56 simulation over median weather and what-ifs, with a 2D canvas fallback. Labelled "Illustration of simulated values — not a photo."
- **Rotation Builder:** "Build your own rotation" lets a user place crops in three seasons and press Grow. Only the field's 36 ranked rotations can be built (disabled cards state the rule). The comparison table (water use, bad-year water, bare-soil months, evidence grade) comes from the ranking; the 3D replay re-runs the same FAO-56 water balance in the browser and matches the Python model (20 fields × 36 rotations × 3 weathers, max difference 0.0000057 mm).
- **Farm View:** An illustrated isometric farm with two plots, the current rotation and the user's, on the same field, weeks and weather. Crops, bare soil, sprinklers, rain and sky follow the weekly simulated values; the barn, trees, pond, fences and paths are labelled "Scenery, not data". "Soil X-ray" switches to the glass soil view. Limits: one median-rain weather year, not a forecast; seasons the model does not simulate are shown as "not simulated"; frame rates measured only with software rendering.
- **Advisor Console & Scoreboard:** Reports the calibration credibility score for the field, identifies which measurement would most reduce decision uncertainty, computes the minimum parameter shift needed to flip the top recommendation, and evaluates hindcast accuracy against empirical baselines, diagnostic breakdowns, and pre-registered grade-validity tests.
- **Add My Field (Version 0):** Zero-server client-side field digitizer and rotation evaluator running entirely in the farmer's browser using local storage without server uploads.
- **Guided Tour:** 8-step "try it" walkthrough (field card, season, priority weights, ranking explainer, 3D simulation, building a rotation, limits, adding a field), each step ticked by a real action in the app.

Overlays include field-scale slope erosion exposure, regional GRACE/GRACE-FO water storage trends, and SMAP soil moisture anomalies (clearly flagged as coarse regional context). Every recommendation explains why it was suggested, its supporting evidence, benefits, data gaps, and risks requiring local review.

### How it works
1. **Witness 1 (Physics):** Implements the FAO-56 dual crop coefficient root-zone water balance model, computing daily transpiration, soil evaporation, and water stress forced by NASA POWER solar radiation, temperatures, humidity, wind speed, and precipitation.
2. **Witness 2 (Field's Own Past):** Calibrates crop rooting depth and soil water capacity against the field's multi-year HLS vegetation index curve using Approximate Bayesian Computation (ABC), generating a 0–100% past credibility score.
3. **Witness 3 (Neighbours):** Evaluates previous-crop rotation effects using Double Machine Learning with spatial cross-fitting. In Kansas, pre-registered diagnostic tests (covariate balance across historical crop sequences and placebo/negative controls) failed (0 of 92 primary contrasts and 0 of 32 matched contrasts passed all checks). Consequently, an automated AI safety circuit breaker keeps the neighbour witness strictly OFF in grading, capping Kansas evidence grades at B.
4. **Grading & Ranking:** An agreement engine synthesizes active witnesses into evidence grades A–D. A Pareto filter and regret minimizer rank options according to user preferences.

### How we kept it honest
- **Source Tagging:** Every quantitative figure displays a source tag: `[O]` observed by satellite, `[D]` derived by model from satellite data, `[E]` external non-NASA ground data, or `[A]` human assumption.
- **Spatial Resolution & Scale Flags:** Field-specific claims strictly use interior 30 m pixels from HLS. Coarser datasets (NASA POWER at ~50 km, SMAP at 9 km, GRACE at 0.5°) are explicitly flagged with `◌` (coarse) indicators and restricted to regional background context.
- **Strict Leakage Prevention:** All hindcast evaluations enforce a strict 2021-12-31 data freeze; no post-cut-off satellite observations or weather data are accessible to the model during backtesting.
- **Honest Hindcast Results:**
  - Evaluated on 266 maize and sorghum field-seasons across 2022–2024 against three baselines (B0 field mean, B1 regional mean, B2 uncalibrated physics).
  - FieldWitness achieved lower CRPS on green-up date (19.3 vs 20.7), peak date (11.5 vs 12.7), and season greenness total (14.9 vs 15.1), but by modest margins.
  - Baseline B0 outperformed FieldWitness on ground cover days (25.3 vs 30.4).
  - 90% uncertainty intervals were under-dispersed (holding 52% of green-up dates, 35% of greenness totals, and 9% of cover days). These limitations are transparently published in the app and documentation.
  - **Grade Validity Check:** Pre-registered test could not show that evidence grades predict forecasting accuracy (n = 463 field-seasons: grade-B CRPS 17.0 vs grade-D 24.0, difference 95% CI [-3.3, 14.3]; grade D had only 25 field-seasons; verdict: not shown).
  - **Hindcast Diagnostic Breakdown:** FieldWitness forecast-mode canopy integral CRPS beats B1 (diff +1.23 [0.48, 1.99]) and B2 (+1.35 [0.74, 1.90]) overall and for maize, but does not strictly beat baselines for sorghum (+0.77 [-0.10, 1.64], 95% CI spans 0). Winter wheat has no baseline run (existing baseline code is single-calendar year only) and exhibits a peak timing absolute error of 58.9 d [52.2, 66.3] d with a signed median offset of +36.0 d (untested explanation: uncalibrated phenology prior stage lengths).
- **Negative Results Preserved:** The season detection algorithm missed its pre-registered 90% accuracy target (achieving 78.3% on held-out test data, 188 of 240 field-seasons; 74.6% in pilot checks). Rather than tuning post-hoc, this failure is published openly in the UI and methods documentation.
- **No Overclaiming:** No yield predictions in tonnes, no speculative profit calculations, no claims of "measuring soil carbon from orbit", and no opaque AI decision-making.

---

## 3. NASA Data Used
*(Field names and length limits to verify against the 2026 guide on 13 Nov)*

1. **Harmonized Landsat Sentinel-2 (HLS):**
   - Products: `HLSL30` v002 (Landsat 8/9 OLI, DOI: 10.5067/HLS/HLSL30.002) and `HLSS30` v002 (Sentinel-2A/B MSI, DOI: 10.5067/HLS/HLSS30.002) surface reflectance, Fmask quality bands, and pre-computed vegetation index layers (`HLSL30_VI`, `HLSS30_VI`).
   - Role: Provides 30 m resolution time series (2013–2024) of field interior pixels for NDVI/EVI historical trajectory, ABC calibration, and hindcast verification.
2. **NASA GIBS True-Colour Basemap:**
   - Layer: `HLS_S30_Nadir_BRDF_Adjusted_Reflectance` via NASA Global Imagery Browse Services (GIBS) / LP DAAC (EPSG:3857, Level 0..12 tiles).
   - Role: Cloud-free 30 m summer true-colour basemap (2023-07-04) aligned with field boundaries and fence-lines. Attribution: *Imagery: NASA GIBS / LP DAAC (HLS S30, 2023-07-04)*.
3. **NASA POWER Daily Meteorology API (AG Community):**
   - Parameters: Daily maximum/minimum temperature (T2M_MAX, T2M_MIN), relative humidity (RH2M), surface wind speed (WS2M), solar radiation (ALLSKY_SFC_SW_DWN), and precipitation (PRECTOTCORR).
   - Role: Forces the FAO-56 dual crop water balance model and populates crop thermal/frost vulnerability calendars.
4. **SMAP Level 4 Soil Moisture:**
   - Product: `SPL4SMGP` v008 (DOI: 10.5067/T5RUATAQREF8).
   - Role: Regional 9 km root-zone soil moisture anomaly context layer.
5. **GRACE / GRACE-FO JPL Mascons:**
   - Product: `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` via PO.DAAC.
   - Role: Regional terrestrial water storage decadal anomaly and trend context.
6. **NASADEM Global Elevation:**
   - Product: `NASADEM_HGT` v001 (DOI: 10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001) at 1 arc-second (~30 m).
   - Role: Derives local field slope to compute relative water erosion exposure.
7. **ECOSTRESS (Evaluation Only):**
   - Product: `ECO_L3T_JET` v003 investigated via CMR for evapotranspiration cross-checks; preserved for post-hackathon pipeline expansion.

---

## 4. Other Datasets Used
*(Field names and length limits to verify against the 2026 guide on 13 Nov)*

1. **USDA NASS Crop Sequence Boundaries (CSB), 2017–2024 Edition:**
   - Role: Provides field boundary geometry and annual crop classification labels for Kansas pilot fields (public domain).
2. **ISRIC SoilGrids 2.0:**
   - Properties: Clay, sand, silt fraction, bulk density, and organic carbon at 250 m resolution (CC-BY 4.0; DOI: 10.5194/soil-7-217-2021).
   - Role: Provides regional soil texture and organic carbon context and serves as background confounders in neighbour causal analysis. (Not used to derive root-zone water capacity in the simulation, which uses a calibrated 150 mm baseline).
3. **FAO Irrigation and Drainage Paper 56 (FAO-56):**
   - Tables 11, 12, 17, 22, and 24: Basal crop coefficients ($K_{cb}$), stage lengths, root depths, depletion fractions ($p$), and yield response factors ($K_y$).
4. **EuroCrops HCAT3 Taxonomy & French RPG:**
   - Standardized crop classification codes for European multi-region architecture (CC-BY-SA 4.0 / Licence Ouverte 2.0).
5. **GBIF Backbone Taxonomy & USDA NRCS PLANTS Database:**
   - Crop botanical family definitions used to enforce rotation family-break constraints (CC-BY 4.0 / Public domain).
6. **Fields of the World (FTW):**
   - AI-derived field boundaries (CC-BY 4.0) evaluated as candidate source for future global regions; not used in Kansas pilot.
7. **Kansas WIMAS:**
   - State water diversion database identified for ground-truth irrigation cross-checks.
8. **OpenET:**
   - Explicitly excluded from MVP due to unverified commercial license terms.

---

## 5. Use of Artificial Intelligence
*(Field names and length limits to verify against the 2026 guide on 13 Nov)*

- **Development Assistance:** FieldWitness was engineered using agentic AI pair programming tools—**Claude Code** (Anthropic) and **Google Antigravity** (Google DeepMind)—under strict human supervisory control across defined milestone gates.
- **Working Agreement & Guardrails:**
  - Strict prohibition against fabricating citations, datasets, or mathematical constants;
  - Every API endpoint verified with live documentation before code execution;
  - Mandatory logging and visibility of all negative test outcomes;
  - Comprehensive pre-commit secret scans (gitleaks) and zero credential leakage;
  - Co-authorship trailers (`Co-Authored-By`) attached to AI-assisted commits.
- **AI Absence in Product Core:** The FieldWitness runtime engine contains **zero generative AI models or opaque neural networks making agricultural recommendations**. All decision-support metrics are calculated deterministically from published FAO equations, empirical Bayesian calibration, and transparent Pareto dominance logic with user-governed weights.
