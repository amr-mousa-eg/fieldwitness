import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import ar from "../src/strings/ar.json";
import en from "../src/strings/en.json";
import type { FieldPack, FieldSim3DInputs, RegionHindcast, RegionIndex } from "../src/types";

const ROOT = resolve(import.meta.dirname, "..", "..");
const readPackJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(ROOT, rel), "utf8")) as T;

interface SsurgoCheckReport {
  n_fields: number;
  n_ssurgo_ok: number;
}

describe("Phase P1 (SSURGO [E] Kansas & 6-crop Central Ukraine)", () => {
  it("keeps 100% EN/AR string key parity", () => {
    const enKeys = Object.keys(en).sort();
    const arKeys = Object.keys(ar).sort();
    expect(enKeys).toEqual(arKeys);
  });

  it("ships Kansas packs with observed SSURGO [E] TAW or SoilGrids [E] fallback across all 200 fields", () => {
    const ssurgoCheck = readPackJson<SsurgoCheckReport>("results/validation/soil_ssurgo_check.json");
    expect(ssurgoCheck.n_fields).toBe(200);
    expect(ssurgoCheck.n_ssurgo_ok).toBe(198);
    const ablation = readPackJson<{ baseline_note: string }>("results/validation/ssurgo_ablation_report.json");
    expect(ablation.baseline_note).toContain("198 fields");
    expect(ablation.baseline_note).toContain("2 shallow fields");

    const ksIndex = readPackJson<RegionIndex>("packs/demo/ks_t14slh/index.json");
    expect(ksIndex.fields).toHaveLength(200);
    const taws: number[] = [];
    for (const summary of ksIndex.fields) {
      const pack = readPackJson<FieldPack>(`packs/demo/ks_t14slh/${summary.field_id}.json`);
      const inputs = readPackJson<FieldSim3DInputs>(`packs/demo/ks_t14slh/${summary.field_id}.sim3d_inputs.json`);
      taws.push(inputs.params.taw_mm);
      for (const opt of pack.options) {
        const tawGap = opt.explanation.gaps.filter((g) => /\btaw\b/i.test(g));
        expect(tawGap).toHaveLength(0);
      }
    }
    expect(taws).toHaveLength(200);
    expect(Math.max(...taws)).toBeGreaterThan(300);
  });

  it("ships Central Ukraine packs with 6 candidate crops including sunflower, soybean, and cover_crop", () => {
    const uaIndex = readPackJson<RegionIndex>("packs/demo/ua_central_t36uvu/index.json");
    expect(uaIndex.fields).toHaveLength(120);
    const crops = new Set<string>();
    let totalOptions = 0;
    let gradeACandidates = 0;
    for (const summary of uaIndex.fields) {
      const pack = readPackJson<FieldPack>(`packs/demo/ua_central_t36uvu/${summary.field_id}.json`);
      for (const opt of pack.options) {
        if (opt.option_id !== "current") {
          totalOptions += 1;
          if (opt.grade === "A") gradeACandidates += 1;
        }
        for (const c of opt.sequence) crops.add(c);
      }
    }
    expect(totalOptions).toBe(960);
    expect(gradeACandidates).toBe(44);
    expect(crops.has("sunflower")).toBe(true);
    expect(crops.has("soybean")).toBe(true);
    expect(crops.has("cover_crop")).toBe(true);
    expect(crops.has("winter_wheat")).toBe(true);
    expect(crops.has("maize")).toBe(true);
    expect(crops.has("fallow")).toBe(true);

    const uaHindcast = readPackJson<RegionHindcast>("packs/demo/ua_central_t36uvu/hindcast.json");
    expect(uaHindcast.rows.length).toBe(20);
    expect(new Set(uaHindcast.rows.map((r) => r.method))).toEqual(new Set(["fieldwitness", "B0", "B1", "B2"]));
  });
});
