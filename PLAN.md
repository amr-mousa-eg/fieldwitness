# PLAN.md — FieldWitness implementation plan

Version 1.2 · 4 Nov 2026 · Hackathon 14–15 Nov 2026 (submission closes 23:59 local time on 15 Nov).

**Changes in v1.1** (answers to Claude Code's first review): Python pinned to 3.12; gitleaks CLI instead of the Action; a walking-skeleton milestone (§1); explicit tagging rule and schema fixes (§3); season-year convention (T2.2); batched physics runtime targets (T3.5, T6.2); two hindcast modes and documented boundary leakage (Phase 7); HLS true-colour basemap for offline use (T9.1); Kluger et al. 2025 citation confirmed (T5.4).

**Changes in v1.2-ext** (user approval 4 Nov 2026, final proposal Q1–Q7): §3b app data files (`TaggedSeries`, `TaggedGrid`, series, calendar, scenarios, layers, index, hindcast and region-list models) implemented in `src/fieldwitness/schemas.py`; six new exempt fields; season day-of-year rule (§3 `Season`, T2.2); no SOS/peak/EOS in `series`; scenarios hold weather-sensitive metrics only (T6.8); T9.9 reads `bare_by_option`; stretch S7 (colouring by an alternative); T8.1/T8.2 cover the new files.

**Changes in v1.2** (addendum merged 4 Nov 2026, user): pre-event build schedule (§6 replaced); challenge alignment with the official text in `docs/official_challenge.md` (§1b); new tasks T1.8, T2.5, T3.6, T3.7 (stretch), T6.0, T6.6–T6.9, T9.9–T9.11; T9.3 changed; `Explanation` added to `Option` (§3); fixed "does not replace your judgment" line; Phase 10 deployment note.

This plan is ordered so that the end-to-end loop works early and gets better later. Never start a phase before the previous phase's **gate** passes. Stretch tasks (`S*`) only start when every MVP task is ticked.

> **Pre-event build (v1.2).** Code written before the event is assumed allowed (see DECISIONS.md; to be confirmed against the official 2026 Submission Guide on 13 Nov). Build the full MVP before 13 Nov; 13 Nov is a review and freeze day; 14–15 Nov are for polish, demo and submission. The CLAUDE.md working agreement is unchanged: one task at a time, plan first at the start of each phase, gates still apply.

---

## 1. Goal and definition of done

**Goal:** a public, no-login static web app plus a public repo. For pilot fields in three regions it shows the field's satellite story, three ranked rotation options with A–D evidence grades, the witnesses behind each grade, what to measure next, and a hindcast scoreboard comparing FieldWitness against baselines on 2022–2024.

**Definition of done (MVP)**

- [x] App deployed at a public URL (https://amr-mousa-eg.github.io/fieldwitness/); loads in a private browser window with no login; works with Wi-Fi off after first load.
- [x] Five views work for every demo field: Map · Field story · Field Card · Advisor Console · Hindcast scoreboard (verified on all 200 Kansas fields).
- [ ] Hindcast (cut-off 2021-12-31, scored on 2022–24) completed for ≥ 1 Tier 1 and ≥ 1 Tier 3 region, with baselines B0–B3, results in `results/hindcast/`.
- [x] All tests green in CI; leakage tests pass; no untagged numbers in packs (251 pytest tests, 0 pack problems).
- [x] README, DATA.md (every dataset + licence), AI_USE.md, LICENSE present (all verified in Phase 10).

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
    sos: Tagged; peak: Tagged; eos: Tagged        # day of the harvest year; negative = previous autumn (unit "day of harvest year"; see T2.2)
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

Region-level files: `packs/<region>/index.json` (list of fields, bbox), `packs/<region>/hindcast.json` (baseline comparison table), `packs/<region>/layers.json` (regional trend layers and Current-option field colouring) and `packs/regions.json` (region list); models and the full file layout in §3b.

**Tagging rule (what the "no untagged numbers" validator checks).** Every value a user reads as a claim about the field or an option must be `Tagged`, or sit inside a `TaggedSeries` / `TaggedGrid` (§3b: one unit, tag and source for a whole array): all `Season` metrics, `credibility`, every `Option.metrics` entry, `Option.regret`, `Advice.flip_probability`, `WitnessResult.estimate`, and `LedgerEntry.predicted` / `observed`. Exempt by design, listed in `schemas.EXEMPT_FIELDS`: identifiers, `area_ha`, `interior_pixels`, `clear_obs`, `crop_conf`, `n`, `rank`, `diagnostics`, `scores` (these are bookkeeping or scoring outputs whose provenance is the module itself), and from §3b `bbox_lonlat` (geometry), `dt_c` and `dp_pct` (scenario grid coordinates we choose), `resolution_km` (product metadata, shown with its `resolution_source`), `years_with_data` and `clear_frac` (observation counts and fractions, like `clear_obs`). The validator walks the pack and fails on any float outside `Tagged` that is not on the exempt list.

### 3b. Extension: app data files (final, approved by the user 2026-11-04)

Copied from the final `docs/schema_ext_proposal.md` §3 on branch `app` (commit `dd97bf5`; decisions Q1–Q7 in its §5 and in DECISIONS.md). **Implemented in `src/fieldwitness/schemas.py`** (with the §3 models, the validators noted as comments below, `EXEMPT_FIELDS`, `SEQUENCE_ONLY_METRICS` and `check_tagged`; tests in `tests/test_schemas.py`). Pipeline code imports the models from `fieldwitness.schemas`; it does not define its own. T8.2 exports them to `app/src/types.ts`. `FieldPack` is unchanged.

```python
# --- changes to existing §3 models ----------------------------------------------------
# Season.sos / peak / eos: "day of year" -> "day of the harvest year, negative = previous autumn" (Q1)
# EXEMPT_FIELDS += {"bbox_lonlat", "dt_c", "dp_pct", "resolution_km", "years_with_data", "clear_frac"} (Q3)
# The tag validator treats Tagged, TaggedSeries and TaggedGrid as tagged containers.

class TaggedSeries(BaseModel):
    """Many numbers that share one unit, tag and source (keeps per-field files small)."""
    x: list[date] | list[int]  # dates, or years / months
    values: list[float | None]
    lo90: list[float | None] | None = None
    hi90: list[float | None] | None = None
    unit: str
    tag: Tag
    source: str
    # validator: values / lo90 / hi90 have the same length as x

# --- <field_id>.series.json -----------------------------------------------------------
class FieldSeries(BaseModel):
    schema_version: str
    field_id: str
    ndvi: TaggedSeries         # observed, tag O: median over interior pixels per clear date
    evi: TaggedSeries          # observed, tag O
    clear_frac: list[float]    # clear-pixel fraction per date in ndvi.x (bookkeeping)
    ndvi_smooth: TaggedSeries  # smoothed curve, tag D
    # SOS / peak / EOS are not repeated: the app reads them from FieldPack.story (Q2)
    data_as_of: date
    # validator: ndvi, evi and clear_frac share the same dates

# --- <field_id>.calendar.json ---------------------------------------------------------
Hazard = Literal["heat", "frost", "water_stress", "extreme_rain_bare"]

class BareMonth(BaseModel):
    month: int                 # 1..12 (Field(ge=1, le=12))
    bare_share: Tagged | None  # share of years bare in this month; None when insufficient
    clear_obs: int
    years_with_data: int
    insufficient: bool         # T2.5: too few clear observations -> "insufficient data", not filled

class CropVulnerability(BaseModel):
    crop: str
    years: tuple[int, int]               # POWER weather years used, e.g. (2001, 2021)
    thresholds: dict[Hazard, Tagged]     # cited source (tag E) or tag A with a note
    threshold_notes: dict[Hazard, str]
    shares: dict[Hazard, TaggedSeries]   # x = months 1..12, values = share of years, tag D

class FieldCalendar(BaseModel):
    schema_version: str
    field_id: str
    bare_observed: list[BareMonth]               # T2.5, tag O, 12 items
    bare_observed_years: tuple[int, int]
    bare_by_option: dict[str, TaggedSeries]      # simulated bare share per month per option, tag D
    vulnerability: list[CropVulnerability]       # current crops + every option crop (T3.6)
    data_as_of: date

# --- <field_id>.scenarios.json --------------------------------------------------------
# T6.7 metrics defined only by the crop sequence: identical in every scenario, kept in the pack (Q6)
SEQUENCE_ONLY_METRICS = frozenset({"legume_share", "family_breaks", "forage_value", "deep_root_share"})

class Scenario(BaseModel):
    scenario_id: str                          # e.g. "t+1_p-10"
    dt_c: float                               # temperature change, °C (grid coordinate)
    dp_pct: float                             # rainfall change, % (grid coordinate)
    metrics: dict[str, dict[str, Tagged]]     # option_id -> weather-sensitive metric -> value
    ranks: dict[str, int]                     # option_id -> rank under default weights

class FieldScenarios(BaseModel):
    schema_version: str
    field_id: str
    baseline_id: str           # "t+0_p+0" = the pack's own Option metrics
    note: str                  # "Sensitivity tests on past weather, not climate projections."
    scenarios: list[Scenario]  # 3 temperatures x 4 rainfall = 12 (T6.8)
    data_as_of: date
    # validator: exactly 12 scenarios; baseline_id is one of them; no SEQUENCE_ONLY_METRICS

# --- packs/<region>/layers.json -------------------------------------------------------
class GridCell(BaseModel):
    bbox_lonlat: tuple[float, float, float, float]  # W, S, E, N
    values: list[float | None]                      # one per year in the parent grid's `years`

class TaggedGrid(BaseModel):
    """A coarse raster as cells; one unit, tag and source for every value."""
    years: list[int]
    cells: list[GridCell]
    unit: str
    tag: Tag
    source: str

class RegionalLayer(BaseModel):
    layer_id: Literal["grace_tws", "smap_anomaly", "heatwave_days"]
    resolution_km: float
    resolution_source: str     # product doc the resolution comes from
    scale_flag: bool           # True whenever a pixel is larger than field area / 4 (CLAUDE.md rule 5)
    grid: TaggedGrid           # map layer with year slider (T9.11b)
    region_mean: TaggedSeries  # x = years; context strip (T9.9)
    trend: Tagged              # slope per year over region_mean, tag D

FieldColourMetric = Literal["erosion_exposure", "water_stress_share", "frost_share"]

class RegionLayers(BaseModel):
    schema_version: str
    region_id: str
    layers: list[RegionalLayer]
    field_colouring: dict[FieldColourMetric, dict[str, Tagged]]  # metric -> field_id -> value, Current option (Q5)
    data_as_of: date

# --- packs/<region>/index.json, packs/<region>/hindcast.json, packs/regions.json -------
class FieldSummary(BaseModel):
    field_id: str
    geometry_wkt: str
    area_ha: float
    current_sequence: list[str]
    top_option_id: str
    top_grade: Literal["A", "B", "C", "D"]

class RegionIndex(BaseModel):
    schema_version: str
    region_id: str
    name: str
    tier: Literal[1, 2, 3]
    bbox_lonlat: tuple[float, float, float, float]
    basemap: str | None        # path of the HLS true-colour composite (T9.1); None = neutral fallback
    fields: list[FieldSummary]
    data_as_of: date

class HindcastRow(BaseModel):
    method: Literal["fieldwitness", "B0", "B1", "B2", "B3"]
    mode: Literal["forecast", "forced"]
    metric: str                # "canopy_integral" | "cover_days" | "sos" | "peak" | "water_use_mm"
    n: int                     # scored field-seasons
    scores: dict[str, float]   # crps, covered50, covered90, timing_err_days (as LedgerEntry.scores)

class RegionHindcast(BaseModel):
    schema_version: str
    region_id: str
    cutoff: date
    scored_years: list[int]
    crop_observed_source: Literal["label", "classifier"]
    rows: list[HindcastRow]
    story_field_id: str        # field whose ledger is the predicted-vs-observed chart
    data_as_of: date

class RegionEntry(BaseModel):
    region_id: str; name: str; tier: Literal[1, 2, 3]

class RegionList(BaseModel):   # packs/regions.json, for the region switcher (T9.1)
    regions: list[RegionEntry]
```

**File layout** (user decision 2026-11-04). Per field: `packs/<region>/<field_id>.json` (`FieldPack`), `<field_id>.series.json` (`FieldSeries`), `<field_id>.calendar.json` (`FieldCalendar`), `<field_id>.scenarios.json` (`FieldScenarios`). Per region: `packs/<region>/index.json` (`RegionIndex`), `hindcast.json` (`RegionHindcast`), `layers.json` (`RegionLayers`). Global: `packs/regions.json` (`RegionList`, Q7). Each file < 300 KB.

**Decisions (Q1–Q7):** Q1 season dates are days of the harvest year (T2.2); Q2 `series` does not repeat SOS/peak/EOS — the app reads them from `FieldPack.story`; Q3 six new exempt fields; Q4 `bare_by_option` is new simulated output (tag D) from physics (T3/T6), not part of T2.5, used by T9.9; Q5 field colouring describes the Current option only (colouring by an alternative is stretch S7); Q6 scenarios store weather-sensitive metrics only — `SEQUENCE_ONLY_METRICS` (`legume_share`, `family_breaks`, `forage_value`, `deep_root_share`) live once in `Option.metrics` and the validator rejects them in a scenario; Q7 `packs/regions.json` approved.

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

- [x] **T1.1 `asof` guard.** *Done 2026-11-04: `fieldwitness.data.asof` (as_of, limit_end, guard, forcing_weather channel, reader registry); `tests/test_leakage.py` runs every registered reader under a 2021-12-31 cut-off and fails if a reader has no case.* Context manager `with as_of(date):` that every data reader respects; readers raise if they return records after the cut-off. *Accept:* leakage tests in `tests/test_leakage.py` pass for every reader.
- [x] **T1.2 POWER client.** *Done 2026-11-04: `fieldwitness.data.power` — one call returns 2001–2024 (8,766 days, no gaps) for the Kansas tile centre; −999 → NaN; Parquet cache per point rounded to 0.01°; test on a recorded (trimmed) response.* Daily point API (`https://power.larc.nasa.gov/api/temporal/daily/point`), community `AG`; verify parameter names (T2M_MAX, T2M_MIN, RH2M or dew point, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR) against the API docs before use. Disk cache (Parquet) per grid cell. *Accept:* 2001–2024 daily series for one point; missing values handled; test with a recorded response.
- [x] **T1.3 SoilGrids client.** *Done 2026-11-04 via the WCS fallback (REST down): 5 properties × 6 depths × {mean, Q0.05, Q0.5, Q0.95} for all 200 Kansas pilot fields, 24,000 values, 0 missing; units converted per the ISRIC table; tag E.* REST `properties/query` for sand, silt, clay, SOC, bulk density at the depths needed; Q50 plus Q05/Q95. *Accept:* values for 5 points cached; units documented.
- [x] **T1.4 Field resolver** *Done 2026-11-04 (Kansas): 200 pilot fields (wheat 89, sorghum 57, maize 54; 116 of 121 10 km blocks) from 9,905 CSB 2024 candidates; 20 points → 14 polygons / 6 "no field"; interior pixels match an independent GDAL count on 3 fields (`results/pilot_fields/`, `results/resolver_check.json`).* (`resolve/`). Point → polygon (CSB/EuroCrops first in Tier 1–2, FTW otherwise); `field_id` hash; interior-pixel mask on the HLS 30 m grid: fields are **annual arable crop parcels** where a crop taxonomy exists (HCAT3 rule in `fieldwitness.data.hcat`, full class list in `docs/hcat_annual_arable.md`); a pixel is interior when its centre lies ≥ 15 m (half a pixel) inside the field edge, i.e. a 15 m inward buffer (`fieldwitness.resolve.pixels`). *Changed 2026-11-04 from a one-pixel (30 m) buffer: in the T0.5 census the share of fields with ≥ 4 interior pixels at 30 m vs 15 m was Kansas 88.6 % → 98.1 % (full tile), Beauce 54 % → 61 %, Nile Delta 6.9 % → 33.6 %, Punjab 2.4 % → 18.3 %; 30 m discarded many usable fields, 15 m still keeps every counted pixel centre half a pixel from the edge (DECISIONS.md).* Scale flags. *Accept:* 20 points across regions return a polygon or "no field"; interior pixel counts match a manual check on 3 fields.
- [x] **T1.5 HLS-VI series.** *(Done 2026-11-04, Kansas: 134,685 field-dates, 200/200 fields, 2015-09→2024-12; `data/hls_qa.py`, QA rule in its docstring, as_of reader + leakage case + QA test.)* (a) AppEEARS area request for all pilot fields per region; (b) fallback: STAC search + COG windowed reads with `rioxarray`. Use the HLS quality layer (Fmask) to drop cloud, shadow, snow. Output: per field, per date, median NDVI/EVI over interior pixels + clear-pixel fraction. *Accept:* series for all pilot fields 2016–2024; QA rule documented.
- [x] **T1.6 Labels.** *Done 2026-11-04 (Kansas): CSB 2017–2024 crop per pilot field-year by spatial join (ids do not persist across the per-year files); 1,600/1,600 field-years labelled; coverage report `results/labels/ks_t14slh_coverage.json`.* Per field-year crop label from CSB (Tier 1, `ftw/harmonized-field-data/us_usda_cropland`, 2017–2024 edition) and the French RPG/EuroCrops V2 series (Tier 2, `ftw/harmonized-field-data/fr`); harmonise crop names to `crops.yaml`; select fields as annual arable crop parcels on the current (most recent) year (`fieldwitness.data.hcat.is_annual_arable`, same definition as T1.4); in crop histories keep fallow and temporary grass as the crop states "fallow" and "temporary_grass" (`history_state`), never dropped, and remove a field from history analysis only if it leaves arable use (`stays_arable`: a year in HCAT3 groups 3302–3308; 3399 and missing codes are "unknown" states); map the unmapped France `crop:code` values (null `hcat:code` in 2023–24). *Accept:* label table with coverage report.
- [ ] **T1.7 Water truth (Tier 1).** Kansas WIMAS annual volumes for points of diversion in the region (verify access); (OpenET removed from the MVP 2026-11-04, see S6); ECOSTRESS ET overpasses (`ECO_L3T_JET` v003) for Tier 2–3 pilot fields. *Accept:* whichever sources are accessible are cached; unavailable ones are logged in `DECISIONS.md`.
- [x] **T1.8 Context datasets.** *(Done 2026-11-04: GRACE trend + SMAP monthly anomaly cached for all 3 regions; NASADEM slope for Kansas fields only, as no fields exist yet for Ukraine/Toulouse; ids and shapes in `docs/api_notes.md`.)* Verify collection IDs and access first (rule 2). (a) SRTM or NASADEM 30 m elevation → slope per field (mean over interior pixels). (b) GRACE/GRACE-FO mascon terrestrial water storage → regional monthly series and linear trend since 2002 for each pilot region; it is coarse, so context only, with a scale flag, never a field claim. (c) SMAP L4 root-zone soil moisture → monthly anomaly for the region (context). *Accept:* values cached for all three regions; ids and response shapes in `docs/api_notes.md`.

**Gate 1:** one full Tier 1 region has polygons, HLS series, weather, **soil values for the pilot fields (T1.3)** and labels on disk.

### Phase 2 — Field story (`src/fieldwitness/story/`)

- [x] **T2.1 Smoothing.** *(done 2026-11-04: `story/smooth.py`, numpy-only SG, params in `config/story.yaml`, property test passes)* Savitzky–Golay on gap-filled series (window and order in config); optional GPR later. *Accept:* property test: output length = input; no values outside [-1, 1].
- [ ] **T2.2 Seasons and phenology.** *(code done 2026-11-04: `story/seasons.py`, `tests/test_seasons.py`; acceptance check run once, FAILED 74.6% < 90%, see `results/story/ks_seasons_check.json`; not ticked)* Segment the series into seasons and assign each to its **harvest year** (calendar year of EOS), matching how CDL/CSB label winter wheat; a second season ending in the same year gets `index = 1`; where a crop has winter and spring variants (wheat, barley; `config/crops.yaml`), assign the variant per field-season from the observed green-up: autumn green-up before winter → winter variant, spring green-up only → spring variant (tag `D`); SOS/EOS by amplitude-threshold method (e.g. 20%/50% of seasonal amplitude, choice documented); peak, canopy integral, cover days (NDVI ≥ cover threshold), bare days. Each output `Tagged` with tag `O` (direct metrics) or `D` (thresholded). **Day-of-year rule (v1.2-ext):** `sos`, `peak` and `eos` are counted in days of the harvest year, negative for the previous autumn, with 1 Jan of the harvest year = 1 and 31 Dec of the previous year = 0 (unit string `"day of harvest year"`); e.g. sown 15 Oct 2022, harvest year 2023 → SOS = −77. *Accept:* on 30 labelled fields, the number of detected seasons matches the crop calendar for ≥ 90% (target, team choice).
- [ ] **T2.3 Crop classifier.** Random Forest on phenology features + monthly composites; train on Tier 1–2 labels; spatially blocked CV; calibrated probabilities → `crop_conf`. *Accept:* `results/classifier/` with per-crop F1, confusion matrix, US→EU and EU→US transfer scores.
- [ ] **T2.4 WorldCereal cross-check (Tier 3).** Compare 2021 classifier output with WorldCereal 2021 maize/cereal maps. *Accept:* agreement table.
- [x] **T2.5 Bare-soil calendar.** *(done 2026-11-04 for Kansas: `story/bare.py`, 200/200 fields, 0 insufficient months; `results/story/ks_bare_calendar.json`; cover threshold 0.30 is tag A)* Per field: for each month, the share of past years (≥ 2016) in which the field was bare (NDVI below the cover threshold in T2.2), with clear-observation counts. Tag O. *Accept:* calendar for all pilot fields; months with too few clear observations are marked "insufficient data", not filled.

**Gate 2:** field stories for all pilot fields; classifier report committed.

### Phase 3 — Witness 1: physics (`src/fieldwitness/physics/`)

- [x] **T3.1 ETo.** *(done 2026-11-04: Example 18 reproduced in tests/test_eto.py; POWER→ETo/rain forcing in physics/forcing.py.)* FAO-56 Penman–Monteith daily (Eq. 6 and supporting equations). *Accept:* unit tests reproduce the FAO-56 worked examples (numbers taken from the paper) within the rounding shown there.
- [x] **T3.2 Crop coefficient curve.** *(done 2026-11-04: physics/kc.py, Fig. 34 shape + Eq. 62/65 adjust, tests/test_kc.py.)* Piecewise Kc from stage lengths, adjusted Kc_mid for climate (FAO-56 Eq. 62). Sowing date is a parameter. *Accept:* tests on known shapes.
- [x] **T3.3 Water balance.** *(done 2026-11-04: `physics/waterbal.py`, hypothesis tests for mass/Ks/Dr bounds pass; CR=0 and runoff fraction tag A.)* Daily root-zone depletion (FAO-56 Eq. 85) with TAW, RAW, Ks (Eq. 84), runoff (simple), deep percolation; irrigation policies: `rainfed`, `trigger_at_RAW(efficiency)`, `fixed_seasonal_mm`. *Accept:* property tests: mass closes each day, 0 ≤ Ks ≤ 1, 0 ≤ Dr ≤ TAW.
- [x] **T3.4 Season outputs.** *(done 2026-11-04: `physics/season.py`, tests/test_season.py; canopy proxy = Kc/Kc_mid; FAO-33 equation number UNVERIFIED, cover_frac 0.5 tag A.)* ETa, irrigation mm, Relative Yield Index via FAO-33 Ky (`1 − Ya/Ym = Ky (1 − ETa/ETc)`), simulated canopy proxy (Kc-shaped curve) for comparison with HLS, cover days. *Accept:* outputs tagged `D`.
- [x] **T3.5 Rotation simulation.** *(done 2026-11-04: `physics/rotation.py` + `irr_mask` in waterbal.run; benchmark 200×30×20 (3 seasons) = 8.4 s; kc_fallow 0.3 tag A UNVERIFIED; crop windows must fit in one calendar year.)* Run a sequence of crops with carry-over soil water between seasons and fallow periods. **Design for batching from day one:** state arrays shaped `(options, draws, years)` stepped through days in NumPy, so one call simulates everything for a field. *Accept:* benchmark test — 200 sequences × 30 draws × 20 years for one field in < 60 s on the laptop. If it misses, profile first, then consider `numba` (ask before adding it).
- [x] **T3.6 Vulnerability calendar.** For the current crop and each option crop, using the crop stages from T3.2 and POWER weather 2001–cut-off: share of years with (a) heat-stress days in the sensitive stage (Tmax above a crop-specific threshold), (b) frost after green-up (Tmin ≤ 0 °C), (c) water stress (simulated Ks < 1) by stage, (d) extreme-rain days (above the local 99th percentile of daily rain) falling on bare soil. **Thresholds come from a cited source or are tagged A with a note; never from memory.** *Accept:* a month × hazard table per field-crop. *Done 2026-11-04:* `physics/vulnerability.py` + `config/vulnerability.yaml`; heat thresholds are tag A placeholders (UNVERIFIED); Ks comes from the water balance; no real-field run yet.

**Gate 3:** physics runs for every pilot field and crop; FAO tests pass.

### Phase 4 — Witness 2: own past (`src/fieldwitness/infer/`)

- [x] **T4.1 Hidden variables and priors.** *(done 2026-11-07: `config/priors.yaml` + `infer/priors.py` + tests; all priors tag A, UNVERIFIED team choices with reasons.)* sowing-date offset, TAW scale, irrigated (bool), seasonal irrigation mm, Kc_mid scale. Priors in config, with reasons.
- [x] **T4.2 Synthetic fields.** *(done 2026-11-07: `infer/forward.py`, `infer/synthetic.py`, `config/synthetic.yaml`, `scripts/t42_synthetic.py`, tests; gaps + noise sd 0.013 from the Kansas HLS census (tag D); NDVI map, stress coupling, nominal sow day tag A UNVERIFIED; truth and ABC share one forward model.)* Generate fields with known hidden values; simulate their seasons; add realistic noise and cloud gaps taken from the census.
- [x] **T4.3 ABC rejection.** *(Done 2026-11-07: `infer/abc.py`, `scripts/t43_abc.py`, `results/inference/abc_recovery*`; 300 fields, N=6000/yr, k=300: taw_scale, irrigation_mm, kc_mid_scale within ±5 pts but weakly informative (sd ratio 0.76–0.90); sow_offset over-covers (0.85/0.997, conservative) so listed not calibrated; irrigated by accuracy 0.77.)* Summary statistics: SOS, peak timing, EOS, canopy integral (+ seasonal ET where available). Distance on standardised stats; keep the closest *k* draws as posterior "worlds" (k = 300 default). *Accept:* on synthetic fields: parameter recovery plots, 50/90% coverage per variable within ±5 points of nominal, or the variable is listed as not identifiable.
- [x] **T4.4 Simulation-based calibration.** SBC rank histograms per variable. *Accept:* figures in `results/inference/`. *(done 2026-11-07: `scripts/t44_sbc.py` → `sbc.json`, `sbc_<var>.svg`; 500 fields; flat: irrigated, taw_scale; hump (too wide): sow_offset_days, irrigation_mm; kc_mid_scale skewed. Negative results reported.)*
- [ ] **T4.5 Real fields + credibility.** Run on pilot fields; credibility = Spearman rank of seasons (observed vs simulated canopy integral) + median timing error, combined as in `grading.yaml`. *Accept:* credibility for every pilot field; distribution figure. *(2026-11-07 run, NOT ticked: `scripts/t45_credibility.py` → `results/inference/credibility.json`, `credibility_hist.svg`. 185/200 fields have credibility (101 full, 84 timing-only <3 seasons); 15 winter-wheat-only fields are not assessable because only maize and sorghum are modelled. Median 0.50, 42.7 % ≥ 0.6. In-sample posterior predictive. Waiting for user decision.)*
- [ ] **T4.6 Irrigation check (Tier 1).** Posterior irrigation vs WIMAS annual volumes (season scale only). *Accept:* bias and R² reported, whatever they are.

**Gate 4:** posteriors and credibility for all pilot fields; synthetic diagnostics committed.

### Phase 5 — Witness 3: neighbours (`src/fieldwitness/neighbours/`)

- [x] **T5.1 Field-season table.** *(Done 7 Nov: `neighbours/table.py`, `scripts/t51_table.py` → `data/neighbours/ks_t14slh_field_season.parquet` (1400 rows, 1040 with outcomes, 200 fields; only the 200 pilot fields, no enlargement), `results/neighbours/precrop_contrast_counts.csv`; fixed per-crop windows (A); no irrigation proxy, no ET.)* For Tier 1–2 regions (enlarge to surrounding tiles if n is small): field, year, previous crop, current crop, outcomes (canopy integral, peak, season length, cover days, drought-season canopy drop, ET if available), confounders (season weather aggregates, soil, field size, x/y cell, earlier crops, irrigation proxy). *Accept:* table + row counts per precrop contrast.
- [x] **T5.2 Double ML.** *(Done 7 Nov: `neighbours/dml.py`, `scripts/t52_dml.py` -> `results/neighbours/effects.csv`; 144 rows, 92 fitted, 20 with CI excluding 0; block-grouped cross-fitting; no multiple-testing correction, diagnostics pending T5.3.)* Partially linear model (verify the `doubleml` API from its docs; fallback EconML) with gradient-boosting or RF nuisance learners, cross-fitting; contrasts per outcome crop (e.g. maize after soybean vs maize after maize). Split by wet vs dry season (precip percentile). *Accept:* effects with 95% CIs in `results/neighbours/effects.csv`.
- [x] **T5.3 Diagnostics.** Placebo (next year's crop as treatment), negative-control outcome (pre-treatment season), propensity overlap, covariate balance. *Accept:* contrasts failing diagnostics are flagged and not shown as evidence. — Done: 0/92 contrasts pass all four checks (balance fails everywhere: two-year rotation history); none shown as evidence, see `results/neighbours/diagnostics.md`.
- [x] **T5.4 Literature check.** *(Done 8 Nov: `scripts/t54_literature.py` -> `results/neighbours/literature_check.md`; sources arXiv:2506.02384v2 Table S9 US rows (v2 title "Precrop Payoffs…", ERL 20 (2025) 114037) + NASA Earth Observatory "How to Rotate Crops" (28 Jul 2025); stratum all: 2 agree, 1 disagree, 13 inconclusive; none passes T5.3, descriptive only.)* Compare signs with published US precrop findings: Kluger, Di Tommaso & Lobell (2025), "Evaluating crop rotations around the world using satellite imagery and causal machine learning", arXiv:2506.02384 (citation confirmed by the planning research; open the paper to take numbers). Note our outcomes are canopy/water, not yield. *Accept:* `results/neighbours/literature_check.md` listing agreements and disagreements.
- [x] **T5.xa Matching-history design.** *(Done 2026-11-08: `src/fieldwitness/neighbours/matching.py`, `scripts/t5xa_matching.py` -> `results/neighbours/matching_effects.csv`, `matching_diagnostics.csv`, `matching_diagnostics.md`; 32 fitted, 32 overlap pass, 8 balance pass (SMD <= 0.25), 0 shown as evidence due to placebo/negctrl failure or small sample; T5.3 primary negative result confirmed, neighbour witness remains OFF in grading.)* Secondary analysis conditioning on identical previous-2-year crop (`prev2_crop`) to eliminate the two-year rotation imbalance identified in T5.3. DoubleML PLR with spatial block cross-fitting and preregistered diagnostics. *Accept:* matching effects and diagnostics tables committed; negative results reported honestly.
- [x] **T5.xb Surrounding tiles.** *(Done 2026-11-08: `scripts/t5xb_estimate_tiles.py` -> `results/neighbours/tiles_estimate.json`, `tiles_estimate.md`; 1 tile = 1.23 GB, 8 surrounding tiles = 9.81 GB; stopped per CLAUDE.md Rule 11 download cap > 1 GB.)* Estimate HLS download size to enlarge Kansas sample to adjacent MGRS 100 km tiles; stop if > 1 GB. *Accept:* size estimate documented, stop condition respected.
- [ ] **T5.xc Re-grade.** *(Trigger condition not met: T5.xc specifies re-grading "only if a contrast passes". Since 0 contrasts passed diagnostics in T5.3 and T5.xa, neighbour witness stays OFF, and existing packs remain valid without re-grading.)* Re-run `scripts/t65_grade.py`, rebuild and validate packs only if a contrast passes.

**Gate 5:** at least one Tier 1 contrast passes diagnostics.

### Phase 6 — Agreement and rotation engine (`agree/`, `rotate/`)

- [x] **T6.0 Current rotation.** *(Done 2026-11-07: `rotate/current.py`, `packs/build.py`, 7 tests pass in `tests/test_current.py` incl. `test_every_kansas_field_has_current`; Kansas packs have option 1 "Current", deltas and gaps shown.)* Derive the field's current rotation from its last three seasons in the field story (labels in Tier 1–2, classifier in Tier 3, with confidence). It is always option 1 ("Current"), even when it contains a crop excluded from new options (then it is simulated where possible and the gap is shown). *Accept:* every pack has a Current option; benefits are shown as deltas against it.
- [x] **T6.1 Candidates.** *(Done 2026-11-07: `rotate/candidates.py`, Kansas 5 crops → 61 sequences, ban property test passes; windows from config, not observed SOS/EOS because T2.2 failed.)* Enumerate 3-season sequences from the region's **rotation options** (`fieldwitness.config.rotation_options`: crops with `mvp_role` rotation or rotation_no_yield; barley is prediction-only because RYI needs a verified Ky, rapeseed is history-only; user decision 2026-11-04); hard constraints: allowed crops, calendar fit (season windows from observed local SOS/EOS), max consecutive same family, user bans. *Accept:* banned crop never appears (property test).
- [x] **T6.2 Evaluate.** *(Done 7 Nov: 200 fields × 61 candidates, max 18.3 s/field; `results/rotate/evaluation.json`.)* Prune candidates with hard constraints first, then for each survivor simulate in one batched call (T3.5) over posterior worlds (subsample, default 30) × weather years 2001–cut-off; metrics: mean water use, irrigation, RYI, cover days, CVaR10 of water and of RYI. *Accept:* runtime < 60 s per field for all candidates (cache as needed).
- [x] **T6.3 Rank.** *(Done 7 Nov: `rotate/rank.py`, `config/ranking.yaml`, `results/rotate/ranking.json`; reproducible, 175 tests pass; weights tag A; see DECISIONS for RYI-metric caveat.)* Pareto filter + weighted score (default weights in config, user-movable in the app via precomputed per-weight-preset rankings or in-browser recomputation from per-option metrics). Regret matrix across weather years. *Accept:* rankings reproducible with seed.
- [x] **T6.4 What to measure next + counterfactual flip.** *(Done 7 Nov: `rotate/flip.py` incl. `advice()` → schema `Advice`; `results/rotate/flip.json`, 200 fields × 4 presets; sowing offset not analysed, it is not a world input.)* For each uncertain input (TAW, sowing offset, irrigation, Kc scale): share of posterior draws where rank 1 changes; smallest single-input change that flips rank 1. *Accept:* values in `Advice`.
- [x] **T6.5 Grades.** Apply `grading.yaml` rule using physics vs neighbour effects for the matching transition. *Accept:* each option has grade + reasons; unit tests for each grade branch. *(Done 2026-11-07 physics + own-past only: 187 fields × 36 options → B 2772, C 3600, D 360; 13 fields with non-simulatable Current have no grades; neighbour witness absent until T5.2 → re-run `scripts/t65_grade.py` then.)*
- [x] **T6.6 Strategy explanation.** *(Done 2026-11-07: `rotate/explain.py` + `tests/test_explain.py`, 203 tests pass; wiring into packs is T8.1.)* Add `Explanation` (§3) to every `Option`: `why`, `evidence`, `benefits`, `gaps`, `risks`. Generated by deterministic rules and templates from the computed metrics; every sentence is traceable to a number or flag (no LLM). *Accept:* unit tests for each template; no option has an empty `gaps` or `risks` list.
- [x] **T6.7 Priority metrics** (done 2026-11-07: 6 metrics x 36 options x 200 fields in `results/rotate/priority.json`, none missing; erosion/residue thresholds tag A, UNVERIFIED) (each a `Tagged` value in `Option.metrics`):
  - `legume_share`: share of seasons with a Fabaceae crop (family from GBIF, verified). Label: "nitrogen-fixing crops in the rotation". Tag D. No kg N claim.
  - `family_breaks`: number of family changes between consecutive seasons. Label: "pest and disease break opportunities". Tag D.
  - `erosion_exposure`: relative index = Σ over days of (simulated bare or low cover) × (daily rain above an erosive threshold, IMERG/POWER) × slope factor (SRTM). Unitless, compared between options of the same field only. Tag D. **Not tonnes of soil.**
  - `residue_proxy`: organic-matter input proxy from simulated canopy integral plus cover days. Label: "organic matter input (proxy, not soil carbon)". Tag D.
  - `forage_value`: per crop, a yes/no forage use from a cited source (e.g. FAO crop descriptions), else tag A.
  - `deep_root_share`: share of seasons with a crop whose maximum rooting depth (FAO-56 Table 22, verified) is above a stated threshold. Label: "deep-rooting crops in the rotation". Tag D.
  - Market suitability is **not** a metric. It is a user constraint ("crops I can sell") on the Field Card, stored as user input.
  *Accept:* all metrics present for every option; labels match this list exactly.
- [x] **T6.8 Weather what-ifs.** *(done 2026-11-07: 12 scenarios x 200 fields, 46.7 KB/field raw in `results/rotate/scenarios.json`; split into `<field_id>.scenarios.json` at T8.1.)*** For each field, precompute every option under a small grid of weather changes applied to the historical years: temperature +0, +1, +2 °C × rainfall −20%, −10%, 0, +10%. Store per-option metrics per scenario in `<field_id>.scenarios.json` (§3b `FieldScenarios`; weather-sensitive metrics only — `SEQUENCE_ONLY_METRICS` stay in the pack's `Option.metrics`, Q6), so the app's sliders switch between precomputed results instead of simulating in the browser. These are sensitivity tests, not climate projections; say so in the UI. *Accept:* 12 scenarios per field; pack size still under the limit, or the scenarios split into a second file per field.
- [x] **T6.9 Farmer corrections.** (Done: backend, TS port, localStorage, Field Card panel; real-pack test on all Kansas packs shows a corrected history changes the Current sequence, tag E, "re-run needed". No precomputed alternatives (no §3 slot). Not run in a browser: unattended.) The app lets a user correct the field's crop history, sowing date and irrigation status. Corrections are stored locally in the browser, tagged E ("farmer-entered"), and shown alongside the satellite version. In the static demo, a correction switches to a precomputed alternative where one exists, and otherwise shows "re-run needed: available in live mode" (API, T8.3). *Accept:* a corrected history visibly changes the Current option and its tags.

**Gate 6:** full `FieldPack` (minus ledger) for one field validates against the schema.

### Phase 7 — Ledger and hindcast (`ledger/`)

**Two hindcast modes, both stored, clearly labelled:**

- **Forecast mode (headline).** What a farmer would actually have received on 1 Jan 2022: weather for 2022–24 is unknown, so each prediction uses the ensemble of past weather years ≤ cut-off. Tests decision value. Intervals are wide by nature; score coverage and CRPS against baselines run the same way.
- **Forced mode (diagnostic).** Same calibration, but the model is driven with the real 2022–24 POWER weather. Tests whether the model is right *given* the weather. This is the one exception to the `as_of` guard: forcing weather enters through a separate, explicitly named channel (`forcing_weather=`), never through calibration or training data. A leakage test checks that only that channel reads post-cut-off data.

**Known, accepted leakage (document in DECISIONS.md and on the Methods page):** field boundaries come from CSB 2024 / FTW 2024–25, which are built from post-2021 imagery. Boundaries are geometry only; no post-cut-off crop labels, outcomes or effects are used. If an older CSB edition is easy to read, prefer it for Tier 1.

**Tier 3 caveat:** the "observed crop" comes from our classifier, so Tier 3 scoring is weaker. Score Tier 3 mainly on crop-agnostic outcomes (SOS, peak timing, canopy integral, cover days) and say so in the scoreboard.

- [x] **T7.1 Predict.** (done 2026-11-08: Kansas 200 fields incl. winter wheat; barley forward model + unit test only, `tests/test_barley_prediction_only.py`; barley hindcast runs when a Tier 2/3 region has fields: blocked input, not a stop) With `as_of=2021-12-31`, re-run Phases 2–6 fitting on data ≤ cut-off; for every pilot field and every option, store predictions for 2022, 2023, 2024 seasons (sos, peak, canopy integral, cover days, water use) with 50/90% intervals. Barley (winter and spring) is included in these predictions (they need only Kc and stage lengths) but is not a rotation option; rapeseed seasons are history only (no predictions: no verified stage lengths or Ky).
- [x] **T7.2 Observe and score.** (Kansas only, maize+sorghum+winter wheat since T7.1b (463 seasons), conditional scoring; weak skill, see DECISIONS; figure `results/hindcast/ks_t14slh_crps.svg`) For the crop actually observed each season (conditional scoring), compute CRPS (from posterior samples), 50/90% coverage, timing error (days), and cross-field Spearman of canopy integral. *Accept:* `results/hindcast/<region>.json` + figures.
- [x] **T7.3 Baselines.** *(Done 2026-11-08: commit dc744b9, `scripts/t73_baselines.py` -> `results/hindcast/ks_t14slh_baselines.json`; B0-B2 scored on Kansas hindcast; B3 omitted pending neighbour witness.)* B0 field mean of past seasons · B1 FAO-table engine (default dates, default soil, Kc × ETo) · B2 uncalibrated physics · B3 neighbour-only. Same scoring. *Accept:* comparison table per tier; results reported whatever they show.
- [x] **T7.4 Ablation + degradation (if time).** Remove witness 2 or 3; degrade observations (fewer clear dates, small fields). *Accept:* skill-vs-field-size curve.

**Gate 7:** hindcast tables for ≥ 1 Tier 1 and ≥ 1 Tier 3 region.

### Phase 8 — Packs and API (`packs/`, `api/`)

- [x] **T8.1 Export packs.** *(Done 2026-11-07, Kansas: 802 files valid, max 279 KB; `cli validate-packs` + CI step on `packs/demo`; `hindcast.json` and the story-field ledger come from `scripts/t72_export.py`, run after `build-packs`; heat-wave layer not built, see DECISIONS.)* `cli build-packs --region <id>` writes every file in the §3b layout: per field `<field_id>.json`, `.series.json`, `.calendar.json`, `.scenarios.json`; per region `index.json`, `hindcast.json`, `layers.json`; and `packs/regions.json`; validates every file against the models in `src/fieldwitness/schemas.py` (already written; do not redefine them) with `check_tagged`; fails if any user-facing number is untagged. *Accept:* each pack < 300 KB; validator in CI.
- [x] **T8.2 Types.** *(Done 2026-11-07: `scripts/gen_types.py` → `app/src/types.ts`; `npm --prefix app run build` (incl. `tsc --noEmit`) passes, 45 app tests pass.)* Generate `app/src/types.ts` from the Pydantic schemas, §3 and §3b (JSON Schema → TS). *Accept:* app compiles against generated types.
- [ ] **T8.3 Optional API.** FastAPI serving packs and a `/simulate` endpoint for live mode. Not used by the deployed demo.

### Phase 9 — Web app (`app/`)

React + Vite + TypeScript, MapLibre GL, a chart library (Recharts or Observable Plot — pick one), strings in `app/src/strings/en.json`. Data loaded from `/packs/...` static files; a service worker caches them for offline use.

- [x] **T9.1 Shell + Map view.** *(Done: commit 4b92da0, app/src/MapView.tsx, app/src/MapLibreMap.tsx, app/tests/mapLayers.test.ts; MapLibre GL, offline service worker, true-colour basemap fallback.)* Region switcher; field polygons from `index.json`; click → open field. **Basemap = our own HLS true-colour composite** of each pilot tile (cloud-free median, peak season), rendered by the pipeline as a small raster or PMTiles file. It is NASA data (no licence problem) and ships with the app, so it works offline. Fallback: a plain neutral background with field outlines. No third-party imagery tiles. *Accept:* loads offline after first visit.
- [x] **T9.2 Field story view.** *(Done: commit 3758960, app/src/FieldStoryView.tsx; season timeline, crop chips, NDVI curve with SOS/peak/EOS marks, scale-flag badges; verified on Kansas packs in 	ests/real-packs.test.ts.)* Season timeline (crop chips with confidence), NDVI curve with SOS/peak/EOS marks, scale-flag badges.
- [x] **T9.3 Field Card view (changed in v1.2).** *(Done: commits 3758960 & 0eab706, app/src/FieldCardView.tsx, app/tests/rank.test.ts, app/tests/correctionPanel.test.ts.)* Shows Current + at least 2 alternatives (sequence, water use, bad-year water, cover days, RYI, grade badge), priority sliders for water, bare-soil months, bad-year risk, erosion exposure, legume share and residue proxy (re-ranked in the browser from per-option metrics), constraint toggles (ban crop, irrigation yes/no, seasonal water cap in mm, crops I can't plant or harvest) plus a "crops I can sell" constraint. Each option opens a detail panel with the five explanation parts (T6.6).
- [x] **T9.4 Advisor Console view.** *(Done: commit 081c955, app/src/AdvisorConsoleView.tsx, app/tests/advisor.test.ts.)* Witnesses side by side per option (estimate + interval + n + diagnostics), credibility and back-test chart (observed vs simulated seasons), what-to-measure-next, counterfactual flip; source-tag legend (O/D/E/A) on every number.
- [x] **T9.5 Hindcast scoreboard.** *(Done: commit 5436ee3, app/src/HindcastScoreboardView.tsx, app/tests/hindcast.test.ts.)* Per region: FieldWitness vs B0–B3 on CRPS, coverage, timing error; one field's predicted-vs-observed 2022–24 as the story chart.
- [x] **T9.6 Methods & data page.** *(Done: commit 61ab7fa, app/src/MethodsView.tsx, app/tests/methods.test.ts.)* Datasets, licences, non-promises, limits, link to repo.
- [x] **T9.7 Responsive + accessibility.** *(Done: commit e81efa4, app/src/index.css; 380 px viewport works, keyboard navigation, colour never carries meaning alone.)* 380 px viewport works; keyboard navigation; colour never carries meaning alone.
- [x] **T9.8 Deploy.** *(Done 2026-11-08: Deployed to GitHub Pages at https://amr-mousa-eg.github.io/fieldwitness/ [mirror: https://willowy-kleicha-452dbc.netlify.app]; static build with all 200 Kansas packs, service worker offline caching enabled, loads in a private window with no login.)*
- [x] **T9.9 Calendar view.** *(Done: commit 6e5acc1, app/src/CalendarView.tsx, app/tests/calendar.test.ts.)* The bare-soil calendar (T2.5) and the vulnerability calendar (T3.6) for the current rotation, with a toggle to show an alternative's calendar: observed bare months from `FieldCalendar.bare_observed` (T2.5), an option's simulated bare months from `FieldCalendar.bare_by_option` (tag D, Q4). A regional context strip shows the GRACE trend, SMAP anomaly and slope, each scale-flagged.
- [x] **T9.10 Explainers.** *(Done: commit 30c7aa7, app/src/Explainer.tsx, app/src/strings/en.json, app/tests/explainers.test.ts.)* A small "What is this?" next to evapotranspiration, soil moisture anomaly, NDVI, frost risk, water balance, Relative Yield Index, evidence grade and source tags, plus short explainers on nitrogen-fixing, cover, deep-rooting and drought-tolerant crops. Each explainer is two or three plain sentences with a cited source (FAO-56, NASA Earthdata pages, or the FAO crop chapters), kept in `app/src/strings/en.json`.
- [x] **T9.11 Map layers.** *(Done: commit 03d8113, app/src/MapLayers.tsx, app/tests/mapLayers.test.ts.)* (a) Field colouring by erosion exposure, water-stress share or frost share (from T3.6 and T6.7). (b) Regional trend layers with a year slider: GRACE water storage, SMAP soil-moisture anomaly, and heat-wave days from POWER. Every layer shows its resolution and scale flag.
- [x] **Fixed line** on the Field Card and the Methods page: *(Verified in app/src/FieldCardView.tsx and app/src/MethodsView.tsx)* "FieldWitness helps you explore options. It does not replace your judgment or local agricultural advice."

### Phase 10 — Hardening and submission

- [x] **T10.1 Documentation & licence.** *(Done 2026-11-08: MIT License committed; README.md finalized with overview, honest hindcast results, and run instructions; DATA.md updated with complete formal citations and DOIs; AI_USE.md updated with Claude Code and Google Antigravity disclosure.)*
- [x] **T10.2 Red-team checklist.** *(Done 2026-11-08: `scripts/t10_red_team_audit.py` -> all checks passed; no forbidden claims, 0 untagged numbers in packs, English UI text, all external sources referenced.)*
- [ ] **T10.3 Freeze and tag.** Freeze `main`, tag `v1.0-spaceapps`, verify the deployed URL and repo in a private window (scheduled for 13 Nov after official rules review, with user approval).
- [ ] **Deployment note.** (Informational: GitHub Pages deployed at https://amr-mousa-eg.github.io/fieldwitness/ via GitHub Actions on public repo).

### Phase 11 — Polish & Submission Preparation (Target: 10–13 Nov)

Ordered priority list (P0 → P1 → P2). Planning mode required per task. Standing permission: push to `main` without asking when pytest, ruff, pre-commit, npm test, and npm build pass.

#### P0 — MUST BE DONE (target: 10 Nov)
- [ ] **P0.1 Real basemap (T9.1 basemap part).** NASA imagery only (D1).
  - (a) Check NASA GIBS official docs for a true-colour layer at ~30 m (Landsat/HLS), usable with MapLibre (WMTS/XYZ), its terms and exact required attribution. MODIS/VIIRS-only layers don't count.
  - (b) If found: use it as the base layer with attribution shown on map. Offline/error: fall back to neutral background without breaking the app.
  - (c) If not found: build a cloud-free summer true-colour composite of tile T14SLH from HLS (bands and scaling from HLS user guide), export compressed image or PMTiles into `packs/demo`, show as MapLibre raster layer. Estimate download first; name new dependencies and wait for OK.
  - (d) Verify field visibility at region zoom (outlines + markers contrast) and alignment at field zoom on 3 fields visually.
  - (e) Document in `DATA.md` and Methods page: source, resolution, date of imagery, attribution.
- [ ] **P0.2 Readable field names.**
  - (a) Show "Field N" (stable numbering, e.g. sorted by field_id or north→south, documented), area, and short hash ID in small text.
  - (b) Field list: sortable by number, area, and grade; search box for "Field N".
- [ ] **P0.3 Map legend.**
  - (a) Explain marker/outline colours (from code) and the scale-flag symbol.
  - (b) Visible in both themes, collapsible on mobile.
- [ ] **P0.4 Light and dark mode (D2).**
  - (a) All colours as CSS tokens (custom properties) for both themes; no hard-coded colours in components, charts, or map overlays.
  - (b) Default from `prefers-color-scheme`; header toggle (Light / Dark / System) saved in localStorage (try/catch protected).
  - (c) Recharts, map overlays, legend, grade badges, crop chips, banners, disclaimer switch cleanly; basemap stays legible.
  - (d) WCAG AA contrast (4.5:1 text, 3:1 large/UI) in both themes, checking grade badges especially.
  - (e) No theme flash on load (theme applied before first paint).
  - (f) Desktop screenshots of every view in light and dark mode.
- [ ] **P0.5 Honest statements visible in the app.**
  - (a) Methods page & Advisor Console state plainly: hindcast skill is weak (actual numbers from results/), season detection missed target (78.3 % vs 90 %), neighbour witness off (0 of 32 matched contrasts passed all checks), grades top out at B.
  - (b) Fixed disclaimer line on every view.
- [ ] **P0.6 Live site check after deploying P0.**
  - (a) Private browser window: all 200 fields load, no DEMO DATA banner, no console errors, offline reload works.
  - (b) Mobile viewport (380 px): no sideways scroll, legend and toggle usable.
  - (c) Report result with screenshots (desktop light, desktop dark, mobile).

#### P1 — SHOULD BE DONE (target: 12 Nov)
- [ ] **P1.7 Performance optimization.** Lazy-load map and chart code to reduce initial JS payload (baseline: 1.77 MB). Report before/after sizes without changing behavior.
- [ ] **P1.8 First-visit guidance.** Short "How to read this" panel (3–4 sentences, dismissible, remembered in localStorage) on map view explaining fields, grades, disclaimer.
- [ ] **P1.9 Consistency pass.** Align numbers, datasets, live URL, and limits across README, DATA.md, AI_USE.md, Methods page, and `docs/drafts/submission.md`.
- [ ] **P1.10 Submission drafts (`docs/drafts/submission.md`).** Project summary, detailed description, NASA data used, other data, AI use. Mark length limits "to verify against the 2026 guide on 13 Nov". Keep claims grounded in results/.
- [ ] **P1.11 Accessibility verification.** Keyboard navigation across all views (run `app/scripts/keyboard-check.mjs`), visible focus in both themes, accessible labels/alt text for map controls.
- [ ] **P1.12 Final test-and-report.** Full test suites, live site check, update handoff documentation.

#### P2 — ONLY IF EVERYTHING ABOVE IS DONE (AND NOT AFTER 12 NOV)
- [x] **P2.13 Add my field — version 0 (Kansas T14SLH).** Static, zero-server, device-only guided form with coverage check against true T14SLH UTM tile polygon, 2026/2025/2024 harvest-year history, inches/mm irrigation input, priority sliders, CSV template/upload, local storage (tag E), nearest analysed field distance matching with disclaimers, and coverage/roadmap documentation. (Replaces Nile Delta confidence map per user decision).
- [ ] **P2.14 Toulouse through Phases 1–8.** Skipped per user instruction (scope Kansas only for submission).
- [ ] **P2.15 T4.6 WIMAS check.** Only when file is placed in `data/wimas/`.

### Stretch (only after all MVP boxes are ticked)

- [ ] S1 Evidence Atlas view (aggregated effects + data-confidence map from the FTW 500 m confidence raster, field size, clear-obs counts).
- [ ] S2 NEX-GDDP-CMIP6 future lens for one SSP.
- [ ] S3 Prithvi-EO-2.0 crop classifier benchmark vs Random Forest (Colab GPU).
- [ ] S4 Tier 3 neighbour effects from inferred crop histories.
- [ ] S5 Live any-point mode via the API.
- [ ] S6 OpenET seasonal ET as an extra water witness for Kansas fields — only if the user accepts OpenET's terms (moved from T1.7, 2026-11-04).
- [ ] S7 Map colouring by an alternative option (T9.11a colours by the Current option only; user decision Q5, 2026-11-04).
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

## 9. Milestone M1 — Migration to second laptop (8 Nov 2026)

- [x] **V1 Git sync:** Repository cloned, main...origin/main in sync (d54f122).
- [x] **V2 Commit hash:** d54f122caa455990d87fd762f21cf52d925df69c verified.
- [x] **V3 Commit count:** 232 commits verified.
- [x] **V4 Branches:** main (active), origin/main, origin/app verified.
- [x] **V6 Data restoration:** data/ (927 files, 1,573.9 MB), packs/ (804 files, 81.7 MB), docs/refs/ (178 files, 1.7 MB; FAO-56 Ch. 2, 3, 4, 6, 8, Annex 2 pages and all 181 image references), logs/ (228 files, 2.4 MB) restored.
- [x] **V7 Python runtime:** uv run python --version -> Python 3.12.16.
- [x] **V8 Pytest test suite:** uv run pytest -q -> 247 passed (all tests incl. needs_data pass, 0 failures).
- [x] **V9 Linters:** uv run ruff check . and uv run ruff format --check . -> clean (151 files).
- [x] **V10 Commit hooks:** uv run pre-commit run --all-files -> all hooks Passed (ruff-check, ruff-format, gitleaks 8.30.1).
- [x] **V11 App tests:** in app/: npm test -> 58 passed (13 test files).
- [x] **V12 App build:** in app/: npm run build -> static build succeeded in 2.82s.
- [x] **V13 Pack validator:** uv run python -m fieldwitness.cli validate-packs packs/ks_t14slh -> 0 problems.

## 10. Phase 11 Polish & Submission Freeze (8–13 Nov 2026)

### P0 — Must be done (target: 10 Nov)
- [x] **P0.1 Real basemap (T9.1):** NASA GIBS HLS S30 true-colour layer (2023-07-04, 30m, EPSG:3857) integrated with official attribution; offline fallback to neutral background without breaking app; visual alignment verified on fields 7008ff6b, 52a7fe05, 20332278; DATA.md and Methods updated.
- [x] **P0.2 Readable field names:** Stable 1-based numbering sorted lexicographically by `field_id` (`Field 1`–`Field 200`), area in ha, short hash ID; sortable by number, area, grade; search box matching "Field N" and hash.
- [x] **P0.3 Map legend:** Visual legend explaining amber field outline/markers, selected highlight, tile boundary, grades B/C/D (A disabled), scale-flag symbols (● fine / ◌ coarse); visible in both themes, collapsible on phones (<48rem).
- [x] **P0.4 Light and dark mode (D2):** Complete CSS tokens for light and dark; prefers-color-scheme default with header toggle (Light / Dark / System) saved in localStorage with try/catch fallback; pre-paint script to prevent theme flash; dynamic charts (Recharts) and map overlays; WCAG AA contrast (text >= 4.5:1, UI >= 3:1); screenshots of every view in light and dark captured.
- [x] **P0.5 Honest statements visible in app:** Methods page and Advisor Console plainly state weak hindcast skill (canopy integral 90% coverage 35.0%, cover days 9.0%, r=0.264), season detection missed target (78.3% vs 90%), neighbour witness OFF (0/32 passed checks), grades capped at B; fixed disclaimer line on every view.
- [ ] **P0.6 Live site check after deploying P0:** Verify live site in private window (all 200 fields load, no DEMO DATA banner, 0 console errors, offline reload works, 380px phone width).

### P1 — Should be done (target: 12 Nov)
- [x] **P1.7 Performance (code splitting):** Lazy-load map (`MapView`) and chart/page code (`FieldPage`, `Scoreboard`, `MethodsPage`, `AdvisorConsole`) via `React.lazy` and `Suspense`. Initial JS payload reduced from 1,785.76 kB (501.1 kB gzip) to 273.64 kB (86.98 kB gzip) — an 84.7% reduction; initial CSS reduced from 89.97 kB to 19.76 kB (78.0% reduction). Verified no change in behavior or offline capability.
- [x] **P1.8 First-visit guidance:** Added dismissible, remembered `GuidancePanel.tsx` (persisted in `localStorage` under `fw-guidance-dismissed` with error fallback) on Map view. Explains 200 Kansas pilot fields, A–D evidence grades (max B with neighbour witness OFF), and the fixed disclaimer.
- [x] **P1.9 Consistency pass:** Cross-checked and aligned numbers and facts across `README.md`, `DATA.md`, `AI_USE.md`, Methods page, and `docs/drafts/submission.md`. Removed Netlify mirror link from `README.md` (GitHub Pages sole public URL per D3); unified season detector test metric (78.3% held-out test, 74.6% pilot check vs 90% target); verified SoilGrids only (no POLARIS/SSURGO); confirmed OpenET marked unread/unused.
- [x] **P1.10 Submission drafts:** Authored complete draft in `docs/drafts/submission.md` with summary, detailed description, NASA data (HLS, GIBS basemap, POWER, SMAP, GRACE, NASADEM), other data (CSB, SoilGrids, FAO-56, HCAT3), and dual AI disclosure (Claude Code + Google Antigravity). Marked "field names and length limits to verify against the 2026 guide on 13 Nov".
- [x] **P1.11 Accessibility audit:** Ran `scripts/keyboard-check.mjs` (all 13 checks PASS including skip-link, focus restoration on route changes, explainer escape, 380px no-overflow); verified high-contrast visible focus ring tokens (`--focus`) in light (`#1f6fb2`) and dark (`#7cb8ec`); accessible labels on map controls.
- [x] **P1.12 Final test-and-report:** Full suite verification passed completely: `uv run pytest -q` (251 passed), `uv run ruff check .` (clean), `uv run pre-commit run --all-files` (all Passed), `npm test` (61 passed), `npm run build` (clean), `validate-packs` (0 problems), `t10_red_team_audit.py` (all passed), `offline-check.mjs` (renders app shell with 0 errors).
- [x] **P1.13 PageSpeed Optimization & Core Web Vitals:** Fixed performance bottlenecks on live site: removed 804 eager pre-cache fetches on first load (switching to on-demand caching in `sw.js`); batch-rendered field list items progressively (initial 25 on first frame, then 35 per frame via `requestAnimationFrame`) to keep TBT under control; eliminated layout shifts (CLS dropped from 1.286 to 0.000) by sizing lazy map placeholders and making mobile guidance an overlay; added meta description, `robots.txt`, and `llms.txt`. First-load requests dropped from 838 to 38, initial payload from 29.7 MB to 1.25 MB (and ~91 KiB excluding NASA GIBS basemap tiles).
- [x] **P1.14 Desktop PageSpeed & Desktop CLS Stabilization:** Stabilized desktop viewport height with `.app--map` directly on shell container (eliminating unconstrained 16,444 px expansion and MapLibre fitBounds thrashing); stabilized header with `.header-actions` and pre-rendered `.app-nav` (eliminating multi-line wrapping and reducing desktop CLS to 0.001); bounded GIBS tiles (`minzoom: 10`, `maxzoom: 12`, Kansas bounding box) eliminating 404 console errors; optimized map startup using `index.bbox_lonlat` and `fadeDuration: 0` (reducing TBT to 120 ms). Desktop Lighthouse verified: Performance 88, TBT 120 ms, CLS 0.001, Payload 1.59 MB, 0 console errors, A11y 100, Best Practices 100, SEO 100.


### P2 — Only if everything above is done, and not after 12 Nov
- [x] **P2.13 Add my field — version 0 (Kansas T14SLH).** Static, zero-server, device-only guided form with coverage check against true T14SLH UTM tile polygon, 2026/2025/2024 harvest-year history, inches/mm irrigation input, priority sliders, CSV template/upload, local storage (tag E), nearest analysed field distance matching with disclaimers, and coverage/roadmap documentation. (Replaces Nile Delta confidence map per user decision).
- [ ] **P2.14 Toulouse through Phases 1–8.** Skipped per user instruction (scope Kansas only for submission).
- [ ] **P2.15 T4.6 WIMAS check:** Only when file is provided in `data/wimas/`.

### Pre-freeze Polish Improvements (9–13 Nov 2026)
- [x] **P2.16 Grade validity check (analysis, no model changes).** Pre-registered in `DECISIONS.md` before execution; evaluated strictly under cut-off `as_of(2021-12-31)`; Current-option grades evaluated on 2022–2024 hindcast (n=463, B=170, C=268, D=25; all n >= 20). Primary test (forecast canopy integral CRPS Grade B vs D: B=16.96, D=24.02, difference +7.07, 10 km spatial block bootstrap 95% CI [-3.28, 14.32]) did not reach significance (CI spans 0). Negative result documented on Scoreboard ("Grades did not predict accuracy in our test, n = 463") and Methods page. 0 model changes made. Results in `results/hindcast/grade_validity.*`.
- [x] **P2.17 Plain-language summary on Field Card.** One sentence per field generated only from pack numbers (Current vs top alternative: bare-soil months, water use, bad-year water, grade) + side-by-side comparison chart. Updates dynamically when sliders move; handles "current is best", tie cases, and trade-offs both ways; real units; source tags; forbidden words checked in red team audit. Verified on all 200 Kansas pilot fields.
- [x] **P2.18 Guided tour & Field in 3D.** "Take the tour" button, 7 steps (field story -> history/source tag [E] -> options & trade-offs -> crop calendar -> hindcast check -> Field in 3D -> add my field), keyboard accessible (Escape / arrow keys), robust to missing selectors, both themes. Field in 3D view with Three.js procedural scene (translucent amber crops, water stress fading, 156-week scrubber, fallback 2D toggle, "Simulated with the weather of 2007; not a forecast" header disclaimer). Fully code-split via `React.lazy` and isolated CSS bundles (`TourGuide.css`, `Field3DView.css`); 0 bytes loaded on map page.
- [ ] **P2.19 Printable field report.** Print stylesheet producing one A4 page per field (story, three options, explanations, disclaimer).

---

## 11. Phase 12 — Evidence and clarity (Deadline: 12 Nov 2026 EOD; 13 Nov is freeze)

### Order and Cut Line
- **MUST**: Item 1, Item 7, Item 9, Item 10, Item 5
- **SHOULD**: Item 3, Item 8, Item 6
- **COULD**: Item 2, Item 4
*Rule*: If time runs short, drop from the bottom of the list first.

### Tasks

#### MUST (Core Evidence & Usability)
- [x] **Item 1: Diagnose why hindcast skill is weak (science, no new data).**
  - Pre-registered in `DECISIONS.md` (commit `e021f3e`) BEFORE running. Evaluated 463 field-seasons across 200 Kansas pilot fields (years 2022–2024) under cut-off `as_of(2021-12-31)`.
  - Spatial block bootstrap (10 km blocks, 1,000 resamples, seed 42); n per cell reported; n < 20 reported as "too few to judge".
  - Primary test: FieldWitness forecast-mode canopy integral CRPS beats B1 (diff +1.23 [0.48, 1.99]) and B2 (diff +1.35 [0.74, 1.90]) overall and for maize, but CI spans 0 for sorghum (diff +0.77 [-0.10, 1.64]). Winter wheat timing reveals severe offset (+36 d signed median error, abs error 58.9 d [52.2, 66.3] d) due to uncalibrated phenology prior stage lengths.
  - Output: `results/hindcast/diagnosis.json`, `results/hindcast/diagnosis.md`, live exploratory section mounted on Scoreboard and Methods pages (`DiagnosisSection.tsx`), unit tests passing (`diagnosis.test.ts`).

- [x] **Item 7: "Why this ranking?" explainer (Field Card).**
  - Implemented in `RankingExplainerSection.tsx`, `rankingExplainer.ts`, and `rankingExplainerConfig.ts` with dominant contribution threshold `0.40` in `config/ranking.yaml` (tag A).
  - Exact mathematical breakdown of score: weight × normalised value = contribution; sum of contributions equals ranking score verified on all 200 real Kansas packs and all alternative options.
  - Side-by-side comparison with next-best option (#1 vs #2), relative score impact, raw tagged values, normalised value bars, and accessible table (`aria-labelledby`).
  - Deterministic sentence: "Ranked first mainly because \"[criterion]\" scored higher ([share]% of the score difference vs [next])" when dominant share ≥ 40%; otherwise "Several criteria contribute similarly to this option's top ranking over [next]".
  - Zero forbidden words verified across all 200 packs. Updates live as priority sliders move; light and dark themes; mobile responsive.

- [x] **Item 9: Methods diagram.** (redesigned 11 Nov 2026 after user feedback: old SVG was hard to read)
  - `MethodsDiagram.tsx`: four numbered stages in order: 1 What we observe (one Data box listing HLS, GIBS basemap, POWER, SMAP, GRACE, NASADEM, SoilGrids, CSB) → 2 What we model (field story 78.3% vs 90% target; Witness 1 and 2 ON; Witness 3 OFF "0 of 32") → 3 What we check (evidence grade capped at B; hindcast: weak skill, underdispersed CIs, beats B1/B2 overall and for maize) → 4 What you get (rotation options). No new claims; every line comes from the Methods page text.
  - HTML grid, not SVG: left to right on desktop, a separate vertical layout below 52rem at full text size (≥ 14 px). Witness 3 OFF = dashed border + hatched band + "OFF" badge (not colour alone). Theme tokens only.
  - Every box is a real link (`#/<region>/methods#<id>`) to its section or `#glossary-…` entry, with a visible focus ring; `MethodsPage` now scrolls to and focuses that target (this also fixes the "Open in glossary" links). The diagram is an ordered list of links inside a `<figure>` with caption, so no separate sr-only copy.
  - `methodsDiagram.test.ts`: sources checked against `DATASETS`; 4 stages in order; OFF marker; every box target exists on the page; phone layout and minimum text size; no hard-coded colours; no forbidden words. Overflow check passes at 360/390 px.

- [x] **Item 10: "What we got wrong" section (Methods page and README).**
  - Factual, dated list documented on the Methods page and README citing repository files, commits, and decision entries.
  - Covers: season detection missed target (78.3% vs 90%); neighbour witness failed all diagnostics (0/32 passed); ranking rewarded fallow until metric changed; rank-order bug in packs (`ce69ebf`) and mis-tracked T6.8 numbers; broken DOIs in `DATA.md`; invented datasets (POLARIS/SSURGO) removed; circularity trap avoided in grade-validity test; reconciled grade counts between pages; performance regression measured and fixed.
  - Neutral tone with specific file/commit citations. Tested in `methods.test.ts`.

- [x] **Item 8: Explainers in 3D view and glossary.**
  - Added short "What is this?" notes (2–3 plain sentences each) for root-zone soil water, available water capacity, water stress (Ks), canopy proxy, evapotranspiration, fallow & bare soil directly inside the Field-in-3D view (`Field3DView.tsx`) and metric strips.
  - Cites verified FAO-56 (Chapters 1, 6, 8) and NASA pages; URLs tested and confirmed returning HTTP 200.
  - Canopy proxy strictly documented as $K_c / K_{c,\max}$ from the FAO-56 dual crop coefficient model (not a direct photo measurement; zero yield/profit claims).
  - Technical glossary on Methods page (`#glossary`) covers all technical terms (3D terms, evidence grade, source tags O/D/E/A, hindcast, CRPS, credibility, witness, bare-soil months, bad-year water). Every 3D note links to its glossary anchor (`#glossary-${id}`).
  - Unit tests passing in `sim3dExplainers.test.ts` and `explainers.test.ts`. Zero new dependencies, no schema changes.

- [x] **Fixes F1–F4 (11 Nov, user-reported, before freeze).**
  - F1 tour buttons: `--accent` was never defined, so Next showed white text on no fill. Added `--accent`/`--on-accent` to every theme block; Next is filled, Back outlined (`--muted` border), Back hidden on step 1. `tourContrast.test.ts` computes WCAG ratios from the tokens (text ≥ 4.5:1, borders ≥ 3:1, light and dark).
  - F2 phone overflow: field tabs wrap, controls `max-width: 100%`, 3D controls stack, long tagged values wrap. `app/scripts/overflow-check.mjs` checks every route at 360 and 390 px against the device width: all pass.
  - F3 3D weather year: disclaimer reads `weather_year` from the pack (was hard-coded 2007); no other hard-coded 2007 in app, README or Methods. `field3d.test.ts` checks all 200 packs.
  - F4 map: GIBS MODIS Terra Corrected Reflectance (Level9, 2023-08-15, cloud-free over the pilot; layer and template from GIBS GetCapabilities) below zoom 10, HLS from zoom 10. First view shows imagery; dark ring on field points; one credit line; offline fallback unchanged (offline check passes).

- [x] **Soil check: independent soil check vs USDA SSURGO (11 Nov, read-only).**
  - `scripts/check_ssurgo.py` + `src/fieldwitness/data/ssurgo.py` (SDA POST REST, one point per request, cached in `data/ssurgo/`); unit test `tests/test_ssurgo.py` reproduces NRCS `aws0100wta` (21.44 cm) from horizons. API shape in `docs/api_notes.md`; citation/terms in `DATA.md`.
  - Finding: the pipeline never derives TAW from SoilGrids; every field starts from `taw_base_mm` = 150 mm (A) × ABC `taw_scale`. Compared that TAW (posterior median) with SSURGO AWS over 0–135 cm (FAO-56 maize root depth mean), component-percent weighted.
  - Result (negative): n = 198/200; simulation median 142 mm vs SSURGO 282 mm; bias −119 mm (median −128), MAE 122 mm; Pearson −0.09, Spearman −0.12. 0–100 cm: bias −49 mm. SoilGrids vs SSURGO texture: sand r 0.65 (bias −0.7 pts), clay r 0.32 (bias +6.0 pts). 2 fields unmatched (profile ends at 91–102 cm).
  - Outputs `results/validation/soil_ssurgo_check.{json,csv,md,png}`; Methods section "Independent soil check (USDA SSURGO)" (tag E); SoilGrids "use" row corrected (it is not a water-balance input). No simulation input, pack or result changed.
- [x] **Try-it tour (11 Nov, user-approved plan).** Rebuilt the guided tour as a "try it" tour: compact card docked at the bottom (bottom sheet on phones), no overlay or focus trap, outline on the real control. 7 steps tick on real app events (`src/tourEvents.ts`, `fw:tour`): open a field (map/list), choose a season in Field story, move a priority slider, find "Why this ranking?", press Play + a −20 % rain scenario in Field in 3D, find the Scoreboard grade-validity verdict, press Cairo then Garden City in Add my field. Next always works; Skip/Escape restore the start page; progress in localStorage (try/catch). Missing target = text only. Text reuses existing claims only (tested). Cairo preset (Tahrir Square, 30.0444 N 31.2357 E) shows the existing "not supported" message. `tests/tour.test.ts` (25 tests) + `tourContrast.test.ts` green.

#### Roadmap (Not Built in this Version — Post-Freeze Roadmap)
- **Item 5: Arabic interface (i18n / RTL).** Post-freeze roadmap.
- **Item 3: Check soil water and rain against independent data (SMAP / GPM).** Post-freeze roadmap.
- **Item 6: Compare two fields side by side.** Post-freeze roadmap.
- **Item 2: Compare water use with NASA-derived evapotranspiration (ECOSTRESS).** Post-freeze roadmap.
- **Item 4: WIMAS irrigation check (waits for user-provided data).** Post-freeze roadmap.

