// Farmer corrections to the Current rotation (PLAN.md T6.9). Mirrors
// src/fieldwitness/rotate/corrections.py: same rules, same RERUN_NEEDED text, same key format.
// A correction is farmer-entered ground data: tag E, source "farmer". The label version is kept.

export const RERUN_NEEDED = "re-run needed: available in live mode";
export const SOURCE_FARMER = "farmer";
export const SOURCE_LABEL = "label";
export const FALLOW = "fallow";

export interface CurrentRotation {
  fieldId: string;
  years: number[]; // season years, oldest first
  sequence: string[];
  confidence: number;
  tag: string;
  simulatable: boolean;
  gaps: string[];
  secondCrops: Record<number, string>;
}

export interface Corrections {
  cropByYear: Record<number, string>;
  sowingDay: Record<number, number>;
  irrigated: boolean | null; // null = not corrected
}

export interface CorrectedCurrent {
  original: CurrentRotation;
  corrected: CurrentRotation;
  sourceByYear: Record<number, string>;
  needsRerun: boolean;
  notes: string[];
}

export const emptyCorrections = (): Corrections => ({
  cropByYear: {},
  sowingDay: {},
  irrigated: null,
});

const numKeys = (r: Record<number, unknown>): number[] =>
  Object.keys(r)
    .map(Number)
    .sort((a, b) => a - b);

/** Stable key of a correction set; names a precomputed alternative (Python: correction_key). */
export function correctionKey(corr: Corrections): string {
  const parts = numKeys(corr.cropByYear).map((y) => `c${y}=${corr.cropByYear[y]}`);
  parts.push(...numKeys(corr.sowingDay).map((y) => `s${y}=${corr.sowingDay[y]}`));
  if (corr.irrigated !== null) parts.push(`irr=${corr.irrigated ? 1 : 0}`);
  return parts.join(";");
}

/** Apply `corr` to `cur`. `alternatives` = correction keys with a precomputed pack. */
export function applyCorrections(
  cur: CurrentRotation,
  corr: Corrections,
  allowed: Set<string>,
  alternatives: Set<string> | null = null,
): CorrectedCurrent {
  const ok = new Set([...allowed, FALLOW]);
  const corrYears = numKeys(corr.cropByYear);
  const bad = corrYears.filter((y) => !cur.years.includes(y));
  if (bad.length) {
    throw new Error(`years [${bad.join(", ")}] are not in the Current rotation [${cur.years.join(", ")}]`);
  }
  const seq = cur.sequence.map((c, i) => corr.cropByYear[cur.years[i]] ?? c);
  const sourceByYear: Record<number, string> = {};
  for (const y of cur.years) sourceByYear[y] = y in corr.cropByYear ? SOURCE_FARMER : SOURCE_LABEL;
  // A farmer entry replaces the label: the double-crop note and the "not simulated" gap no longer apply.
  const gaps = cur.gaps.filter((g) => !corrYears.some((y) => g.startsWith(`${y}:`)));
  const secondCrops: Record<number, string> = {};
  for (const y of numKeys(cur.secondCrops)) {
    if (!(y in corr.cropByYear)) secondCrops[y] = cur.secondCrops[y];
  }
  cur.years.forEach((y, i) => {
    if (sourceByYear[y] === SOURCE_FARMER && !ok.has(seq[i])) {
      gaps.push(`${y}: '${seq[i]}' (farmer-entered) is not simulated`);
    }
  });
  const corrected: CurrentRotation = {
    ...cur,
    sequence: seq,
    gaps,
    secondCrops,
    simulatable: seq.every((c) => ok.has(c)),
  };
  const notes = corrYears.map((y) => `${y}: crop set by farmer (tag E, farmer-entered)`);
  let needsRerun = false;
  const physicsChanged = Object.keys(corr.sowingDay).length > 0 || corr.irrigated !== null;
  if (physicsChanged || corrYears.length > 0) {
    const key = correctionKey(corr);
    if (alternatives !== null && alternatives.has(key)) {
      notes.push(`precomputed alternative '${key}' available`);
    } else if (physicsChanged || seq.some((c, i) => c !== cur.sequence[i])) {
      needsRerun = true;
      notes.push(RERUN_NEEDED);
    }
  }
  return { original: cur, corrected, sourceByYear, needsRerun, notes };
}
