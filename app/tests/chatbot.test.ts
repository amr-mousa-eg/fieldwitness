import { describe, expect, it } from "vitest";
import { answerQuestion, buildSystemPrompt } from "../src/chatbotContext";
import { fetchLiveClimateProfile } from "../src/liveClimateApi";
import type { FieldCalendar, FieldPack, FieldScenarios } from "../src/types";

const MOCK_PACK: FieldPack = {
  schema_version: "1",
  field: {
    field_id: "02cced77704c6b4a72bfdb5e0462c450800b7ae3",
    geometry_wkt: "POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))",
    area_ha: 64.5,
    region_id: "ks_t14slh",
    tier: 1,
    boundary_source: "CSB",
    scale_flags: { HLS: false, POWER: true },
    interior_pixels: 412,
  },
  story: [
    {
      year: 2023,
      index: 0,
      crop: "winter_wheat",
      crop_conf: 1,
      crop_source: "label",
      sos: { value: 100, unit: "day", tag: "O", source: "HLS" },
      peak: { value: 145, unit: "day", tag: "O", source: "HLS" },
      eos: { value: 185, unit: "day", tag: "O", source: "HLS" },
      canopy_integral: { value: 65, unit: "NDVI-d", tag: "D", source: "HLS" },
      cover_days: { value: 170, unit: "d", tag: "D", source: "HLS" },
      bare_days: { value: 195, unit: "d", tag: "D", source: "HLS" },
      clear_obs: 24,
    },
  ],
  credibility: { value: 0.64, unit: "0-1", tag: "D", source: "ABC" },
  options: [
    {
      option_id: "current",
      sequence: ["winter_wheat", "fallow", "winter_wheat"],
      metrics: {
        water_use_mm: { value: 1380, unit: "mm", tag: "D", source: "sim" },
        ryi: { value: 0.26, unit: "0-1", tag: "D", source: "sim" },
      },
      witnesses: [],
      grade: "B",
      grade_reasons: ["own past agrees"],
      regret: { value: 0.08, unit: "RYI", tag: "D", source: "rank" },
      rank: 0,
      explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
    },
    {
      option_id: "winter_wheat|sorghum|fallow",
      sequence: ["winter_wheat", "sorghum", "fallow"],
      metrics: {
        water_use_mm: { value: 1450, unit: "mm", tag: "D", source: "sim" },
        bad_year_water_mm: { value: 1702, unit: "mm", tag: "D", source: "sim" },
        cover_days: { value: 243, unit: "days", tag: "D", source: "sim" },
        ryi: { value: 0.35, unit: "0-1", tag: "D", source: "sim" },
      },
      witnesses: [],
      grade: "B",
      grade_reasons: ["own past agrees"],
      regret: { value: 0.05, unit: "RYI", tag: "D", source: "rank" },
      rank: 1,
      explanation: { why: [], evidence: [], benefits: [], gaps: [], risks: [] },
    },
  ],
  advice: {
    measure_next: "Measure the soil water holding capacity (TAW): it changes rank 1 in 30% of worlds.",
    flip_probability: { value: 0.3, unit: "share", tag: "D", source: "flip" },
    counterfactual_flip: "soil water holding capacity (TAW): rank 1 changes at -30%",
  },
  ledger: [],
  data_as_of: "2024-12-31",
  generated_at: "2026-11-07T00:00:00Z",
};

const MOCK_CALENDAR: FieldCalendar = {
  schema_version: "1.2",
  field_id: MOCK_PACK.field.field_id,
  bare_observed: [
    { month: 1, bare_share: { value: 0.75, unit: "share", tag: "O", source: "HLS" }, clear_obs: 12, years_with_data: 6, insufficient: false },
  ],
  bare_observed_years: [2017, 2024],
  bare_by_option: {},
  vulnerability: [
    {
      crop: "sorghum",
      years: [2001, 2021],
      thresholds: {},
      threshold_notes: {},
      shares: {
        water_stress: { x: [1, 2, 3], values: [0.1, 0.45, 0.2], unit: "share", tag: "D", source: "sim" },
        heat: { x: [1, 2, 3], values: [0.05, 0.3, 0.1], unit: "share", tag: "D", source: "sim" },
      },
    },
  ],
  data_as_of: "2024-12-31",
};

const MOCK_SCENARIOS: FieldScenarios = {
  schema_version: "1.2",
  field_id: MOCK_PACK.field.field_id,
  baseline_id: "t+0_p+0",
  note: "Sensitivity tests on past weather, not climate projections.",
  scenarios: [
    { scenario_id: "t+0_p+0", dt_c: 0, dp_pct: 0, metrics: {}, ranks: { "winter_wheat|sorghum|fallow": 1 } },
    { scenario_id: "t+2_p-20", dt_c: 2, dp_pct: -20, metrics: {}, ranks: { "winter_wheat|fallow|winter_wheat": 1 } },
  ],
  data_as_of: "2024-12-31",
};

describe("FieldWitness Context Chatbot & Live Physics", () => {
  it("answers general project questions about the Three Witnesses", () => {
    const ans = answerQuestion("How do the three witnesses work?", {
      page: "methods",
      regionId: "ks_t14slh",
    });
    expect(ans.text).toContain("FAO-56");
    expect(ans.text).toContain("K-State Colby");
    expect(ans.followUps.length).toBeGreaterThan(0);
  });

  it("enforces scope guardrails against profit and harvest mass claims", () => {
    const ans = answerQuestion("What will my profit in dollars be?", {
      page: "map",
      regionId: "ks_t14slh",
    });
    expect(ans.text).toContain("does not predict dollar profit");
    expect(ans.text).toContain("Relative Yield Index");
  });

  it("answers active field, calendar, and climate scenario questions", () => {
    const ctx = {
      page: "field",
      regionId: "ks_t14slh",
      fieldId: MOCK_PACK.field.field_id,
      fieldNumberLabel: "1",
      fieldPack: MOCK_PACK,
      fieldCalendar: MOCK_CALENDAR,
      fieldScenarios: MOCK_SCENARIOS,
    };
    const rotAns = answerQuestion("What is the top rotation for this field?", ctx);
    expect(rotAns.text).toContain("Field 1");
    expect(rotAns.text).toContain("1450 mm");
    expect(rotAns.text).toContain("0.35");

    const calAns = answerQuestion("What are the bare soil months and hazards?", ctx);
    expect(calAns.text).toContain("Jan (75%)");
    expect(calAns.text).toContain("45%");

    const scenAns = answerQuestion("What should I measure next or under climate scenarios?", ctx);
    expect(scenAns.text).toContain("winter_wheat|fallow|winter_wheat");
  });

  it("builds a rich system prompt containing project facts, calendar, scenarios, and active field context", () => {
    const prompt = buildSystemPrompt({
      page: "field",
      regionId: "ks_t14slh",
      fieldId: MOCK_PACK.field.field_id,
      fieldNumberLabel: "1",
      fieldPack: MOCK_PACK,
      fieldCalendar: MOCK_CALENDAR,
      fieldScenarios: MOCK_SCENARIOS,
      priorities: { waterUse: 3, badYearWater: 2, bareSoil: 1, ryi: 2, regret: 0 },
    });
    expect(prompt).toContain("FieldWitness Scientific Assistant");
    expect(prompt).toContain("CURRENTLY VIEWED FIELD");
    expect(prompt).toContain("High Observed Bare-Soil Months [O]: Jan (75%)");
    expect(prompt).toContain("Weather Sensitivity (+2 °C, -20% rain)");
    expect(prompt).toContain("Active Priority Weights [A]: waterUse=3");
  });

  it("simulates multi-year FAO-56 rotations cleanly in global offline fallback mode", async () => {
    const origFetch = globalThis.fetch;
    globalThis.fetch = (() => Promise.reject(new Error("offline"))) as typeof fetch;
    try {
      const prof = await fetchLiveClimateProfile(39.39, -101.05, {
        irrigationBudgetMm: 100,
        cantGrow: ["winter_wheat"],
      });
      expect(prof.recommendedRotations.length).toBeGreaterThan(0);
      expect(prof.recommendedRotations[0].waterUseMm).toBeGreaterThan(0);
      expect(prof.recommendedRotations[0].ryi).toBeGreaterThan(0);
      expect(prof.soilContext.estimatedAweMm).toBeGreaterThanOrEqual(200);
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});
