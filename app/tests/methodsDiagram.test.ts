import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DIAGRAM_BOXES } from "../src/MethodsDiagram";

const SRC = join(import.meta.dirname, "../src");
const diagramSource = readFileSync(join(SRC, "MethodsDiagram.tsx"), "utf8");

const FORBIDDEN_WORDS = ["guarantee", "will increase", "yield", "profit", "similar soils"];

describe("Methods Diagram (Phase 12, Item 9)", () => {
  it("defines all required architectural boxes against the official source list", () => {
    expect(DIAGRAM_BOXES.length).toBe(15);

    const ids = DIAGRAM_BOXES.map((b) => b.id);
    expect(ids).toContain("ds_hls");
    expect(ids).toContain("ds_power");
    expect(ids).toContain("ds_smap");
    expect(ids).toContain("ds_grace");
    expect(ids).toContain("ds_nasadem");
    expect(ids).toContain("ds_gibs");
    expect(ids).toContain("ds_soilgrids");
    expect(ids).toContain("ds_csb");
    expect(ids).toContain("field_story");
    expect(ids).toContain("w1_physics");
    expect(ids).toContain("w2_past");
    expect(ids).toContain("w3_neighbours");
    expect(ids).toContain("agreement");
    expect(ids).toContain("rotation_rank");
    expect(ids).toContain("hindcast_check");
  });

  it("labels Witness 3 as OFF with diagnostic failure notice", () => {
    const w3 = DIAGRAM_BOXES.find((b) => b.id === "w3_neighbours");
    expect(w3).toBeDefined();
    expect(w3?.status).toBe("OFF");
    expect(w3?.sublabel).toBe("OFF: no neighbour contrast passed the diagnostic checks (0 of 32)");
  });

  it("states honest hindcast results in the hindcast box", () => {
    const hindcast = DIAGRAM_BOXES.find((b) => b.id === "hindcast_check");
    expect(hindcast).toBeDefined();
    expect(hindcast?.label).toBe("Hindcast Check");
    expect(hindcast?.sublabel).toContain("Weak skill");
    expect(hindcast?.sublabel).toContain("underdispersed CIs");
    expect(hindcast?.sublabel).toContain("beats B1/B2 overall");
  });

  it("implements responsive SVG structure with accessibility metadata and text alternative", () => {
    expect(diagramSource).toContain('<figure className="methods-diagram-wrap"');
    expect(diagramSource).toContain('viewBox="0 0 840 510"');
    expect(diagramSource).toContain('role="img"');
    expect(diagramSource).toContain('<title id="diagram-title">');
    expect(diagramSource).toContain('<desc id="diagram-desc">');
    expect(diagramSource).toContain('<ol className="sr-only">');

    // Every box in DIAGRAM_BOXES must have a matching SVG group
    for (const box of DIAGRAM_BOXES) {
      expect(diagramSource).toContain(`id="box-${box.id}"`);
    }
  });

  it("uses theme tokens and contains zero hardcoded hex colors", () => {
    expect(diagramSource).toContain("var(--rule)");
    expect(diagramSource).toContain("var(--muted)");
    expect(diagramSource).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });

  it("contains zero forbidden words across all diagram labels", () => {
    for (const box of DIAGRAM_BOXES) {
      const text = `${box.label} ${box.sublabel ?? ""}`.toLowerCase();
      for (const forbidden of FORBIDDEN_WORDS) {
        expect(text).not.toContain(forbidden);
      }
    }
  });
});
