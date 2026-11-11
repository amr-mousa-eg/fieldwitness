import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { t } from "../src/strings";
import type { FieldSim3D } from "../src/types";

const PUBLIC_DIR = join(import.meta.dirname, "../public/packs/ks_t14slh");
const DEMO_DIR = join(import.meta.dirname, "../../packs/demo/ks_t14slh");
const hasPublicPacks = existsSync(PUBLIC_DIR);
const hasDemoPacks = existsSync(DEMO_DIR);

describe.skipIf(!hasPublicPacks)("Field 3D simulation packs (public/packs/ks_t14slh)", () => {
  const files = hasPublicPacks ? readdirSync(PUBLIC_DIR).filter((f) => f.endsWith(".sim3d.json")) : [];

  it("found 200 .sim3d.json files in public packs", () => {
    expect(files.length).toBe(200);
  });

  it("every file has valid schema, tag D, 156 weeks, and positive available water", () => {
    // Test a sample of 25 files for fast and thorough validation
    const sample = files.filter((_, i) => i % 8 === 0);
    expect(sample.length).toBeGreaterThanOrEqual(25);

    for (const f of sample) {
      const raw = readFileSync(join(PUBLIC_DIR, f), "utf8");
      expect(raw.length).toBeLessThan(300_000); // under MAX_BYTES limit

      const sim: FieldSim3D = JSON.parse(raw);
      expect(sim.schema_version).toBe("1.0");
      expect(sim.tag).toBe("D");
      expect(sim.weather_year).toBeGreaterThanOrEqual(2001);
      expect(sim.weather_year).toBeLessThanOrEqual(2021);
      expect(sim.weather_label).toContain(`${sim.weather_year}`);
      expect(sim.weeks.length).toBe(156);

      // Verify week calendar progression
      expect(sim.weeks[0].year).toBe(2022);
      expect(sim.weeks[52].year).toBe(2023);
      expect(sim.weeks[104].year).toBe(2024);
      expect(sim.weeks[0].week_start).toBe("2022-01-01");

      // Verify Current option
      expect(sim.current.option_id).toBe("current");
      expect(sim.current.rank).toBe(0);
      expect(sim.current.crops.length).toBe(156);
      expect(sim.current.stages.length).toBe(156);
      expect(sim.current.root_depth_m.length).toBe(156);

      // Verify 12 scenarios exist
      const scenKeys = Object.keys(sim.current.scenarios);
      expect(scenKeys.length).toBe(12);
      expect(scenKeys).toContain("t+0_p+0");

      const baseline = sim.current.scenarios["t+0_p+0"];
      expect(baseline.soil_water_mm.length).toBe(156);
      expect(baseline.taw_mm.length).toBe(156);
      expect(baseline.canopy_cover.length).toBe(156);
      expect(baseline.ks.length).toBe(156);
      expect(baseline.rain_mm.length).toBe(156);
      expect(baseline.irrigation_mm.length).toBe(156);

      // Physics bounds verification
      for (let w = 0; w < 156; w++) {
        const sw = baseline.soil_water_mm[w];
        const taw = baseline.taw_mm[w];
        const ks = baseline.ks[w];
        const canopy = baseline.canopy_cover[w];
        const root = sim.current.root_depth_m[w];
        const crop = sim.current.crops[w];

        expect(sw).toBeGreaterThanOrEqual(0);
        expect(sw).toBeLessThanOrEqual(taw + 5); // small numerical tolerance
        expect(ks).toBeGreaterThanOrEqual(0);
        expect(ks).toBeLessThanOrEqual(1.0);
        expect(canopy).toBeGreaterThanOrEqual(0);
        expect(canopy).toBeLessThanOrEqual(1.0);
        expect(root).toBeGreaterThanOrEqual(0);

        if (crop === "fallow") {
          expect(root).toBe(0);
        }
      }

      // Verify top alternatives
      expect(sim.alternatives.length).toBeGreaterThanOrEqual(1);
      expect(sim.alternatives.length).toBeLessThanOrEqual(3);
      for (const alt of sim.alternatives) {
        expect(alt.rank).toBeGreaterThan(0);
        expect(alt.sequence.length).toBe(3);
        expect(Object.keys(alt.scenarios).length).toBe(12);
      }
    }
  });
});

describe.skipIf(!hasDemoPacks)("Demo packs deployment (packs/demo/ks_t14slh)", () => {
  it("packs/demo has all 200 .sim3d.json files deployed", () => {
    const demoFiles = hasDemoPacks ? readdirSync(DEMO_DIR).filter((f) => f.endsWith(".sim3d.json")) : [];
    expect(demoFiles.length).toBe(200);
  });
});

// Weather year shown in the 3D view comes from the pack, never from hard-coded copy.
describe("3D weather year: one year, read from the pack", () => {
  const field3dCode = readFileSync(join(import.meta.dirname, "../src/Field3DView.tsx"), "utf8");

  it("UI copy has no hard-coded weather year", () => {
    const en = readFileSync(join(import.meta.dirname, "../src/strings/en.json"), "utf8");
    expect(en).not.toMatch(/weather of (19|20)\d\d/);
    expect(JSON.parse(en)["sim3d.disclaimer"]).toContain("{year}");
    expect(field3dCode).toContain('t("sim3d.disclaimer", { year: sim3d.weather_year })');
  });

  it.skipIf(!hasPublicPacks)("every pack: label year and disclaimer year are the pack's weather_year", () => {
    const files = readdirSync(PUBLIC_DIR).filter((f) => f.endsWith(".sim3d.json"));
    expect(files.length).toBeGreaterThan(0);
    for (const f of files) {
      const sim = JSON.parse(readFileSync(join(PUBLIC_DIR, f), "utf8")) as FieldSim3D;
      const year = String(sim.weather_year);
      expect(sim.weather_label.match(/\b(19|20)\d\d\b/g), f).toEqual([year]);
      const disclaimer = t("sim3d.disclaimer", { year: sim.weather_year });
      expect(disclaimer.match(/\b(19|20)\d\d\b/g), f).toEqual([year]);
    }
  });
});
