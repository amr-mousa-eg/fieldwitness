import en from "./strings.json";

export type BuilderKey = keyof typeof en;

/** Rotation Builder strings: kept in the lazy builder chunk so the initial bundle is unchanged. */
export function bt(key: BuilderKey, vars: Record<string, string | number> = {}): string {
  return en[key].replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}
