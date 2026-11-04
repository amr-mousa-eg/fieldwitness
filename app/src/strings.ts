import en from "./strings/en.json";

export type StringKey = keyof typeof en;

/** Look up an English UI string and fill {placeholders}. */
export function t(key: StringKey, vars: Record<string, string | number> = {}): string {
  return en[key].replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}
