import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  HIGH_TIER,
  LOW_TIER,
  fpsStats,
  headsVisible,
  isTooSlow,
  pickQuality,
  plantsPerSide,
  rainDropCount,
  seasonGrowth,
  showIrrigation,
  waterFillFraction,
} from "../src/field3d/growth";
import type { FieldSim3D } from "../src/types";

describe("3D illustration is driven only by pack values", () => {
  it("rain drops: none in a dry week, more with more rain, capped", () => {
    expect(rainDropCount(0, 240)).toBe(0);
    expect(rainDropCount(-1, 240)).toBe(0);
    expect(rainDropCount(0.3, 240)).toBeGreaterThan(0);
    expect(rainDropCount(10, 240)).toBeLessThan(rainDropCount(30, 240));
    expect(rainDropCount(500, 240)).toBe(240);
  });

  it("irrigation lines only when the model applied irrigation", () => {
    expect(showIrrigation(0)).toBe(false);
    expect(showIrrigation(12.5)).toBe(true);
  });

  it("water fill is soil water / TAW, clamped", () => {
    expect(waterFillFraction(50, 100)).toBeCloseTo(0.5);
    expect(waterFillFraction(120, 100)).toBe(1);
    expect(waterFillFraction(10, 0)).toBe(0);
  });

  it("plant height follows the season's highest canopy proxy and never shrinks within a season", () => {
    const crops = ["fallow", "maize", "maize", "maize", "maize", "fallow"];
    const stages = ["fallow", "initial", "development", "mid", "late", "fallow"];
    const canopy = [0, 0.2, 0.6, 1, 0.4, 0];
    expect(seasonGrowth(crops, stages, canopy, 0)).toBe(0);
    expect(seasonGrowth(crops, stages, canopy, 1)).toBeCloseTo(0.2);
    expect(seasonGrowth(crops, stages, canopy, 3)).toBeCloseTo(1);
    expect(seasonGrowth(crops, stages, canopy, 4)).toBeCloseTo(1);
    expect(seasonGrowth(crops, stages, canopy, 5)).toBe(0);
  });

  it("a new season of the same crop restarts growth", () => {
    const crops = ["maize", "maize", "maize", "maize"];
    const stages = ["mid", "late", "initial", "development"];
    const canopy = [1, 0.5, 0.1, 0.3];
    expect(seasonGrowth(crops, stages, canopy, 2)).toBeCloseTo(0.1);
    expect(seasonGrowth(crops, stages, canopy, 3)).toBeCloseTo(0.3);
  });

  it("heads appear from the mid stage, never in fallow", () => {
    expect(headsVisible("maize", "development")).toBe(false);
    expect(headsVisible("maize", "mid")).toBe(true);
    expect(headsVisible("winter_wheat", "late")).toBe(true);
    expect(headsVisible("fallow", "mid")).toBe(false);
  });
});

describe("phone performance caps", () => {
  it("phones and low-core devices get the low tier with dpr ≤ 1.5", () => {
    expect(pickQuality(390, 8)).toBe(LOW_TIER);
    expect(pickQuality(1280, 4)).toBe(LOW_TIER);
    expect(pickQuality(1280, 8)).toBe(HIGH_TIER);
    expect(LOW_TIER.dprCap).toBeLessThanOrEqual(1.5);
  });

  it("instance counts stay under the tier cap and are lower on phones", () => {
    for (const crop of ["maize", "sorghum", "winter_wheat"] as const) {
      for (const tier of [HIGH_TIER, LOW_TIER]) {
        const n = plantsPerSide(crop, tier);
        expect(n * n * 2).toBeLessThanOrEqual(tier.maxPlantInstances);
      }
      expect(plantsPerSide(crop, LOW_TIER)).toBeLessThan(plantsPerSide(crop, HIGH_TIER));
    }
    expect(plantsPerSide("fallow", HIGH_TIER)).toBe(0);
  });

  it("fallback rule: median below 28 fps (30 fps with vsync jitter tolerance)", () => {
    expect(isTooSlow(Array(60).fill(1000 / 20))).toBe(true);
    expect(isTooSlow(Array(60).fill(1000 / 27))).toBe(true);
    expect(isTooSlow(Array(60).fill(1000 / 29.9))).toBe(false);
    expect(isTooSlow(Array(60).fill(1000 / 60))).toBe(false);
    expect(isTooSlow([])).toBe(false);
    const s = fpsStats([...Array(9).fill(1000 / 60), 1000 / 10]);
    expect(s.median).toBeCloseTo(60);
    expect(s.p10).toBeCloseTo(10);
  });
});

const PUBLIC_DIR = join(import.meta.dirname, "../public/packs/ks_t14slh");
describe.skipIf(!existsSync(PUBLIC_DIR))("weather inputs exist in every pack", () => {
  it("rain_mm and irrigation_mm are numeric per week, so rain and irrigation visuals are data-driven", () => {
    const files = readdirSync(PUBLIC_DIR).filter((f) => f.endsWith(".sim3d.json"));
    let irrigatedWeeks = 0;
    for (const f of files.filter((_, i) => i % 10 === 0)) {
      const sim = JSON.parse(readFileSync(join(PUBLIC_DIR, f), "utf8")) as FieldSim3D;
      for (const opt of [sim.current, ...sim.alternatives]) {
        for (const sc of Object.values(opt.scenarios)) {
          expect(sc.rain_mm.length).toBe(156);
          expect(sc.irrigation_mm.length).toBe(156);
          for (let w = 0; w < 156; w++) {
            expect(Number.isFinite(sc.rain_mm[w])).toBe(true);
            expect(Number.isFinite(sc.irrigation_mm[w])).toBe(true);
            if (showIrrigation(sc.irrigation_mm[w])) irrigatedWeeks++;
          }
        }
      }
    }
    expect(irrigatedWeeks).toBeGreaterThan(0);
  });
});
