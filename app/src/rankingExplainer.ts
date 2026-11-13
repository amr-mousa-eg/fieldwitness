import {
  type Metrics,
  type Priorities,
  type PriorityKey,
  type Ranked,
  DEFAULT_PRIORITIES,
  PRIORITY_KEYS,
  PRIORITY_METRICS,
} from "./rank";
import { RANKING_EXPLAINER_CONFIG } from "./rankingExplainerConfig";
import { optionName, t } from "./strings";
import type { Option } from "./types";

export interface MetricContributionDetail {
  metric: string;
  labelKey: string;
  value: number | null;
  unit: string;
  tag: string;
  better: "lower" | "higher";
  scaled: number; // 0..1
}

export interface PriorityContribution {
  key: PriorityKey;
  label: string;
  weight: number; // 0..3
  scaledValue: number; // 0..1 (average scaled across priority's metrics)
  contribution: number; // (weight * scaledValue) / totalWeight
  metrics: MetricContributionDetail[];
}

export interface OptionBreakdown {
  option: Option;
  totalScore: number;
  contributions: PriorityContribution[];
}

export interface RankingExplanation {
  top: OptionBreakdown;
  next?: OptionBreakdown;
  scoreDiff: number;
  dominantPriority?: PriorityKey;
  dominantShare?: number;
  sentence: string;
}

const PRIORITY_LABELS: Record<PriorityKey, string> = {
  water: "Use less water",
  bare: "Fewer bare-soil months",
  badYear: "Do better in a bad year",
  erosion: "Less erosion",
  legume: "More nitrogen-fixing crops",
  residue: "More organic matter input",
};

/**
 * Compute the exact mathematical breakdown of priority contributions for a given option
 * against the cohort of compared options under current priorities.
 *
 * Invariant: sum(contributions.map(c => c.contribution)) === totalScore.
 */
export function computeOptionBreakdown(
  target: { option: Option; metrics: Metrics },
  allOptions: { option: Option; metrics: Metrics }[],
  p: Priorities,
): OptionBreakdown {
  const totalWeight = PRIORITY_KEYS.reduce((s, k) => s + p[k], 0);
  const contributions: PriorityContribution[] = [];
  let scoreSum = 0;

  for (const k of PRIORITY_KEYS) {
    const weight = p[k];
    const metricConfigs = PRIORITY_METRICS[k];
    const details: MetricContributionDetail[] = [];

    for (const { metric, better } of metricConfigs) {
      const tagged = target.metrics[metric];
      const val = tagged?.value ?? null;
      const allVals = allOptions
        .map((o) => o.metrics[metric]?.value)
        .filter((v): v is number => v != null);

      let scaled = 0;
      if (val != null && allVals.length > 0) {
        const lo = Math.min(...allVals);
        const hi = Math.max(...allVals);
        const rawScaled = hi === lo ? 1 : (val - lo) / (hi - lo);
        scaled = better === "higher" ? rawScaled : 1 - rawScaled;
      }

      details.push({
        metric,
        labelKey: `metric.${metric}`,
        value: val,
        unit: tagged?.unit ?? "",
        tag: tagged?.tag ?? "D",
        better,
        scaled,
      });
    }

    const avgScaled = details.length > 0 ? details.reduce((acc, m) => acc + m.scaled, 0) / details.length : 0;
    const contribution = totalWeight === 0 ? 0 : (weight * avgScaled) / totalWeight;
    scoreSum += contribution;

    contributions.push({
      key: k,
      label: PRIORITY_LABELS[k],
      weight,
      scaledValue: avgScaled,
      contribution,
      metrics: details,
    });
  }

  return {
    option: target.option,
    totalScore: scoreSum,
    contributions,
  };
}

/**
 * Generate side-by-side breakdown and deterministic plain-language explainer
 * comparing the #1 top-ranked option against the #2 next-best option.
 */
export function explainTopRanking(
  allRankedKept: Ranked[],
  p: Priorities,
): RankingExplanation | null {
  if (allRankedKept.length === 0) return null;

  const rows = allRankedKept.map((r) => ({ option: r.option, metrics: r.metrics }));
  const breakdowns = allRankedKept.map((r) => computeOptionBreakdown(r, rows, p));
  // Order options strictly by preference score under the evaluated priority weights
  breakdowns.sort((a, b) => b.totalScore - a.totalScore);

  const topBreakdown = breakdowns[0];
  const nextBreakdown = breakdowns.length > 1 ? breakdowns[1] : undefined;

  if (!nextBreakdown) {
    return {
      top: topBreakdown,
      scoreDiff: 0,
      sentence: t("rankExplainer.single"),
    };
  }

  const scoreDiff = Math.max(0, topBreakdown.totalScore - nextBreakdown.totalScore);
  const nextName = optionName(nextBreakdown.option);

  if (scoreDiff < 0.001) {
    return {
      top: topBreakdown,
      next: nextBreakdown,
      scoreDiff,
      sentence: t("rankExplainer.equal", { nextOption: nextName }),
    };
  }

  // Find priority contributions to score difference
  let maxShare = -Infinity;
  let dominantPrio: PriorityKey | undefined = undefined;

  for (let i = 0; i < PRIORITY_KEYS.length; i++) {
    const k = PRIORITY_KEYS[i];
    const diff = topBreakdown.contributions[i].contribution - nextBreakdown.contributions[i].contribution;
    const share = diff / scoreDiff;
    if (share > maxShare) {
      maxShare = share;
      dominantPrio = k;
    }
  }

  if (
    dominantPrio &&
    maxShare >= RANKING_EXPLAINER_CONFIG.dominantContributionShare
  ) {
    const pct = Math.round(maxShare * 100);
    const critLabel = PRIORITY_LABELS[dominantPrio];
    return {
      top: topBreakdown,
      next: nextBreakdown,
      scoreDiff,
      dominantPriority: dominantPrio,
      dominantShare: maxShare,
      sentence: t("rankExplainer.mainlyBecause", {
        criterion: critLabel,
        share: pct,
        nextOption: nextName,
      }),
    };
  }

  return {
    top: topBreakdown,
    next: nextBreakdown,
    scoreDiff,
    dominantPriority: dominantPrio,
    dominantShare: maxShare,
    sentence: t("rankExplainer.similar", { nextOption: nextName }),
  };
}

/**
 * Returns deterministic ranking explanation for ranked alternatives.
 */
export function explainRanking(
  allRankedKept: Ranked[],
  p: Priorities = DEFAULT_PRIORITIES,
): RankingExplanation {
  const res = explainTopRanking(allRankedKept, p);
  if (res) return res;
  const rows = allRankedKept.map((r) => ({ option: r.option, metrics: r.metrics }));
  const top = allRankedKept.length > 0
    ? computeOptionBreakdown(allRankedKept[0], rows, p)
    : { option: {} as Option, totalScore: 0, contributions: [] };
  return {
    top,
    scoreDiff: 0,
    sentence: t("rankExplainer.single"),
  };
}

