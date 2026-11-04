import type { Tagged } from "./types";

const SHARE_UNITS = /^(share|probability)/;

/** "0.33 share of seasons" -> "33 %"; other units keep their own name. */
export function formatNumber(value: number, unit: string, digits?: number): string {
  if (SHARE_UNITS.test(unit)) return `${Math.round(value * 100)} %`;
  const d = digits ?? (Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2);
  return value.toLocaleString("en", { maximumFractionDigits: d, minimumFractionDigits: 0 });
}

/** Shares print as %, and 0–1 indices (RYI, scores) need no unit after the number. */
export function unitLabel(unit: string): string {
  return SHARE_UNITS.test(unit) || unit.includes("0–1") ? "" : unit;
}

export function formatTagged(v: Tagged, digits?: number): string {
  if (v.value === null) return "no data";
  const u = unitLabel(v.unit);
  return `${formatNumber(v.value, v.unit, digits)}${u ? ` ${u}` : ""}`;
}

/** Signed difference to a reference value, in the value's own unit. */
export function formatDelta(v: Tagged, ref: Tagged, digits?: number): string | null {
  if (v.value === null || ref.value === null) return null;
  const d = v.value - ref.value;
  const body = formatNumber(Math.abs(d), v.unit, digits);
  if (body === "0" || body === "0 %") return "same";
  return `${d > 0 ? "+" : "−"}${body}`;
}

/**
 * Season dates are days of the harvest year; 1 = 1 Jan, 0 = 31 Dec of the year before,
 * negative = earlier that autumn (schema decision Q1, 2026-11-04).
 */
export function harvestDayToDate(harvestYear: number, day: number): Date {
  return new Date(Date.UTC(harvestYear, 0, 1) + (day - 1) * 86_400_000);
}

export function formatDate(d: Date): string {
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
