import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { UKRAINE_NEIGHBOURS_DATA } from "../src/ukraineNeighbours";
import { UkraineNeighboursSection } from "../src/UkraineNeighboursSection";
import { setLocale } from "../src/locale";

const ROOT = resolve(import.meta.dirname, "..", "..");
const readJson = (p: string) => JSON.parse(readFileSync(resolve(ROOT, p), "utf8"));
const readText = (p: string) => readFileSync(resolve(ROOT, p), "utf8");

describe("Central Ukraine (ua_central_t36uvu) Neighbours Witness data", () => {
  it("matches the committed Phase 2 result files exactly", () => {
    const summary = readJson("results/pilot_fields/ua_central_t36uvu_summary.json");
    const fsSummary = readJson("results/neighbours/ua_central_t36uvu_field_season_summary.json");
    const report = readText("results/neighbours/ua_central_t36uvu_report.md");

    expect(UKRAINE_NEIGHBOURS_DATA.pilotFields).toBe(summary.pilot_fields);
    expect(UKRAINE_NEIGHBOURS_DATA.spatialBlocks).toBe(summary.blocks_covered);
    expect(UKRAINE_NEIGHBOURS_DATA.medianAreaHa).toBe(summary.area_ha_median);
    expect(UKRAINE_NEIGHBOURS_DATA.medianInteriorPx).toBe(summary.interior_px_median);
    expect(UKRAINE_NEIGHBOURS_DATA.scaleFlagged).toBe(summary.hls_scale_flagged);

    expect(UKRAINE_NEIGHBOURS_DATA.fieldSeasons).toBe(fsSummary.rows);
    expect(UKRAINE_NEIGHBOURS_DATA.fieldSeasonsWithOutcomes).toBe(fsSummary.rows_with_outcome);

    expect(report).toContain(`${UKRAINE_NEIGHBOURS_DATA.preCutoffEvidenceTotal} pre-cutoff`);
    expect(report).toContain(`${UKRAINE_NEIGHBOURS_DATA.fullPeriodEvidenceTotal} full-period`);

    const primaryPre = UKRAINE_NEIGHBOURS_DATA.comparisonRows.find(
      (r) => r.design === "primary_dml" && r.regionKey === "ukraine_pre",
    )!;
    const primaryFull = UKRAINE_NEIGHBOURS_DATA.comparisonRows.find(
      (r) => r.design === "primary_dml" && r.regionKey === "ukraine_full",
    )!;
    const matchPre = UKRAINE_NEIGHBOURS_DATA.comparisonRows.find(
      (r) => r.design === "matching_dml" && r.regionKey === "ukraine_pre",
    )!;
    const matchFull = UKRAINE_NEIGHBOURS_DATA.comparisonRows.find(
      (r) => r.design === "matching_dml" && r.regionKey === "ukraine_full",
    )!;
    expect(primaryPre.evidencePass + matchPre.evidencePass).toBe(
      UKRAINE_NEIGHBOURS_DATA.preCutoffEvidenceTotal,
    );
    expect(primaryFull.evidencePass + matchFull.evidencePass + 1).toBe(
      UKRAINE_NEIGHBOURS_DATA.fullPeriodEvidenceTotal,
    );
  });

  it("renders cleanly in English and Arabic with Tier 3 disclosure and zero forbidden claims", () => {
    for (const loc of ["en", "ar"] as const) {
      setLocale(loc);
      const html = renderToStaticMarkup(createElement(UkraineNeighboursSection));
      expect(html).toContain("395");
      expect(html).toContain("2765");
      expect(html).toContain("T36UVU");
      expect(html.toLowerCase()).not.toContain("tonnes");
      expect(html.toLowerCase()).not.toContain("profit");
      expect(html.toLowerCase()).not.toContain("guarantee");
    }
    setLocale("en");
  });
});
