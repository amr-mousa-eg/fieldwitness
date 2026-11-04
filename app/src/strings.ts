import en from "./strings/en.json";

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
