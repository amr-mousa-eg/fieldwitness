import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  type Priorities,
  DEFAULT_PRIORITIES,
  PRIORITY_KEYS,
  rankOptions,
  NO_CONSTRAINTS,
  scores,
} from "../src/rank";
import {
  computeOptionBreakdown,
  explainTopRanking,
} from "../src/rankingExplainer";
import { RANKING_EXPLAINER_CONFIG } from "../src/rankingExplainerConfig";
import type { FieldPack } from "../src/types";

const FORBIDDEN_WORDS = ["guarantee", "will increase", "yield", "profit", "similar soils"];

describe("Ranking Explainer (Phase 12, Item 7)", () => {
  const packsDir = path.resolve(__dirname, "../public/packs/ks_t14slh");
  const packFiles = fs
    .readdirSync(packsDir)
    .filter((f) => /^[0-9a-f]{40}\.json$/.test(f))
    .sort();

  it(`finds exactly 200 real Kansas pilot packs (found ${packFiles.length})`, () => {
    expect(packFiles.length).toBe(200);
  });

  it("proves sum of contributions equals ranking score for all 200 packs and ALL alternatives", () => {
    const testPriorities: Priorities[] = [
      DEFAULT_PRIORITIES,
      { water: 3, bare: 1, badYear: 2, erosion: 0, legume: 2, residue: 1 },
      { water: 0, bare: 3, badYear: 3, erosion: 1, legume: 0, residue: 2 },
      { water: 1, bare: 1, badYear: 1, erosion: 1, legume: 1, residue: 1 },
    ];

    let totalOptionsEvaluated = 0;

    for (const file of packFiles) {
      const pack: FieldPack = JSON.parse(
        fs.readFileSync(path.join(packsDir, file), "utf-8")
      );
      const rows = pack.options.map((o) => ({ option: o, metrics: o.metrics }));

      for (const p of testPriorities) {
        const scoreMap = scores(
          rows.map((r) => ({ id: r.option.option_id, metrics: r.metrics })),
          p
        );

        for (const row of rows) {
          totalOptionsEvaluated++;
          const breakdown = computeOptionBreakdown(row, rows, p);
          const sumContributions = breakdown.contributions.reduce(
            (acc, c) => acc + c.contribution,
            0
          );

          // 1. Sum of contributions matches breakdown totalScore
          expect(Math.abs(sumContributions - breakdown.totalScore)).toBeLessThan(1e-7);

          // 2. Breakdown totalScore matches exact rank.ts scores output
          const expectedScore = scoreMap.get(row.option.option_id) ?? 0;
          expect(Math.abs(breakdown.totalScore - expectedScore)).toBeLessThan(1e-7);

          // 3. Every contribution is non-negative and <= 1
          for (const c of breakdown.contributions) {
            expect(c.contribution).toBeGreaterThanOrEqual(0);
            expect(c.contribution).toBeLessThanOrEqual(1.0001);
            expect(c.scaledValue).toBeGreaterThanOrEqual(0);
            expect(c.scaledValue).toBeLessThanOrEqual(1.0001);
          }
        }
      }
    }

    expect(totalOptionsEvaluated).toBeGreaterThan(1000);
  });

  it("enforces dominant threshold rule (>= 40% vs several criteria contribute similarly)", () => {
    // 1. Controlled synthetic test: 3 equal criteria (33.3% each < 40%) -> similar branch
    const optA: Option = {
      option_id: "opt_a",
      crops: ["corn"],
      sequence: ["corn"],
      grade: "B",
      metrics: {
        water_use_mm: { value: 300, unit: "mm", tag: "D" },
        cover_days: { value: 200, unit: "days", tag: "D" },
        erosion_exposure: { value: 1.0, unit: "t/ha", tag: "D" },
      },
    };
    const optB: Option = {
      option_id: "opt_b",
      crops: ["soy"],
      sequence: ["soy"],
      grade: "B",
      metrics: {
        water_use_mm: { value: 400, unit: "mm", tag: "D" },
        cover_days: { value: 100, unit: "days", tag: "D" },
        erosion_exposure: { value: 2.0, unit: "t/ha", tag: "D" },
      },
    };

    const triPriorities: Priorities = {
      water: 2,
      bare: 2,
      erosion: 2,
      badYear: 0,
      legume: 0,
      residue: 0,
    };
    const rankedEqual = rankOptions([optA, optB], triPriorities, NO_CONSTRAINTS, null);
    const explEqual = explainTopRanking(rankedEqual, triPriorities);

    expect(explEqual).not.toBeNull();
    expect(explEqual?.next).toBeDefined();
    expect(explEqual?.dominantShare).toBeCloseTo(1 / 3, 2);
    expect(explEqual?.dominantShare).toBeLessThan(RANKING_EXPLAINER_CONFIG.dominantContributionShare);
    expect(explEqual?.sentence).toContain("Several criteria contribute similarly to this option's top ranking over");

    // 2. Controlled synthetic test: 1 dominant criterion (100% >= 40%) -> dominant branch
    const singlePriorities: Priorities = {
      water: 3,
      bare: 0,
      erosion: 0,
      badYear: 0,
      legume: 0,
      residue: 0,
    };
    const rankedDominant = rankOptions([optA, optB], singlePriorities, NO_CONSTRAINTS, null);
    const explDominant = explainTopRanking(rankedDominant, singlePriorities);

    expect(explDominant).not.toBeNull();
    expect(explDominant?.next).toBeDefined();
    expect(explDominant?.dominantShare).toBe(1.0);
    expect(explDominant?.dominantShare).toBeGreaterThanOrEqual(RANKING_EXPLAINER_CONFIG.dominantContributionShare);
    expect(explDominant?.sentence).toContain("mainly because");
    expect(explDominant?.sentence).toContain("Use less water");
    expect(explDominant?.sentence).toContain("100% of the score difference vs");

    // 3. Scan real packs to verify consistency of sentence branch with dominantShare threshold
    for (const file of packFiles.slice(0, 50)) {
      const pack: FieldPack = JSON.parse(
        fs.readFileSync(path.join(packsDir, file), "utf-8")
      );
      const ranked = rankOptions(pack.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
      const expl = explainTopRanking(ranked, DEFAULT_PRIORITIES);

      if (expl && expl.next && expl.scoreDiff >= 0.001) {
        if (expl.dominantShare != null && expl.dominantShare >= RANKING_EXPLAINER_CONFIG.dominantContributionShare) {
          expect(expl.sentence).toContain("mainly because");
          expect(expl.sentence).toContain("% of the score difference vs");
        } else if (expl.dominantShare != null) {
          expect(expl.sentence).toContain("Several criteria contribute similarly");
        }
      }
    }
  });

  it("verifies zero forbidden words in all explainer sentences across all 200 packs", () => {
    for (const file of packFiles) {
      const pack: FieldPack = JSON.parse(
        fs.readFileSync(path.join(packsDir, file), "utf-8")
      );
      const ranked = rankOptions(pack.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS, null);
      const explanation = explainTopRanking(ranked, DEFAULT_PRIORITIES);

      if (explanation) {
        const sentence = explanation.sentence.toLowerCase();
        for (const forbidden of FORBIDDEN_WORDS) {
          expect(sentence).not.toContain(forbidden);
        }
      }
    }
  });
});
