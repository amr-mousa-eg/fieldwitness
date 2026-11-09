import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import en from "../src/strings/en.json";

const SRC = join(import.meta.dirname, "../src");
const strings = en as Record<string, string>;
const methods = readFileSync(join(SRC, "MethodsPage.tsx"), "utf8");

describe("Methods & data page (T9.6)", () => {
  it("has name, use and licence for every dataset", () => {
    const ids = /DATASETS = \[([^\]]+)\]/.exec(methods)![1].match(/"(\w+)"/g)!.map((s) => s.slice(1, -1));
    expect(ids.length).toBeGreaterThan(5);
    for (const id of ids) {
      for (const part of ["name", "use", "licence"]) expect(strings[`methods.ds.${id}.${part}`], `${id}.${part}`).toBeTruthy();
    }
  });

  it("has every numbered list item it renders", () => {
    for (const [prefix, n] of [...methods.matchAll(/list\("([\w.]+)", (\d+)\)/g)].map((m) => [m[1], Number(m[2])] as const)) {
      for (let i = 1; i <= n; i++) expect(strings[`${prefix}.${i}`], `${prefix}.${i}`).toBeTruthy();
    }
  });

  it("shows the fixed line on the Field Card and the Methods page", () => {
    for (const f of ["MethodsPage.tsx", "FieldCard.tsx"]) {
      expect(readFileSync(join(SRC, f), "utf8")).toContain('t("fixed.judgment")');
    }
    expect(strings["fixed.judgment"]).toBe(
      "FieldWitness helps you explore options. It does not replace your judgment or local agricultural advice.",
    );
  });

  it("includes all post-freeze roadmap items on Methods page", () => {
    expect(strings["methods.roadmap.future.1"]).toContain("Arabic");
    expect(strings["methods.roadmap.future.2"]).toContain("Compare two fields");
    expect(strings["methods.roadmap.future.3"]).toMatch(/SMAP.*GPM/);
    expect(strings["methods.roadmap.future.4"]).toMatch(/ECOSTRESS.*WIMAS/);
    expect(strings["methods.roadmap.future.5"]).toContain("tile-by-tile");
  });
});
