import { describe, expect, it } from "vitest";
import { answerQuestion, buildSystemPrompt } from "../src/chatbotContext";
import type { FieldPack } from "../src/types";

const MOCK_PACK: FieldPack = {
  schema_version: "1",
  field: {
    field_id: "02cced77704c6b4a72bfdb5e0462c450800b7ae3",
    region_id: "ks_t14slh",
    area_ha: 64.5,
    interior_pixels: 412,
    boundary_source: "USDA CSB",
    scale_flag: false,
    geometry: { type: "Polygon", coordinates: [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]] },
  },
  story: [
    {
      year: 2023,
      crop: "winter_wheat",
      crop_source: "USDA CSB",
      sos_doy: 100,
      peak_doy: 145,
      eos_doy: 185,
      canopy_integral: 65,
      cover_days: 170,
      clear_obs: 24,
      tag: "O",
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

describe("FieldWitness Context Chatbot", () => {
  it("answers general project questions about the Three Witnesses", () => {
    const ans = answerQuestion("How do the three witnesses work?", {
      page: "methods",
      regionId: "ks_t14slh",
    });
    expect(ans.text).toContain("FAO-56");
    expect(ans.text).toContain("K-State Colby");
    expect(ans.followUps.length).toBeGreaterThan(0);
  });

  it("enforces scope guardrails against profit and tonnes/ha claims", () => {
    const ans = answerQuestion("What will my profit in dollars be?", {
      page: "map",
      regionId: "ks_t14slh",
    });
    expect(ans.text).toContain("does not predict dollar profit");
    expect(ans.text).toContain("Relative Yield Index");
  });

  it("answers active field questions using live FieldPack data", () => {
    const ans = answerQuestion("What is the top rotation for this field?", {
      page: "field",
      regionId: "ks_t14slh",
      fieldId: MOCK_PACK.field.field_id,
      fieldNumberLabel: "1",
      fieldPack: MOCK_PACK,
    });
    expect(ans.text).toContain("Field 1");
    expect(ans.text).toContain("1450 mm");
    expect(ans.text).toContain("0.35");
  });

  it("builds a system prompt containing both project facts and active field context", () => {
    const prompt = buildSystemPrompt({
      page: "field",
      regionId: "ks_t14slh",
      fieldId: MOCK_PACK.field.field_id,
      fieldNumberLabel: "1",
      fieldPack: MOCK_PACK,
    });
    expect(prompt).toContain("FieldWitness assistant");
    expect(prompt).toContain("CURRENTLY VIEWED FIELD");
    expect(prompt).toContain("64.5 ha");
  });
});
