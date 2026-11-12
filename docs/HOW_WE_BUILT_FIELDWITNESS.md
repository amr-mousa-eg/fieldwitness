# How we built FieldWitness: from the first idea to the live website

*Written 12 Nov 2026, about the project as it stood at its last recorded change (commit a3524f9, dated 11 Nov 2026). Every fact comes from the project's own records. Where the records are silent, this document says so.*

FieldWitness is a website that helps a farmer or farm advisor think about crop rotation. A rotation is the order in which crops are grown in the same field over the years, for example wheat, then fallow (a season left unplanted), then sorghum. For each of 200 real fields in Kansas, USA, the site lists possible three-season rotations and ranks them. It does not decide for anyone. It shows the evidence behind each option, says how strong that evidence is with a grade from A to D, and treats each recommendation as a prediction that later satellite pictures can check. It was built for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting Farms with NASA Data".

## The 60-second version

- The project started on 4 Nov 2026 in the records and reached its latest recorded state on 11 Nov 2026: 276 recorded changes in about eight days.
- The idea: every recommendation should rest on three independent "witnesses": a physics model of soil water, the field's own satellite history, and what neighbouring fields did.
- The team used NASA data (satellite pictures of fields since 2013, daily weather, and more) plus U.S. field maps and crop records, and the open FAO-56 guide for crop water use.
- The team chose Kansas, USA, for the first and, so far, only region: 200 fields, picked by measurement, not by hand.
- Two of the three witnesses work. The third, "neighbours", was tried, failed its own pre-set tests, and was switched off. As a result, no option can earn grade A. The best possible grade is B.
- The team tested the model against the past: it "predicted" 2022 to 2024 using only data up to 31 Dec 2021, then compared with what satellites saw. The results are mixed and are published as they are.
- Several tests did not go well: the season detector missed its target (78.3% against 90%), the neighbour evidence failed, and the grades could not be shown to predict accuracy. All of this is stated on the website.
- The website runs on the visitor's own device from pre-computed data. It needs no login, and it keeps working offline after the first visit.
- AI coding assistants (Claude Code, and Google Antigravity for part of the work) wrote most of the code under the team's direction. The website itself contains no AI that makes recommendations.
- Late additions include a 3D view of the soil, a "build your own rotation" tool, an illustrated farm view, a guided tour, and an "Add my field" page.

## Contents

<!-- TOC -->

## How to read this document

Each stage has the same parts: the goal, the steps, the reasoning, an everyday comparison, the results, what went wrong, and where to look. Stages overlap in time, because several things were built at once. If two records disagree, the text says which one was trusted.

## Mini glossary

- **Satellite data:** pictures and measurements taken from space that cover the same places again and again.
- **HLS (Harmonized Landsat Sentinel-2):** a NASA product that combines two satellite families into one set of pictures with a 30-metre pixel, roughly the size of a small house plot. FieldWitness uses it to see how green each field is through the year.
- **Pixel:** one square dot of a satellite picture.
- **Simulation (model):** a computer calculation that imitates how something works, here how water moves through soil and crops.
- **FAO-56:** a public guide from the United Nations food agency. It gives the formulas and tables for how much water crops use.
- **Soil water balance:** a daily ledger of the soil's water: rain and irrigation go in; plant use, evaporation and drainage take it out.
- **Calibration:** adjusting a model's unknown settings until it matches what was really observed. Here, each field's own satellite history is used.
- **Credibility score:** a number from 0 to 1 for how well the calibrated model reproduced a field's own past seasons.
- **Witness:** one independent line of evidence. FieldWitness has three: physics, the field's own past, and neighbours.
- **Evidence grade (A to D):** a letter for how well the witnesses agree on an option. A needs all three witnesses. B is the best possible today.
- **Source tag:** a one-letter label on every number: O observed by satellite, D derived by a model from satellite data, E external non-NASA data, A assumption.
- **Hindcast:** testing a forecasting method on the past. You pretend it is an earlier date, forecast, then check against what really happened.
- **Baseline:** a deliberately simple method used as a yardstick. If a fancy method cannot beat the baseline, the fancy part is not adding much.
- **CRPS:** a score for forecasts that give a range of possible outcomes. Lower is better.
- **Field pack:** one data file per field, holding everything the website needs to show that field.

## Timeline

| Stage | Dates (2026) | What was built | Key result |
|---|---|---|---|
| 0 Challenge and idea | Before 4 Nov (not recorded); 4 Nov | Reading the challenge; first plan | Plan written; three-witness idea set |
| 1 Project set-up | 4 Nov | Repository, automatic checks, secret scanning, working rules | Checks passed on GitHub |
| 2 Data access | 4 Nov | Tested every data source before use | Most sources worked; some blocked or dropped |
| 3 Regions and crops | 4 Nov | Data census; crop settings from FAO-56 | Kansas chosen; 11 crops configured |
| 4 Fields and histories | 4 to 5 Nov | 200 Kansas fields, satellite series, crop labels, soil | 134,685 field-dates; 1,600 labelled field-years |
| 5 Field story | 4 Nov | Season and bare-soil detection | Season detection 78.3% vs 90% target (missed) |
| 6 Physics model | 4 Nov | Soil water balance | Reproduces the FAO-56 worked example |
| 7 Calibration | 7 Nov | Matching the model to each field's history | 185 of 200 fields get a credibility score |
| 8 Rotation engine | 7 to 8 Nov | Rotation list, ranking, grades, explanations, what-ifs | 36 ranked rotations per field; grades B, C, D only |
| 9 Neighbour evidence | 7 to 8 Nov | Natural-experiment analysis | 0 of 92 comparisons passed; switched off |
| 10 Field packs | 4 and 7 Nov | One data file per field, with strict checks | 200 field packs, no problems found |
| 11 The website | 4 to 7 Nov | Map, field story, field card, calendar, advisor console, scoreboard, methods | Joined to the real data on 7 Nov |
| 12 Testing on the past | 7 to 8 Nov | Hindcast and baselines | Small edge on some measures; weak overall |
| 13 Going online | 7 to 9 Nov | Hosting set-up | Live on GitHub Pages |
| 14 New computer | 8 Nov | Move to a second laptop and a second AI assistant | All tests passed on the new machine |
| 15 Polish | 8 Nov | Satellite basemap, readable names, legend, light and dark mode | All polish tasks done |
| 16 Speed | 8 to 9 Nov | Faster loading | Starting code cut by 84.7% |
| 17 Late features | 9 to 11 Nov | Add my field, 3D view, tour, diagnosis, builder, farm view | Several more honest negative results |
| 18 Final state | 11 Nov | Everything on by default | See the final sections |

## Stage 0 — Reading the challenge and choosing the idea

**Dates:** Before 4 Nov 2026 (the records don't say when work began); the challenge text and the first plan are dated 4 Nov 2026.  
**The goal in one sentence:** Turn the official challenge into a clear plan that a small team and AI assistants could build in days.

**What we did, step by step:**
1. The team copied the official challenge text, "Field Shift: Adapting Farms with NASA Data", into the project on 4 Nov. It asks for a tool that compares crop rotations, explains each one, and supports a farmer without replacing the farmer's judgment.
2. A written plan (PLAN.md) set out the work in phases, each ending in a "gate": a check that must pass before the next phase starts. Claude Code reviewed the first version. Its answers produced version 1.1, for example pinning the Python version and starting with a small end-to-end "walking skeleton" for one region.
3. The same day, a second addition (version 1.2) matched the plan to the challenge line by line. It added the field's current rotation as option 1, a five-part explanation for every option (why suggested, evidence, benefits, information gaps, risks), a calendar of bare-soil months, a calendar of the seasons when crops are most at risk, and sliders for weather what-ifs.
4. The plan fixed the core idea: three independent "witnesses" behind every option. It also fixed what the site must never claim: yield in tonnes, soil fertility measured from space, price or profit forecasts, or a language model making the decision.
5. The plan listed candidate regions in three tiers and left the final choice to a measurement (Stage 3).

**Why we did it this way:** The plan says to build "the smallest demo that is still the real idea" first, end to end, and widen only afterwards. The "never claim" list was meant to keep the site honest from the start.

**Analogy:** Reading the exam question twice and writing an outline before writing the essay.

**What came out of it:** A plan in phases with gates, a list of what each challenge requirement maps to, and a fixed set of rules for how the AI assistants must work (Stage 1).

**What went wrong or surprised us:** The plan cited a 2025 research paper as "confirmed by the planning research". Claude Code marked that as unverified until it could open the paper. The paper was checked later (Stage 9). The records don't say what existing tools or papers the team reviewed before writing the plan, who drafted version 1.0, or why this idea was chosen over others.

**Where to look:** PLAN.md (sections 1, 1b and 2), docs/official_challenge.md, DECISIONS.md (entry "Plan review").

## Stage 1 — Setting up the project and the way of working

**Dates:** 4 Nov 2026.  
**The goal in one sentence:** Build a clean workshop first: a code repository, automatic checks, a secret scanner, and written rules for the AI assistants.

**What we did, step by step:**
1. Claude Code created the repository layout (commit 1d3a3a5): a place for the data code, the physics, the website, the tests and the results. Python was pinned to version 3.12, because the newest version on the machine was too new for the map-data tools.
2. GitHub, the website that stores the code, was set up to run automatic checks on every change. These are a test run and a secret scan. The secret scan uses a tool called gitleaks, which looks for passwords and keys that must never be published.
3. A rule file (CLAUDE.md) was written with twelve hard rules. The main ones: never invent data, endpoints or citations; test every outside data service with one small call before using it; label every number with a source tag; report failures; run the secret scan before every commit; and ask before downloading more than 1 gigabyte, adding a new software package, or changing the data layout.
4. A working agreement was set: do one task at a time, state a short plan first, and count a task as done only when its acceptance test passes and the plan is ticked.
5. The NASA login details were stored outside the project in a private file. The user fixed a formatting error in it so that login worked.

**Why we did it this way:** Rule 1 and rule 2 exist because AI assistants can produce convincing but invented details. The secret scan and the "ask first" rules limit the damage a mistake can do.

**Analogy:** Setting up a lab with safety rules, a lab book and a checklist before the first experiment.

**What came out of it:** The first change passed both automatic checks on GitHub. From then on, every later change was recorded in a dated log (DECISIONS.md).

**What went wrong or surprised us:** Installing two tools on Windows hung, so they were installed another way (one from a checksum-verified download). The formatter reformatted the plan's Markdown and damaged a section; it was restored and the formatter was told to skip Markdown files. The scanner's ready-made hook failed on Windows, so a local version was used. A first check of the GitHub results used a login token taken from the computer's credential manager. That led to a new rule 12: never pull tokens or passwords out of credential managers.

**Where to look:** CLAUDE.md, DECISIONS.md ("T0.1 scaffold choices", "T0.2 progress"), commits 1d3a3a5 and 799f04a, the .github folder.

## Stage 2 — Getting access to the data

**Dates:** 4 Nov 2026.  
**The goal in one sentence:** Prove, with one small real request each, that every data source the plan needs actually works.

**What we did, step by step:**
1. NASA login: Claude Code logged in to NASA's data service, searched for the satellite pictures of the Kansas tile, and found one for 4 Jul 2023. It also found that the cloud-and-shadow mask lives in a different NASA product than the greenness values, so two products must be read together.
2. Satellite archive depth: for 2016 to 2024 every year had pictures, but 2016 and 2017 had fewer (65 and 83 scenes against roughly 160 to 205 in later years). This was recorded as a data limit.
3. AppEEARS, a NASA service that cuts out the data for chosen places: a test request finished in about 22.5 minutes and returned 17 files, all verified by checksum.
4. Field boundary and crop datasets: boxes were read from three sources. The U.S. Crop Sequence Boundaries (CSB) gave 20,190 field polygons in the Kansas box. French field data gave 6,198 in a test box in the Beauce. A global field-boundary set gave 15,529 in a Punjab test box. A size cap of 200 megabytes per query stopped an over-large Kansas read, and the user chose to skip it because CSB was the Kansas source anyway.
5. Weather, soil and others: NASA POWER daily weather worked. The soil service SoilGrids was down. The Kansas water-use records (WIMAS) needed someone to accept a disclaimer. The user, not the assistant, had to decide that. The service OpenET was moved out of the main scope until the user read its terms.

**Why we did it this way:** Rule 2 says to test before using. The user then split the data sources into "essential" ones (satellite, weather, field maps, soil) and "validation only" ones (water-use records, ECOSTRESS heat data), so a missing validation source would not block the whole project.

**Analogy:** Checking that every road, bridge and petrol station on the route is open before planning the trip.

**What came out of it:** Satellite, weather, field-boundary and crop-label sources were confirmed. The real response formats were written down in a notes file.

**What went wrong or surprised us:** The office network blocked a software add-on used to read remote files (an error saying the transfer was blocked by company policy). The user decided not to work around the block, and a different tool was used. A second login to the AppEEARS service cancelled the first one's access, which showed up later as an error (Stage 4). Early AI exploration also proposed two soil sources (POLARIS and SSURGO) that had not been verified. They were dropped and only SoilGrids was used. (SSURGO came back on 11 Nov for a check only, Stage 17.) Broken links to dataset identifiers (DOIs) in the data documentation were found by an automatic link check and replaced.

**Where to look:** docs/api_notes.md, DECISIONS.md (entries "T0.2" to "Gate 0 rule change"), DATA.md, commits 6034b1d, c88deff, 237bd3c.

## Stage 3 — Choosing where to work, and taking crop settings from FAO-56

**Dates:** 4 Nov 2026.  
**The goal in one sentence:** Choose the first regions by measuring them, not by guessing, and load each crop's water settings from the published FAO-56 guide.

**What we did, step by step:**
1. A "census" counted, for six candidate areas, how many usable satellite scenes there were, how big the fields were, and how many fields were large enough to measure. Candidates were Kansas, two areas in France (Beauce and Toulouse), central Ukraine, the Nile Delta and Punjab.
2. The user set a measurement rule: a field is measurable only if at least four whole 30-metre satellite pixels fall inside it, keeping 15 metres away from the edge. The edge distance was changed from 30 to 15 metres, which lifted the Kansas share from 88.6% to 98.1%.
3. The user defined a "field" as an annual arable crop parcel, using an official crop-class table (HCAT3, 278 classes kept). A later design fix said that fallow and temporary-grass years stay in a field's crop history, because dropping them would break rotations such as wheat, fallow, wheat.
4. The user chose the final regions on 4 Nov: Kansas first, Toulouse second, central Ukraine third. Ukraine passed its checks (median field 3.29 hectares in a small sample of 141 fields, 73.8% measurable). Toulouse failed the checks on all parcels but passed (87.5% measurable) once only arable parcels were counted. The Nile Delta was kept only as a data showcase and Punjab was rejected.
5. The crop settings file was built from FAO-56 tables: 11 crops, 82 values read from the guide's tables and 9 marked as team assumptions. Each crop's plant family was checked against two plant databases (GBIF and USDA PLANTS).

**Why we did it this way:** Choosing by numbers made the decision traceable. Taking constants from the published tables, not from memory, follows rule 8 (formulas and values must cite their source).

**Analogy:** Surveying several building plots (soil, access, size) before buying one, and copying the building code from the official book, not from memory.

**What came out of it:** Three tiers of regions on paper. Only Kansas was carried through to the website; France and Ukraine remain planned.

**What went wrong or surprised us:** A filter rule for one crop group used the wrong text prefix and wrongly dropped neighbouring crops such as safflower. A check against the official table caught it. Many satellite scenes cover only a small part of a tile (median coverage of 15% to 25% in some Punjab and Nile seasons), so raw scene counts overstated the data. The Ukraine boundary read was over the size cap, and the user approved a one-off read.

**Where to look:** docs/census/, DECISIONS.md ("Final regions", "Design fix"), config/regions.yaml, config/crops.yaml, docs/hcat_annual_arable.md, commits e3c47ec, 79a385e.

## Stage 4 — Fields and their histories

**Dates:** 4 to 5 Nov 2026.  
**The goal in one sentence:** Pick the 200 Kansas pilot fields and collect each one's satellite greenness history, crop labels, soil and surroundings.

**What we did, step by step:**
1. From 9,905 candidate Kansas parcels (annual arable in 2024, a crop the project models, enough interior pixels, inside the tile), the program picked 200 pilot fields: 89 winter wheat, 57 sorghum and 54 maize. It spread them over 116 of the 121 ten-kilometre blocks, using a fixed random seed. The median field is about 32 hectares.
2. Satellite greenness for every field: asking for whole areas hit the service's output limits, so the team used point requests instead, in 30 tasks. The data came to about 1.3 gigabytes, which is above the 1 gigabyte rule, so the user approved a one-time exception.
3. The result is 134,685 field-dates for all 200 fields across 2015 to 2024, with a mean clear-sky share of 95%.
4. Crop labels came from CSB for 2017 to 2024: all 1,600 field-years were labelled.
5. Weather: NASA POWER daily weather from 2001 to 2024, with no gaps (8,766 days). Soil: SoilGrids through its backup map service, 24,000 values with none missing. Context: land slope (median 1.55 degrees), a regional water-storage trend from the GRACE satellites (Kansas about −0.93 cm of water per year since 2002), and a regional soil-moisture signal from SMAP.
6. A guard called "as_of" was built so that code can only read data dated before a chosen cut-off date. Tests run every data reader under a 31 Dec 2021 cut-off and fail if one reads later data.

**Why we did it this way:** The guard makes later forecast tests honest (Stage 12). The coarse data (weather, soil moisture, water storage) is used only as background; field-level claims use the 30-metre satellite pixels, because a coarse pixel can cover many fields.

**Analogy:** Gathering the medical history for 200 patients: records, measurements and the same rules about which records the doctor may look at.

**What came out of it:** Gate 1 (the data checkpoint) was reviewed on 5 Nov and passed for Kansas.

**What went wrong or surprised us:** The service's login token is shared, so one program's logout cancelled another's access and caused a "forbidden" error; the downloader now logs in again once. Neither of two early estimates of the download size was exact. Field ids in the CSB files do not carry over from year to year, so each year uses the polygon that contains the pilot field's centre point. The Kansas water-use records and an irrigated-or-not split were not obtained, because they need user action (a disclaimer or a separate login). Fifteen fields have fewer than 12 interior pixels (the minimum is 4).

**Where to look:** results/pilot_fields/, results/labels/, docs/gates/gate-1.md, DECISIONS.md ("Phase 1 (Kansas) log"), commits b3af2fd, 66442af, f56aa80, 2aa35ce.

## Stage 5 — The field story: seasons and bare soil

**Dates:** 4 Nov 2026.  
**The goal in one sentence:** Turn each field's raw greenness curve into a readable story: when each crop season starts and peaks, and which months the soil is usually bare.

**What we did, step by step:**
1. The greenness curves were smoothed with a standard method (Savitzky–Golay) to remove noise from clouds.
2. Code found the seasons in each curve and the crop growth phases within them.
3. A bare-soil calendar was built for every field: for each month, the share of past years when the field was bare. All 200 fields had enough data for every month. The "bare" cut-off (0.30 on the greenness scale) is a team assumption, tagged A.
4. The season detector was tested against the known crop labels with a rule set before the test. The acceptance rule was at least 90% of seasons right.

**Why we did it this way:** The bare-soil calendar answers a challenge requirement directly (when are fields typically bare?). The test rule was fixed first so the result could not be bent to fit.

**Analogy:** Reading a heart-rate trace and marking where each beat starts and peaks, then checking your marks against a doctor's.

**What came out of it:** The calendar works. The season detector did not reach its target: 74.6% on the first 30 fields (240 field-years), 82.9% on a development set after adding two extra rules, and 78.3% on a fresh test set run once (155 of 198 field-seasons). Winter wheat and fallow were the weakest.

**What went wrong or surprised us:** The target was missed and the user decided not to tune further. The result was kept on record, and the app says so. A planned crop classifier (task T2.3) was postponed to keep the end-to-end build moving. Because of this, crop timing windows in the model are team choices, not detected values.

**Where to look:** results/story/, DECISIONS.md ("T2.2"), commits ca26373, 603fca3, 998af5f.

## Stage 6 — The physics model: a water ledger for the soil

**Dates:** 4 Nov 2026.  
**The goal in one sentence:** Build the first witness: a calculation of how much water each crop and rotation would find in the soil, day by day.

**What we did, step by step:**
1. Reference evapotranspiration (ET, the water a standard grass surface would lose to the air each day) was computed from NASA POWER weather with the FAO-56 formula. The tests reproduce the FAO-56 guide's own worked example.
2. A crop coefficient curve was added. It scales the reference ET to each crop's growth stage, following the guide's figure and two climate-adjustment equations.
3. The soil water balance was written as a daily ledger following FAO-56 equations 82 to 85. Rain and irrigation add water. Crop use, evaporation and deep drainage subtract it. A stress factor reduces crop use as soil dries. Automatic property tests check that water is conserved every day and that values stay within their limits.
4. Season outputs: water use, irrigation, a 0-to-1 Relative Yield Index (how much water shortage held a crop back, not tonnes), a canopy proxy to compare with the satellite, and the number of days with ground cover.
5. A rotation simulation carries soil water from one season and fallow period into the next. A vulnerability calendar counts, for each crop, how often heat, frost, water stress or extreme rain hit its sensitive stages.

**Why we did it this way:** FAO-56 is the standard public method, so each number can be traced to a published equation. The ledger carries water across seasons, so a thirsty crop leaves the next crop a drier soil.

**Analogy:** A bank account with deposits (rain), withdrawals (plants and sun) and a balance (soil water).

**What came out of it:** Physics for all pilot crops. A test benchmark of 200 fields with 30 parameter sets over 20 weather years took 8.4 seconds.

**What went wrong or surprised us:** On the first try the assistant stopped because it could not open the FAO-56 text, and rule 8 forbids using constants from memory. Work resumed once the FAO-56 text was on hand (the records don't say who supplied it). Several settings (for example, fallow ground cover and runoff) are team assumptions. A later soil check (Stage 17) found the model's soil water capacity far below an independent soil survey.

**Where to look:** src/fieldwitness/physics/, docs/fao56_equations.md, PLAN.md (Phase 3), commits ead4337, c58ec37, 88ca5b2.

## Stage 7 — Calibration: letting each field's own history tune the model

**Dates:** 7 Nov 2026.  
**The goal in one sentence:** Build the second witness: adjust the model's unknown settings for each field until it imitates that field's own past satellite seasons, and score how well it succeeded.

**What we did, step by step:**
1. Five unknown settings per field were listed: the sowing-date offset, a soil water capacity scale, whether the field is irrigated, the seasonal irrigation amount, and a crop-coefficient scale. Each got a starting range with a written reason. All are marked as assumptions (tag A).
2. Made-up test fields with known answers were generated, with the same noise and cloud gaps seen in real Kansas data.
3. The method is called approximate Bayesian computation, or ABC. It runs thousands of guesses for the five settings, compares each simulated season with the satellite curve, and keeps the closest guesses (300 out of 6,000 per year in the test).
4. The method was checked on 300 made-up fields, then with a second test on 500 (simulation-based calibration, which asks whether the stated ranges are honest).
5. On the real fields, a credibility score was computed from how well simulated and observed seasons agreed in rank order and in timing.

**Why we did it this way:** ABC needs no assumptions about the shape of the errors, and testing on made-up fields with known answers shows what the method can and cannot recover. The scores are computed only from data before the cut-off date.

**Analogy:** Tuning a guitar string against a reference note: try settings, listen, keep the ones closest to the target.

**What came out of it:** 185 of 200 fields get a credibility score: 101 with three or more seasons ("full") and 84 with fewer ("timing only"). The median is 0.5, and 42.7% of fields score 0.6 or more. The other 15 fields, which only grew winter wheat, cannot be scored, because only maize and sorghum are calibrated.

**What went wrong or surprised us:** On the made-up fields, three settings (soil water capacity, irrigation amount, crop-coefficient scale) were recovered within five percentage points but with little new information. The sowing offset was over-cautious, and "irrigated or not" was right 77% of the time. In the second test, two settings had honest ranges, two had ranges that were too wide, and one was skewed. These negative results were reported. The scores are in-sample (the same data trained and scored). The planned check of irrigation against Kansas water-use records (T4.6) was never done, because those records were not obtained. The plan keeps T4.5 unticked.

**Where to look:** results/inference/, config/priors.yaml, src/fieldwitness/infer/, commits 60b81d0, 98171b7, 494efb1, 461f513.

## Stage 8 — The rotation engine

**Dates:** 7 to 8 Nov 2026.  
**The goal in one sentence:** List every allowed three-season rotation, simulate each, rank them by the farmer's priorities, grade the evidence, and explain each in plain words.

**What we did, step by step:**
1. The field's current rotation (from its last three seasons) always appears first, labelled "Current".
2. Candidate rotations were built from five Kansas choices: maize, sorghum, winter wheat, fallow and a cover crop. Hard rules removed bad ones. Crops must fit the calendar. No more than two seasons in a row from the same plant family. Each rotation needs at least one harvested crop. No two non-crop seasons (fallow or cover) in a row. The last two rules were added on 7 Nov. Of 61 sequences first listed, 36 candidates remained per field.
3. Each candidate was simulated over many possible soil settings and weather years 2001 to 2021. Measured outputs: water use, irrigation, a Relative Yield Index per rotation year (the user chose that definition on 7 Nov), bare-soil months, and "bad-year water", the average of the driest 10% of years.
4. Ranking: options that are worse on everything are removed, then the rest get a weighted score. The default weights are assumptions, and the website's sliders let the user change them.
5. Grades A to D come from how well the witnesses agree. A "what to measure next" advice and the smallest change that would flip the top option were computed.
6. Explanations were written from fixed templates over the computed numbers, with no language model. Priority metrics cover nitrogen-fixing crops, pest-cycle breaks, an erosion exposure index, an organic-matter input proxy, deep rooting and forage value.
7. Twelve weather what-ifs per field (three temperature shifts times four rainfall shifts) were precomputed. Farmers can also correct a field's crop history, sowing date or irrigation, and that correction is kept only in their browser.

**Why we did it this way:** The challenge asks for at least three strategies including the existing one, each with a reason, evidence, benefits, gaps and risks. Templates keep every sentence traceable to a number.

**Analogy:** A hiring panel that scores each candidate on several criteria, shows its working, and lets you change how much each criterion matters.

**What came out of it:** 187 fields were graded across 36 options each: 2,772 got B, 3,600 got C and 360 got D, and none got A. For 13 fields the current rotation could not be simulated, so they have no grades. The what-ifs show the ranking is fragile: the top option changes in 10% to 59.5% of fields, depending on the scenario.

**What went wrong or surprised us:** Early ranking runs rewarded bare fallow, because it uses no crop water. It was fixed by adding bare-soil penalties and diversity rules. Results were re-run on 7 Nov after the yield-index definition and the new rules changed. Later (Stage 10) a bug stored the position in the sorted list instead of the rank. Counts for the weather what-ifs had been taken from intermediate output, not the final files. Both were fixed and covered by automatic tests.

**Where to look:** src/fieldwitness/rotate/, config/ranking.yaml, config/grading.yaml, results/rotate/, commits 2e5d0b2, e12f2c3, 449a43e, 79342cd, db8de7d, c575436.

## Stage 9 — The neighbour evidence (switched off)

**Dates:** 7 to 8 Nov 2026.  
**The goal in one sentence:** Build the third witness: learn from natural experiments, where similar neighbouring fields grew different previous crops, to estimate what the previous crop does.

**What we did, step by step:**
1. A table of 1,400 field-seasons (1,040 with measured outcomes) was assembled.
2. The user approved two new software packages (scikit-learn and doubleml). The method is double machine learning, a way to estimate the effect of a choice while adjusting for other differences between fields. Test folds kept whole 10-kilometre blocks together.
3. Before running, four pass-or-fail checks with fixed thresholds were set: overlap (do the compared groups look alike?), balance, a placebo test (an effect that should be zero), and a negative control.
4. A literature check on 8 Nov compared the signs of the results with a published paper's table: 2 agreed, 1 disagreed and 13 were inconclusive. The check is descriptive only.
5. A second design matched fields with the same two-year history. A third idea, adding more satellite tiles, was costed and stopped by the 1-gigabyte rule.

**Why we did it this way:** Pre-set thresholds stop the team from keeping only the results that look good. A failed check means the number must not be shown as evidence.

**Analogy:** A school exam where the pass mark is written before the paper is marked.

**What came out of it:** The first analysis produced 144 effect estimates, 92 of them fitted. 20 had intervals excluding zero, but no correction for repeated testing was made (about five false alarms are expected). None of the 92 passed all four checks, and balance failed for all of them, because the crop two years back is tied to the previous crop. The matched design (72 rows, 32 fitted) passed the overlap check in all 32 and the balance check in 8, but none passed every check. The neighbour witness stays off, evidence grades stop at B, and the neighbour-only baseline (B3) was never run. Each extra tile would need about 1.23 gigabytes.

**What went wrong or surprised us:** The result is negative and is stated as such. The paper check was blocked for a day because the unattended assistant could not open the paper. The README quotes "0 of 32" and the gate review "0 of 92": they describe the matched and the first analysis. The result files back both. The assistant loop also kept re-running the blocked task (see "The way of working").

**Where to look:** results/neighbours/, docs/gates/gate-5.md, src/fieldwitness/neighbours/, commits 1229691, 47eb655, ad3e91a, 554a0f9, dee409f.

## Stage 10 — Packing the results into one data file per field

**Dates:** 4 Nov (data contracts) and 7 Nov 2026 (pack builder).  
**The goal in one sentence:** Give the website one tidy, checked data file per field, so it runs without a server.

**What we did, step by step:**
1. The exact shape of each data file ("schemas") was written once in Python and approved by the user on 4 Nov (a change to it needs approval, rule 11).
2. A pack builder writes, for each field, a field pack (with 37 options: Current plus 36 ranked), a greenness series, a calendar file and a what-if file. Later, two 3D files were added (Stage 17). There are also region-level files for the field index, the map layers and the hindcast.
3. A validator checks every file. No untagged number is allowed, and no file may be 300 kilobytes or larger (the largest is 279 KB). It runs in the automatic checks on GitHub.
4. The website's data types are generated from the Python shapes automatically, so the two cannot drift.

**Why we did it this way:** One data file per field keeps loading small and lets the site work offline. Tagging every number stops unlabeled values from reaching users.

**Analogy:** A standard form for each patient file, with a clerk who rejects incomplete forms.

**What came out of it:** All 200 Kansas packs validate with no problems (Gate 6, 7 Nov). The current demo folder holds 1,203 files: 200 fields with six files each, plus three region files.

**What went wrong or surprised us:** On the first real-data load the rank saved in each file was the sort position, not the true rank (commit ce69ebf, fixed 7 Nov). Tests that need data stored only on the builders' machines are marked, so that GitHub's checks stay green without that data (commit 34ac382).

**Where to look:** src/fieldwitness/schemas.py, src/fieldwitness/packs/, scripts/gen_types.py, docs/gates/gate-6.md, commits 30c8f78, 0628b30, 7cd207d, ce69ebf, fa07804.

## Stage 11 — Building the website

**Dates:** 4 to 7 Nov 2026.  
**The goal in one sentence:** Build the screens a farmer or advisor would use, while the data was still being made.

**What we did, step by step:**
1. The website was started on a separate branch, using made-up "SYNTHETIC" sample data that follows the real data shapes. A build guard refuses to publish a site built on fake data, and a banner marks it.
2. The first screens (4 Nov) were the map with an offline-ready set-up, the field story and the Field Card.
3. On 6 and 7 Nov came the Advisor console, the scoreboard of past predictions, the calendar, plain-language explainers with cited sources, map layers (erosion, water stress, frost, regional water storage and soil moisture), a Methods page, responsive layout and accessibility.
4. On 7 Nov the site was connected to the real Kansas packs. This revealed a few bugs, which were fixed. The branch was merged into the main code line, called the Gate 6 merge.
5. On 8 Nov a panel for farmer corrections was added.

**Why we did it this way:** Building on sample data in parallel saved time. The guard prevents an embarrassing mistake: showing invented numbers as real.

**Analogy:** Building a shop display with mock products while waiting for the stock to arrive, and a sign that the products are props.

**What came out of it:** The five core views work for all 200 fields: Map, Field story, Field Card, Advisor Console and Hindcast scoreboard. The tools are React, Vite, TypeScript and MapLibre (a map library).

**What went wrong or surprised us:** The first real-pack load revealed wrong rank values (Stage 10). Package installs were blocked in unattended runs, so some app checks waited for a person to approve them.

**Where to look:** app/src/, app/fixtures/, commits 4b92da0, 3758960, 081c955, 5436ee3, 0ec0fdc, cd3a25a.

## Stage 12 — Testing the model against the past

**Dates:** 7 to 8 Nov 2026 (extra analyses 9 Nov, see Stage 17).  
**The goal in one sentence:** Check honestly whether the whole method forecasts better than simple methods.

**What we did, step by step:**
1. The cut-off date was set to 31 Dec 2021. All data after it was fenced off by the "as_of" guard, and tests make sure no reader can pass it.
2. For every field, the method re-ran Stages 5 to 8 using only older data and "predicted" the 2022, 2023 and 2024 seasons.
3. Predictions were scored against what the satellite really saw. Two modes were used: forecast mode uses past weather only, and forced mode uses the actual weather.
4. Three baselines were scored on the same field-seasons. B0 is the field's own earlier seasons of the same crop. B1 is the FAO table method with default dates and soil. B2 is the same physics with no calibration. B3, a neighbour-only baseline, was not run.
5. On 7 Nov the first run covered 266 maize and sorghum field-seasons. On 8 Nov winter wheat was added: 463 field-seasons in all.

**Why we did it this way:** A forecast method can only be trusted if it beats a simple one on data it has never seen.

**Analogy:** A school exam on questions the student never saw, with last year's average class mark as the comparison.

**What came out of it:** On the 266 maize and sorghum seasons (lower scores are better):

| Measure | FieldWitness | Best baseline | 90% range held the truth |
|---|---|---|---|
| Green-up date | 19.3 | 20.7 (B0) | 52% |
| Peak date | 11.5 | 12.7 (B2) | 89% |
| Season greenness total | 14.9 | 15.1 (B0) | 35% |
| Ground cover days | 30.4 | 25.3 (B0, better) | 9% |

FieldWitness leads on three of four measures, by small margins. Its ranges are too narrow. Across fields, the field's own past mean (B0) ordered the fields better (rank correlation 0.33 against 0.26). Other tests: no clear trend with field size, and no change when only half or a quarter of the satellite dates were kept.

**What went wrong or surprised us:** The weak skill was found on the first run, logged, and kept as it was, with no tuning. Winter wheat has no baseline, because the baseline code handled single-calendar years only.

**Where to look:** results/hindcast/, scripts/t73_baselines.py, PLAN.md (Phase 7), commits a228b03, dc744b9, 1e24f1e, 61fdf2a, 7dfa295, 2296e09, d54f122.
