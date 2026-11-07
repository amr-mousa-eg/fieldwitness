import en from "./strings/en.json";
import type { Option } from "./types";

export type StringKey = keyof typeof en;

/** Look up an English UI string and fill {placeholders}. */
export function t(key: StringKey, vars: Record<string, string | number> = {}): string {
  return en[key].replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

/** Display name of a crop key from config/crops.yaml; unknown keys are shown as written. */
export function cropName(crop: string): string {
  const key = `crop.${crop}`;
  return key in en ? en[key as StringKey] : crop;
}

/** Display name of a metric key (T6.7 labels are kept exactly as PLAN.md words them). */
export function metricName(metric: string): string {
  const key = `metric.${metric}`;
  return key in en ? en[key as StringKey] : metric;
}

/**
 * "Current", "Alternative 1" (fixture ids), "Sorghum → Fallow → Sorghum" (pipeline ids are the
 * crop keys joined by "|"); other ids are shown as written.
 */
export function optionName(o: Pick<Option, "option_id">): string {
  if (o.option_id === "current") return t("card.current");
  const n = /^alt(\d+)$/.exec(o.option_id)?.[1];
  if (n) return t("card.alt", { n });
  return o.option_id.includes("|") ? o.option_id.split("|").map(cropName).join(" → ") : o.option_id;
}
