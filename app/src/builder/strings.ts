import { getLocale } from "../locale";
import ar from "./strings.ar.json";
import en from "./strings.json";

export type BuilderKey = keyof typeof en;

/** Rotation Builder strings: kept in the lazy builder chunk so the initial bundle is unchanged. */
export function bt(key: BuilderKey, vars: Record<string, string | number> = {}): string {
  const dict = (getLocale() === "ar" ? ar : en) as Record<string, string>;
  const template = dict[key] ?? en[key] ?? String(key);
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}
