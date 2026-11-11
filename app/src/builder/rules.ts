// Rotation Builder rules. A rotation the user builds is allowed only if it is one of the field's
// ranked rotations in the pack (the pipeline's candidates, `rotate/candidates.py`), so the
// builder never shows a rotation the ranking did not evaluate. The rule checks below only explain
// WHY a card is disabled, in the order of `rotate/candidates.py`:
//   1. at least one harvested crop; 2. no two non-crop seasons (fallow, cover crop) in a row;
//   3. at most `max_family_run` seasons in a row of the same botanical family (crops.yaml, A).
// Anything else that rules a card out is reported as "no ranked rotation fits".
import { isHistoryOnly } from "../seasons";
import type { FieldPack, Option } from "../types";

export const N_SEASONS = 3;
export const NON_CROP = new Set(["fallow", "cover_crop"]);
export type Placed = (string | null)[];
export type RuleId = "needs_crop" | "two_non_crop" | "family_run" | "not_ranked";

export interface RuleContext {
  legal: string[][];
  families: Record<string, string | null>;
  maxFamilyRun: number;
}

/**
 * Ranked rotations of the field that the builder can offer: the pipeline's candidates. Current is
 * a reference option and may break the rules (e.g. three cereals in a row), so it is offered only
 * when it is also a candidate.
 */
export function legalSequences(pack: FieldPack): string[][] {
  const seen = new Set<string>();
  const out: string[][] = [];
  for (const o of pack.options) {
    const key = o.sequence.join("|");
    if (o.option_id === "current" || o.sequence.length !== N_SEASONS || o.sequence.some(isHistoryOnly) || seen.has(key)) continue;
    seen.add(key);
    out.push(o.sequence);
  }
  return out;
}

/** The pack option with exactly this sequence (a ranked rotation before Current). */
export function optionFor(pack: FieldPack, seq: string[]): Option | null {
  const key = seq.join("|");
  const all = pack.options.filter((o) => o.sequence.join("|") === key);
  return all.find((o) => o.option_id !== "current") ?? all[0] ?? null;
}

/** First rule broken by the placed seasons (empty slots are not judged), or null. */
export function ruleBroken(placed: Placed, ctx: RuleContext): { rule: RuleId; family?: string } | null {
  if (placed.every((c) => c !== null) && placed.every((c) => NON_CROP.has(c as string))) return { rule: "needs_crop" };
  for (let i = 1; i < placed.length; i++) {
    const a = placed[i - 1];
    const b = placed[i];
    if (a && b && NON_CROP.has(a) && NON_CROP.has(b)) return { rule: "two_non_crop" };
  }
  let run = 0;
  let prev: string | null = null;
  for (const c of placed) {
    const fam = c ? (ctx.families[c] ?? null) : null;
    run = fam !== null && fam === prev ? run + 1 : 1;
    prev = fam;
    if (fam !== null && run > ctx.maxFamilyRun) return { rule: "family_run", family: fam };
  }
  return null;
}

/** Can `crop` go into `slot` with the other placed seasons? If not, why not. */
export function cardState(
  placed: Placed,
  slot: number,
  crop: string,
  ctx: RuleContext,
): { ok: true } | { ok: false; rule: RuleId; family?: string } {
  const next = placed.map((c, i) => (i === slot ? crop : c));
  const broken = ruleBroken(next, ctx);
  if (broken) return { ok: false, ...broken };
  const fits = ctx.legal.some((seq) => seq.every((c, i) => next[i] === null || next[i] === c));
  return fits ? { ok: true } : { ok: false, rule: "not_ranked" };
}

/** A complete placement that is one of the field's ranked rotations. */
export function isComplete(placed: Placed, ctx: RuleContext): placed is string[] {
  return placed.every((c) => c !== null) && ctx.legal.some((s) => s.join("|") === placed.join("|"));
}
