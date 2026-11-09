import en from "./strings/en.json";

/**
 * Explainer ids (T9.10). Text, source and link live in strings/en.json as
 * explain.<id>.title / .body / .source / .url; every source was read on 2026-11-06.
 */
export const EXPLAINERS = [
  "evapotranspiration",
  "soil_moisture_anomaly",
  "ndvi",
  "frost",
  "water_balance",
  "ryi",
  "evidence_grade",
  "source_tags",
  "nitrogen_fixing",
  "cover_crop",
  "deep_rooting",
  "drought_tolerant",
  "root_zone_soil_water",
  "available_water_capacity",
  "water_stress_ks",
  "canopy_proxy",
  "fallow_bare_soil",
  "hindcast",
  "crps",
  "credibility",
  "witness",
  "bare_soil_months",
  "bad_year_water",
] as const;
export type ExplainerId = (typeof EXPLAINERS)[number];

/** 3D simulation notes that appear directly in the Field in 3D view (Item 8). */
export const SIM3D_EXPLAINERS: ExplainerId[] = [
  "root_zone_soil_water",
  "available_water_capacity",
  "water_stress_ks",
  "canopy_proxy",
  "evapotranspiration",
  "fallow_bare_soil",
];

export interface ExplainerText {
  title: string;
  body: string;
  source: string;
  /** Empty when the source is this project's own rules (no external page). */
  url: string;
}

export function explainer(id: ExplainerId): ExplainerText {
  const s = en as Record<string, string>;
  const get = (part: string) => s[`explain.${id}.${part}`] ?? "";
  return { title: get("title"), body: get("body"), source: get("source"), url: get("url") };
}

/** Which explainer belongs next to a metric name (T6.7 keys). */
export const METRIC_EXPLAINER: Partial<Record<string, ExplainerId>> = {
  water_use_mm: "evapotranspiration",
  bad_year_water_mm: "bad_year_water",
  ryi: "ryi",
  bad_year_ryi: "drought_tolerant",
  cover_days: "cover_crop",
  legume_share: "nitrogen_fixing",
  deep_root_share: "deep_rooting",
  bare_soil_months: "bare_soil_months",
};
