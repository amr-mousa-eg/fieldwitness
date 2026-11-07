// Hand-written mirror of the pack schemas, until T8.2 generates this file from
// src/fieldwitness/schemas.py. Part 1 = PLAN.md §3. Part 2 = PROPOSED extension
// (docs/schema_ext_proposal.md), not yet approved for `main`.

// ---------------------------------------------------------------- Part 1 — PLAN.md §3

export type Tag = "O" | "D" | "E" | "A";

export interface Tagged {
  value: number | null;
  lo50?: number | null;
  hi50?: number | null;
  lo90?: number | null;
  hi90?: number | null;
  unit: string;
  tag: Tag;
  source: string;
}

export interface Field {
  field_id: string;
  geometry_wkt: string;
  area_ha: number;
  region_id: string;
  tier: 1 | 2 | 3;
  boundary_source: "FTW" | "CSB" | "EuroCrops" | "user";
  scale_flags: Record<string, boolean>;
  interior_pixels: number;
}

export interface Season {
  year: number;
  index: number;
  crop: string | null;
  crop_conf: number;
  crop_source: "label" | "classifier" | "user";
  /** day of the harvest year; negative = previous autumn */
  sos: Tagged;
  peak: Tagged;
  eos: Tagged;
  canopy_integral: Tagged;
  cover_days: Tagged;
  bare_days: Tagged;
  clear_obs: number;
}

export interface WitnessResult {
  witness: "physics" | "own_past" | "neighbours";
  metric: string;
  estimate: Tagged;
  n?: number | null;
  diagnostics: Record<string, number | boolean | string>;
}

export interface Explanation {
  why: string[];
  evidence: string[];
  benefits: string[];
  gaps: string[];
  risks: string[];
}

export type Grade = "A" | "B" | "C" | "D";

export interface Option {
  option_id: string;
  sequence: string[];
  metrics: Record<string, Tagged>;
  witnesses: WitnessResult[];
  grade: Grade;
  grade_reasons: string[];
  regret: Tagged;
  rank: number;
  explanation: Explanation;
}

export interface Advice {
  measure_next: string;
  flip_probability: Tagged;
  counterfactual_flip: string;
}

export interface LedgerEntry {
  field_id: string;
  as_of: string; // ISO date
  model_version: string;
  mode: "forecast" | "forced";
  season_year: number;
  season_index: number;
  crop: string;
  crop_observed_source: "label" | "classifier";
  predicted: Record<string, Tagged>;
  observed?: Record<string, Tagged> | null;
  scores?: Record<string, number> | null;
}

export interface FieldPack {
  schema_version: string;
  field: Field;
  story: Season[];
  credibility: Tagged;
  options: Option[];
  advice: Advice;
  ledger: LedgerEntry[];
  data_as_of: string;
  generated_at: string;
}

// ---------------------------------------------------------------- Part 2 — PROPOSED

/** PROPOSED: many numbers sharing one unit, tag and source. */
export interface TaggedSeries {
  x: string[] | number[]; // ISO dates, or years / months
  values: (number | null)[];
  lo90?: (number | null)[] | null;
  hi90?: (number | null)[] | null;
  unit: string;
  tag: Tag;
  source: string;
}

/** PROPOSED: <field_id>.series.json. SOS/peak/EOS marks come from FieldPack.story. */
export interface FieldSeries {
  schema_version: string;
  field_id: string;
  ndvi: TaggedSeries;
  evi: TaggedSeries;
  clear_frac: number[];
  ndvi_smooth: TaggedSeries;
  data_as_of: string;
}

/** PROPOSED: <field_id>.calendar.json */
export type Hazard = "heat" | "frost" | "water_stress" | "extreme_rain_bare";
export interface BareMonth {
  month: number;
  bare_share: Tagged | null;
  clear_obs: number;
  years_with_data: number;
  insufficient: boolean;
}
export interface CropVulnerability {
  crop: string;
  years: [number, number];
  thresholds: Record<Hazard, Tagged>;
  threshold_notes: Record<Hazard, string>;
  shares: Record<Hazard, TaggedSeries>;
}
export interface FieldCalendar {
  schema_version: string;
  field_id: string;
  bare_observed: BareMonth[];
  bare_observed_years: [number, number];
  bare_by_option: Record<string, TaggedSeries>;
  vulnerability: CropVulnerability[];
  data_as_of: string;
}

/** PROPOSED: <field_id>.scenarios.json */
export interface Scenario {
  scenario_id: string;
  dt_c: number;
  dp_pct: number;
  /** option_id -> weather-sensitive metric -> value; sequence-only metrics live in the pack. */
  metrics: Record<string, Record<string, Tagged>>;
  ranks: Record<string, number>;
}
export interface FieldScenarios {
  schema_version: string;
  field_id: string;
  baseline_id: string;
  note: string;
  scenarios: Scenario[];
  data_as_of: string;
}

/** PROPOSED: packs/<region>/layers.json */
export interface GridCell {
  bbox_lonlat: [number, number, number, number];
  values: (number | null)[];
}
export interface TaggedGrid {
  years: number[];
  cells: GridCell[];
  unit: string;
  tag: Tag;
  source: string;
}
export interface RegionalLayer {
  layer_id: "grace_tws" | "smap_anomaly" | "heatwave_days";
  resolution_km: number;
  resolution_source: string;
  scale_flag: boolean;
  grid: TaggedGrid;
  region_mean: TaggedSeries;
  trend: Tagged;
}
export type FieldColourMetric = "erosion_exposure" | "water_stress_share" | "frost_share";
export interface RegionLayers {
  schema_version: string;
  region_id: string;
  layers: RegionalLayer[];
  /** metric -> field_id -> value, always for the Current option. */
  field_colouring: Record<FieldColourMetric, Record<string, Tagged>>;
  data_as_of: string;
}

/** PROPOSED: packs/<region>/index.json, packs/<region>/hindcast.json, packs/regions.json */
export interface FieldSummary {
  field_id: string;
  geometry_wkt: string;
  area_ha: number;
  current_sequence: string[];
  top_option_id: string;
  top_grade: Grade;
}
export interface RegionIndex {
  schema_version: string;
  region_id: string;
  name: string;
  tier: 1 | 2 | 3;
  bbox_lonlat: [number, number, number, number];
  basemap: string | null;
  fields: FieldSummary[];
  data_as_of: string;
}
export interface HindcastRow {
  method: "fieldwitness" | "B0" | "B1" | "B2" | "B3";
  mode: "forecast" | "forced";
  metric: string;
  n: number;
  scores: Record<string, number>;
}
export interface RegionHindcast {
  schema_version: string;
  region_id: string;
  cutoff: string;
  scored_years: number[];
  crop_observed_source: "label" | "classifier";
  rows: HindcastRow[];
  story_field_id: string;
  data_as_of: string;
}
export interface RegionEntry {
  region_id: string;
  name: string;
  tier: 1 | 2 | 3;
}
export interface RegionList {
  regions: RegionEntry[];
}
