# Gate 1 review — Kansas (T14SLH), 2026-11-05

Gate 1 definition (PLAN.md): one full Tier 1 region has polygons, HLS series, weather, soil values for the pilot fields and labels on disk.

**Verdict: Gate 1 data layer PASSES for Kansas. Phase 2 has one FAILED acceptance test (T2.2). T1.7 is open (validation-only).**

Evidence: 127 tests pass, ruff check and format clean (2026-11-05).

## Gate 1 items

| Item | Result | Evidence |
|---|---|---|
| Polygons (T1.4) | PASS | 200 pilot fields from 9,905 CSB 2024 candidates; interior pixels match an independent GDAL count on 3 fields; `results/resolver_check.json` |
| HLS series (T1.5) | PASS | 134,685 field-dates, 200/200 fields, every year 2015–2024, mean clear fraction 0.95 |
| Weather (T1.2) | PASS | POWER 2001–2024, 8,766 days, no gaps (tile centre) |
| Soil (T1.3) | PASS | 5 properties × 6 depths × 4 stats × 200 fields = 24,000 values, 0 missing, tag E |
| Labels (T1.6) | PASS | 1,600/1,600 field-years labelled (CSB 2017–2024) |
| Context (T1.8) | PASS | GRACE trend, SMAP monthly anomaly (3 regions), NASADEM slope (Kansas only) |
| Water truth (T1.7) | UNVERIFIED / open | WIMAS needs the user to accept a disclaimer; ECOSTRESS not read. Validation-only, not required for Gate 1 |

## The three review checks

**(a) SoilGrids: no-data rule (tag A) vs real values.**
- The rule masks a cell when the property's `mean` coverage is 0 (WCS declares no nodata; raw 0 occurs over water/urban).
- Zero cells in the tile rasters: 676 of 238,286 (0.28 %) for every property and depth checked (`results/gate1_soil_nodata.json`, `scripts/gate1_soil_check.py`).
- Effect on the 200 fields: **0 of 24,000 values are missing**, so the rule never left a field without a value. 22 % of fields (per property, same for all five) have only one valid cell (field smaller than a 250 m cell, value taken from the cell under the representative point). No value in the pack comes from the rule itself; all are real SoilGrids values, tag E. Where the rule only masked cells, the choice stays an assumption (A).
- Field medians (mean stat, all depths pooled): bdod 1.39–1.68 kg/dm³ (median 1.53); clay 19.8–43.2 % (32.2); sand 6.0–56.9 % (16.9); silt 23.1–62.5 % (50.1); SOC 1.5–20.5 g/kg (6.5).
- Not done: a per-field count of masked cells inside field footprints and a masked vs non-masked comparison (UNVERIFIED how many fields had any masked cell). UNVERIFIED whether the 0 = no-soil reading is correct for every depth.

**(b) Irrigated/rainfed stratification.** NOT DONE. WorldCereal needs a Terrascope login (user-only). No split exists. Consequence: water-balance results for Kansas cannot be stratified by irrigation until the user supplies access, or WIMAS (T1.7) is accepted.

**(c) 12-pixel sampling.** Seeded, pixel centres, interior pixels only (15 m inward buffer). 2,325 sampled pixels over 200 fields; **15 of 200 fields have fewer than 12 interior pixels** (minimum 4). Those fields use all their interior pixels.

## Phase 2 status carried into this gate

| Test | Result | Evidence |
|---|---|---|
| T2.1 smoothing property test | PASS | `tests/test_story.py` |
| T2.5 bare-soil calendar | PASS | 200/200 fields, 0 insufficient months |
| **T2.2 season count ≥ 90 %** | **FAIL** | 74.6 % on the original 30; dev 82.9 %; fresh test set 78.3 % (run once). `results/story/ks_seasons_test.json`. Winter wheat weakest (0.66). Not ticked; no further tuning (user decision 2026-11-04) |
| T2.3 classifier | not started | inherits a 78 %-accurate season detector |

## Open risks

- T2.2 failure is reported, not hidden. Anything using seasons must say "78 % detector".
- Only Kansas has fields; Ukraine and Toulouse have context data but no resolved fields, HLS series or soil yet.
- Phase 3 physics T3.1–T3.6 are done (tests only; no real-field run yet).
