import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { EXPLAINERS, METRIC_EXPLAINER, explainer } from "../src/explainers";

const SRC = join(import.meta.dirname, "../src");

describe("explainers (T9.10)", () => {
  it("each has a title, two or three sentences and a cited source", () => {
    for (const id of EXPLAINERS) {
      const e = explainer(id);
      expect(e.title, id).not.toBe("");
      expect(e.source, id).not.toBe("");
      // Sentence ends: ". " or a final "." (abbreviations like "Eq. 82" and "et al." excluded).
      const sentences = e.body.replace(/\b(Eq|al|Vol)\./g, "$1").split(/\.(?:\s|$)/).filter((s) => s.trim());
      expect(sentences.length, `${id}: ${e.body}`).toBeGreaterThanOrEqual(2);
      expect(sentences.length, `${id}: ${e.body}`).toBeLessThanOrEqual(3);
      expect(e.url === "" || e.url.startsWith("https://"), id).toBe(true);
    }
  });

  it("only external pages have links; project rules have none", () => {
    for (const id of EXPLAINERS) {
      const e = explainer(id);
      if (e.source.startsWith("FieldWitness")) expect(e.url, id).toBe("");
      else expect(e.url, id).not.toBe("");
    }
  });

  it("every explainer is placed somewhere in the app", () => {
    const code = readdirSync(SRC)
      .filter((f) => f.endsWith(".tsx"))
      .map((f) => readFileSync(join(SRC, f), "utf8"))
      .join("\n");
    const mapped = new Set(Object.values(METRIC_EXPLAINER));
    for (const id of EXPLAINERS) {
      expect(mapped.has(id) || code.includes(`"${id}"`), id).toBe(true);
    }
  });
});
