import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { EXPLAINERS, SIM3D_EXPLAINERS, explainer } from "../src/explainers";

const SRC = join(import.meta.dirname, "../src");
const field3dCode = readFileSync(join(SRC, "Field3DView.tsx"), "utf8");
const methodsCode = readFileSync(join(SRC, "MethodsPage.tsx"), "utf8");

describe("3D Simulation Explainers & Technical Glossary (Phase 12, Item 8)", () => {
  it("includes all 6 required 3D simulation notes in SIM3D_EXPLAINERS", () => {
    const required3D = [
      "root_zone_soil_water",
      "available_water_capacity",
      "water_stress_ks",
      "canopy_proxy",
      "evapotranspiration",
      "fallow_bare_soil",
    ];
    for (const term of required3D) {
      expect(SIM3D_EXPLAINERS).toContain(term);
    }
  });

  it("ensures every 3D note has 2-3 plain sentences and cites FAO-56 or NASA", () => {
    for (const id of SIM3D_EXPLAINERS) {
      const e = explainer(id);
      expect(e.title, id).not.toBe("");
      const sentences = e.body.replace(/\b(Eq|al|Vol)\./g, "$1").split(/\.(?:\s|$)/).filter((s) => s.trim());
      expect(sentences.length, `${id} sentence count: ${sentences.length}`).toBeGreaterThanOrEqual(2);
      expect(sentences.length, `${id} sentence count: ${sentences.length}`).toBeLessThanOrEqual(3);
      expect(e.source).toMatch(/FAO|NASA/);
      expect(e.url).toMatch(/^https:\/\/(www\.fao\.org|science\.nasa\.gov|smap\.jpl\.nasa\.gov)/);
    }
  });

  it("verifies canopy proxy matches model definition (Kc/Kc max, not photo measurement, no yield/profit)", () => {
    const cp = explainer("canopy_proxy");
    expect(cp.body).toContain("Kc");
    expect(cp.body).toContain("not a direct satellite photo measurement");
    expect(cp.body.toLowerCase()).not.toMatch(/\b(yield|profit|forecast)\b/);
  });

  it("verifies all required technical terms exist in EXPLAINERS glossary list", () => {
    const requiredGlossary = [
      "root_zone_soil_water",
      "available_water_capacity",
      "water_stress_ks",
      "canopy_proxy",
      "evapotranspiration",
      "fallow_bare_soil",
      "evidence_grade",
      "source_tags",
      "hindcast",
      "crps",
      "credibility",
      "witness",
      "bare_soil_months",
      "bad_year_water",
    ];
    for (const term of requiredGlossary) {
      expect(EXPLAINERS).toContain(term);
    }
  });

  it("links every 3D note to its technical glossary entry", () => {
    expect(field3dCode).toContain("sim3d-guide");
    expect(field3dCode).toContain("sim3d-guide-glossary-link");
    expect(field3dCode).toContain("methods#glossary-");
    expect(methodsCode).toContain('id="glossary"');
    expect(methodsCode).toContain("glossary-entry");
    expect(methodsCode).toContain("glossary-${id}");
  });
});
