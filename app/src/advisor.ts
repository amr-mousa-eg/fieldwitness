import type { LedgerEntry, Option, Tagged, WitnessResult } from "./types";

/** The three witnesses, in the order the console shows them (CLAUDE.md "What we are building"). */
export const WITNESSES = ["physics", "own_past", "neighbours"] as const;
export type WitnessName = (typeof WITNESSES)[number];

export interface WitnessRow {
  metric: string;
  /** One entry per witness; undefined = this witness has no estimate for the metric. */
  cells: Record<WitnessName, WitnessResult | undefined>;
}

/** Witness results of one option, one row per metric, witnesses side by side (T9.4). */
export function witnessRows(option: Option): WitnessRow[] {
  const metrics = [...new Set(option.witnesses.map((w) => w.metric))];
  return metrics.map((metric) => ({
    metric,
    cells: Object.fromEntries(
      WITNESSES.map((name) => [name, option.witnesses.find((w) => w.witness === name && w.metric === metric)]),
    ) as Record<WitnessName, WitnessResult | undefined>,
  }));
}

/** Witnesses with no estimate for any metric of this option. */
export function missingWitnesses(option: Option): WitnessName[] {
  return WITNESSES.filter((name) => !option.witnesses.some((w) => w.witness === name));
}

/** True / false = the observed value is inside / outside the predicted range; null = no range. */
export function inside(pred: Tagged, obs: Tagged, level: 50 | 90): boolean | null {
  const lo = level === 50 ? pred.lo50 : pred.lo90;
  const hi = level === 50 ? pred.hi50 : pred.hi90;
  if (lo == null || hi == null || obs.value === null) return null;
  return obs.value >= lo && obs.value <= hi;
}

export interface BacktestRow {
  season_year: number;
  season_index: number;
  crop: string;
  mode: LedgerEntry["mode"];
  predicted: Tagged;
  observed: Tagged;
}

/** Ledger entries that have both a prediction and an observation of `metric`, oldest first. */
export function backtestRows(ledger: LedgerEntry[], metric: string): BacktestRow[] {
  return ledger
    .filter((e) => e.predicted[metric] && e.observed?.[metric])
    .sort((a, b) => a.season_year - b.season_year || a.season_index - b.season_index)
    .map((e) => ({
      season_year: e.season_year,
      season_index: e.season_index,
      crop: e.crop,
      mode: e.mode,
      predicted: e.predicted[metric],
      observed: e.observed![metric],
    }));
}

export interface BacktestOffset {
  /** Always 0: the prediction is the reference line. null when nothing was predicted. */
  pred: number | null;
  /** [below, above] distances from the prediction to its 90 % bounds (ErrorBar format). */
  err: [number, number] | undefined;
  /** Observed minus predicted, in the metric's unit. */
  obs: number | null;
}

/**
 * Chart data relative to each prediction, so seasons of different crops share one axis:
 * a dot inside the bar means the observation fell inside the 90 % range.
 */
export function backtestOffsets(rows: BacktestRow[]): BacktestOffset[] {
  return rows.map(({ predicted: p, observed: o }) => {
    if (p.value === null) return { pred: null, err: undefined, obs: null };
    const err: [number, number] | undefined =
      p.lo90 != null && p.hi90 != null ? [p.value - p.lo90, p.hi90 - p.value] : undefined;
    return { pred: 0, err, obs: o.value === null ? null : o.value - p.value };
  });
}

/** Metrics scored in the ledger (predicted and observed at least once), in first-seen order. */
export function backtestMetrics(ledger: LedgerEntry[]): string[] {
  const keys = ledger.flatMap((e) => Object.keys(e.predicted).filter((k) => e.observed?.[k]));
  return [...new Set(keys)];
}
