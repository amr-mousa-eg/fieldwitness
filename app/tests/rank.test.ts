import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  DEFAULT_PRIORITIES,
  NO_CONSTRAINTS,
  type Priorities,
  findScenario,
  metricsFor,
  rankOptions,
  scores,
} from "../src/rank";
import type { FieldPack, FieldScenarios, Option, Tagged } from "../src/types";

const DIR = join(import.meta.dirname, "../fixtures/ks_demo_synthetic");
const read = <T>(name: string): T => JSON.parse(readFileSync(join(DIR, name), "utf8"));
const packNames = readdirSync(DIR).filter((f) => /^[0-9a-f]{40}\.SYNTHETIC\.json$/.test(f));
const packs = packNames.map((f) => read<FieldPack>(f));
const scenariosOf = (p: FieldPack) => read<FieldScenarios>(`${p.field.field_id}.scenarios.SYNTHETIC.json`);

const tagged = (value: number): Tagged => ({ value, unit: "x", tag: "D", source: "test" });
const opt = (id: string, seq: string[], m: Record<string, number>, rank: number): Option => ({
  option_id: id,
  sequence: seq,
  metrics: Object.fromEntries(Object.entries(m).map(([k, v]) => [k, tagged(v)])),
  witnesses: [],
  grade: "C",
  grade_reasons: [],
  regret: tagged(0),
  rank,
  explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
});

describe("rankOptions", () => {
  it("keeps the pipeline ranking while priorities are untouched", () => {
    for (const p of packs) {
      const r = rankOptions(p.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
      const expected = [...p.options].sort((a, b) => a.rank - b.rank).map((o) => o.option_id);
      expect(r.map((x) => x.option.option_id)).toEqual(expected);
    }
  });

  it("uses the scenario's ranks under a what-if", () => {
    const p = packs[0];
    const s = findScenario(scenariosOf(p), 2, -20)!;
    const r = rankOptions(p.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, s);
    const expected = Object.entries(s.ranks).sort((a, b) => a[1] - b[1]).map(([id]) => id);
    expect(r.map((x) => x.option.option_id)).toEqual(expected);
  });

  it("puts the lowest water use first when only water matters", () => {
    const only: Priorities = { water: 3, bare: 0, badYear: 0, erosion: 0, legume: 0, residue: 0 };
    for (const p of packs) {
      const r = rankOptions(p.options, only, NO_CONSTRAINTS, null);
      const water = r.map((x) => x.metrics.water_use_mm.value!);
      expect(water).toEqual([...water].sort((a, b) => a - b));
    }
  });

  it("never keeps an alternative with a banned or ungrowable crop, but always keeps Current", () => {
    for (const p of packs) {
      for (const crop of new Set(p.options.flatMap((o) => o.sequence))) {
        for (const key of ["dontWant", "cantGrow"] as const) {
          const r = rankOptions(p.options, DEFAULT_PRIORITIES, { ...NO_CONSTRAINTS, [key]: [crop] }, null);
          for (const x of r.filter((y) => y.kept && y.option.option_id !== "current")) {
            expect(x.option.sequence).not.toContain(crop);
          }
          const cur = r.find((y) => y.option.option_id === "current")!;
          expect(cur.kept).toBe(true);
          expect(cur.violations.length > 0).toBe(cur.option.sequence.includes(crop));
        }
      }
    }
  });

  it("applies can-sell, irrigation and water-cap constraints", () => {
    const options = [
      opt("current", ["maize", "fallow"], { water_use_mm: 500, irrigation_mm: 100 }, 1),
      opt("alt1", ["sorghum", "fallow"], { water_use_mm: 400, irrigation_mm: 0 }, 2),
      opt("alt2", ["winter_wheat", "cover_crop"], { water_use_mm: 350, irrigation_mm: 20 }, 3),
    ];
    const kept = (c: Partial<typeof NO_CONSTRAINTS>) =>
      rankOptions(options, DEFAULT_PRIORITIES, { ...NO_CONSTRAINTS, ...c }, null)
        .filter((x) => x.kept)
        .map((x) => x.option.option_id);
    expect(kept({ canSell: ["sorghum"] })).toEqual(["current", "alt1"]); // fallow/cover never sold
    expect(kept({ irrigation: "no" })).toEqual(["current", "alt1"]);
    expect(kept({ waterCapMm: 380 })).toEqual(["current", "alt2"]);
  });
});

describe("scores and metricsFor", () => {
  it("scores 1 for the best and 0 for the worst on a single metric", () => {
    const s = scores(
      [
        { id: "a", metrics: { water_use_mm: tagged(300) } },
        { id: "b", metrics: { water_use_mm: tagged(500) } },
      ],
      { water: 1, bare: 0, badYear: 0, erosion: 0, legume: 0, residue: 0 },
    );
    expect(s.get("a")).toBe(1);
    expect(s.get("b")).toBe(0);
  });

  it("replaces only weather-sensitive metrics under a what-if", () => {
    const p = packs[0];
    const s = findScenario(scenariosOf(p), 1, -10)!;
    const o = p.options[0];
    const m = metricsFor(o, s);
    expect(m.water_use_mm).toEqual(s.metrics[o.option_id].water_use_mm);
    expect(m.legume_share).toEqual(o.metrics.legume_share); // sequence-only: from the pack
  });
});
