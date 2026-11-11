// Rotation Builder rules and wording (feature flag ?builder=1).
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { cardState, isComplete, legalSequences, optionFor, ruleBroken, type RuleContext } from "../src/builder/rules";
import builderStrings from "../src/builder/strings.json";
import { simulateOption } from "../src/field3d/physics";
import { compareToCurrent } from "../src/fieldSummary";
import type { FieldPack, FieldSim3DInputs } from "../src/types";

const DIR = join(import.meta.dirname, "../public/packs/ks_t14slh");
const hasPacks = existsSync(DIR) && readdirSync(DIR).some((f) => f.endsWith(".sim3d_inputs.json"));
const KEYS = ["maize", "sorghum", "winter_wheat", "cover_crop", "fallow"];
const POACEAE = { maize: "Poaceae", sorghum: "Poaceae", winter_wheat: "Poaceae", cover_crop: "Poaceae", fallow: null };

describe("builder rules (synthetic)", () => {
  const ctx: RuleContext = { legal: [["maize", "fallow", "sorghum"], ["fallow", "maize", "winter_wheat"]], families: POACEAE, maxFamilyRun: 2 };

  it("explains each rule in the order of rotate/candidates.py", () => {
    expect(ruleBroken(["fallow", "cover_crop", null], ctx)?.rule).toBe("two_non_crop");
    expect(ruleBroken(["fallow", "maize", "cover_crop"], ctx)).toBeNull();
    expect(ruleBroken(["maize", "sorghum", "winter_wheat"], ctx)).toEqual({ rule: "family_run", family: "Poaceae" });
    expect(ruleBroken(["maize", "cover_crop", "sorghum"], ctx)?.rule).toBe("family_run"); // oat proxy is Poaceae
    expect(ruleBroken([null, null, null], ctx)).toBeNull();
  });

  it("a card is allowed only if some ranked rotation still fits", () => {
    expect(cardState([null, null, null], 0, "maize", ctx).ok).toBe(true);
    expect(cardState(["maize", null, null], 1, "fallow", ctx).ok).toBe(true);
    expect(cardState(["maize", null, null], 1, "sorghum", ctx)).toEqual({ ok: false, rule: "not_ranked" });
    expect(cardState(["fallow", null, null], 1, "cover_crop", ctx)).toEqual({ ok: false, rule: "two_non_crop" });
    expect(isComplete(["maize", "fallow", "sorghum"], ctx)).toBe(true);
    expect(isComplete(["maize", "fallow", null], ctx)).toBe(false);
  });

  it("wording: no points, scores, yield, tonnes, profit or price", () => {
    const text = Object.values(builderStrings).join(" ").toLowerCase();
    for (const w of ["points?", "scores?", "yields?", "tonnes?", "profits?", "prices?", "win", "level up"])
      expect(text, w).not.toMatch(new RegExp(String.raw`\b${w}\b`));
  });
});

describe.skipIf(!hasPacks)("builder rules on the real packs", () => {
  const files = hasPacks ? readdirSync(DIR).filter((f) => f.endsWith(".sim3d_inputs.json")) : [];
  const ctxFor = (pack: FieldPack, inp: FieldSim3DInputs): RuleContext => ({
    legal: legalSequences(pack),
    families: Object.fromEntries(Object.entries(inp.slots.crops).map(([k, s]) => [k, s.family])),
    maxFamilyRun: inp.slots.max_family_run,
  });

  it("every one of the 125 sequences is either a ranked rotation or breaks a stated rule", () => {
    for (const f of files.slice(0, 40)) {
      const inp = JSON.parse(readFileSync(join(DIR, f), "utf8")) as FieldSim3DInputs;
      const pack = JSON.parse(readFileSync(join(DIR, `${inp.field_id}.json`), "utf8")) as FieldPack;
      const ctx = ctxFor(pack, inp);
      expect(ctx.legal).toHaveLength(36);
      for (const a of KEYS)
        for (const b of KEYS)
          for (const c of KEYS) {
            const seq = [a, b, c];
            const legal = isComplete(seq, ctx);
            expect(legal, seq.join("|")).toBe(ruleBroken(seq, ctx) === null);
            if (legal) expect(optionFor(pack, seq)?.metrics.water_use_mm?.value, seq.join("|")).not.toBeNull();
          }
    }
  });

  it("a built rotation plays in 3 weathers and gets the Field Card sentence vs Current", () => {
    const f = files[0];
    const inp = JSON.parse(readFileSync(join(DIR, f), "utf8")) as FieldSim3DInputs;
    const pack = JSON.parse(readFileSync(join(DIR, `${inp.field_id}.json`), "utf8")) as FieldPack;
    const seq = legalSequences(pack)[5];
    const opt = simulateOption(inp, seq);
    expect(Object.keys(opt.scenarios).sort()).toEqual(["t+0_p+0", "t+0_p-20", "t+2_p+0"]);
    const current = pack.options.find((o) => o.option_id === "current");
    const mine = optionFor(pack, seq);
    if (current?.metrics.water_use_mm && mine) {
      const s = compareToCurrent(current, { ...mine, option_id: seq.join("|") }).sentence;
      expect(s).toMatch(/^Switching to .+\(evidence: grade [A-D]\)\.$/);
    }
  });
});
