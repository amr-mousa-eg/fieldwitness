// Field Card logic (T9.3), kept pure for tests: priorities -> in-browser ranking, user
// constraints -> which options stay, weather what-ifs -> which metrics apply.
import type { FieldScenarios, Option, Scenario, Tagged } from "./types";

export type PriorityKey = "water" | "bare" | "badYear" | "erosion" | "legume" | "residue";
export type Priorities = Record<PriorityKey, number>; // 0 = ignore … 3 = high
export const PRIORITY_KEYS: PriorityKey[] = ["water", "bare", "badYear", "erosion", "legume", "residue"];
export const DEFAULT_PRIORITIES: Priorities = { water: 2, bare: 2, badYear: 2, erosion: 2, legume: 2, residue: 2 };

/** Which Option.metrics each priority reads, and which direction is better. */
export const PRIORITY_METRICS: Record<PriorityKey, { metric: string; better: "lower" | "higher" }[]> = {
  water: [{ metric: "water_use_mm", better: "lower" }],
  bare: [{ metric: "cover_days", better: "higher" }], // more cover days = fewer bare months
  badYear: [
    { metric: "bad_year_water_mm", better: "lower" },
    { metric: "bad_year_ryi", better: "higher" },
  ],
  erosion: [{ metric: "erosion_exposure", better: "lower" }],
  legume: [{ metric: "legume_share", better: "higher" }],
  residue: [{ metric: "residue_proxy", better: "higher" }],
};

export const isDefault = (p: Priorities) => PRIORITY_KEYS.every((k) => p[k] === DEFAULT_PRIORITIES[k]);

export type Metrics = Record<string, Tagged>;

/** The option's metrics under a weather what-if: weather-sensitive values replace the pack's. */
export function metricsFor(option: Option, scenario: Scenario | null): Metrics {
  return scenario ? { ...option.metrics, ...(scenario.metrics[option.option_id] ?? {}) } : option.metrics;
}

export function findScenario(s: FieldScenarios | null, dt: number, dp: number): Scenario | null {
  return s?.scenarios.find((x) => x.dt_c === dt && x.dp_pct === dp) ?? null;
}

/**
 * Weighted score in [0, 1]: each metric is scaled across the options being compared
 * (1 = best of them); a priority averages its metrics; missing values are skipped.
 */
export function scores(rows: { id: string; metrics: Metrics }[], p: Priorities): Map<string, number> {
  const out = new Map<string, number>();
  const total = PRIORITY_KEYS.reduce((s, k) => s + p[k], 0);
  for (const row of rows) {
    let sum = 0;
    for (const k of PRIORITY_KEYS) {
      if (p[k] === 0) continue;
      const parts = PRIORITY_METRICS[k].flatMap(({ metric, better }) => {
        const v = row.metrics[metric]?.value;
        const all = rows.map((r) => r.metrics[metric]?.value).filter((x): x is number => x != null);
        if (v == null || all.length === 0) return [];
        const lo = Math.min(...all);
        const hi = Math.max(...all);
        const scaled = hi === lo ? 1 : (v - lo) / (hi - lo);
        return [better === "higher" ? scaled : 1 - scaled];
      });
      if (parts.length) sum += (p[k] * parts.reduce((a, b) => a + b, 0)) / parts.length;
    }
    out.set(row.id, total === 0 ? 0 : sum / total);
  }
  return out;
}

export interface Constraints {
  dontWant: string[];
  cantGrow: string[];
  /** null = the user has not said; otherwise every sold crop in an option must be in this list. */
  canSell: string[] | null;
  irrigation: "unset" | "yes" | "no";
  waterCapMm: number | null;
}
export const NO_CONSTRAINTS: Constraints = { dontWant: [], cantGrow: [], canSell: null, irrigation: "unset", waterCapMm: null };

/** Rotation states that are never sold, so "can sell" does not apply to them. */
export const NOT_SOLD = new Set(["fallow", "cover_crop"]);

export type Violation =
  | { kind: "dontWant" | "cantGrow" | "cantSell"; crop: string }
  | { kind: "irrigation"; value: Tagged }
  | { kind: "waterCap"; value: Tagged; cap: number };

export function violations(sequence: string[], m: Metrics, c: Constraints): Violation[] {
  const out: Violation[] = [];
  for (const crop of new Set(sequence)) {
    if (c.dontWant.includes(crop)) out.push({ kind: "dontWant", crop });
    if (c.cantGrow.includes(crop)) out.push({ kind: "cantGrow", crop });
    if (c.canSell && !NOT_SOLD.has(crop) && !c.canSell.includes(crop)) out.push({ kind: "cantSell", crop });
  }
  const irr = m.irrigation_mm;
  if (c.irrigation === "no" && irr?.value != null && irr.value > 0) out.push({ kind: "irrigation", value: irr });
  const water = m.water_use_mm;
  if (c.waterCapMm != null && water?.value != null && water.value > c.waterCapMm) {
    out.push({ kind: "waterCap", value: water, cap: c.waterCapMm });
  }
  return out;
}

export interface Ranked {
  option: Option;
  metrics: Metrics;
  rank: number;
  violations: Violation[];
  kept: boolean; // Current is always kept (T6.0) even when it breaks a constraint
}

/**
 * Rank the options the user can still choose. Default priorities keep the pipeline's ranking
 * (the scenario's ranks under a what-if); moved sliders re-rank in the browser.
 */
export function rankOptions(options: Option[], p: Priorities, c: Constraints, scenario: Scenario | null): Ranked[] {
  const rows = options.map((option) => {
    const metrics = metricsFor(option, scenario);
    const v = violations(option.sequence, metrics, c);
    return { option, metrics, violations: v, kept: option.option_id === "current" || v.length === 0 };
  });
  const kept = rows.filter((r) => r.kept);
  const baseRank = (o: Option) => scenario?.ranks[o.option_id] ?? o.rank;
  let order: typeof kept;
  if (isDefault(p)) {
    order = [...kept].sort((a, b) => baseRank(a.option) - baseRank(b.option));
  } else {
    const s = scores(kept.map((r) => ({ id: r.option.option_id, metrics: r.metrics })), p);
    order = [...kept].sort(
      (a, b) => s.get(b.option.option_id)! - s.get(a.option.option_id)! || baseRank(a.option) - baseRank(b.option),
    );
  }
  const ranked = order.map((r, i) => ({ ...r, rank: i + 1 }));
  const dropped = rows.filter((r) => !r.kept).map((r) => ({ ...r, rank: 0 }));
  return [...ranked, ...dropped];
}
