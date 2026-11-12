# Appendix to "How we built FieldWitness"

This appendix belongs to [HOW_WE_BUILT_FIELDWITNESS.md](HOW_WE_BUILT_FIELDWITNESS.md). It holds the longer lists: the key commits per stage, the main numbers with their source files, and the facts that were re-checked against the files.

## A. Key commits per stage

Each line is a commit hash, its date and its message, taken from the git history. The lists are the "Where to look" commits of each stage, not every commit.

### Stage 0 — Reading the challenge and choosing the idea


### Stage 1 — Setting up the project and the way of working

- 1d3a3a5 2026-11-04 chore: scaffold repo (T0.1)
- 799f04a 2026-11-04 chore: ignore local agent skills; document _netrc credentials path

### Stage 2 — Getting access to the data

- 6034b1d 2026-11-04 feat: Earthdata access check and HLS-VI archive depth (T0.2)
- c88deff 2026-11-04 feat: AppEEARS and field-dataset access checks (T0.3, T0.4)
- 237bd3c 2026-11-04 feat: Gate 0 access checks, crop roles and verified families

### Stage 3 — Choosing where to work, and taking crop settings from FAO-56

- e3c47ec 2026-11-04 feat: data census and final region choice (T0.5)
- 79a385e 2026-11-04 feat: crop, region and grading configs from FAO-56 (T0.6)

### Stage 4 — Fields and their histories

- b3af2fd 2026-11-04 feat: Kansas pilot fields and field resolver (T1.4)
- 66442af 2026-11-04 feat: as_of leakage guard and POWER client (T1.1, T1.2); T1.5/T1.6 code
- f56aa80 2026-11-04 feat(T1.5): HLS series parser, QA rule, as_of reader, tests; downloads complete
- 2aa35ce 2026-11-04 feat: SoilGrids per pilot field (T1.3) and context datasets (T1.8 partial)

### Stage 5 — The field story: seasons and bare soil

- ca26373 2026-11-04 feat(T2.1,T2.5): SG smoothing, bare-soil calendar, story config, tests
- 603fca3 2026-11-04 feat(T2.2): seasons/phenology code and tests; acceptance check failed (74.6%), blocked
- 998af5f 2026-11-04 feat(T2.2): dormancy + crop-amplitude rules; dev 82.9%, fresh test 78.3% (target 90% missed, negative result)

### Stage 6 — The physics model: a water ledger for the soil

- ead4337 2026-11-04 feat(T3.1): FAO-56 daily ETo verified against Example 18; FAO-56 source
- c58ec37 2026-11-04 feat(T3.3): FAO-56 root-zone water balance (Eq. 82-85) with irrigation policies; T3.3 ticked
- 88ca5b2 2026-11-04 feat(T3.5): batched rotation simulation with soil-water carry-over; T3.5 ticked

### Stage 7 — Calibration: letting each field's own history tune the model

- 60b81d0 2026-11-07 feat(T4.1): hidden-variable priors (tag A) with sampler and tests
- 98171b7 2026-11-07 feat(T4.3): ABC rejection, recovery on synthetic fields, SVG plots, tests
- 494efb1 2026-11-07 feat(T4.4): simulation-based calibration rank histograms
- 461f513 2026-11-07 feat(T4.5): pilot-field credibility (ABC on real seasons), histogram, sorghum sow day (A)

### Stage 8 — The rotation engine

- 2e5d0b2 2026-11-07 feat(T6.1): candidate rotations with hard constraints, property test
- e12f2c3 2026-11-07 feat(T6.2): per-field evaluation of 61 candidates (200 fields, max 18 s)
- 449a43e 2026-11-07 feat(T6.3): Pareto + weighted ranking, regret matrix, 200 fields
- 79342cd 2026-11-07 feat(T6.5): grade all options vs simulated Current (physics + own past)
- db8de7d 2026-11-07 feat(T6.8): weather what-ifs, 12 scenarios x 200 fields
- c575436 2026-11-07 feat(T6.9): farmer corrections backend (Current rotation overrides, tag E)

### Stage 9 — The neighbour evidence (switched off)

- 1229691 2026-11-07 feat(neighbours): double ML previous-crop effects with block-grouped folds (T5.2)
- 47eb655 2026-11-07 feat(neighbours): T5.3 diagnostics (placebo, negative control, overlap, balance); 0/92 pass
- ad3e91a 2026-11-07 docs: Gate 5 review (fail, negative result); T5.4 blocked on paper access
- 554a0f9 2026-11-08 fix(autopilot): unblock loop; T5.4 literature check; subtask rules
- dee409f 2026-11-08 feat(T5.xa): matching-history neighbour design and diagnostics

### Stage 10 — Packing the results into one data file per field

- 30c8f78 2026-11-04 feat(schemas): final §3/§3b data contracts (Q1-Q7) in fieldwitness.schemas
- 0628b30 2026-11-07 feat(T8.1): pack builder part 1 (field pack, series, scenarios, index)
- 7cd207d 2026-11-07 feat(T8.1): pack validator, CI step, Gate 6 review
- ce69ebf 2026-11-07 fix(packs): store each option's rank, not the sort order; scenario ranks too
- fa07804 2026-11-07 feat(types): generate app/src/types.ts from the Pydantic schemas (T8.2, app compile unchecked)

### Stage 11 — Building the website

- 4b92da0 2026-11-04 feat(app): T9.1 shell + map view (MapLibre, offline service worker)
- 3758960 2026-11-04 feat(app): T9.2 field story and T9.3 field card (against SYNTHETIC fixtures)
- 081c955 2026-11-06 feat(app): T9.4 Advisor console (against SYNTHETIC fixtures)
- 5436ee3 2026-11-06 feat(app): T9.5 Hindcast scoreboard (against SYNTHETIC fixtures)
- 0ec0fdc 2026-11-07 feat(app): load real packs via sync-packs; fixes found on Kansas packs
- cd3a25a 2026-11-07 merge: branch app into main (Gate 6 merge)

### Stage 12 — Testing the model against the past

- a228b03 2026-11-07 feat(T7.1): Kansas hindcast, fieldwitness forecast+forced, scored (negative result logged)
- dc744b9 2026-11-07 feat(T7.3): baselines B0-B2 scored on Kansas hindcast (B3 not run)
- 1e24f1e 2026-11-07 feat(T7.2): hindcast.json, story ledger, CRPS figure (Kansas)
- 61fdf2a 2026-11-08 feat(T7.1b): Kansas hindcast with winter wheat (463 seasons), scored; weak skill kept as is
- 7dfa295 2026-11-08 feat(T7.4a): skill vs field size curve; no clear size trend, reported as is
- 2296e09 2026-11-08 feat(T7.4b): degraded-observation hindcast (50/25 % dates); no CRPS change, reported as is
- d54f122 2026-11-08 feat(T7.4c): ablation table from T7.3 baselines; tick T7.4

### Stage 13 — Putting it online

- e885221 2026-11-07 build(app): deployment prep for GitHub Pages and Netlify (not deployed)
- 90c6af7 2026-11-08 docs(T9.8): record live Netlify deployment URL and update plan ticks
- 9f81a89 2026-11-08 ci(deploy): configure GitHub Pages deployment and commit demo packs
- 05f9a5f 2026-11-08 ci(deploy): trigger github pages build
- dff337b 2026-11-09 fix(ci): resilient gitleaks download and safe test guard for packs

### Stage 14 — Moving to a new computer and a second AI assistant

- 037beb6 2026-11-08 docs: migration to second laptop (milestone M1, environment updates, handoff)

### Stage 15 — Polish

- 2820910 2026-11-08 docs(plan): add Phase 11 Polish work list (P0-P2) through 13 Nov freeze
- da1a8ab 2026-11-08 feat(polish): complete P0 polish tasks (basemap, readable fields, legend, light/dark mode, honest statements)
- ce2a214 2026-11-08 feat(polish): complete P1 tasks (lazy-load code-splitting, guidance panel, consistency pass, submission draft, a11y)

### Stage 16 — Speed fixes

- bbe53fe 2026-11-08 perf(pagespeed): eliminate pre-cache payload, batch field list, fix CLS, add SEO
- ad66fae 2026-11-08 fix(perf): resolve desktop layout shifts, GIBS tile bounding, and map startup blocking time
- 0662f39 2026-11-09 fix(perf): code-split tour and 3d views, correct tag E terminology, translucent amber crops, and header notice

### Stage 17 — Features added late

- 73131da 2026-11-09 feat(custom-field): implement 'Add my field' version 0 with true tile footprint check, local storage, nearest field match
- 1ccba79 2026-11-09 feat: empirical grade validity check and transparent scoreboard reporting
- 29df4a5 2026-11-09 feat(3d): implement Field in 3D tab with procedural scene and FAO-56 weekly series
- dc6ad14 2026-11-09 feat(tour): implement 7-step guided tour and add 2d fallback toggle to 3d view
- e021f3e 2026-11-09 docs(pre-reg): pre-register Item 1 diagnostic breakdown of hindcast skill
- b166c99 2026-11-09 feat(hindcast): diagnostic breakdown of hindcast skill across crops, years, sizes, and grades (Item 1)
- 4c4a566 2026-11-09 feat(card): 'Why this ranking?' explainer with score contribution breakdown (Item 7)
- d5a486a 2026-11-11 fix(app): tour button contrast, phone overflow, 3D weather year, low-zoom MODIS backdrop (#2)
- bc9ba40 2026-11-11 feat(validation): independent soil check vs USDA SSURGO (read-only) (#5)
- 6c8faad 2026-11-11 feat(3d): Rotation Builder (Level B, 3D only) behind ?builder=1 (#8)
- aefa104 2026-11-11 feat(3d): Farm view of Field in 3D (visuals only), behind the builder flag (#9)
- 5e426ca 2026-11-11 fix(3d): live theme and lag-free view toggles in Field in 3D (#10)
- a3524f9 2026-11-11 feat(app): Rotation Builder and Farm view on by default (#11)

### Stage 18 — The final state


## B. Main numbers and where they come from

| Number | Value | Source file |
|---|---|---|
| Recorded changes (commits) | 276, from 4 Nov to 11 Nov 2026 | git history |
| Pilot fields | 200 (89 winter wheat, 57 sorghum, 54 maize) from 9,905 candidates | results/pilot_fields/ks_t14slh_summary.json |
| Satellite field-dates | 134,685, all 200 fields, Sep 2015 to Dec 2024 | the HLS series data file (local data folder) |
| Labelled field-years | 1,600 of 1,600 (2017 to 2024) | results/labels/ks_t14slh_coverage.json |
| Season detection | 74.6% (first 30 fields), 78.3% on the fresh test set, target 90% | results/story/, DECISIONS.md, README.md |
| Credibility scores | 185 of 200 (101 full, 84 timing only), 15 not assessable, median 0.5 | results/inference/credibility.json |
| Options per field | 37 (Current plus 36 ranked) | any field pack in the demo folder |
| Grades over all options | B 2,772; C 3,600; D 360; 187 fields graded | results/rotate/grades_summary.json |
| Top option changes under what-ifs | 10% to 59.5% of fields, by scenario | results/rotate/scenarios_summary.json |
| Neighbour analysis | 144 effects, 92 fitted, 0 passed all checks; matched design 72 rows, 32 fitted, 0 shown | results/neighbours/, docs/gates/gate-5.md |
| Hindcast, 266 seasons | green-up 19.3 vs 20.7; peak 11.5 vs 12.7; greenness total 14.9 vs 15.1; cover days 30.4 vs 25.3 | results/hindcast/ks_t14slh_baselines.json |
| Grade validity, 463 seasons | grade B 16.96, grade D 24.02, difference 7.07, 95% interval from −3.28 to 14.32 | results/hindcast/grade_validity.md |
| Diagnosis | beats B1 by 1.23 and B2 by 1.35 overall; sorghum interval spans 0; winter wheat peak error 58.9 days | results/hindcast/diagnosis.md |
| Soil check | 198 of 200 fields; simulation about 142 mm against 282 mm; Pearson −0.09 | results/validation/soil_ssurgo_check.json |
| Rotation Builder parity | 20 fields, 2,160 runs, largest difference 0.0000057 mm | results/validation/sim3d_parity.json |
| Data files in the demo folder | 1,203 (200 fields times 6 files plus 3) | packs/demo |
| Largest data file | 279 kilobytes (the field index) | packs/demo |
| Tests | 274 Python tests; 190 website tests passed, 1 skipped | test collection and a run on 12 Nov |
| Starting code size | 1,785.76 kB to 273.64 kB | DECISIONS.md (P1.7) |
| Handoff commits by the loop | 106 (1 on 4 Nov, 83 on 7 Nov, 22 on 8 Nov) | git history |

## C. Facts re-checked against the files

These were checked directly against files or the git history on 12 Nov 2026, not copied from older reports.

1. Number of commits: 276 (git).
2. Per-field files and total files in the demo folder: 200 each of six kinds, 1,203 in all (directory listing).
3. Python tests: 274 collected. Website tests: 32 files, 190 passed, 1 skipped (a run).
4. Credibility counts and median (credibility.json).
5. Pilot crop quotas, 9,905 candidates, 116 of 121 blocks (summary file).
6. HLS rows: 134,685 for 200 fields from 2 Sep 2015 to 31 Dec 2024 (the data file).
7. Labelled field-years: 1,600 (coverage file).
8. Grade counts and number of graded fields (grades summary).
9. What-if range of top-option changes: 0.10 to 0.595 (scenarios summary).
10. Hindcast CRPS and coverage for FieldWitness and B0 (baselines file).
11. Grade-validity means, difference and interval (grade validity file).
12. Diagnosis table: maize, sorghum and winter wheat rows (diagnosis file).
13. Neighbour effect rows: 144 effects and 72 matched rows (row counts of the CSV files); pass counts from the gate review and diagnostics file.
14. Soil check: n = 198, Pearson −0.087, mean bias −119 mm, simulation median 142.5 mm (check file).
15. Rotation Builder parity numbers (parity file).
16. Handoff commits by date: 1, 83, 22 (git).
17. Co-author trailers: Sonnet 5.5 on 158 lines, Opus 5.5 on 69; none on the three 8 and 9 Nov commits checked (git).
18. Largest data file: the field index, 279 kB (file sizes).
19. Baseline B1 definition: FAO table method (baseline script docstring and plan), which differs from the README wording.
20. Fixed line "does not replace your judgment" exists in the website's text file.
