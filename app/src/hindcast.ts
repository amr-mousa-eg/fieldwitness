import type { HindcastRow, RegionHindcast } from "./types";

/** FieldWitness first, then the baselines of T7.3 in order. */
export const METHODS: HindcastRow["method"][] = ["fieldwitness", "B0", "B1", "B2", "B3"];

/** Timing error is only meaningful for date metrics (T7.2). */
export const TIMING_METRICS = new Set(["sos", "peak", "eos"]);

export type ScoreKey = "crps" | "covered50" | "covered90" | "mae_median" | "timing_err_days";

/** Display order. `mae_median` = mean |observed − median prediction| (scripts/t72_score.py on main). */
const SCORE_KEYS: ScoreKey[] = ["crps", "covered50", "covered90", "mae_median", "timing_err_days"];

/** Score columns for one metric table: only keys some row has (packs differ in what they score). */
export function scoreKeysOf(rows: HindcastRow[], metric: string): ScoreKey[] {
  return SCORE_KEYS.filter(
    (k) => (k !== "timing_err_days" || TIMING_METRICS.has(metric)) && rows.some((r) => typeof r.scores[k] === "number"),
  );
}

/** Baselines without any row in this hindcast (e.g. B3 not run), so the page can say so. */
export function methodsNotRun(h: RegionHindcast): HindcastRow["method"][] {
  return METHODS.filter((m) => !h.rows.some((r) => r.method === m));
}

/** Nominal coverage of each interval: a calibrated method covers this share of seasons. */
const COVERAGE_TARGET: Partial<Record<ScoreKey, number>> = { covered50: 0.5, covered90: 0.9 };

/** Distance from ideal: lower is better for every key (CRPS, |timing error|, |coverage − target|). */
export function badness(key: ScoreKey, value: number): number {
  const target = COVERAGE_TARGET[key];
  return target !== undefined ? Math.abs(value - target) : Math.abs(value);
}

export function modesOf(h: RegionHindcast): HindcastRow["mode"][] {
  return (["forecast", "forced"] as const).filter((m) => h.rows.some((r) => r.mode === m));
}

export function metricsOf(h: RegionHindcast, mode: HindcastRow["mode"]): string[] {
  return [...new Set(h.rows.filter((r) => r.mode === mode).map((r) => r.metric))];
}

export function rowsFor(h: RegionHindcast, mode: HindcastRow["mode"], metric: string): HindcastRow[] {
  return h.rows
    .filter((r) => r.mode === mode && r.metric === metric)
    .sort((a, b) => METHODS.indexOf(a.method) - METHODS.indexOf(b.method));
}

/** Methods with the best score for `key` (ties kept); empty when no row has the score. */
export function bestMethods(rows: HindcastRow[], key: ScoreKey): Set<HindcastRow["method"]> {
  const scored = rows.filter((r) => typeof r.scores[key] === "number");
  if (scored.length === 0) return new Set();
  const min = Math.min(...scored.map((r) => badness(key, r.scores[key])));
  return new Set(scored.filter((r) => badness(key, r.scores[key]) === min).map((r) => r.method));
}
