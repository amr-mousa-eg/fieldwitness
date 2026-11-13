import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import builderAr from "../src/builder/strings.ar.json";
import builderEn from "../src/builder/strings.json";
import { answerQuestion } from "../src/chatbotContext";
import { ComparePage } from "../src/ComparePage";
import { DiagnosisSection } from "../src/DiagnosisSection";
import { generateFieldSummary } from "../src/fieldSummary";
import { localizeCounterfactualFlip, localizeGradeReason, localizeMeasureNext, unitLabel } from "../src/format";
import { DEFAULT_PRIORITIES, NO_CONSTRAINTS, rankOptions } from "../src/rank";
import { RankingExplainerSection } from "../src/RankingExplainerSection";
import { explainTopRanking } from "../src/rankingExplainer";
import { compareHref, parseCompareQuery, parseHash } from "../src/route";
import { cropName, getLocale, setLocale, t } from "../src/strings";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { FieldPack, Option, RegionIndex } from "../src/types";

describe("bilingual i18n (EN / AR)", () => {
  it("keeps 100% key and placeholder parity between en.json and ar.json", () => {
    const enKeys = Object.keys(en).sort();
    const arKeys = Object.keys(ar).sort();
    expect(arKeys).toEqual(enKeys);

    for (const k of enKeys) {
      const enVars = [...en[k as keyof typeof en].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      const arVars = [...ar[k as keyof typeof ar].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      expect(arVars, `placeholder mismatch on ${k}`).toEqual(enVars);
    }
  });

  it("keeps 100% key and placeholder parity between builder/strings.json and builder/strings.ar.json", () => {
    const enKeys = Object.keys(builderEn).sort();
    const arKeys = Object.keys(builderAr).sort();
    expect(arKeys).toEqual(enKeys);

    for (const k of enKeys) {
      const enVars = [...builderEn[k as keyof typeof builderEn].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      const arVars = [...builderAr[k as keyof typeof builderAr].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      expect(arVars, `builder placeholder mismatch on ${k}`).toEqual(enVars);
    }
  });

  it("switches locales cleanly and restores EN default", () => {
    const prev = getLocale();
    try {
      setLocale("ar");
      expect(getLocale()).toBe("ar");
      expect(t("nav.compare")).toBe("المقارنة");
      expect(cropName("winter_wheat")).toBe("القمح الشتوي");

      setLocale("en");
      expect(getLocale()).toBe("en");
      expect(t("nav.compare")).toBe("Compare");
      expect(cropName("winter_wheat")).toBe("Winter wheat");
    } finally {
      setLocale(prev);
    }
  });

  it("renders Arabic sub-sections, field summaries, ranking explanations, and chatbot replies cleanly", () => {
    const prev = getLocale();
    const tagD = (value: number, unit: string) => ({ value, unit, tag: "D" as const, source: "FAO-56" });
    const currentOpt: Option = {
      option_id: "current",
      sequence: ["winter_wheat", "sorghum", "fallow"],
      metrics: {
        water_use_mm: tagD(520, "mm"),
        bad_year_water_mm: tagD(480, "mm"),
        bare_soil_months: tagD(7, "months"),
        erosion_exposure: tagD(0.45, "0–1"),
        legume_share: tagD(0, "0–1"),
        family_breaks: tagD(2, "count"),
      },
      witnesses: [],
      grade: "B",
      grade_reasons: [],
      regret: tagD(0.15, "0–1"),
      rank: 2,
      explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
    };
    const altOpt: Option = {
      option_id: "alt_1",
      sequence: ["winter_wheat", "sorghum", "cover_crop"],
      metrics: {
        water_use_mm: tagD(470, "mm"),
        bad_year_water_mm: tagD(440, "mm"),
        bare_soil_months: tagD(4, "months"),
        erosion_exposure: tagD(0.25, "0–1"),
        legume_share: tagD(0.33, "0–1"),
        family_breaks: tagD(3, "count"),
      },
      witnesses: [],
      grade: "B",
      grade_reasons: [],
      regret: tagD(0, "0–1"),
      rank: 1,
      explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
    };
    const samplePack: FieldPack = {
      schema_version: "1.0",
      as_of: "2024-12-31",
      generated_at: "2024-12-31T00:00:00Z",
      data_as_of: "2024-12-31",
      field: {
        field_id: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
        region_id: "ks_t14slh",
        tier: 1,
        boundary_source: "CSB",
        area_ha: 42.5,
        geometry_wkt: "POLYGON ((-101 39.3, -100.99 39.3, -100.99 39.31, -101 39.31, -101 39.3))",
        interior_pixels: 120,
        scale_flags: { hls: false },
      },
      story: [],
      credibility: tagD(0.72, "0–1"),
      options: [currentOpt, altOpt],
      advice: {
        measure_next: "soil moisture",
        flip_probability: tagD(0.12, "0–1"),
        counterfactual_flip: "if -20% rain",
      },
      ledger: [],
    };

    try {
      setLocale("ar");
      const ranked = rankOptions(samplePack.options, DEFAULT_PRIORITIES, NO_CONSTRAINTS);
      const rankExpl = explainTopRanking(ranked, DEFAULT_PRIORITIES);
      expect(rankExpl).not.toBeNull();
      expect(rankExpl!.sentence).not.toContain("ranks #1");
      expect(rankExpl!.sentence).toContain("الحالية");

      const summary = generateFieldSummary(samplePack, DEFAULT_PRIORITIES, NO_CONSTRAINTS);
      expect(summary.sentence).toContain("الدليل:");

      const reply = answerQuestion("كيف يعمل الشهود الثلاثة؟", {
        page: "scoreboard",
        regionId: "ks_t14slh",
        locale: "ar",
      });
      expect(reply.text).toContain("شهود");

      const diagHtml = renderToStaticMarkup(createElement(DiagnosisSection));
      expect(diagHtml).toContain(ar["diagnosis.heading"]);
      expect(diagHtml).not.toContain(">YES<");
      expect(diagHtml).not.toContain(">NO<");
      expect(diagHtml).toContain("yes-badge");
      expect(diagHtml).toContain("no-badge");

      const rankHtml = renderToStaticMarkup(
        createElement(RankingExplainerSection, { ranked, priorities: DEFAULT_PRIORITIES }),
      );
      expect(rankHtml).toContain(ar["rankExplainer.heading"]);
      expect(rankHtml).not.toContain("Why this ranking?");

      expect(localizeMeasureNext("Measure the soil water holding capacity (TAW): it changes rank 1 in 30% of worlds.")).toContain("السعة التخزينية لمياه التربة");
      expect(localizeCounterfactualFlip("soil water holding capacity (TAW): rank 1 changes at -30%; seasonal irrigation amount: no flip in the tested range")).toContain("لا انقلاب ضمن النطاق المختبَر");
      expect(localizeGradeReason("own past agrees (credibility 0.64 >= 0.6)")).toContain("التاريخ الذاتي للحقل يتفق");
      expect(unitLabel("mm per rotation (CVaR10, upper tail)")).toBe("ملم (أسوأ 10٪)");
    } finally {
      setLocale(prev);
    }
  });
});

describe("Compare view routing and SSR", () => {
  it("parses and builds #/<region>/compare?a=...&b=... URLs without breaking RegionRoute", () => {
    const href = compareHref("ks_t14slh", "field_aaa", "field_bbb");
    expect(href).toBe("#/ks_t14slh/compare?a=field_aaa&b=field_bbb");
    const r = parseHash(href);
    expect(r.regionId).toBe("ks_t14slh");
    expect(r.page).toBe("compare");
    expect(r.fieldId).toBeNull();
    expect(parseCompareQuery(href)).toEqual({ a: "field_aaa", b: "field_bbb" });
  });

  it("renders ComparePage selectors and headings cleanly", () => {
    const index: RegionIndex = {
      schema_version: "1.0",
      region_id: "ks_t14slh",
      name: "Kansas",
      tier: 1,
      bbox_lonlat: [-101.5, 39.0, -100.5, 40.0],
      basemap: null,
      data_as_of: "2024-12-31",
      fields: [
        {
          field_id: "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
          centroid_lonlat: [-101.0, 39.3],
          area_ha: 42.5,
          current_crop: "winter_wheat",
          current_sequence: ["winter_wheat", "sorghum", "fallow"],
          top_grade: "B",
        },
        {
          field_id: "bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222",
          centroid_lonlat: [-101.1, 39.4],
          area_ha: 65.0,
          current_crop: "maize",
          current_sequence: ["maize", "soybean", "winter_wheat"],
          top_grade: "B",
        },
      ],
    };

    const html = renderToStaticMarkup(createElement(ComparePage, { index }));
    expect(html).toContain(t("compare.heading"));
    expect(html).toContain(t("compare.fieldA"));
    expect(html).toContain(t("compare.fieldB"));
    expect(html).toContain("42.5 ha");
    expect(html).toContain("65.0 ha");
  });
});
