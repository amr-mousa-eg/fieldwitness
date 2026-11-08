// Browser store for farmer corrections (PLAN.md T6.9). One localStorage entry per field id.
// Every storage access is in try/catch: the app works when storage is unavailable or the data is bad.
import { type Corrections, emptyCorrections } from "./corrections";

const PREFIX = "fw.corrections.v1.";

export interface StorageLike {
  getItem(k: string): string | null;
  setItem(k: string, v: string): void;
  removeItem(k: string): void;
}

function defaultStorage(): StorageLike | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null; // access itself can throw (blocked cookies / privacy mode)
  }
}

const isNumRecord = (x: unknown, kind: "string" | "number"): x is Record<number, never> => {
  if (typeof x !== "object" || x === null || Array.isArray(x)) return false;
  return Object.entries(x).every(([k, v]) => Number.isInteger(Number(k)) && typeof v === kind);
};

/** Validate parsed JSON into Corrections; null if the shape is wrong. */
export function parseCorrections(raw: unknown): Corrections | null {
  if (typeof raw !== "object" || raw === null) return null;
  const r = raw as Record<string, unknown>;
  if (!isNumRecord(r.cropByYear, "string") || !isNumRecord(r.sowingDay, "number")) return null;
  if (r.irrigated !== null && typeof r.irrigated !== "boolean") return null;
  const num = (o: Record<number, unknown>) =>
    Object.fromEntries(Object.entries(o).map(([k, v]) => [Number(k), v]));
  return {
    cropByYear: num(r.cropByYear) as Record<number, string>,
    sowingDay: num(r.sowingDay) as Record<number, number>,
    irrigated: r.irrigated,
  };
}

export function loadCorrections(fieldId: string, store: StorageLike | null = defaultStorage()): Corrections {
  try {
    const s = store?.getItem(PREFIX + fieldId);
    if (!s) return emptyCorrections();
    return parseCorrections(JSON.parse(s)) ?? emptyCorrections();
  } catch {
    return emptyCorrections();
  }
}

/** Returns true if saved. An empty correction set removes the entry. */
export function saveCorrections(
  fieldId: string,
  corr: Corrections,
  store: StorageLike | null = defaultStorage(),
): boolean {
  try {
    if (!store) return false;
    const empty =
      Object.keys(corr.cropByYear).length === 0 &&
      Object.keys(corr.sowingDay).length === 0 &&
      corr.irrigated === null;
    if (empty) store.removeItem(PREFIX + fieldId);
    else store.setItem(PREFIX + fieldId, JSON.stringify(corr));
    return true;
  } catch {
    return false;
  }
}

export function clearCorrections(fieldId: string, store: StorageLike | null = defaultStorage()): boolean {
  try {
    if (!store) return false;
    store.removeItem(PREFIX + fieldId);
    return true;
  } catch {
    return false;
  }
}
