import { isHistoryOnly } from "./seasons";
import type { CropVulnerability, FieldCalendar, Hazard, Option } from "./types";

export const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
export const HAZARDS: Hazard[] = ["heat", "frost", "water_stress", "extreme_rain_bare"];

/** Shade step 0–4 for a share 0–1; colour only supports the printed percentage (T9.7). */
export function shadeLevel(share: number | null): number | null {
  if (share === null) return null;
  return Math.min(4, Math.max(0, Math.ceil(share * 4)));
}

/**
 * Vulnerability entries for the crops of one option, in sequence order, plus crops without one.
 * History-only states (e.g. perennial forage, `seasons.ts`) are listed apart: they are not simulated.
 */
export function vulnerabilityFor(
  cal: FieldCalendar,
  option: Pick<Option, "sequence">,
): { found: CropVulnerability[]; missing: string[]; historyOnly: string[] } {
  const all = [...new Set(option.sequence)];
  const historyOnly = all.filter(isHistoryOnly);
  const crops = all.filter((c) => !isHistoryOnly(c));
  const found = crops.flatMap((c) => cal.vulnerability.filter((v) => v.crop === c));
  const missing = crops.filter((c) => !cal.vulnerability.some((v) => v.crop === c));
  return { found, missing, historyOnly };
}

/** Value of a month-indexed series (x = months 1..12) for `month`; null when absent. */
export function monthValue(x: (string | number)[], values: (number | null)[], month: number): number | null {
  const i = x.findIndex((m) => Number(m) === month);
  return i < 0 ? null : (values[i] ?? null);
}
