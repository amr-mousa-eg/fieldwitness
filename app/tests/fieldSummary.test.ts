import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  computeBareSoilMonths,
  generateFieldSummary,
  resolveTopOptions,
} from "../src/fieldSummary";
import { DEFAULT_PRIORITIES, NO_CONSTRAINTS, type Priorities } from "../src/rank";
import type { FieldPack, Option } from "../src/types";

// Helper to construct a mock Option
function mockOption(
  id: string,
  sequence: string[],
  waterUse: number,
  badYearWater: number,
  coverDays: number,
  grade: "A" | "B" | "C" | "D",
  rank: number
): Option {
  return {
    option_id: id,
    sequence,
    rank,
    grade,
    grade_reasons: [],
    witnesses: [],
    regret: { value: 0.1, unit: "regret", tag: "D", source: "test" },
    explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
    metrics: {
      water_use_mm: { value: waterUse, unit: "mm per rotation", tag: "D", source: "test" },
      bad_year_water_mm: { value: badYearWater, unit: "mm per rotation", tag: "D", source: "test" },
      cover_days: { value: coverDays, unit: "days per rotation", tag: "D", source: "test" },
      ryi: { value: 0.5, unit: "0-1", tag: "D", source: "test" },
    },
  };
}

function mockPack(options: Option[]): FieldPack {
  return {
    schema_version: "1.2",
    field: {
      field_id: "test_field_123",
      geometry_wkt: "POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))",
      area_ha: 50.0,
      region_id: "ks_t14slh",
      tier: 1,
      boundary_source: "CSB",
      scale_flags: { HLS: false, POWER: false, SoilGrids: false },
      interior_pixels: 500,
    },
    story: [],
    credibility: { value: 0.8, unit: "0-1", tag: "D", source: "test" },
    options,
  };
}

describe("fieldSummary generator unit tests", () => {
  it("computes bare soil months correctly from cover days", () => {
    // 1095 days = 36 months total
    // 319 cover days -> 776 bare days -> 776 / 30.4375 = 25.49 -> 25.5 months
    expect(computeBareSoilMonths(319)).toBeCloseTo(25.5, 1);
    // 1095 cover days -> 0 bare days -> 0.0 months
    expect(computeBareSoilMonths(1095)).toBe(0);
    // 0 cover days -> 1095 bare days -> 36.0 months
    expect(computeBareSoilMonths(0)).toBeCloseTo(36.0, 1);
  });

  it("handles the 'current is best' case when current ranks #1", () => {
    const cur = mockOption("current", ["maize", "fallow", "wheat"], 1200, 1500, 400, "B", 1);
    const alt = mockOption("alt1", ["sorghum", "sorghum", "sorghum"], 1400, 1800, 300, "C", 2);
    const pack = mockPack([cur, alt]);

    const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
    expect(res.isCurrentBest).toBe(true);
    expect(res.sentence).toBe("Your current rotation ranks best for the priorities you set (evidence: grade B).");
    expect(res.sentence).not.toContain("NaN");
    expect(res.sentence).not.toContain("undefined");
  });

  it("handles trade-offs both ways: less water but more bare soil", () => {
    // Current: 1500 mm water, 2000 mm bad water, 400 cover days (bare = (1095-400)/30.4375 = 22.8)
    // Alt: 1460 mm water (-40 mm), 2000 mm bad water (0 mm), 370 cover days (bare = (1095-370)/30.4375 = 23.8 -> +1 month)
    const cur = mockOption("current", ["maize", "maize", "maize"], 1500, 2000, 400, "D", 2);
    const alt = mockOption("alt1", ["sorghum", "fallow", "sorghum"], 1460, 2000, 370, "C", 1);
    const pack = mockPack([cur, alt]);

    const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
    expect(res.isCurrentBest).toBe(false);
    expect(res.sentence).toContain("uses 40 mm less water, but has 1 more bare-soil month (evidence: grade C).");
  });

  it("handles trade-offs both ways: more water but fewer bare soil months", () => {
    // Current: 1400 mm water, 1800 mm bad water, 300 cover days (bare = 26.1)
    // Alt: 1480 mm water (+80 mm), 1800 mm bad water (0 mm), 361 cover days (bare = 24.1 -> -2.0 months)
    const cur = mockOption("current", ["maize", "fallow", "fallow"], 1400, 1800, 300, "C", 2);
    const alt = mockOption("alt1", ["wheat", "wheat", "wheat"], 1480, 1800, 361, "B", 1);
    const pack = mockPack([cur, alt]);

    const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
    expect(res.isCurrentBest).toBe(false);
    expect(res.sentence).toContain("has 2 fewer bare-soil months, but uses 80 mm more water (evidence: grade B).");
  });

  it("handles the tie case ('about the same') when differences are below thresholds", () => {
    // Thresholds: water 25 mm, bad water 25 mm, bare soil 1 month
    const cur = mockOption("current", ["maize", "sorghum", "wheat"], 1500, 2000, 400, "C", 2);
    const alt = mockOption("alt1", ["sorghum", "maize", "wheat"], 1510, 2010, 410, "C", 1);
    const pack = mockPack([cur, alt]);

    const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
    expect(res.isCurrentBest).toBe(false);
    expect(res.sentence).toContain("has about the same water use, bad-year water and bare soil as your current rotation (evidence: grade C).");
  });

  it("handles pure advantages (all pros, no cons)", () => {
    const cur = mockOption("current", ["maize", "maize", "maize"], 1600, 2200, 300, "D", 2);
    const alt = mockOption("alt1", ["sorghum", "sorghum", "sorghum"], 1400, 1900, 391, "B", 1);
    const pack = mockPack([cur, alt]);

    const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
    expect(res.isCurrentBest).toBe(false);
    expect(res.sentence).toContain("uses 200 mm less water and 300 mm less in bad years and has 3 fewer bare-soil months (evidence: grade B).");
  });

  it("updates dynamically when priority sliders move", () => {
    const cur = mockOption("current", ["maize", "maize", "maize"], 1600, 2200, 300, "D", 3);
    const waterSaver = mockOption("alt_water", ["fallow", "sorghum", "fallow"], 1000, 1300, 150, "C", 1);
    const coverMax = mockOption("alt_cover", ["cover_crop", "wheat", "cover_crop"], 1700, 2300, 600, "B", 2);
    const pack = mockPack([cur, waterSaver, coverMax]);

    // Priority 1: High priority on water saving (water: 3, bare: 0)
    const prioWater: Priorities = { water: 3, bare: 0, badYear: 0, erosion: 0, legume: 0, residue: 0 };
    const resWater = generateFieldSummary(pack, prioWater, NO_CONSTRAINTS, null);
    expect(resWater.topAlternative?.option_id).toBe("alt_water");
    expect(resWater.sentence).toContain("uses 600 mm less water");

    // Priority 2: High priority on ground cover (water: 0, bare: 3)
    const prioCover: Priorities = { water: 0, bare: 3, badYear: 0, erosion: 0, legume: 0, residue: 0 };
    const resCover = generateFieldSummary(pack, prioCover, NO_CONSTRAINTS, null);
    expect(resCover.topAlternative?.option_id).toBe("alt_cover");
    expect(resCover.sentence).toContain("has 10 fewer bare-soil months");
  });
});

describe("sentence verification across all real Kansas pilot packs", () => {
  const packsDir = join(import.meta.dirname, "../../packs/ks_t14slh");
  const hasPacks = existsSync(packsDir);

  it.skipIf(!hasPacks)("evaluates all 200 real field packs without NaN, untagged values, or forbidden words", () => {
    const files = readdirSync(packsDir).filter(
      (f) =>
        f.endsWith(".json") &&
        !f.includes(".series.") &&
        !f.includes(".calendar.") &&
        !f.includes(".scenarios.") &&
        !["index.json", "layers.json", "hindcast.json"].includes(f)
    );
    expect(files.length).toBe(200);

    const FORBIDDEN_WORDS = [
      /\byield\b/i,
      /\btonnes?\b/i,
      /\bbushels?\b/i,
      /\bprofit\b/i,
      /\bguarantee[ds]?\b/i,
      /\bcertain(?:ly|ty)?\b/i,
      /\bproven\b/i,
    ];

    for (const file of files) {
      const pack = JSON.parse(readFileSync(join(packsDir, file), "utf8")) as FieldPack;
      const res = generateFieldSummary(pack, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);

      // Sentence integrity
      expect(res.sentence).toBeTruthy();
      expect(res.sentence).not.toContain("NaN");
      expect(res.sentence).not.toContain("undefined");
      expect(res.sentence).not.toContain("null");
      expect(res.sentence.endsWith(").")).toBe(true);
      expect(res.sentence).toMatch(/\(evidence: grade [A-D]\)\.$/);

      // No forbidden claims
      for (const pattern of FORBIDDEN_WORDS) {
        expect(res.sentence).not.toMatch(pattern);
      }

      // Check tokens have valid tags
      for (const tok of res.tokens) {
        if (tok.kind === "tagged") {
          expect(["O", "D", "E", "A"]).toContain(tok.tag);
          expect(tok.source).toBeTruthy();
          expect(typeof tok.value).toBe("number");
          expect(isNaN(tok.value)).toBe(false);
        }
      }
    }
  });
});
