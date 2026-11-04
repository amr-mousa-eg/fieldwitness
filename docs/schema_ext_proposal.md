# PROPOSED extension to PLAN.md §3 (data contracts)

**Status:** PROPOSAL, app branch only, 2026-11-04. Not approved for `main`. CLAUDE.md rule 11: §3 changes need the user's approval. After approval, the models move into `src/fieldwitness/schemas.py` (on `main`), T8.2 generates `app/src/types.ts` from them, and `scripts/fixture_schemas.py` Part 1 is deleted.

**Canonical code:** `scripts/fixture_schemas.py` (Part 2). The models below are a copy of it. The synthetic fixtures in `app/fixtures/ks_demo_synthetic/` validate against it; the examples below are trimmed from those fixtures. **Every number in the examples is SYNTHETIC.**

## 1. Why

Several Phase 9 views need data that §3 does not define:

| View | Needs | Proposed file |
|---|---|---|
| T9.2 Field story | HLS NDVI/EVI per date, smoothed curve, SOS/peak/EOS marks | `<field_id>.series.json` |
| T9.9 Calendar | bare-soil calendar (T2.5), vulnerability calendar (T3.6), an alternative's bare months | `<field_id>.calendar.json` |
| T9.3 what-if sliders | T6.8 weather grid, per option and metric | `<field_id>.scenarios.json` |
| T9.11 + T9.9 strip | GRACE, SMAP anomaly, heat-wave days; field colouring values | `packs/<region>/layers.json` |
| T9.1 Map, T9.5 Scoreboard | `index.json` and `hindcast.json` are *named* in §3 but have no model | `index.json`, `hindcast.json` |
| T9.1 region switcher | list of regions | `packs/regions.json` (new) |

The `FieldPack` (§3) is unchanged. File layout (user decision 2026-11-04): per field `<field_id>.json` (§3), `.series.json`, `.calendar.json`, `.scenarios.json`; per region `index.json`, `hindcast.json`, `layers.json`. Each file < 300 KB.

## 2. Conventions

1. **Tagging.** Same rule as §3: every user-facing number is tagged. Two new containers carry one `unit`, `tag` and `source` for a whole array, so long series stay small:
   - `TaggedSeries` — `x` (dates, years or months) plus `values` (and optional `lo90`/`hi90`), same length (validated).
   - `TaggedGrid` — a coarse raster as cells; each cell has a `bbox_lonlat` and one value per year.
   The validator (`check_tagged`) treats `Tagged`, `TaggedSeries` and `TaggedGrid` as tagged, and fails on any other float that is not exempt.
2. **Proposed additions to `EXEMPT_FIELDS`** (all bookkeeping, geometry or inputs, not claims about the field):
   `bbox_lonlat` (geometry), `dt_c` and `dp_pct` (scenario grid coordinates that we choose), `resolution_km` (product metadata, shown with its `resolution_source`), `years_with_data` and `clear_frac` (counts and fractions of observations, like §3's `clear_obs`).
3. **Day-of-year for seasons that cross the new year.** §3 says `sos`/`peak`/`eos` are "day of year", which is ambiguous for winter wheat (sown Oct 2022, harvest year 2023). The fixtures use **day of the harvest year, negative = the previous autumn** (unit string `"day of harvest year"`; 15 Oct 2022 → −77 (31 Dec 2022 = 0) for harvest year 2023). See open question Q1.
4. **Size.** Largest synthetic file: `scenarios` at 83 KB (4 options × 12 metrics × 12 scenarios); `series` 25–27 KB for 8 years; `layers` 20 KB with a 12 × 12 SMAP grid.

## 3. Models (Pydantic v2)

```python
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
class SeasonMarks(BaseModel):
    """SOS / peak / EOS of one story season. Must equal the matching `Season` in the pack."""
    season_year: int
    season_index: int = 0
    sos: Tagged; peak: Tagged; eos: Tagged

class FieldSeries(BaseModel):
    schema_version: str
    field_id: str
    ndvi: TaggedSeries         # observed, tag O: median over interior pixels per clear date
    evi: TaggedSeries          # observed, tag O
    clear_frac: list[float]    # clear-pixel fraction per date in ndvi.x (bookkeeping)
    ndvi_smooth: TaggedSeries  # smoothed curve, tag D
    marks: list[SeasonMarks]
    data_as_of: date
    # validator: ndvi, evi and clear_frac share the same dates

# --- <field_id>.calendar.json ---------------------------------------------------------
Hazard = Literal["heat", "frost", "water_stress", "extreme_rain_bare"]

class BareMonth(BaseModel):
    month: int                 # 1..12
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
class Scenario(BaseModel):
    scenario_id: str                          # e.g. "t+1_p-10"
    dt_c: float                               # temperature change, °C (grid coordinate)
    dp_pct: float                             # rainfall change, % (grid coordinate)
    metrics: dict[str, dict[str, Tagged]]     # option_id -> metric -> value (same keys as Option)
    ranks: dict[str, int]                     # option_id -> rank under default weights

class FieldScenarios(BaseModel):
    schema_version: str
    field_id: str
    baseline_id: str           # "t+0_p+0" = the pack's own Option metrics
    note: str                  # "Sensitivity tests on past weather, not climate projections."
    scenarios: list[Scenario]  # 3 temperatures x 4 rainfall = 12 (T6.8)
    data_as_of: date
    # validator: exactly 12 scenarios; baseline_id is one of them

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
    field_colouring: dict[FieldColourMetric, dict[str, Tagged]]  # metric -> field_id -> value
    colouring_option: str      # option the colouring describes: "current"
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

## 4. One example per file (SYNTHETIC, trimmed; `//` marks cuts)

### `<field_id>.series.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "field_id": "9440e11e394e394f92c4bf4d62cf24fd30972541",
  "ndvi": { "x": ["2016-09-01", "2016-09-04", "2016-09-10" /* … one per clear date */],
            "values": [0.076, 0.194, 0.176 /* … */], "lo90": null, "hi90": null,
            "unit": "NDVI", "tag": "O", "source": "SYNTHETIC:fixture@0.1" },
  "evi":  { "x": ["2016-09-01", "2016-09-04", "2016-09-10"], "values": [0.036, 0.124, 0.086],
            "unit": "EVI", "tag": "O", "source": "SYNTHETIC:fixture@0.1" },
  "clear_frac": [0.85, 0.77, 0.9 /* … same length as ndvi.x */],
  "ndvi_smooth": { "x": ["2016-09-01", "2016-09-08", "2016-09-15" /* … weekly */],
                   "values": [0.141, 0.142, 0.145], "unit": "NDVI", "tag": "D",
                   "source": "SYNTHETIC:fixture@0.1" },
  "marks": [
    { "season_year": 2017, "season_index": 0,
      "sos":  { "value": -77.0, "lo50": -80.0, "hi50": -74.0, "lo90": -85.0, "hi90": -69.0,
                "unit": "day of harvest year", "tag": "O", "source": "SYNTHETIC:fixture@0.1" },
      "peak": { "value": 123.0, "unit": "day of harvest year", "tag": "O", "source": "SYNTHETIC:fixture@0.1" /* bands cut */ },
      "eos":  { "value": 168.0, "unit": "day of harvest year", "tag": "O", "source": "SYNTHETIC:fixture@0.1" } }
    // … one per story season
  ],
  "data_as_of": "2024-12-31"
}
```

### `<field_id>.calendar.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "field_id": "9440e11e394e394f92c4bf4d62cf24fd30972541",
  "bare_observed": [
    { "month": 1, "bare_share": null, "clear_obs": 4, "years_with_data": 2, "insufficient": true },
    { "month": 2, "bare_share": { "value": 0.62, "unit": "share of years", "tag": "O",
                                  "source": "SYNTHETIC:fixture@0.1" },
      "clear_obs": 31, "years_with_data": 8, "insufficient": false }
    // … 12 months
  ],
  "bare_observed_years": [2017, 2024],
  "bare_by_option": {
    "current": { "x": [1, 2, 3 /* … 12 */], "values": [0.67, 0.67, 0.67 /* … */],
                 "unit": "share of years", "tag": "D", "source": "SYNTHETIC:fixture@0.1" }
    // … one per option_id
  },
  "vulnerability": [
    { "crop": "sorghum", "years": [2001, 2021],
      "thresholds": {
        "heat":  { "value": null, "unit": "°C Tmax", "tag": "A", "source": "SYNTHETIC:fixture@0.1" },
        "frost": { "value": 0.0,  "unit": "°C Tmin", "tag": "A", "source": "SYNTHETIC:fixture@0.1" }
        // … water_stress, extreme_rain_bare
      },
      "threshold_notes": { "heat": "SYNTHETIC placeholder; real value must come from T3.6." /* … */ },
      "shares": {
        "heat": { "x": [1, 2, 3 /* … 12 */], "values": [0.0, 0.0, 0.0 /* … */],
                  "unit": "share of years", "tag": "D", "source": "SYNTHETIC:fixture@0.1" }
        // … frost, water_stress, extreme_rain_bare
      } }
    // … one per crop in Current and in every option
  ],
  "data_as_of": "2024-12-31"
}
```

### `<field_id>.scenarios.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "field_id": "9440e11e394e394f92c4bf4d62cf24fd30972541",
  "baseline_id": "t+0_p+0",
  "note": "Sensitivity tests on past weather, not climate projections.",
  "scenarios": [
    { "scenario_id": "t+0_p-20", "dt_c": 0.0, "dp_pct": -20.0,
      "metrics": {
        "current": {
          "water_use_mm": { "value": 440.0, "lo50": 419.0, "hi50": 460.0, "lo90": 390.0, "hi90": 489.0,
                            "unit": "mm/season", "tag": "D", "source": "SYNTHETIC:fixture@0.1" }
          // … every key of Option.metrics
        }
        // … one per option_id
      },
      "ranks": { "current": 1, "alt3": 2, "alt2": 3, "alt1": 4 } }
    // … 12 scenarios: dt_c in {0, 1, 2} x dp_pct in {-20, -10, 0, +10}
  ],
  "data_as_of": "2024-12-31"
}
```

### `packs/<region>/layers.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "region_id": "ks_demo_synthetic",
  "layers": [
    { "layer_id": "grace_tws", "resolution_km": 50.0,
      "resolution_source": "SYNTHETIC placeholder; take from the product docs.",
      "scale_flag": true,
      "grid": { "years": [2016, 2017, 2018 /* … 2024 */],
                "cells": [ { "bbox_lonlat": [-101.3039, 37.8375, -100.6646, 38.3409],
                             "values": [-3.35, -3.42, 0.1 /* … one per year */] } /* … */ ],
                "unit": "cm water equivalent anomaly", "tag": "D", "source": "SYNTHETIC:fixture@0.1" },
      "region_mean": { "x": [2016, 2017, 2018 /* … */], "values": [-1.837, -3.397, -4.487 /* … */],
                       "unit": "cm water equivalent anomaly", "tag": "D", "source": "SYNTHETIC:fixture@0.1" },
      "trend": { "value": -0.258, "lo90": -0.486, "hi90": -0.03,
                 "unit": "cm water equivalent anomaly per year", "tag": "D", "source": "SYNTHETIC:fixture@0.1" } }
    // … smap_anomaly, heatwave_days
  ],
  "field_colouring": {
    "erosion_exposure": {
      "9440e11e394e394f92c4bf4d62cf24fd30972541": { "value": 0.91, "unit": "relative index", "tag": "D",
                                                    "source": "SYNTHETIC:fixture@0.1" }
      // … one per field
    }
    // … water_stress_share, frost_share
  },
  "colouring_option": "current",
  "data_as_of": "2024-12-31"
}
```

### `packs/<region>/index.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "region_id": "ks_demo_synthetic",
  "name": "Kansas — DEMO DATA (synthetic)",
  "tier": 1,
  "bbox_lonlat": [-101.3039, 37.8375, -100.0253, 38.8444],
  "basemap": null,
  "fields": [
    { "field_id": "9440e11e394e394f92c4bf4d62cf24fd30972541",
      "geometry_wkt": "POLYGON ((-100.92459 38.016384, -100.92459 38.023616, -100.91541 38.023616, -100.91541 38.016384, -100.92459 38.016384))",
      "area_ha": 64.7, "current_sequence": ["winter_wheat", "sorghum", "fallow"],
      "top_option_id": "current", "top_grade": "B" }
    // … one per field
  ],
  "data_as_of": "2024-12-31"
}
```

### `packs/<region>/hindcast.json`

```jsonc
{
  "schema_version": "1.2+ext-proposal-SYNTHETIC",
  "region_id": "ks_demo_synthetic",
  "cutoff": "2021-12-31",
  "scored_years": [2022, 2023, 2024],
  "crop_observed_source": "label",
  "rows": [
    { "method": "fieldwitness", "mode": "forecast", "metric": "canopy_integral", "n": 259,
      "scores": { "crps": 5.18, "covered50": 0.41, "covered90": 0.93, "timing_err_days": 7.1 } }
    // … method x mode x metric
  ],
  "story_field_id": "9440e11e394e394f92c4bf4d62cf24fd30972541",
  "data_as_of": "2024-12-31"
}
```

### `packs/regions.json`

```json
{ "regions": [ { "region_id": "ks_demo_synthetic", "name": "Kansas — DEMO DATA (synthetic)", "tier": 1 } ] }
```

## 5. Open questions (need a decision before `main` adopts this)

- **Q1 Day-of-year convention** (§2.3). Adopt "day of harvest year, negative = previous autumn" for `Season.sos/peak/eos` and `SeasonMarks`? This touches §3 `Season` and T2.2 on `main`.
- **Q2 Duplicated marks.** `SeasonMarks` repeats `Season.sos/peak/eos` from the pack, as requested. The generator checks that they are equal. Alternative: drop `marks` and let the app read them from the pack (one source of truth, smaller file).
- **Q3 Exempt additions** (§2.2): confirm `bbox_lonlat`, `dt_c`, `dp_pct`, `resolution_km`, `years_with_data`, `clear_frac`.
- **Q4 `bare_by_option`** is new pipeline output (simulated cover from physics, tag D), not part of T2.5. It is needed for T9.9's "show an alternative's calendar" toggle.
- **Q5 Field colouring** describes the Current option only (`colouring_option`). Should a user be able to colour the map by an alternative?
- **Q6 Scenario size.** Scenarios repeat all 12 metrics; only the weather-sensitive ones change (water use, irrigation, RYI, bad-year values, erosion). Storing only those would roughly halve the file.
- **Q7 `regions.json`** is a new file not named in §3.
