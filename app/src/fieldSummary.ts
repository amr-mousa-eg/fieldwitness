/**
 * Field summary generator (Item 2).
 * Generates a dynamic one-sentence plain-language summary and side-by-side metric comparison
 * contrasting the field's Current rotation with the top-ranked alternative under active priority weights.
 *
 * Requirements:
 * - Real units only: water_use_mm (mm), bad_year_water_mm (mm), bare-soil months (months), grade.
 * - "about the same" when differences are within stated thresholds (config/field_summary.yaml, tag A).
 * - Trade-offs shown both ways ("...uses 40 mm less water, but has 1 more bare-soil month").
 * - If Current ranks best: "Your current rotation ranks best for the priorities you set (evidence: grade X)."
 * - No yield, profit, or certainty words; ends with evidence grade: "(evidence: grade X)".
 * - Every number source-tagged (tag D for derived model metrics, tag A for thresholds).
 */

import {
  DAYS_PER_MONTH,
  ROTATION_DAYS,
  SUMMARY_THRESHOLDS,
} from "./fieldSummaryConfig";
import {
  type Constraints,
  type Priorities,
  rankOptions,
} from "./rank";
import { optionName } from "./strings";
import type { FieldPack, Option, Scenario, Tag } from "./types";

export interface TaggedNumber {
  value: number;
  unit: string;
  tag: Tag;
  source: string;
}

export interface MetricComparisonItem {
  metric: "water_use_mm" | "bad_year_water_mm" | "bare_soil_months";
  label: string;
  unit: string;
  currentValue: number;
  topValue: number;
  diff: number; // topValue - currentValue
  isAboutTheSame: boolean;
  isFavorableForTop: boolean | null; // true if top is better, false if worse, null if same
  tag: Tag;
  source: string;
}

export interface ComparisonSummary {
  isCurrentBest: boolean;
  currentOption: Option;
  topAlternative: Option | null;
  sentence: string;
  tokens: SummaryToken[];
  evidenceGrade: string;
  metrics: {
    water_use: MetricComparisonItem;
    bad_year_water: MetricComparisonItem;
    bare_soil: MetricComparisonItem;
  };
}

export type SummaryToken =
  | { kind: "text"; text: string }
  | { kind: "tagged"; value: number; unit: string; tag: Tag; source: string }
  | { kind: "grade"; grade: string };

/** Compute bare-soil months from cover days over a 3-year (1095-day) rotation. */
export function computeBareSoilMonths(coverDays: number | null | undefined): number {
  if (coverDays == null || isNaN(coverDays)) return 0;
  const bareDays = Math.max(0, ROTATION_DAYS - coverDays);
  return Math.round((bareDays / DAYS_PER_MONTH) * 10) / 10;
}

/**
 * Determine the top-ranked alternative option under active user priorities, constraints, and what-ifs.
 */
export function resolveTopOptions(
  pack: FieldPack,
  priorities: Priorities,
  constraints: Constraints,
  scenario: Scenario | null
): { current: Option; topAlt: Option | null; isCurrentBest: boolean } {
  const rankedRows = rankOptions(pack.options, priorities, constraints, scenario);
  const kept = rankedRows.filter((r) => r.kept);

  const currentOption = pack.options.find((o) => o.option_id === "current") ?? pack.options[0];
  const isCurrentBest = kept.length > 0 && kept[0].option.option_id === "current";

  // Top alternative is the highest ranked kept option that is not Current
  const topAltRow = kept.find((r) => r.option.option_id !== "current");
  const topAlt = topAltRow ? topAltRow.option : null;

  return { current: currentOption, topAlt, isCurrentBest };
}

/**
 * Build comparison metrics between Current and Top Alternative.
 */
export function buildMetricComparisons(
  current: Option,
  top: Option
): {
  water_use: MetricComparisonItem;
  bad_year_water: MetricComparisonItem;
  bare_soil: MetricComparisonItem;
} {
  const curWater = Math.round(current.metrics.water_use_mm?.value ?? 0);
  const topWater = Math.round(top.metrics.water_use_mm?.value ?? 0);
  const diffWater = topWater - curWater;
  const sameWater = Math.abs(diffWater) < SUMMARY_THRESHOLDS.water_use_mm;

  const curBadWater = Math.round(current.metrics.bad_year_water_mm?.value ?? 0);
  const topBadWater = Math.round(top.metrics.bad_year_water_mm?.value ?? 0);
  const diffBadWater = topBadWater - curBadWater;
  const sameBadWater = Math.abs(diffBadWater) < SUMMARY_THRESHOLDS.bad_year_water_mm;

  const curBareMonths = computeBareSoilMonths(current.metrics.cover_days?.value);
  const topBareMonths = computeBareSoilMonths(top.metrics.cover_days?.value);
  const diffBareMonths = Math.round((topBareMonths - curBareMonths) * 10) / 10;
  const sameBare = Math.abs(diffBareMonths) < SUMMARY_THRESHOLDS.bare_soil_months;

  return {
    water_use: {
      metric: "water_use_mm",
      label: "Water use",
      unit: "mm",
      currentValue: curWater,
      topValue: topWater,
      diff: diffWater,
      isAboutTheSame: sameWater,
      isFavorableForTop: sameWater ? null : diffWater < 0,
      tag: "D",
      source: "FAO-56 water balance simulation over posterior worlds",
    },
    bad_year_water: {
      metric: "bad_year_water_mm",
      label: "Bad-year water",
      unit: "mm",
      currentValue: curBadWater,
      topValue: topBadWater,
      diff: diffBadWater,
      isAboutTheSame: sameBadWater,
      isFavorableForTop: sameBadWater ? null : diffBadWater < 0,
      tag: "D",
      source: "FAO-56 water balance upper 10% tail (CVaR10)",
    },
    bare_soil: {
      metric: "bare_soil_months",
      label: "Bare soil",
      unit: "months",
      currentValue: curBareMonths,
      topValue: topBareMonths,
      diff: diffBareMonths,
      isAboutTheSame: sameBare,
      isFavorableForTop: sameBare ? null : diffBareMonths < 0,
      tag: "D",
      source: "simulated crop cover duration over 3 seasons",
    },
  };
}

interface Clause {
  text: string;
  isPro: boolean;
  tokens: SummaryToken[];
}

/**
 * Generate field summary sentence and comparison metrics.
 */
export function generateFieldSummary(
  pack: FieldPack,
  priorities: Priorities,
  constraints: Constraints,
  scenario: Scenario | null
): ComparisonSummary {
  const { current, topAlt, isCurrentBest } = resolveTopOptions(
    pack,
    priorities,
    constraints,
    scenario
  );

  // Fallback if no alternative options exist or only current
  const targetOption = topAlt ?? current;
  const metrics = buildMetricComparisons(current, targetOption);
  const evidenceGrade = targetOption.grade;

  if (isCurrentBest || !topAlt) {
    const text = `Your current rotation ranks best for the priorities you set (evidence: grade ${current.grade}).`;
    const tokens: SummaryToken[] = [
      { kind: "text", text: "Your current rotation ranks best for the priorities you set (evidence: " },
      { kind: "grade", grade: current.grade },
      { kind: "text", text: ")." },
    ];
    return {
      isCurrentBest: true,
      currentOption: current,
      topAlternative: topAlt,
      sentence: text,
      tokens,
      evidenceGrade: current.grade,
      metrics,
    };
  }

  // Generate clauses for top alternative vs current
  const clauses: Clause[] = [];

  // 1. Water use clause
  if (!metrics.water_use.isAboutTheSame) {
    const absDiff = Math.abs(metrics.water_use.diff);
    const isLess = metrics.water_use.diff < 0;
    clauses.push({
      text: `uses ${absDiff} mm ${isLess ? "less" : "more"} water`,
      isPro: isLess,
      tokens: [
        { kind: "text", text: "uses " },
        { kind: "tagged", value: absDiff, unit: "mm", tag: "D", source: metrics.water_use.source },
        { kind: "text", text: ` ${isLess ? "less" : "more"} water` },
      ],
    });
  }

  // 2. Bad-year water clause
  if (!metrics.bad_year_water.isAboutTheSame) {
    const absDiff = Math.abs(metrics.bad_year_water.diff);
    const isLess = metrics.bad_year_water.diff < 0;
    clauses.push({
      text: `${absDiff} mm ${isLess ? "less" : "more"} in bad years`,
      isPro: isLess,
      tokens: [
        { kind: "tagged", value: absDiff, unit: "mm", tag: "D", source: metrics.bad_year_water.source },
        { kind: "text", text: ` ${isLess ? "less" : "more"} in bad years` },
      ],
    });
  }

  // 3. Bare soil clause
  if (!metrics.bare_soil.isAboutTheSame) {
    const absMonths = Math.abs(Math.round(metrics.bare_soil.diff));
    const isFewer = metrics.bare_soil.diff < 0;
    const monthWord = absMonths === 1 ? "month" : "months";
    clauses.push({
      text: `has ${absMonths} ${isFewer ? "fewer" : "more"} bare-soil ${monthWord}`,
      isPro: isFewer,
      tokens: [
        { kind: "text", text: "has " },
        { kind: "tagged", value: absMonths, unit: monthWord, tag: "D", source: metrics.bare_soil.source },
        { kind: "text", text: ` ${isFewer ? "fewer" : "more"} bare-soil ${monthWord}` },
      ],
    });
  }

  const optLabel = optionName(topAlt);
  const startText = `Switching to ${optLabel} `;
  const startTokens: SummaryToken[] = [{ kind: "text", text: startText }];
  const endTokens: SummaryToken[] = [
    { kind: "text", text: " (evidence: " },
    { kind: "grade", grade: evidenceGrade },
    { kind: "text", text: ")." },
  ];

  // Case: all differences are within threshold ("about the same")
  if (clauses.length === 0) {
    const text = `Switching to ${optLabel} has about the same water use, bad-year water and bare soil as your current rotation (evidence: grade ${evidenceGrade}).`;
    const tokens: SummaryToken[] = [
      ...startTokens,
      { kind: "text", text: "has about the same water use, bad-year water and bare soil as your current rotation" },
      ...endTokens,
    ];
    return {
      isCurrentBest: false,
      currentOption: current,
      topAlternative: topAlt,
      sentence: text,
      tokens,
      evidenceGrade,
      metrics,
    };
  }

  const pros = clauses.filter((c) => c.isPro);
  const cons = clauses.filter((c) => !c.isPro);

  let sentenceBodyText = "";
  const bodyTokens: SummaryToken[] = [];

  const joinTokens = (list: Clause[], sep = " and ") => {
    const res: SummaryToken[] = [];
    list.forEach((c, idx) => {
      if (idx > 0) res.push({ kind: "text", text: sep });
      res.push(...c.tokens);
    });
    return res;
  };

  if (pros.length > 0 && cons.length > 0) {
    // Trade-off both ways
    const proText = pros.map((c) => c.text).join(" and ");
    const conText = cons.map((c) => c.text).join(" and ");
    sentenceBodyText = `${proText}, but ${conText}`;

    bodyTokens.push(...joinTokens(pros));
    bodyTokens.push({ kind: "text", text: ", but " });
    bodyTokens.push(...joinTokens(cons));
  } else if (pros.length > 0) {
    sentenceBodyText = pros.map((c) => c.text).join(" and ");
    bodyTokens.push(...joinTokens(pros));
  } else {
    sentenceBodyText = cons.map((c) => c.text).join(" and ");
    bodyTokens.push(...joinTokens(cons));
  }

  const sentence = `${startText}${sentenceBodyText} (evidence: grade ${evidenceGrade}).`;
  const tokens = [...startTokens, ...bodyTokens, ...endTokens];

  return {
    isCurrentBest: false,
    currentOption: current,
    topAlternative: topAlt,
    sentence,
    tokens,
    evidenceGrade,
    metrics,
  };
}
