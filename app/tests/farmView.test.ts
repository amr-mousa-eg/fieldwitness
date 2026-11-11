// Farm view data mapping (src/field3d/farm.ts): every visual state comes from one week's pack
// values or the calendar month; scenery is not data.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DRY_WEEK_MM, isCoverWeek, plotWeek, summerness, weekLook, weekTelemetry } from "../src/field3d/farm";
import { FARM_TEXT } from "../src/field3d/farmText";
import { isHistoryOnly } from "../src/seasons";
import type { FieldSim3D, Sim3DOption, Sim3DScenario } from "../src/types";

const DIR = join(import.meta.dirname, "../public/packs/ks_t14slh");
const hasPacks = existsSync(DIR);
const N = 156;

function synth(crops: string[], stages: string[], over: Partial<Sim3DScenario> = {}, sequence = ["maize", "fallow", "sorghum"]) {
  const option: Sim3DOption = { option_id: "x", sequence, rank: 1, label: "", crops, stages, root_depth_m: Array(N).fill(0), scenarios: {} };
  const scen: Sim3DScenario = {
    soil_water_mm: Array(N).fill(60),
    taw_mm: Array(N).fill(120),
    canopy_cover: Array(N).fill(0),
    ks: Array(N).fill(1),
    rain_mm: Array(N).fill(0),
    irrigation_mm: Array(N).fill(0),
    ...over,
  };
  return { option, scen };
}

describe("farm view: plot state per week", () => {
  it("a crop week: kind, growth from canopy, heads from mid, straw when late, stress = 1 - Ks", () => {
    const crops = Array(N).fill("fallow");
    const stages = Array(N).fill("fallow");
    for (let w = 10; w < 30; w++) {
      crops[w] = "maize";
      stages[w] = w < 15 ? "initial" : w < 22 ? "development" : w < 27 ? "mid" : "late";
    }
    const canopy = Array(N).fill(0).map((_, w) => (w >= 10 && w < 30 ? Math.min(1, (w - 9) / 15) : 0));
    const ks = Array(N).fill(1);
    ks[25] = 0.4;
    const irr = Array(N).fill(0);
    irr[25] = 12;
    const { option, scen } = synth(crops, stages, { canopy_cover: canopy, ks, irrigation_mm: irr });
    const early = plotWeek(option, scen, 12);
    expect(early).toMatchObject({ kind: "maize", heads: false, ripe: false, stress: 0, irrigating: false });
    const mid = plotWeek(option, scen, 25);
    expect(mid).toMatchObject({ kind: "maize", heads: true, ripe: false, irrigating: true });
    expect(mid.stress).toBeCloseTo(0.6);
    expect(mid.growth).toBeCloseTo(canopy[25]);
    expect(plotWeek(option, scen, 28)).toMatchObject({ ripe: true, heads: true });
    expect(plotWeek(option, scen, 5)).toMatchObject({ kind: "bare", growth: 0 });
    expect(plotWeek(option, scen, 5).wetness).toBeCloseTo(0.5); // soil water / TAW
  });

  it("cover crop = run of >= 2 fallow-labelled weeks with canopy > 0; a single such week is a crop boundary", () => {
    const crops = Array(N).fill("fallow");
    const canopy = Array(N).fill(0);
    canopy[40] = 0.1; // lone boundary week
    for (let w = 60; w < 70; w++) canopy[w] = 0.5;
    const { option, scen } = synth(crops, Array(N).fill("fallow"), { canopy_cover: canopy }, ["maize", "cover_crop", "fallow"]);
    expect(isCoverWeek(option, scen, 40)).toBe(false);
    expect(plotWeek(option, scen, 40).kind).toBe("bare");
    expect(plotWeek(option, scen, 65)).toMatchObject({ kind: "cover", growth: 0.5 });
    expect(plotWeek(option, scen, 60).kind).toBe("cover");
  });

  it("history-only season: neutral plot, nothing simulated shown", () => {
    const { option, scen } = synth(Array(N).fill("fallow"), Array(N).fill("fallow"), { irrigation_mm: Array(N).fill(5), ks: Array(N).fill(0.2) }, ["perennial_forage", "sorghum", "sorghum"]);
    expect(plotWeek(option, scen, 10)).toMatchObject({ kind: "not_simulated", historyKey: "perennial_forage", stress: 0, wetness: 0, irrigating: false, growth: 0 });
    expect(plotWeek(option, scen, 60).kind).toBe("bare");
  });
});

describe("farm view: sky and ground from the weekly rain and month", () => {
  it("dry weeks look dry, rainy weeks overcast with rain drops", () => {
    const rain = Array(N).fill(0);
    rain[20] = 30;
    const dry = weekLook(rain, 10, 7, false, 80);
    const wet = weekLook(rain, 20, 7, false, 80);
    expect(dry).toMatchObject({ dryness: 1, wet: 0, rainDrops: 0 });
    expect(wet.wet).toBe(1);
    expect(wet.rainDrops).toBeGreaterThan(0);
    expect(wet.sky).not.toBe(dry.sky);
    expect(dry.grass).not.toBe(weekLook(Array(N).fill(DRY_WEEK_MM + 5), 10, 7, false, 80).grass);
  });

  it("season weight: summer 1, winter 0", () => {
    expect(summerness(7)).toBeGreaterThan(0.95);
    expect(summerness(1)).toBeLessThan(0.05);
    expect(weekLook(Array(N).fill(5), 10, 1, false, 80).grass).not.toBe(weekLook(Array(N).fill(5), 10, 7, false, 80).grass);
  });

  it("labels scenery as not data; no game or yield wording", () => {
    expect(FARM_TEXT.scenery).toContain("Scenery, not data");
    const text = Object.values(FARM_TEXT).join(" ").toLowerCase();
    for (const w of ["points?", "stars?", "coins?", "scores?", "happy", "yields?", "profits?", "level up"])
      expect(text, w).not.toMatch(new RegExp(String.raw`\b${w}\b`));
  });
});

describe.skipIf(!hasPacks)("farm view on the real packs", () => {
  it("plot kinds agree with the pack for every option and week of all 200 fields", () => {
    const files = readdirSync(DIR).filter((f) => f.endsWith(".sim3d.json"));
    expect(files).toHaveLength(200);
    let cover = 0;
    for (const f of files) {
      const s = JSON.parse(readFileSync(join(DIR, f), "utf8")) as FieldSim3D;
      for (const o of [s.current, ...s.alternatives]) {
        for (const [sid, scen] of Object.entries(o.scenarios)) {
          if (sid !== "t+0_p+0" && sid !== "t+0_p-20") continue;
          for (let w = 0; w < N; w++) {
            const p = plotWeek(o, scen, w);
            if (o.crops[w] !== "fallow") expect(p.kind === o.crops[w] || p.kind === "not_simulated").toBe(true);
            if (p.kind === "cover") {
              cover++;
              expect(o.sequence).toContain("cover_crop");
            }
            if (p.kind === "not_simulated") expect(o.sequence.some(isHistoryOnly)).toBe(true);
            expect(p.irrigating).toBe(p.kind !== "not_simulated" && scen.irrigation_mm[w] > 0);
            const tel = weekTelemetry(o, scen, w);
            expect([tel.soilWater, tel.ks, tel.rain, tel.irrigation]).toEqual([scen.soil_water_mm[w], scen.ks[w], scen.rain_mm[w], scen.irrigation_mm[w]]);
          }
        }
      }
    }
    expect(cover).toBeGreaterThan(0);
  }, 120_000);
});
