import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { DIAGRAM_BOXES, DIAGRAM_SOURCES, DIAGRAM_STAGES, MethodsDiagram } from "../src/MethodsDiagram";
import { EXPLAINERS } from "../src/explainers";
import en from "../src/strings/en.json";

const SRC = join(import.meta.dirname, "../src");
const diagramSource = readFileSync(join(SRC, "MethodsDiagram.tsx"), "utf8");
const methodsSource = readFileSync(join(SRC, "MethodsPage.tsx"), "utf8");
const css = readFileSync(join(SRC, "styles.css"), "utf8");
const strings = en as Record<string, string>;

/** The official source list: DATASETS in MethodsPage.tsx (the Methods data table). */
const DATASETS = /DATASETS = \[([^\]]+)\]/
  .exec(methodsSource)![1]
  .match(/"(\w+)"/g)!
  .map((s) => s.slice(1, -1));

const FORBIDDEN_WORDS = ["guarantee", "will increase", "yield", "profit", "similar soils"];

const boxText = (id: string) => {
  const b = DIAGRAM_BOXES.find((x) => x.id === id);
  expect(b, id).toBeDefined();
  return [b!.label, ...b!.lines, ...(b!.sources ?? []).map((s) => s.name)].join(" ");
};

let html = "";
beforeAll(() => {
  // node test environment: useRoute only reads window.location.hash during render
  (globalThis as { window?: unknown }).window = {
    location: { hash: "#/kansas/methods" },
    addEventListener() {},
    removeEventListener() {},
  };
  html = renderToStaticMarkup(createElement(MethodsDiagram));
});

describe("Methods Diagram (Phase 12, Item 9)", () => {
  it("has four numbered stages in reading order", () => {
    expect(DIAGRAM_STAGES.map((s) => [s.step, s.id, s.title])).toEqual([
      [1, "observe", "What we observe"],
      [2, "model", "What we model"],
      [3, "check", "What we check"],
      [4, "get", "What you get"],
    ]);
    let last = -1;
    for (const s of DIAGRAM_STAGES) {
      const at = html.indexOf(`id="stage-${s.id}"`);
      expect(at, s.id).toBeGreaterThan(last);
      last = at;
    }
    // one arrow between each pair of stages
    expect(html.match(/class="mdia-arrow"/g)).toHaveLength(3);
  });

  it("puts the boxes in the right stages", () => {
    const byStage = Object.fromEntries(DIAGRAM_STAGES.map((s) => [s.id, s.boxes.map((b) => b.id)]));
    expect(byStage).toEqual({
      observe: ["data"],
      model: ["field_story", "w1_physics", "w2_past", "w3_neighbours"],
      check: ["agreement", "hindcast_check"],
      get: ["rotation_rank"],
    });
  });

  it("lists the data sources it uses, all from the official source list", () => {
    const names = DIAGRAM_SOURCES.map((s) => s.name).join(" | ");
    for (const n of ["HLS", "GIBS", "NASA POWER", "SMAP", "GRACE", "NASADEM", "SoilGrids", "CSB"]) {
      expect(names).toContain(n);
    }
    for (const s of DIAGRAM_SOURCES) {
      expect(DATASETS, s.name).toContain(s.dataset);
      expect(html).toContain(`<li>${s.name}</li>`);
    }
    // every dataset name in the diagram also appears in the Methods data table text
    const table = DATASETS.map((d) => strings[`methods.ds.${d}.name`] + " " + strings[`methods.ds.${d}.use`]).join(" ");
    for (const n of ["HLS", "GIBS", "POWER", "SMAP", "GRACE", "NASADEM", "SoilGrids", "Crop Sequence Boundaries"]) {
      expect(table).toContain(n);
    }
  });

  it("keeps the honest facts from the Methods page", () => {
    expect(boxText("field_story")).toContain("78.3%");
    expect(strings["methods.limits.3"]).toContain("78.3 %");
    expect(boxText("agreement")).toContain("Capped at B");
    expect(strings["methods.limits.4"]).toContain("top out at B");
    expect(boxText("w3_neighbours")).toContain("No neighbour contrast passed the diagnostic checks (0 of 32)");
    expect(strings["methods.limits.4"]).toContain("0 of 32");
    const hindcast = boxText("hindcast_check");
    expect(hindcast).toContain("Weak skill");
    expect(hindcast).toContain("underdispersed CIs");
    expect(hindcast).toContain("Beats baselines B1/B2 overall");
    expect(hindcast).toContain("31 Dec 2021");
    expect(boxText("w1_physics")).toContain("FAO-56");
    expect(boxText("w2_past")).toContain("credibility score");
  });

  it("shows Witness 3 as OFF without relying on colour alone", () => {
    const w3 = DIAGRAM_BOXES.find((b) => b.id === "w3_neighbours")!;
    expect(w3.status).toBe("OFF");
    expect(DIAGRAM_BOXES.filter((b) => b.status === "OFF").map((b) => b.id)).toEqual(["w3_neighbours"]);
    const box = /<a id="box-w3_neighbours"[^>]*>/.exec(html)![0];
    expect(box).toContain("mdia-box--off");
    expect(html).toMatch(/<span class="mdia-status mdia-status--off">OFF<\/span>/);
    // dashed border + hatch pattern in the stylesheet
    const rule = /\.mdia-box--off \{([^}]+)\}/.exec(css)![1];
    expect(rule).toContain("border-style: dashed");
    expect(rule).toContain("repeating-linear-gradient");
  });

  it("makes every box a link to an element that exists on the Methods page", () => {
    for (const b of DIAGRAM_BOXES) {
      expect(html, b.id).toContain(`<a id="box-${b.id}" href="#/kansas/methods#${b.target}"`);
      if (b.target.startsWith("glossary-")) {
        expect(EXPLAINERS as readonly string[], b.id).toContain(b.target.slice("glossary-".length));
        expect(methodsSource).toContain("id={`glossary-${id}`}");
      } else {
        expect(methodsSource, b.id).toContain(`id="${b.target}"`);
      }
    }
    expect(css).toMatch(/\.mdia-box:focus-visible \{[^}]*var\(--focus\)/);
  });

  it("has a vertical phone layout and readable text sizes", () => {
    const phone = /@media \(max-width: 52rem\) \{\s*\.mdia-stages \{([^}]+)\}/.exec(css);
    expect(phone).not.toBeNull();
    expect(phone![1]).toContain("grid-template-columns: minmax(0, 1fr)");
    // no font size below 0.875rem (14 px) in the diagram rules
    const block = css.slice(css.indexOf("/* Methods diagram (Item 9"), css.indexOf("@media (max-width: 52rem)"));
    for (const m of block.matchAll(/font-size: ([\d.]+)rem/g)) expect(Number(m[1])).toBeGreaterThanOrEqual(0.875);
  });

  it("has a caption and an ordered list as its text structure", () => {
    expect(html).toMatch(/^<figure class="mdia" aria-labelledby="methods-diagram-caption">/);
    expect(html).toContain('<figcaption id="methods-diagram-caption"');
    expect(html).toContain('<ol class="mdia-stages">');
    expect(html).toContain('<span class="sr-only">Step 1: </span>');
  });

  it("uses theme tokens and contains zero hardcoded colours", () => {
    expect(diagramSource).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
    const block = css.slice(css.indexOf("/* Methods diagram (Item 9"), css.indexOf(".sr-only {", css.indexOf("/* Methods diagram (Item 9")));
    expect(block).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
    for (const token of ["--panel", "--rule", "--ink", "--muted", "--focus", "--accent"]) expect(block).toContain(`var(${token})`);
  });

  it("contains zero forbidden words across all diagram labels", () => {
    for (const b of DIAGRAM_BOXES) {
      const text = boxText(b.id).toLowerCase();
      for (const forbidden of FORBIDDEN_WORDS) expect(text, b.id).not.toContain(forbidden);
    }
  });
});
