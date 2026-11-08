import { describe, expect, it } from "vitest";
import {
  RERUN_NEEDED,
  applyCorrections,
  correctionKey,
  emptyCorrections,
  type CurrentRotation,
} from "../src/corrections";

const ALLOWED = new Set(["maize", "sorghum", "winter_wheat"]);

const cur = (): CurrentRotation => ({
  fieldId: "f1",
  years: [2022, 2023, 2024],
  sequence: ["maize", "sorghum", "alfalfa"],
  confidence: 1.0,
  tag: "E",
  simulatable: false,
  gaps: ["2024: 'alfalfa' is not simulated (no rotation-option parameters)"],
  secondCrops: {},
});

describe("applyCorrections (mirrors tests/test_corrections.py)", () => {
  it("crop correction changes Current and keeps the original", () => {
    const corr = { ...emptyCorrections(), cropByYear: { 2024: "winter_wheat" } };
    const r = applyCorrections(cur(), corr, ALLOWED, new Set());
    expect(r.corrected.sequence).toEqual(["maize", "sorghum", "winter_wheat"]);
    expect(r.original.sequence[2]).toBe("alfalfa");
    expect(r.sourceByYear).toEqual({ 2022: "label", 2023: "label", 2024: "farmer" });
    expect(r.corrected.simulatable).toBe(true);
    expect(r.corrected.gaps).toEqual([]);
    expect(r.needsRerun).toBe(true);
    expect(r.notes).toContain(RERUN_NEEDED);
  });

  it("a precomputed alternative avoids the re-run", () => {
    const corr = { ...emptyCorrections(), cropByYear: { 2024: "winter_wheat" } };
    const r = applyCorrections(cur(), corr, ALLOWED, new Set([correctionKey(corr)]));
    expect(r.needsRerun).toBe(false);
  });

  it("sowing and irrigation need a re-run and keep the sequence", () => {
    const corr = { ...emptyCorrections(), sowingDay: { 2023: 120 }, irrigated: true };
    const r = applyCorrections(cur(), corr, ALLOWED);
    expect(r.corrected.sequence).toEqual(cur().sequence);
    expect(r.needsRerun).toBe(true);
  });

  it("rejects an unknown year", () => {
    const corr = { ...emptyCorrections(), cropByYear: { 1999: "maize" } };
    expect(() => applyCorrections(cur(), corr, ALLOWED)).toThrow();
  });

  it("no correction is the identity", () => {
    const r = applyCorrections(cur(), emptyCorrections(), ALLOWED);
    expect(r.corrected).toEqual(r.original);
    expect(r.needsRerun).toBe(false);
  });

  it("key format matches Python", () => {
    const corr = { cropByYear: { 2024: "maize", 2022: "sorghum" }, sowingDay: { 2023: 120 }, irrigated: false };
    expect(correctionKey(corr)).toBe("c2022=sorghum;c2024=maize;s2023=120;irr=0");
  });
});
