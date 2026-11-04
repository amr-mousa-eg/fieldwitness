# PLAN.md — FieldWitness implementation plan

Version 1.2 · 4 Nov 2026 · Hackathon 14–15 Nov 2026 (submission closes 23:59 local time on 15 Nov).

**Changes in v1.1** (answers to Claude Code's first review): Python pinned to 3.12; gitleaks CLI instead of the Action; a walking-skeleton milestone (§1); explicit tagging rule and schema fixes (§3); season-year convention (T2.2); batched physics runtime targets (T3.5, T6.2); two hindcast modes and documented boundary leakage (Phase 7); HLS true-colour basemap for offline use (T9.1); Kluger et al. 2025 citation confirmed (T5.4).

**Changes in v1.2** (addendum merged 4 Nov 2026, user): pre-event build schedule (§6 replaced); challenge alignment with the official text in `docs/official_challenge.md` (§1b); new tasks T1.8, T2.5, T3.6, T3.7 (stretch), T6.0, T6.6–T6.9, T9.9–T9.11; T9.3 changed; `Explanation` added to `Option` (§3); fixed "does not replace your judgment" line; Phase 10 deployment note.

This plan is ordered so that the end-to-end loop works early and gets better later. Never start a phase before the previous phase's **gate** passes. Stretch tasks (`S*`) only start when every MVP task is ticked.

> **Pre-event build (v1.2).** Code written before the event is assumed allowed (see DECISIONS.md; to be confirmed against the official 2026 Submission Guide on 13 Nov). Build the full MVP before 13 Nov; 13 Nov is a review and freeze day; 14–15 Nov are for polish, demo and submission. The CLAUDE.md working agreement is unchanged: one task at a time, plan first at the start of each phase, gates still apply.

---

## 1. Goal and definition of done

**Goal:** a public, no-login static web app plus a public repo. For pilot fields in three regions it shows the field's satellite story, three ranked rotation options with A–D evidence grades, the witnesses behind each grade, what to measure next, and a hindcast scoreboard comparing FieldWitness against baselines on 2022–2024.

**Definition of done (MVP)**

- [ ] App deployed at a public URL; loads in a private browser window with no login; works with Wi-Fi off after first load.
- [ ] Five views work for every demo field: Map · Field story · Field Card · Advisor Console · Hindcast scoreboard.
- [ ] Hindcast (cut-off 2021-12-31, scored on 2022–24) completed for ≥ 1 Tier 1 and ≥ 1 Tier 3 region, with baselines B0–B3, results in `results/hindcast/`.
- [ ] All tests green in CI; leakage tests pass; no untagged numbers in packs.
- [ ] README, DATA.md (every dataset + licence), AI_USE.md, LICENSE present.

**Walking skeleton first (the smallest demo that is still the real idea).** Build this end to end before widening anything:

- Kansas only (Tier 1), ~200 pilot fields, crops maize / winter wheat / sorghum / fallow (soybean dropped: 0.1 % of the T14SLH tile in CSB 2024, T0.6).
- Witness 1 (physics) + Witness 2 (ABC calibration, credibility) + ledger hindcast vs baselines B0–B2.
- Views: Map · Field story · Field Card · Hindcast scoreboard (Advisor Console may start as a simple panel).
- Grades use only physics + credibility until Witness 3 exists (max grade B).

Then add, in this order: Witness 3 (Tier 1) → Advisor Console → Tier 3 region → Tier 2 region. Each addition must leave the app deployable.

## 1b. Challenge alignment (v1.2)

The official challenge text is in `docs/official_challenge.md`.

| Challenge asks | Status in v1.1 | Change |
|---|---|---|
| Compare at least three rotation strategies, **including the existing rotation** | Options are new sequences only | **T6.0**: the field's current rotation (from its story) is always option 1, labelled "Current"; at least 2 alternatives; benefits and regret are shown relative to Current |
| For each strategy: **why suggested, evidence, benefits, information gaps, risks for local review** | Grades + witnesses only | **T6.6**: a deterministic `Explanation` with these five parts on every option (no LLM) |
| Times when fields are **typically bare** | `bare_days` per season | **T2.5**: monthly bare-soil calendar from HLS history |
| Seasons when current crops are **more vulnerable** (heat stress, frost, water stress, extreme rain) | Not covered | **T3.6**: crop-stage vulnerability calendar |
| Farmer priorities: water use, **forage value, N-fixing, erosion reduction, organic matter, market suitability** | Water, cover, RYI | **T6.7**: priority metrics, all tagged, with proxies named as proxies |
| Interrupt **pest cycles** | Family-break constraint only | Shown as a metric: number of family breaks (T6.7) |
| **Long-term water trends**; GRACE/GRACE-FO, SRTM, SMAP, MODIS | SMAP context only | **T1.8**: GRACE/GRACE-FO regional water-storage trend (context, scale-flagged); SRTM slope for erosion exposure; SMAP root-zone anomaly context |
| Supportive tool, does not replace farmer judgment | Non-promises list | Add one fixed line to the Field Card and the Methods page; the "risks for local review" part of every option |

From the Potential Considerations on the official page (optional for teams, but judges will read them):

| Consideration | Status | Change |
|---|---|---|
| Explain ET, soil moisture anomalies, NDVI, frost risk, water balance | Not covered | **T9.10**: plain-language "What is this?" explainers next to each term |
| How satellite differs from ground measurement, and how combining both helps | Scale contract only | **T6.9**: farmer corrections (crop history, sowing date, irrigation yes/no) enter as ground data, tag E, and re-run calibration; Methods page explains satellite vs ground |
| Compare different SI/statistical approaches | Baselines B0–B3 | Frame the hindcast scoreboard explicitly as an approach comparison; add the T2.3 classifier comparison (phenology rules vs Random Forest) |
| Explain uncertainty and where local expertise is needed | Grades, intervals, gaps, risks | Covered; make the "risks for local review" list name the human check needed |
| Harmonize datasets to a common grid (SMAP, ECOSTRESS LST, GPM, Landsat/MODIS, GEDI, soil) | Deliberately field-based | Keep the field polygon as the common analysis unit; explain on the Methods page why we aggregate to fields rather than resample to one grid (the scale contract). ECOSTRESS LST is added as an observed heat-stress check (**T3.7**, stretch). GEDI is noted and not used (sparse footprints, mostly forest structure); say so on the Methods page |
| Nutrient cycling, erosion, organic matter, pest disruption, water, forage, markets | Covered by T6.7 | Add `deep_root_share` from FAO-56 Table 22 rooting depth (verified data) |
| Brief explanations of N-fixing, cover, deep-rooting and drought-tolerant crops | Not covered | Part of **T9.10**: short cited explainers |
| Maps of trends over time (soil moisture, heat waves, water-storage decline) | Context strip only | **T9.11**: a map layer switcher for the regional trends (GRACE storage, SMAP anomaly, heat-wave days from POWER) with a year slider |
| Field-level vulnerability zones (erosion risk, water stress hotspots, frost-prone) | Not on the map | **T9.11**: colour fields on the map by erosion exposure, water-stress share and frost share |
| Scenario sliders for rainfall or temperature | Not covered | **T6.8**: precomputed weather what-ifs per field |
| Farmer inputs: water availability, equipment limits, market preferences | Crop bans, irrigation yes/no | **T9.3** constraints: seasonal water cap (mm), crops I can't plant or harvest, crops I can sell |

## 2. Pilot regions and crops

**Final choice (T0.5, user, 2026-11-04):** Tier 1 Kansas `T14SLH`; Tier 2 Lauragais near Toulouse `T31TCJ`; Tier 3 central Ukraine `T36UVU`; Nile Delta `T36RTV` only as a data-confidence-map showcase. Evidence: `docs/census/comparison.md`. Original default candidates:

| Tier | Region | Labels | Ground truth for water |
|---|---|---|---|
| 1 | Kansas High Plains, one HLS MGRS tile | USDA Crop Sequence Boundaries 2017–2024 | Kansas WIMAS annual volumes (validation-only; OpenET moved to stretch S6) |
| 2 | One French region, one HLS tile | French RPG field data 2015–2024 via `ftw/harmonized-field-data/fr` (IGN RPG, Licence Ouverte 2.0; 2015, 2016, 2018 from EuroCrops V2, CC-BY-4.0) | ECOSTRESS overpasses |
| 3 | One unlabeled region (Nile Delta / Indian Punjab / central Ukraine) | None (inferred) + WorldCereal 2021 cross-check | ECOSTRESS overpasses |

Crops per region: the 4–6 crops covering most cropland in the census, plus `fallow` and one `cover_crop`. Kansas default: maize, soybean, winter wheat, sorghum, fallow, cover crop.

## 3. Data contracts (do not change without asking)

All schemas live in `src/fieldwitness/schemas.py` as Pydantic v2 models and are exported to `app/src/types.ts` with a script (T8.2).

```python
Tag = Literal["O", "D", "E", "A"]

class Tagged(BaseModel):          # every user-facing number
    value: float | None
    lo50: float | None = None; hi50: float | None = None
    lo90: float | None = None; hi90: float | None = None
    unit: str
    tag: Tag
    source: str                   # dataset id or "model:<module>@<version>"

class Field(BaseModel):
    field_id: str                 # sha1 hex of the WKB of the geometry in EPSG:4326 rounded to 6 decimals (user 2026-11-04)
    geometry_wkt: str
    area_ha: float
    region_id: str; tier: Literal[1, 2, 3]
    boundary_source: Literal["FTW", "CSB", "EuroCrops", "user"]
    scale_flags: dict[str, bool]  # e.g. {"POWER": True, "HLS": False}
    interior_pixels: int

class Season(BaseModel):
    year: int                     # harvest year = calendar year of EOS (winter wheat sown Oct 2022, harvested Jun 2023 -> 2023)
    index: int = 0                # 0 = main season; 1 = second season in the same harvest year (double cropping)
    crop: str | None; crop_conf: float  # 0–1
    crop_source: Literal["label", "classifier", "user"]
    sos: Tagged; peak: Tagged; eos: Tagged        # day of year
    canopy_integral: Tagged; cover_days: Tagged; bare_days: Tagged
    clear_obs: int

class WitnessResult(BaseModel):
    witness: Literal["physics", "own_past", "neighbours"]
    metric: str                   # "water_use_mm" | "irrigation_mm" | "ryi" | "cover_days" | "canopy_integral"
    estimate: Tagged
    n: int | None = None          # neighbours: number of field-seasons
    diagnostics: dict[str, float | bool | str]

class Explanation(BaseModel):     # v1.2, T6.6: deterministic, every sentence traceable to a number or flag
    why: list[str]                # which priority or pattern produced it
    evidence: list[str]           # witnesses and grade, with tags
    benefits: list[str]           # metric deltas vs Current, with units and tags
    gaps: list[str]               # tag-A inputs, missing witnesses, scale flags, unverified parameters
    risks: list[str]              # items needing local review (disease, timing, markets, equipment, missing Ky)

class Option(BaseModel):
    option_id: str
    sequence: list[str]           # e.g. ["soybean", "winter_wheat", "maize"]
    metrics: dict[str, Tagged]    # water_use_mm, irrigation_mm, ryi, cover_days,
                                  # bad_year_water_mm (CVaR10 of water), bad_year_ryi (CVaR10 of RYI)
    witnesses: list[WitnessResult]
    grade: Literal["A", "B", "C", "D"]; grade_reasons: list[str]
    regret: Tagged; rank: int
    explanation: Explanation      # v1.2 (T6.6); option_id "current" = the field's current rotation (T6.0)

class Advice(BaseModel):
    measure_next: str; flip_probability: Tagged
    counterfactual_flip: str      # smallest assumption change that changes rank 1

class LedgerEntry(BaseModel):
    field_id: str; as_of: date; model_version: str
    mode: Literal["forecast", "forced"]      # see Phase 7
    season_year: int; season_index: int = 0; crop: str
    crop_observed_source: Literal["label", "classifier"]  # Tier 3 = classifier: weaker test, say so in the UI
    predicted: dict[str, Tagged]  # sos, peak, canopy_integral, cover_days, water_use_mm
    observed: dict[str, Tagged] | None = None
    scores: dict[str, float] | None = None   # crps, covered50, covered90, timing_err_days

class FieldPack(BaseModel):       # one JSON per field, < 300 KB
    schema_version: str
    field: Field; story: list[Season]
    credibility: Tagged; options: list[Option]; advice: Advice
    ledger: list[LedgerEntry]
    data_as_of: date; generated_at: datetime
```

Region-level files: `packs/<region>/index.json` (list of fields, bbox) and `packs/<region>/hindcast.json` (baseline comparison table).

**Tagging rule (what the "no untagged numbers" validator checks).** Every value a user reads as a claim about the field or an option must be `Tagged`: all `Season` metrics, `credibility`, every `Option.metrics` entry, `Option.regret`, `Advice.flip_probability`, `WitnessResult.estimate`, and `LedgerEntry.predicted` / `observed`. Exempt by design, listed in `schemas.EXEMPT_FIELDS`: identifiers, `area_ha`, `interior_pixels`, `clear_obs`, `crop_conf`, `n`, `rank`, `diagnostics`, `scores` (these are bookkeeping or scoring outputs whose provenance is the module itself). The validator walks the pack and fails on any float outside `Tagged` that is not on the exempt list.

## 4. Configuration files

- `config/regions.yaml` — region id, tier, bbox, HLS tile id, label source, crop list, season windows.
- `config/crops.yaml` — per crop: FAO-56 Kc_ini/mid/end, stage lengths, root depth, p, FAO-33 Ky, family. **Every value has a `ref:` field (paper, table number, page). Values not yet checked are marked `verified: false` and the app shows them as tag `A`.**
- `config/grading.yaml` — thresholds for grades and scale flags (initial values are team choices, labelled as such).

Grading rule (initial, adjustable in `grading.yaml`):

- **A:** physics and neighbours agree (same sign, 90% intervals overlap) AND credibility ≥ threshold AND no key input tagged `A`.
- **B:** two witnesses agree.
- **C:** one witness available or witnesses disagree.
- **D:** decision-driving inputs mostly tagged `A`.

---

## 5. Phases and tasks

Each task: **ID · goal · output · acceptance test**. Tick `[x]` and add a one-line note when done.

### Phase 0 — Setup, access, census (pre-event safe)

- [x] **T0.1 Scaffold.** *Done 2026-11-04: commit `1d3a3a5`, CI run 41743961024 green (test + secret-scan).* Repo layout from CLAUDE.md, `pyproject.toml` (uv, **Python pinned to 3.12** — the system 3.15 is too new for geospatial wheels), ruff, pytest, hypothesis, pre-commit, GitHub Actions running lint + tests, and a secret scan using the **gitleaks CLI binary** (not the gitleaks GitHub Action, to avoid its licence question). *Accept:* CI green on an empty test.
- [x] **T0.2 Earthdata access.** *Done 2026-11-04: login OK; T14SLH 2023-07-04 → `HLS-VI.S30.T14SLH.2023185T172901.v2.0`; shapes, Fmask location and 2016–24 archive depth in `docs/api_notes.md`.* `earthaccess.login()` using `.netrc`; search HLSL30_VI.002 and HLSS30_VI.002 granules for one tile and one date. *Accept:* granule list printed; response shape noted in `docs/api_notes.md`.
- [x] **T0.3 AppEEARS access.** *Done 2026-11-04: task `09338e93-…` (HLS-VI NDVI/EVI + Fmask, T14SLH box, Apr–Oct 2023) done in ~22.5 min; 17 files sha256 OK; NetCDF opened; shapes, time-axis gotcha and 47-vs-33 date gap in `docs/api_notes.md`. Direct-COG fallback (T1.5b) tested and written up 2026-11-04.* Verify the AppEEARS API from its official docs; submit one area request for one polygon (HLS-VI NDVI, EVI, one season). *Accept:* time series CSV/NetCDF downloaded; request + response shape documented. If AppEEARS is slow, document the direct-COG fallback (T1.5b).
- [x] **T0.4 Field datasets.** *Done 2026-11-04: bbox reads under the 200 MB cap — FTW Punjab 15,529, CSB 2024 (T14SLH) 20,190, France RPG 2024 (Beauce) 6,198 polygons; FTW Kansas skipped (204 MB > cap; CSB is Tier 1). URLs + licences in `DATA.md`.* `geopandas.read_parquet(..., bbox=...)` on `pyarrow` (GeoParquet 1.1 `bbox` covering column; anonymous S3 on Source Cooperative first, HTTPS fallback) reads a bbox from (a) Fields of the World global GeoParquet, (b) USDA CSB 2017–2024 GeoParquet, (c) the French RPG/EuroCrops V2 series, all from their published URLs, without downloading whole files. Footers and row-group `bbox` statistics are read first; a query estimated above 200 MB is not run. (DuckDB was dropped: its httpfs/spatial extensions are blocked on this network, see DECISIONS.md.) *Accept:* polygon counts per bbox printed; URLs and licences recorded in `DATA.md`.
- [x] **T0.5 Data census** *Done 2026-11-04: `fieldwitness.cli census`; `docs/census/` (6 regions + comparison); regions chosen by the user: Kansas T14SLH, Toulouse T31TCJ, central Ukraine T36UVU (Nile T36RTV showcase).* (`cli census --region <id>`). Per candidate region: field-size distribution, share of fields with ≥ 4 interior HLS pixels, clear HLS observations per season (2016–2024), label years available, ECOSTRESS overpass count. *Accept:* `docs/census/<region>.md`; **human picks the three regions** and records it in `DECISIONS.md`.
- [x] **T0.6 Configs.** *Done 2026-11-04: `crops.yaml` 11 crops, 82 values verified from FAO-56 Tables 11/12/22/24 and 9 unverified (tag A); crop lists per region from CSB/RPG/FAOSTAT; `grading.yaml` team choices; Pydantic validation in `fieldwitness.config` (tests pass).* Fill `regions.yaml`; fill `crops.yaml` from FAO-56 Tables 11 (stage lengths), 12 (Kc, height), 22 (rooting depth, p) and 24 (seasonal Ky, reproduced from FAO-33), each with `ref:` (table numbers verified 2026-11-04; FAO-33 itself not found on fao.org). *Accept:* schema validation passes; unverified values flagged.

**Gate 0:** access works for every **essential** Tier 1 source; regions chosen; configs validate. *Rule change 2026-11-04 (user): Tier 1 sources are split into essential (HLS, POWER, CSB, SoilGrids) and validation-only (WIMAS, ECOSTRESS; OpenET moved to stretch). Gate 0 requires all essential sources; validation sources may be pending. Further change 2026-11-04 (user): Phase 1 may start with the tasks that do not need soil (T1.1, T1.2, T1.4, T1.5, T1.6, T1.8); soil values for the pilot fields (T1.3) are required for Gate 1, not Gate 0.*

### Phase 1 — Data layer (`src/fieldwitness/data/`)

- [ ] **T1.1 `asof` guard.** Context manager `with as_of(date):` that every data reader respects; readers raise if they return records after the cut-off. *Accept:* leakage tests in `tests/test_leakage.py` pass for every reader.
- [ ] **T1.2 POWER client.** Daily point API (`https://power.larc.nasa.gov/api/temporal/daily/point`), community `AG`; verify parameter names (T2M_MAX, T2M_MIN, RH2M or dew point, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR) against the API docs before use. Disk cache (Parquet) per grid cell. *Accept:* 2001–2024 daily series for one point; missing values handled; test with a recorded response.
- [ ] **T1.3 SoilGrids client.** REST `properties/query` for sand, silt, clay, SOC, bulk density at the depths needed; Q50 plus Q05/Q95. *Accept:* values for 5 points cached; units documented.
- [ ] **T1.4 Field resolver** (`resolve/`). Point → polygon (CSB/EuroCrops first in Tier 1–2, FTW otherwise); `field_id` hash; interior-pixel mask on the HLS 30 m grid: fields are **annual arable crop parcels** where a crop taxonomy exists (HCAT3 rule in `fieldwitness.data.hcat`, full class list in `docs/hcat_annual_arable.md`); a pixel is interior when its centre lies ≥ 15 m (half a pixel) inside the field edge, i.e. a 15 m inward buffer (`fieldwitness.resolve.pixels`). *Changed 2026-11-04 from a one-pixel (30 m) buffer: in the T0.5 census the share of fields with ≥ 4 interior pixels at 30 m vs 15 m was Kansas 88.6 % → 98.1 % (full tile), Beauce 54 % → 61 %, Nile Delta 6.9 % → 33.6 %, Punjab 2.4 % → 18.3 %; 30 m discarded many usable fields, 15 m still keeps every counted pixel centre half a pixel from the edge (DECISIONS.md).* Scale flags. *Accept:* 20 points across regions return a polygon or "no field"; interior pixel counts match a manual check on 3 fields.
- [ ] **T1.5 HLS-VI series.** (a) AppEEARS area request for all pilot fields per region; (b) fallback: STAC search + COG windowed reads with `rioxarray`. Use the HLS quality layer (Fmask) to drop cloud, shadow, snow. Output: per field, per date, median NDVI/EVI over interior pixels + clear-pixel fraction. *Accept:* series for all pilot fields 2016–2024; QA rule documented.
- [ ] **T1.6 Labels.** Per field-year crop label from CSB (Tier 1, `ftw/harmonized-field-data/us_usda_cropland`, 2017–2024 edition) and the French RPG/EuroCrops V2 series (Tier 2, `ftw/harmonized-field-data/fr`); harmonise crop names to `crops.yaml`; select fields as annual arable crop parcels on the current (most recent) year (`fieldwitness.data.hcat.is_annual_arable`, same definition as T1.4); in crop histories keep fallow and temporary grass as the crop states "fallow" and "temporary_grass" (`history_state`), never dropped, and remove a field from history analysis only if it leaves arable use (`stays_arable`: a year in HCAT3 groups 3302–3308; 3399 and missing codes are "unknown" states); map the unmapped France `crop:code` values (null `hcat:code` in 2023–24). *Accept:* label table with coverage report.
- [ ] **T1.7 Water truth (Tier 1).** Kansas WIMAS annual volumes for points of diversion in the region (verify access); (OpenET removed from the MVP 2026-11-04, see S6); ECOSTRESS ET overpasses (`ECO_L3T_JET` v003) for Tier 2–3 pilot fields. *Accept:* whichever sources are accessible are cached; unavailable ones are logged in `DECISIONS.md`.
- [ ] **T1.8 Context datasets.** Verify collection IDs and access first (rule 2). (a) SRTM or NASADEM 30 m elevation → slope per field (mean over interior pixels). (b) GRACE/GRACE-FO mascon terrestrial water storage → regional monthly series and linear trend since 2002 for each pilot region; it is coarse, so context only, with a scale flag, never a field claim. (c) SMAP L4 root-zone soil moisture → monthly anomaly for the region (context). *Accept:* values cached for all three regions; ids and response shapes in `docs/api_notes.md`.

**Gate 1:** one full Tier 1 region has polygons, HLS series, weather, **soil values for the pilot fields (T1.3)** and labels on disk.

### Phase 2 — Field story (`src/fieldwitness/story/`)

- [ ] **T2.1 Smoothing.** Savitzky–Golay on gap-filled series (window and order in config); optional GPR later. *Accept:* property test: output length = input; no values outside [-1, 1].
- [ ] **T2.2 Seasons and phenology.** Segment the series into seasons and assign each to its **harvest year** (calendar year of EOS), matching how CDL/CSB label winter wheat; a second season ending in the same year gets `index = 1`; where a crop has winter and spring variants (wheat, barley; `config/crops.yaml`), assign the variant per field-season from the observed green-up: autumn green-up before winter → winter variant, spring green-up only → spring variant (tag `D`); SOS/EOS by amplitude-threshold method (e.g. 20%/50% of seasonal amplitude, choice documented); peak, canopy integral, cover days (NDVI ≥ cover threshold), bare days. Each output `Tagged` with tag `O` (direct metrics) or `D` (thresholded). *Accept:* on 30 labelled fields, the number of detected seasons matches the crop calendar for ≥ 90% (target, team choice).
- [ ] **T2.3 Crop classifier.** Random Forest on phenology features + monthly composites; train on Tier 1–2 labels; spatially blocked CV; calibrated probabilities → `crop_conf`. *Accept:* `results/classifier/` with per-crop F1, confusion matrix, US→EU and EU→US transfer scores.
- [ ] **T2.4 WorldCereal cross-check (Tier 3).** Compare 2021 classifier output with WorldCereal 2021 maize/cereal maps. *Accept:* agreement table.
- [ ] **T2.5 Bare-soil calendar.** Per field: for each month, the share of past years (≥ 2016) in which the field was bare (NDVI below the cover threshold in T2.2), with clear-observation counts. Tag O. *Accept:* calendar for all pilot fields; months with too few clear observations are marked "insufficient data", not filled.

**Gate 2:** field stories for all pilot fields; classifier report committed.

### Phase 3 — Witness 1: physics (`src/fieldwitness/physics/`)

- [ ] **T3.1 ETo.** FAO-56 Penman–Monteith daily (Eq. 6 and supporting equations). *Accept:* unit tests reproduce the FAO-56 worked examples (numbers taken from the paper) within the rounding shown there.
- [ ] **T3.2 Crop coefficient curve.** Piecewise Kc from stage lengths, adjusted Kc_mid for climate (FAO-56 Eq. 62). Sowing date is a parameter. *Accept:* tests on known shapes.
- [ ] **T3.3 Water balance.** Daily root-zone depletion (FAO-56 Eq. 85) with TAW, RAW, Ks (Eq. 84), runoff (simple), deep percolation; irrigation policies: `rainfed`, `trigger_at_RAW(efficiency)`, `fixed_seasonal_mm`. *Accept:* property tests: mass closes each day, 0 ≤ Ks ≤ 1, 0 ≤ Dr ≤ TAW.
- [ ] **T3.4 Season outputs.** ETa, irrigation mm, Relative Yield Index via FAO-33 Ky (`1 − Ya/Ym = Ky (1 − ETa/ETc)`), simulated canopy proxy (Kc-shaped curve) for comparison with HLS, cover days. *Accept:* outputs tagged `D`.
- [ ] **T3.5 Rotation simulation.** Run a sequence of crops with carry-over soil water between seasons and fallow periods. **Design for batching from day one:** state arrays shaped `(options, draws, years)` stepped through days in NumPy, so one call simulates everything for a field. *Accept:* benchmark test — 200 sequences × 30 draws × 20 years for one field in < 60 s on the laptop. If it misses, profile first, then consider `numba` (ask before adding it).
- [ ] **T3.6 Vulnerability calendar.** For the current crop and each option crop, using the crop stages from T3.2 and POWER weather 2001–cut-off: share of years with (a) heat-stress days in the sensitive stage (Tmax above a crop-specific threshold), (b) frost after green-up (Tmin ≤ 0 °C), (c) water stress (simulated Ks < 1) by stage, (d) extreme-rain days (above the local 99th percentile of daily rain) falling on bare soil. **Thresholds come from a cited source or are tagged A with a note; never from memory.** *Accept:* a month × hazard table per field-crop.

**Gate 3:** physics runs for every pilot field and crop; FAO tests pass.

### Phase 4 — Witness 2: own past (`src/fieldwitness/infer/`)

- [ ] **T4.1 Hidden variables and priors.** sowing-date offset, TAW scale, irrigated (bool), seasonal irrigation mm, Kc_mid scale. Priors in config, with reasons.
- [ ] **T4.2 Synthetic fields.** Generate fields with known hidden values; simulate their seasons; add realistic noise and cloud gaps taken from the census.
- [ ] **T4.3 ABC rejection.** Summary statistics: SOS, peak timing, EOS, canopy integral (+ seasonal ET where available). Distance on standardised stats; keep the closest *k* draws as posterior "worlds" (k = 300 default). *Accept:* on synthetic fields: parameter recovery plots, 50/90% coverage per variable within ±5 points of nominal, or the variable is listed as not identifiable.
- [ ] **T4.4 Simulation-based calibration.** SBC rank histograms per variable. *Accept:* figures in `results/inference/`.
- [ ] **T4.5 Real fields + credibility.** Run on pilot fields; credibility = Spearman rank of seasons (observed vs simulated canopy integral) + median timing error, combined as in `grading.yaml`. *Accept:* credibility for every pilot field; distribution figure.
- [ ] **T4.6 Irrigation check (Tier 1).** Posterior irrigation vs WIMAS annual volumes (season scale only). *Accept:* bias and R² reported, whatever they are.

**Gate 4:** posteriors and credibility for all pilot fields; synthetic diagnostics committed.

### Phase 5 — Witness 3: neighbours (`src/fieldwitness/neighbours/`)

- [ ] **T5.1 Field-season table.** For Tier 1–2 regions (enlarge to surrounding tiles if n is small): field, year, previous crop, current crop, outcomes (canopy integral, peak, season length, cover days, drought-season canopy drop, ET if available), confounders (season weather aggregates, soil, field size, x/y cell, earlier crops, irrigation proxy). *Accept:* table + row counts per precrop contrast.
- [ ] **T5.2 Double ML.** Partially linear model (verify the `doubleml` API from its docs; fallback EconML) with gradient-boosting or RF nuisance learners, cross-fitting; contrasts per outcome crop (e.g. maize after soybean vs maize after maize). Split by wet vs dry season (precip percentile). *Accept:* effects with 95% CIs in `results/neighbours/effects.csv`.
- [ ] **T5.3 Diagnostics.** Placebo (next year's crop as treatment), negative-control outcome (pre-treatment season), propensity overlap, covariate balance. *Accept:* contrasts failing diagnostics are flagged and not shown as evidence.
- [ ] **T5.4 Literature check.** Compare signs with published US precrop findings: Kluger, Di Tommaso & Lobell (2025), "Evaluating crop rotations around the world using satellite imagery and causal machine learning", arXiv:2506.02384 (citation confirmed by the planning research; open the paper to take numbers). Note our outcomes are canopy/water, not yield. *Accept:* `results/neighbours/literature_check.md` listing agreements and disagreements.

**Gate 5:** at least one Tier 1 contrast passes diagnostics.

### Phase 6 — Agreement and rotation engine (`agree/`, `rotate/`)

- [ ] **T6.0 Current rotation.** Derive the field's current rotation from its last three seasons in the field story (labels in Tier 1–2, classifier in Tier 3, with confidence). It is always option 1 ("Current"), even when it contains a crop excluded from new options (then it is simulated where possible and the gap is shown). *Accept:* every pack has a Current option; benefits are shown as deltas against it.
- [ ] **T6.1 Candidates.** Enumerate 3-season sequences from the region's **rotation options** (`fieldwitness.config.rotation_options`: crops with `mvp_role` rotation or rotation_no_yield; barley is prediction-only because RYI needs a verified Ky, rapeseed is history-only; user decision 2026-11-04); hard constraints: allowed crops, calendar fit (season windows from observed local SOS/EOS), max consecutive same family, user bans. *Accept:* banned crop never appears (property test).
- [ ] **T6.2 Evaluate.** Prune candidates with hard constraints first, then for each survivor simulate in one batched call (T3.5) over posterior worlds (subsample, default 30) × weather years 2001–cut-off; metrics: mean water use, irrigation, RYI, cover days, CVaR10 of water and of RYI. *Accept:* runtime < 60 s per field for all candidates (cache as needed).
- [ ] **T6.3 Rank.** Pareto filter + weighted score (default weights in config, user-movable in the app via precomputed per-weight-preset rankings or in-browser recomputation from per-option metrics). Regret matrix across weather years. *Accept:* rankings reproducible with seed.
- [ ] **T6.4 What to measure next + counterfactual flip.** For each uncertain input (TAW, sowing offset, irrigation, Kc scale): share of posterior draws where rank 1 changes; smallest single-input change that flips rank 1. *Accept:* values in `Advice`.
- [ ] **T6.5 Grades.** Apply `grading.yaml` rule using physics vs neighbour effects for the matching transition. *Accept:* each option has grade + reasons; unit tests for each grade branch.
- [ ] **T6.6 Strategy explanation.** Add `Explanation` (§3) to every `Option`: `why`, `evidence`, `benefits`, `gaps`, `risks`. Generated by deterministic rules and templates from the computed metrics; every sentence is traceable to a number or flag (no LLM). *Accept:* unit tests for each template; no option has an empty `gaps` or `risks` list.
- [ ] **T6.7 Priority metrics** (each a `Tagged` value in `Option.metrics`):
  - `legume_share`: share of seasons with a Fabaceae crop (family from GBIF, verified). Label: "nitrogen-fixing crops in the rotation". Tag D. No kg N claim.
  - `family_breaks`: number of family changes between consecutive seasons. Label: "pest and disease break opportunities". Tag D.
  - `erosion_exposure`: relative index = Σ over days of (simulated bare or low cover) × (daily rain above an erosive threshold, IMERG/POWER) × slope factor (SRTM). Unitless, compared between options of the same field only. Tag D. **Not tonnes of soil.**
  - `residue_proxy`: organic-matter input proxy from simulated canopy integral plus cover days. Label: "organic matter input (proxy, not soil carbon)". Tag D.
  - `forage_value`: per crop, a yes/no forage use from a cited source (e.g. FAO crop descriptions), else tag A.
  - `deep_root_share`: share of seasons with a crop whose maximum rooting depth (FAO-56 Table 22, verified) is above a stated threshold. Label: "deep-rooting crops in the rotation". Tag D.
  - Market suitability is **not** a metric. It is a user constraint ("crops I can sell") on the Field Card, stored as user input.
  *Accept:* all metrics present for every option; labels match this list exactly.
- [ ] **T6.8 Weather what-ifs.** For each field, precompute every option under a small grid of weather changes applied to the historical years: temperature +0, +1, +2 °C × rainfall −20%, −10%, 0, +10%. Store per-option metrics per scenario in the pack, so the app's sliders switch between precomputed results instead of simulating in the browser. These are sensitivity tests, not climate projections; say so in the UI. *Accept:* 12 scenarios per field; pack size still under the limit, or the scenarios split into a second file per field.
- [ ] **T6.9 Farmer corrections.** The app lets a user correct the field's crop history, sowing date and irrigation status. Corrections are stored locally in the browser, tagged E ("farmer-entered"), and shown alongside the satellite version. In the static demo, a correction switches to a precomputed alternative where one exists, and otherwise shows "re-run needed: available in live mode" (API, T8.3). *Accept:* a corrected history visibly changes the Current option and its tags.

**Gate 6:** full `FieldPack` (minus ledger) for one field validates against the schema.

### Phase 7 — Ledger and hindcast (`ledger/`)

**Two hindcast modes, both stored, clearly labelled:**

- **Forecast mode (headline).** What a farmer would actually have received on 1 Jan 2022: weather for 2022–24 is unknown, so each prediction uses the ensemble of past weather years ≤ cut-off. Tests decision value. Intervals are wide by nature; score coverage and CRPS against baselines run the same way.
- **Forced mode (diagnostic).** Same calibration, but the model is driven with the real 2022–24 POWER weather. Tests whether the model is right *given* the weather. This is the one exception to the `as_of` guard: forcing weather enters through a separate, explicitly named channel (`forcing_weather=`), never through calibration or training data. A leakage test checks that only that channel reads post-cut-off data.

**Known, accepted leakage (document in DECISIONS.md and on the Methods page):** field boundaries come from CSB 2024 / FTW 2024–25, which are built from post-2021 imagery. Boundaries are geometry only; no post-cut-off crop labels, outcomes or effects are used. If an older CSB edition is easy to read, prefer it for Tier 1.

**Tier 3 caveat:** the "observed crop" comes from our classifier, so Tier 3 scoring is weaker. Score Tier 3 mainly on crop-agnostic outcomes (SOS, peak timing, canopy integral, cover days) and say so in the scoreboard.

- [ ] **T7.1 Predict.** With `as_of=2021-12-31`, re-run Phases 2–6 fitting on data ≤ cut-off; for every pilot field and every option, store predictions for 2022, 2023, 2024 seasons (sos, peak, canopy integral, cover days, water use) with 50/90% intervals. Barley (winter and spring) is included in these predictions (they need only Kc and stage lengths) but is not a rotation option; rapeseed seasons are history only (no predictions: no verified stage lengths or Ky).
- [ ] **T7.2 Observe and score.** For the crop actually observed each season (conditional scoring), compute CRPS (from posterior samples), 50/90% coverage, timing error (days), and cross-field Spearman of canopy integral. *Accept:* `results/hindcast/<region>.json` + figures.
- [ ] **T7.3 Baselines.** B0 field mean of past seasons · B1 FAO-table engine (default dates, default soil, Kc × ETo) · B2 uncalibrated physics · B3 neighbour-only. Same scoring. *Accept:* comparison table per tier; results reported whatever they show.
- [ ] **T7.4 Ablation + degradation (if time).** Remove witness 2 or 3; degrade observations (fewer clear dates, small fields). *Accept:* skill-vs-field-size curve.

**Gate 7:** hindcast tables for ≥ 1 Tier 1 and ≥ 1 Tier 3 region.

### Phase 8 — Packs and API (`packs/`, `api/`)

- [ ] **T8.1 Export packs.** `cli build-packs --region <id>` writes `packs/<region>/<field_id>.json`, `index.json`, `hindcast.json`; validates every file against the schema; fails if any user-facing number is untagged. *Accept:* each pack < 300 KB; validator in CI.
- [ ] **T8.2 Types.** Generate `app/src/types.ts` from the Pydantic schemas (JSON Schema → TS). *Accept:* app compiles against generated types.
- [ ] **T8.3 Optional API.** FastAPI serving packs and a `/simulate` endpoint for live mode. Not used by the deployed demo.

### Phase 9 — Web app (`app/`)

React + Vite + TypeScript, MapLibre GL, a chart library (Recharts or Observable Plot — pick one), strings in `app/src/strings/en.json`. Data loaded from `/packs/...` static files; a service worker caches them for offline use.

- [ ] **T9.1 Shell + Map view.** Region switcher; field polygons from `index.json`; click → open field. **Basemap = our own HLS true-colour composite** of each pilot tile (cloud-free median, peak season), rendered by the pipeline as a small raster or PMTiles file. It is NASA data (no licence problem) and ships with the app, so it works offline. Fallback: a plain neutral background with field outlines. No third-party imagery tiles. *Accept:* loads offline after first visit.
- [ ] **T9.2 Field story view.** Season timeline (crop chips with confidence), NDVI curve with SOS/peak/EOS marks, scale-flag badges.
- [ ] **T9.3 Field Card view (changed in v1.2).** Shows Current + at least 2 alternatives (sequence, water use, bad-year water, cover days, RYI, grade badge), priority sliders for water, bare-soil months, bad-year risk, erosion exposure, legume share and residue proxy (re-ranked in the browser from per-option metrics), constraint toggles (ban crop, irrigation yes/no, seasonal water cap in mm, crops I can't plant or harvest) plus a "crops I can sell" constraint. Each option opens a detail panel with the five explanation parts (T6.6).
- [ ] **T9.4 Advisor Console view.** Witnesses side by side per option (estimate + interval + n + diagnostics), credibility and back-test chart (observed vs simulated seasons), what-to-measure-next, counterfactual flip; source-tag legend (O/D/E/A) on every number.
- [ ] **T9.5 Hindcast scoreboard.** Per region: FieldWitness vs B0–B3 on CRPS, coverage, timing error; one field's predicted-vs-observed 2022–24 as the story chart.
- [ ] **T9.6 Methods & data page.** Datasets, licences, non-promises, limits, link to repo.
- [ ] **T9.7 Responsive + accessibility.** 380 px viewport works; keyboard navigation; colour never carries meaning alone.
- [ ] **T9.8 Deploy.** GitHub Pages (or Netlify) via GitHub Actions on push to `main`. *Accept:* public URL opens in a private window with no login.
- [ ] **T9.9 Calendar view.** The bare-soil calendar (T2.5) and the vulnerability calendar (T3.6) for the current rotation, with a toggle to show an alternative's calendar. A regional context strip shows the GRACE trend, SMAP anomaly and slope, each scale-flagged.
- [ ] **T9.10 Explainers.** A small "What is this?" next to evapotranspiration, soil moisture anomaly, NDVI, frost risk, water balance, Relative Yield Index, evidence grade and source tags, plus short explainers on nitrogen-fixing, cover, deep-rooting and drought-tolerant crops. Each explainer is two or three plain sentences with a cited source (FAO-56, NASA Earthdata pages, or the FAO crop chapters), kept in `app/src/strings/en.json`.
- [ ] **T9.11 Map layers.** (a) Field colouring by erosion exposure, water-stress share or frost share (from T3.6 and T6.7). (b) Regional trend layers with a year slider: GRACE water storage, SMAP soil-moisture anomaly, and heat-wave days from POWER. Every layer shows its resolution and scale flag.
- [ ] **Fixed line** on the Field Card and the Methods page: "FieldWitness helps you explore options. It does not replace your judgment or local agricultural advice."

### Phase 10 — Hardening and submission

- [ ] **T10.1** README (what, why, how to run, results summary, screenshots), DATA.md, AI_USE.md (tools used and where; mark AI-generated code in file headers or commit messages as the 2026 guide requires), LICENSE (MIT or Apache-2.0).
- [ ] **T10.2 Red-team checklist:** no untagged numbers, no forbidden claims, all links public, English everywhere, every external resource listed for the References field.
- [ ] **T10.3** Freeze `main`, tag `v1.0-spaceapps`, verify the deployed URL and repo in a private window.
- [ ] **Deployment note.** GitHub Pages from a private repository may need a paid GitHub plan (verify). Since pre-event code is allowed, either make the repo public when the first deploy happens, or deploy from Netlify/Vercel. Ask the user before making the repo public.

### Stretch (only after all MVP boxes are ticked)

- [ ] S1 Evidence Atlas view (aggregated effects + data-confidence map from the FTW 500 m confidence raster, field size, clear-obs counts).
- [ ] S2 NEX-GDDP-CMIP6 future lens for one SSP.
- [ ] S3 Prithvi-EO-2.0 crop classifier benchmark vs Random Forest (Colab GPU).
- [ ] S4 Tier 3 neighbour effects from inferred crop histories.
- [ ] S5 Live any-point mode via the API.
- [ ] S6 OpenET seasonal ET as an extra water witness for Kansas fields — only if the user accepts OpenET's terms (moved from T1.7, 2026-11-04).
- [ ] T3.7 Observed heat stress (stretch). ECOSTRESS land-surface temperature (verify the collection first) on pilot fields during sensitive stages, as an observed check on the POWER-based heat-stress calendar.

---

## 6. Pre-event schedule (v1.2) with cut lines

Assumes Claude Code builds and the user reviews at each gate. Each day ends with green tests, a commit, and a deployable state from day 6 onward.

| Day | Date | Work | Gate at end of day |
|---|---|---|---|
| 1 | Wed 4 Nov | Close Gate 0 (SoilGrids, families); merge this addendum | Gate 0 closed |
| 2 | Thu 5 Nov | Phase 1 for Kansas (T1.1–T1.6) + T1.8 | Gate 1 (Kansas) |
| 3 | Fri 6 Nov | Phase 2 (incl. T2.5) + Phase 3 (incl. T3.6) for Kansas | Gates 2 and 3 (Kansas) |
| 4 | Sat 7 Nov | Phase 4: synthetic diagnostics, then real fields + credibility | Gate 4 (Kansas) |
| 5 | Sun 8 Nov | Phase 6 (T6.0–T6.8) + Phase 8 packs for Kansas | Gate 6: one valid pack |
| 6 | Mon 9 Nov | Phase 9: Map, Field story, Field Card, Calendar, explainers; first deploy | **Walking skeleton live** |
| 7 | Tue 10 Nov | Phase 7 hindcast (both modes, B0–B3) + scoreboard view; map layers (T9.11) | Gate 7 (Kansas) |
| 8 | Wed 11 Nov | Phase 5 neighbours (Kansas) + Advisor Console + farmer corrections (T6.9); grade A becomes possible | Gate 5 |
| 9 | Thu 12 Nov | Toulouse and Ukraine through Phases 1–8; Nile confidence-map numbers | All three regions in the app |
| 10 | Fri 13 Nov | Read official rules; red team (T10.2); README, DATA, AI_USE, LICENSE; feature freeze | Release candidate |
| — | 14–15 Nov | Bug fixes only, 30-second demo, submission page, References, final deploy | Submitted |

**Cut lines if a day slips:** first drop T3.7 (ECOSTRESS heat check), then the Ukraine and Toulouse neighbour analysis, then the regional trend layers' year slider, then Tier 2, then forced-mode hindcast. Never drop: Current option, the five explanation parts, Kansas hindcast vs baselines, the bare-soil and vulnerability calendars, the what-if sliders, the explainers.

## 7. How to drive Claude Code

**First prompt (session 1):**

```
Read CLAUDE.md and PLAN.md completely. Do not write code yet.
1) Explain the project back to me in 10 lines.
2) List everything in PLAN.md that is unclear, unverified or risky, grouped by phase.
3) Propose exactly how you will do T0.1–T0.3, which commands you will run, and what you need from me (accounts, credentials, decisions). Wait for my approval.
Never fabricate data, endpoints, parameters or results.
```

**Per-task prompt template:**

```
Next task: <ID>. Re-read its acceptance test in PLAN.md.
Plan it in ≤ 10 lines, list any API you must verify first, then wait for my OK.
After implementing: run the tests, show the acceptance evidence, tick the box in PLAN.md, and add a line to DECISIONS.md.
```

**Phase review prompt (at each gate):**

```
We are at Gate <N>. Check every acceptance test of this phase against the actual files and results. List what passes, what fails and what is unverified. Do not fix anything yet.
```

## 8. Human decisions and actions (not for Claude Code)

- [ ] Create Earthdata account; add credentials to `~/.netrc`; authorise LP DAAC and AppEEARS.
- [ ] Read the 2026 Submission and Judging Guides on 13 Nov; record the pre-event-work rule in `DECISIONS.md`.
- [ ] Pick the three regions after the census (T0.5).
- [ ] Confirm OpenET access terms; decide whether to use it.
- [ ] Team roles: Data lead · Science lead · App lead · Story lead (demo + submission page).
- [ ] Paste the official challenge text into `docs/official_challenge.md`.
