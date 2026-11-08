// T6.9c/d: the Current rotation is read from a pack and a correction changes it, tag E.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { currentFromPack } from "../src/CorrectionPanel";
import { RERUN_NEEDED, SOURCE_FARMER, applyCorrections, emptyCorrections } from "../src/corrections";
import type { FieldPack, RegionIndex } from "../src/types";

const DIR = join(import.meta.dirname, "../public/packs");
const read = <T>(p: string): T => JSON.parse(readFileSync(join(DIR, p), "utf8")) as T;
const has = existsSync(join(DIR, "ks_t14slh/index.json"));

describe.skipIf(!has)("corrections on a real pack", () => {
  it("a corrected crop changes the Current sequence and is tagged farmer-entered", () => {
    const index = read<RegionIndex>("ks_t14slh/index.json");
    let tested = 0;
    for (const f of index.fields.slice(0, 10)) {
      const pack = read<FieldPack>(`ks_t14slh/${f.field_id}.json`);
      const cur = currentFromPack(pack);
      if (!cur) continue;
      const allowed = new Set(pack.options.flatMap((o) => o.sequence));
      const year = cur.years[cur.years.length - 1];
      const old = cur.sequence[cur.sequence.length - 1];
      const to = old === "fallow" ? "maize" : "fallow";
      const corr = { ...emptyCorrections(), cropByYear: { [year]: to } };
      const r = applyCorrections(cur, corr, allowed);
      expect(r.corrected.sequence[cur.sequence.length - 1]).toBe(to);
      expect(r.sourceByYear[year]).toBe(SOURCE_FARMER);
      expect(r.needsRerun).toBe(true);
      expect(r.notes).toContain(RERUN_NEEDED);
      expect(r.original.sequence).toEqual(cur.sequence);
      tested++;
    }
    expect(tested).toBeGreaterThan(0);
  });
});
