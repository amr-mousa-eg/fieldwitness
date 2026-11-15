import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CQR_EVALUATION } from "../src/cqrEvaluation";
import { FieldList } from "../src/FieldList";
import { mapAttributionText } from "../src/MapView";
import { MethodsPage } from "../src/MethodsPage";
import { PrintDossier } from "../src/PrintDossier";
import { CqrScoreSection, RegionGradeSummary } from "../src/Scoreboard";
import { UkraineNeighboursSection } from "../src/UkraineNeighboursSection";
import { getLocale, setLocale, t } from "../src/strings";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { FieldPack, FieldSummary, Option, RegionIndex } from "../src/types";

const CSS_PATH = resolve(import.meta.dirname, "..", "src", "styles.css");

function makeSummaries(n: number, grades: FieldSummary["top_grade"][] = ["A", "B", "C", "D"]): FieldSummary[] {
  return Array.from({ length: n }, (_, i) => ({
    field_id: `field_${String(i).padStart(4, "0")}_aaaaaaaaaaaaaaaaaaaaaaaa`,
    geometry_wkt: "POLYGON ((31.9 48.0, 31.91 48.0, 31.91 48.01, 31.9 48.01, 31.9 48.0))",
    area_ha: 25 + i,
    current_sequence: ["winter_wheat", "maize", "fallow"],
    top_option_id: "opt_1",
    top_grade: grades[i % grades.length],
  }));
}

function makePack(regionId: string, withNeighbours: boolean): FieldPack {
  const tagD = (value: number, unit: string) => ({ value, unit, tag: "D" as const, source: "FAO-56" });
  const opt1: Option = {
    option_id: "opt_1",
    sequence: ["winter_wheat", "maize", "cover_crop"],
    metrics: {
      water_use_mm: tagD(510, "mm"),
      bad_year_water_mm: tagD(470, "mm"),
      bare_soil_months: tagD(4, "months"),
      cover_days: tagD(600, "days"),
      erosion_exposure: tagD(0.2, "0-1"),
      legume_share: tagD(0, "0-1"),
      family_breaks: tagD(2, "count"),
      ryi: tagD(0.62, "0-1"),
    },
    witnesses: withNeighbours
      ? [
          {
            witness: "neighbours",
            metric: "cover_days",
            estimate: tagD(28, "days"),
            n: 193,
            diagnostics: {},
          },
        ]
      : [],
    grade: withNeighbours ? "A" : "B",
    grade_reasons: [],
    regret: tagD(0.02, "RYI regret"),
    rank: 1,
    explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
  };
  return {
    schema_version: "1.2",
    field: {
      field_id: "6527d4af27e3e639ee45d1c89dad1a5f800cb6d5",
      geometry_wkt: "POLYGON ((31.9 48.0, 31.91 48.0, 31.91 48.01, 31.9 48.01, 31.9 48.0))",
      area_ha: 44.2,
      region_id: regionId,
      tier: regionId === "ks_t14slh" ? 1 : 3,
      boundary_source: regionId === "ks_t14slh" ? "CSB" : "FTW",
      scale_flags: { hls: false },
      interior_pixels: 350,
    },
    story: [],
    credibility: tagD(0.75, "0-1"),
    options: [opt1],
    advice: {
      measure_next: "Verify local profile TAW",
      flip_probability: { value: null, unit: "probability", tag: "A", source: "not yet computed" },
      counterfactual_flip: "Local soil TAW measurement",
    },
    ledger: [],
    data_as_of: "2024-12-31",
    generated_at: "2024-12-31T00:00:00Z",
  };
}

const unescapeHtml = (s: string) =>
  s.replaceAll("&amp;", "&").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&#x27;", "'").replaceAll("&quot;", '"');

describe("styles.css design tokens", () => {
  it("defines every var(--...) referenced in styles.css under :root and dark theme", () => {
    const css = readFileSync(CSS_PATH, "utf8");
    const definedRoot = new Set<string>();
    for (const m of css.matchAll(/(?:^|[;{]\s*)(--[a-zA-Z0-9-]+)\s*:/gm)) {
      definedRoot.add(m[1]);
    }
    const definedDark = new Set<string>();
    for (const block of css.matchAll(/:root\[data-theme="dark"\]\s*\{([\s\S]*?)\}/g)) {
      for (const m of block[1].matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)) {
        definedDark.add(m[1]);
      }
    }

    const used = new Set<string>();
    for (const m of css.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)\s*(?:,|\))/g)) {
      const hasFallback = css.includes(`var(${m[1]},`);
      if (!hasFallback) used.add(m[1]);
    }

    for (const token of used) {
      expect(definedRoot.has(token), `Missing ${token} in :root`).toBe(true);
    }
    for (const required of ["--grade-fg", "--shade", "--surface-tint", "--surface-raised", "--data-highlight", "--data-pos", "--data-neg"]) {
      expect(definedRoot.has(required), `Missing ${required} in :root`).toBe(true);
      expect(definedDark.has(required), `Missing ${required} in [data-theme="dark"]`).toBe(true);
    }
  });
});

describe("FieldList grade filter & pagination", () => {
  it("renders A/B/C/D filter buttons with counts and Show-all button when > 25 fields", () => {
    const index: RegionIndex = {
      schema_version: "1.2",
      region_id: "ua_central_t36uvu",
      name: "Central Ukraine (T36UVU)",
      tier: 3,
      bbox_lonlat: [31.8, 47.9, 32.1, 48.1],
      basemap: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/2023-08-15/GoogleMapsCompatible_Level12/{z}/{y}/{x}.png",
      fields: makeSummaries(32, ["A", "B", "C", "B"]),
      data_as_of: "2024-12-31",
    };

    const html = renderToStaticMarkup(createElement(FieldList, { index, selectedId: null }));
    expect(html).toContain("grade-filter-bar");
    expect(html).toContain(t("fields.filterAll"));
    expect(html).toContain(t("fields.showAll", { n: 32 }));
    expect(html).toContain('class="grade-dot grade-dot-A"');
  });
});

describe("Scoreboard RegionGradeSummary & UkraineNeighboursSection", () => {
  it("displays honest Kansas vs Ukraine grade-distribution summaries and active Ukraine section", () => {
    const ksIndex: RegionIndex = {
      schema_version: "1.0",
      region_id: "ks_t14slh",
      name: "Kansas High Plains (SW Kansas)",
      tier: 1,
      bbox_lonlat: [-101.5, 39.0, -100.5, 40.0],
      basemap: null,
      fields: makeSummaries(8, ["B", "C", "D", "B"]),
      data_as_of: "2024-12-31",
    };
    const uaIndex: RegionIndex = {
      schema_version: "1.2",
      region_id: "ua_central_t36uvu",
      name: "Central Ukraine (T36UVU)",
      tier: 3,
      bbox_lonlat: [31.8, 47.9, 32.1, 48.1],
      basemap: null,
      fields: makeSummaries(8, ["A", "B", "C", "B"]),
      data_as_of: "2024-12-31",
    };

    const ksHtml = unescapeHtml(renderToStaticMarkup(createElement(RegionGradeSummary, { index: ksIndex })));
    const uaHtml = unescapeHtml(renderToStaticMarkup(createElement(RegionGradeSummary, { index: uaIndex })));
    const uaNbHtml = unescapeHtml(renderToStaticMarkup(createElement(UkraineNeighboursSection)));

    expect(ksHtml).toContain(t("score.gradeDist.kansasNote"));
    expect(uaHtml).toContain(t("score.gradeDist.ukraineNote"));
    expect(uaNbHtml).toContain("m-ukraine");
  });
});

describe("PrintDossier & MapView region awareness", () => {
  it("renders active Neighbours badge and SoilGrids profile for Ukraine, and OFF + SSURGO for Kansas", () => {
    const prev = getLocale();
    try {
      setLocale("en");
      const uaHtml = unescapeHtml(
        renderToStaticMarkup(
          createElement(PrintDossier, {
            pack: makePack("ua_central_t36uvu", true),
            regionId: "ua_central_t36uvu",
          }),
        ),
      );
      expect(uaHtml).toContain("Central Ukraine (T36UVU)");
      expect(uaHtml).toContain(t("print.w3NoteUaActive"));
      expect(uaHtml).toContain(t("print.soilCtxValUa"));

      const ksHtml = unescapeHtml(
        renderToStaticMarkup(
          createElement(PrintDossier, {
            pack: makePack("ks_t14slh", false),
            regionId: "ks_t14slh",
          }),
        ),
      );
      expect(ksHtml).toContain(t("print.badgeOff"));
      expect(ksHtml).toContain(t("print.soilCtxVal"));
    } finally {
      setLocale(prev);
    }
  });

  it("extracts HLS basemap acquisition date dynamically in mapAttributionText", () => {
    const uaUrl =
      "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/2023-08-15/GoogleMapsCompatible_Level12/{z}/{y}/{x}.png";
    expect(mapAttributionText(uaUrl)).toContain("2023-08-15");
    expect(mapAttributionText("custom/tile.png")).toBe(t("map.attribution.hls"));
    expect(mapAttributionText(null)).toBe(t("map.attribution.none"));
  });
});

describe("Methods, Data & Scoreboard updates", () => {
  it("matches CQR_EVALUATION metrics exactly against results/hindcast/conformal/cqr_evaluation.json", () => {
    const raw = JSON.parse(
      readFileSync(resolve(import.meta.dirname, "../../results/hindcast/conformal/cqr_evaluation.json"), "utf8"),
    );
    expect(CQR_EVALUATION.nCalRows).toBe(raw.n_cal_rows);
    expect(CQR_EVALUATION.nTestRows).toBe(raw.n_test_rows);
    expect(CQR_EVALUATION.nSpatialBlocks).toBe(raw.n_spatial_blocks);
    expect(CQR_EVALUATION.rows).toHaveLength(raw.forecast_summary.length);

    for (const row of CQR_EVALUATION.rows) {
      const match = raw.forecast_summary.find(
        (r: { crop: string; metric: string }) => r.crop === row.crop && r.metric === row.metric,
      );
      expect(match, `${row.crop}.${row.metric}`).toBeDefined();
      expect(row.n).toBe(match.n);
      expect(row.storedCov90).toBe(match.stored.cov90.value);
      expect(row.storedWinkler90).toBe(match.stored.winkler90.value);
      expect(row.cqrSymCov90).toBe(match.cqr_sym.cov90.value);
      expect(row.cqrSymWinkler90).toBe(match.cqr_sym.winkler90.value);
      expect(row.cqrAsymCov90).toBe(match.cqr_asym.cov90.value);
      expect(row.cqrAsymWinkler90).toBe(match.cqr_asym.winkler90.value);
      expect(row.gate8595).toBe(match.gate_85_95);
    }
  });

  it("removes leading changelog dates from What we got wrong (EN & AR) without deleting text", () => {
    const enDict = en as Record<string, string>;
    const arDict = ar as Record<string, string>;
    for (let i = 1; i <= 9; i++) {
      const k = `methods.wrong.${i}`;
      expect(enDict[k], `EN ${k}`).not.toMatch(/^\s*\d{4}-\d{2}-\d{2}/);
      expect(arDict[k], `AR ${k}`).not.toMatch(/^\s*\d{4}-\d{2}-\d{2}/);
      expect(enDict[k].length, `EN ${k} text preserved`).toBeGreaterThan(30);
      expect(arDict[k].length, `AR ${k} text preserved`).toBeGreaterThan(20);
    }
  });

  it("renders updated CqrScoreSection, RegionGradeSummary meta lines, and MethodsPage regions/datasets in EN & AR", () => {
    const prev = getLocale();
    const prevWin = (globalThis as { window?: unknown }).window;
    (globalThis as { window?: unknown }).window = {
      location: { hash: "#/ks_t14slh/methods" },
      addEventListener() {},
      removeEventListener() {},
    };
    const ksIndex: RegionIndex = {
      schema_version: "1.0",
      region_id: "ks_t14slh",
      name: "Kansas High Plains (SW Kansas)",
      tier: 1,
      bbox_lonlat: [-101.5, 39.0, -100.5, 40.0],
      basemap: null,
      fields: makeSummaries(4, ["B", "C", "D", "B"]),
      data_as_of: "2024-12-31",
    };
    const uaIndex: RegionIndex = {
      schema_version: "1.2",
      region_id: "ua_central_t36uvu",
      name: "Central Ukraine (T36UVU)",
      tier: 3,
      bbox_lonlat: [31.8, 47.9, 32.1, 48.1],
      basemap: null,
      fields: makeSummaries(4, ["A", "B", "C", "B"]),
      data_as_of: "2024-12-31",
    };
    try {
      for (const loc of ["en", "ar"] as const) {
        setLocale(loc);
        const cqrHtml = unescapeHtml(renderToStaticMarkup(createElement(CqrScoreSection)));
        expect(cqrHtml).toContain(t("score.cqr.heading"));
        expect(cqrHtml).toContain("88.8 %");
        expect(cqrHtml).toContain(t("score.cqr.pass"));

        const ksHtml = unescapeHtml(renderToStaticMarkup(createElement(RegionGradeSummary, { index: ksIndex })));
        expect(ksHtml).toContain(t("score.gradeDist.metaKansas"));
        const uaHtml = unescapeHtml(renderToStaticMarkup(createElement(RegionGradeSummary, { index: uaIndex })));
        expect(uaHtml).toContain(t("score.gradeDist.metaUkraine"));

        const methodsHtml = unescapeHtml(renderToStaticMarkup(createElement(MethodsPage)));
        expect(methodsHtml).toContain('id="m-regions"');
        expect(methodsHtml).toContain(t("methods.regions.heading"));
        expect(methodsHtml).toContain(t("methods.ds.s2cog.name"));
        expect(methodsHtml).toContain(t("methods.ds.worldcereal.name"));
        expect(methodsHtml).not.toMatch(/2026-11-\d{2}/);
      }
    } finally {
      setLocale(prev);
      (globalThis as { window?: unknown }).window = prevWin;
    }
  });
});
