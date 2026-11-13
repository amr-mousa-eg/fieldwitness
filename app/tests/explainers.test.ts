import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { EXPLAINERS, METRIC_EXPLAINER, explainer } from "../src/explainers";
import { getLocale, setLocale } from "../src/strings";

const SRC = join(import.meta.dirname, "../src");

describe("explainers (T9.10)", () => {
  it("each has a title, two or three sentences and a cited source (EN & AR)", () => {
    const prev = getLocale();
    try {
      for (const locale of ["en", "ar"] as const) {
        setLocale(locale);
        for (const id of EXPLAINERS) {
          const e = explainer(id);
          expect(e.title, `${locale}:${id}`).not.toBe("");
          expect(e.source, `${locale}:${id}`).not.toBe("");
          // Sentence ends: ". " or a final "." (abbreviations like "Eq. 82" and "et al." excluded).
          const sentences = e.body.replace(/\b(Eq|al|Vol)\./g, "$1").split(/\.(?:\s|$)/).filter((s) => s.trim());
          expect(sentences.length, `${locale}:${id}: ${e.body}`).toBeGreaterThanOrEqual(2);
          expect(sentences.length, `${locale}:${id}: ${e.body}`).toBeLessThanOrEqual(3);
          expect(e.url === "" || e.url.startsWith("https://"), `${locale}:${id}`).toBe(true);
        }
      }
    } finally {
      setLocale(prev);
    }
  });

  it("only external pages have links; project rules have none (EN & AR)", () => {
    const prev = getLocale();
    try {
      for (const locale of ["en", "ar"] as const) {
        setLocale(locale);
        for (const id of EXPLAINERS) {
          const e = explainer(id);
          if (e.source.startsWith("FieldWitness")) expect(e.url, `${locale}:${id}`).toBe("");
          else expect(e.url, `${locale}:${id}`).not.toBe("");
        }
      }
    } finally {
      setLocale(prev);
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
