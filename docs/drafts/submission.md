<!-- DRAFT (branch app, 2026-11-07). Space Apps 2026 submission texts.
     The field names and length limits are UNVERIFIED: the 2026 Project Submission Guide is released
     13 Nov 2026, and submission is open 14 Nov 09:00 to 15 Nov 23:59 local time
     (spaceappschallenge.org). Fit the texts to the guide when it is out.
     Fill in: team name, app URL, repo URL (the repo must be public), video or slides link if required. -->

# Space Apps 2026 submission: FieldWitness

Challenge: **Field Shift: Adapting Farms with NASA Data**

## Project summary

FieldWitness is a free web app that helps a farmer compare crop rotations for their own field. For
each option, it shows the following:
- water use, bad-year water use and bare-soil months;
- erosion exposure and a 0–1 Relative Yield Index;
- an A–D grade for how strong the evidence is.

The evidence comes from three independent witnesses:
- a FAO-56 water-balance model driven by NASA POWER weather;
- the field's own 30 m satellite history from NASA's Harmonized Landsat Sentinel-2 (HLS), back to
  2013;
- similar neighbouring fields (planned).

Every recommendation is saved as a prediction that next season's satellite data can score. We
tested this honestly on 200 Kansas fields. The tool supports farmer judgment; it does not replace
it.

## Detailed description

**What it does.** A user picks a field on the map. The app then shows four views.

- **Field story:** the field's seasons since 2013, from HLS vegetation index, with green-up, peak
  and end dates.
- **Options:** the current rotation and 3-season alternatives.
  - Priority sliders: water, bare-soil months, bad-year risk, erosion, nitrogen-fixing crops,
    organic matter input.
  - Constraints: banned crops, irrigation, water cap, crops the farmer can sell.
  - Weather what-ifs: temperature and rainfall shifts applied to past weather.
- **Calendar:** observed and simulated bare-soil months, and the months when each crop is most
  exposed to heat, frost, water stress or extreme rain.
- **Advisor console:**
  - how credible the physics is for this field;
  - which measurement would most reduce uncertainty;
  - the smallest change that would flip the top option;
  - a back-test of past predictions.

Map layers colour fields by erosion, water-stress or frost share, and show regional GRACE
water-storage and SMAP soil-moisture trends with their coarse resolution flagged. Each option
explains why it was suggested, what evidence supports it, its benefits, its information gaps, and
the risks that need local review.

**How it works.**
- **Witness 1, physics:** a FAO-56 root-zone water balance forced by NASA POWER daily weather.
- **Witness 2, the field's own past:**
  - the field's HLS history calibrates the physics by approximate Bayesian computation;
  - how well the calibrated model reproduces past seasons gives a credibility score.
- **Witness 3, neighbours:** double machine learning on previous-crop effects across similar
  fields. It is designed, but not finished for this submission.
- **Grades:** an agreement engine turns the witnesses into grades A–D.
- **Ranking:** a Pareto filter with user-movable weights ranks the options.

**How we kept it honest.**
- **Source tags:** every number carries one.
  - O: observed by satellite.
  - D: derived by a model from satellite data.
  - E: external data.
  - A: assumption.
- **Scale:** coarse data (POWER, SMAP, GRACE, SoilGrids) is used only as context or forcing.
  Field-level claims use 30 m HLS interior pixels.
- **No leakage:** a date guard stops the hindcast from reading data after its cut-off.
- **The hindcast:**
  1. We froze all data on 31 Dec 2021.
  2. We predicted 266 maize and sorghum field-seasons in 2022–2024.
  3. We scored the predictions against HLS, together with three simpler baselines.
- **Hindcast result:**
  - FieldWitness had the lowest error (CRPS) for green-up date, peak date and season greenness,
    by small margins.
  - A simple field-average baseline was better for ground-cover days.
  - Our uncertainty ranges were too narrow for most measures.
  - We publish this as it is.
- **Not claimed:** no yields in tonnes, no prices or profits, no soil fertility "measured from
  space", and no AI deciding.

**Benefits.**
- A farmer sees the trade-offs between options (water, bare soil, erosion, risk in a bad year) for
  their own field, not a regional average.
- The farmer sees how much to trust each comparison.
- Every prediction can be checked against later satellite data.

**Tools.**
- Pipeline: Python 3.12, with `earthaccess` and AppEEARS for NASA data.
- Web app: React, Vite, TypeScript, MapLibre and Recharts.
- Delivery: static, works offline, no login, no server.

**Limits.**
- Only one region is built: Kansas, 200 pilot fields.
- The neighbour witness is not finished, so no option gets grade A.
- The season detector reached 78 % against a 90 % target.
- Only maize and sorghum have calibrated physics.

## NASA data

- **HLS:** `HLSL30` and `HLSS30` v2.0 surface reflectance and the `HLSL30_VI` / `HLSS30_VI` v2.0
  vegetation indices (LP DAAC, through earthaccess and AppEEARS). They give the field story,
  calibration and hindcast scoring, at 30 m with interior pixels only.
- **NASA POWER:** the daily point API, AG community (temperature, humidity, wind, solar radiation,
  corrected precipitation). It drives the water balance and the crop-vulnerability calendar.
- **SMAP L4** `SPL4SMGP` v008 (NSIDC, through AppEEARS): regional root-zone soil-moisture anomaly
  (9 km, context only).
- **GRACE/GRACE-FO** JPL mascons `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` (PO.DAAC): regional
  water-storage trend (context only).
- **NASADEM** `NASADEM_HGT` v001 (LP DAAC): field slope, for erosion exposure.
- **ECOSTRESS** `ECO_L3T_JET` v003: found in CMR, but not used in this release.

Product DOIs are to be added from `DATA.md` (T10.1).

## Other data

- **USDA NASS Crop Sequence Boundaries 2017–2024:** field boundaries and crop labels for Kansas
  (public domain).
- **Fields of the World:** global field-boundary predictions (CC-BY-4.0). Listed for the planned
  regions; not used for Kansas.
- **ISRIC SoilGrids 2.0:** soil properties (CC-BY 4.0).
- **FAO-56** (Allen et al. 1998) crop coefficients, stage lengths and yield-response factors.
  FAO-66 was also checked for yield-response factors.
- **FAOSTAT** crop statistics (CC-BY-4.0).
- **GBIF Backbone Taxonomy** and **USDA NRCS PLANTS:** crop families. Licence text to be confirmed.
- **EuroCrops HCAT3** taxonomy (CC-BY-SA-4.0) and French RPG data (Licence Ouverte 2.0). Listed for
  the planned France region.

Full access paths, licences and attributions are in `DATA.md`.

## Use of artificial intelligence

- **How the tool was built:** we built FieldWitness with Claude Code (Anthropic), an AI coding
  assistant. It wrote most of the code, tests and documentation under our direction, and we
  reviewed its work at fixed gates.
- **Rules it worked under:**
  - never invent data, results or citations;
  - verify every API against its official documentation;
  - take formula constants from the cited papers;
  - record failed checks.
- **Marking:** AI-assisted commits carry a `Co-Authored-By: Claude` trailer. `AI_USE.md` explains
  how we used it.
- **The product itself:** it contains no AI that makes or ranks recommendations. It uses a
  documented physics model, Bayesian calibration, statistics and fixed explanation templates. The
  farmer makes the decision.
