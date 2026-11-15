import { type Domain, RAMPS, domainOf } from "./mapLayers";
import type { Grade, Tag, Tagged } from "./types";

export type OptionDeltaMetric =
  | "delta_water_use_mm"
  | "delta_bad_year_water_mm"
  | "delta_bare_months"
  | "delta_ryi"
  | "delta_erosion_exposure";

export const DELTA_METRICS: readonly OptionDeltaMetric[] = [
  "delta_water_use_mm",
  "delta_bad_year_water_mm",
  "delta_bare_months",
  "delta_ryi",
  "delta_erosion_exposure",
] as const;

export const DELTA_METRIC_SET = new Set<string>(DELTA_METRICS);

/** For RYI, positive delta means Rank-1 improves yield index; for the rest, negative means lower risk/water. */
export const HIGHER_IS_BETTER_DELTAS = new Set<OptionDeltaMetric>(["delta_ryi"]);

/** Teal on negative end (improvement), warm brown on positive end (trade-off increase). */
export const RAMP_DIVERGING_LOWER_BETTER: readonly string[] = [...RAMPS.diverging].reverse();

export interface FieldOptionDelta {
  field_id: string;
  current_sequence: string[];
  current_grade: Grade;
  alt_option_id: string;
  alt_sequence: string[];
  alt_grade: Grade;
  deltas: Record<OptionDeltaMetric, Tagged>;
}

export interface OptionDeltaSummary {
  mean: Tagged;
  improved_count: int;
  valid_count: int;
}

type int = number;

export interface RegionOptionDeltas {
  schema_version: string;
  region_id: string;
  data_as_of: string;
  n_fields: number;
  fields: Record<string, FieldOptionDelta>;
  summary: Record<OptionDeltaMetric, OptionDeltaSummary>;
}

export function isDeltaMetric(metric: string | null | undefined): metric is OptionDeltaMetric {
  return typeof metric === "string" && DELTA_METRIC_SET.has(metric);
}

export function deltaRampForMetric(metric: OptionDeltaMetric): readonly string[] {
  return HIGHER_IS_BETTER_DELTAS.has(metric) ? RAMPS.diverging : RAMP_DIVERGING_LOWER_BETTER;
}

export function deltaValuesMap(od: RegionOptionDeltas, metric: OptionDeltaMetric): Record<string, number | null> {
  const out: Record<string, number | null> = {};
  for (const [fid, entry] of Object.entries(od.fields)) {
    out[fid] = entry.deltas[metric]?.value ?? null;
  }
  return out;
}

export function deltaTaggedMap(od: RegionOptionDeltas, metric: OptionDeltaMetric): Record<string, Tagged> {
  const out: Record<string, Tagged> = {};
  for (const [fid, entry] of Object.entries(od.fields)) {
    const t = entry.deltas[metric];
    if (t) out[fid] = t;
  }
  return out;
}

export function deltaDomain(od: RegionOptionDeltas, metric: OptionDeltaMetric): Domain {
  return domainOf(Object.values(deltaValuesMap(od, metric)), true);
}

export function deltaLegendSample(od: RegionOptionDeltas, metric: OptionDeltaMetric): Tagged | undefined {
  return od.summary[metric]?.mean ?? Object.values(od.fields)[0]?.deltas[metric];
}

export function isImprovedDelta(metric: OptionDeltaMetric, value: number | null | undefined): boolean {
  if (value === null || value === undefined || !Number.isFinite(value)) return false;
  return HIGHER_IS_BETTER_DELTAS.has(metric) ? value > 0 : value < 0;
}

export function deltaProvenanceTag(od: RegionOptionDeltas, metric: OptionDeltaMetric): Tag {
  return od.summary[metric]?.mean.tag ?? "D";
}
