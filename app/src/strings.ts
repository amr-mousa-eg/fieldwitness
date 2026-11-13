import { getLocale, setLocale, subscribeLocale, useLocale, type Locale } from "./locale";
import ar from "./strings/ar.json";
import en from "./strings/en.json";
import type { Option } from "./types";

export type StringKey = keyof typeof en;
export type { Locale };
export { getLocale, setLocale, subscribeLocale, useLocale };

function activeDict(locale: Locale = getLocale()): Record<string, string> {
  return locale === "ar" ? (ar as Record<string, string>) : (en as Record<string, string>);
}

/** Look up a localized UI string (EN or AR) and fill {placeholders}. */
export function t(
  key: StringKey,
  vars: Record<string, string | number> = {},
  locale?: Locale,
): string {
  const dict = activeDict(locale);
  const template = dict[key] ?? en[key] ?? String(key);
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

/** Display name of a crop key from config/crops.yaml; unknown keys are shown as written. */
export function cropName(crop: string, locale?: Locale): string {
  const key = `crop.${crop}`;
  const dict = activeDict(locale);
  if (key in dict) return dict[key];
  return key in en ? en[key as StringKey] : crop;
}

/** Display name of a metric key (T6.7 labels are kept exactly as PLAN.md words them). */
export function metricName(metric: string, locale?: Locale): string {
  const key = `metric.${metric}`;
  const dict = activeDict(locale);
  if (key in dict) return dict[key];
  return key in en ? en[key as StringKey] : metric;
}

/**
 * "Current", "Alternative 1" (fixture ids), "Sorghum → Fallow → Sorghum" (pipeline ids are the
 * crop keys joined by "|"); other ids are shown as written.
 */
export function optionName(o: Pick<Option, "option_id">, locale?: Locale): string {
  if (o.option_id === "current") return t("card.current", {}, locale);
  const n = /^alt(\d+)$/.exec(o.option_id)?.[1];
  if (n) return t("card.alt", { n }, locale);
  return o.option_id.includes("|")
    ? o.option_id.split("|").map((c) => cropName(c, locale)).join(" → ")
    : o.option_id;
}
