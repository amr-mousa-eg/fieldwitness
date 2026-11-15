import { describe, expect, it } from "vitest";
import { DIAGNOSIS_DATA } from "../src/diagnosis";

describe("Hindcast Skill Diagnostic Breakdown (Item 1)", () => {
  it("exports valid pre-registered primary question results", () => {
    const data = DIAGNOSIS_DATA;
    expect(data.cut_off_date).toBe("2021-12-31");
    expect(data.sample_size).toBe(463);

    const primary = data.primary_question.results;
    expect(primary.overall.n_paired_baselines).toBe(463);
    expect(primary.overall.beats_b1).toBe(true);
    expect(primary.overall.beats_b2).toBe(true);
    expect(primary.overall.diff_vs_b1_ci95?.[0]).toBeGreaterThan(0);
    expect(primary.overall.diff_vs_b2_ci95?.[0]).toBeGreaterThan(0);

    // Maize beats B1 and B2
    const maize = primary.by_crop.maize;
    expect(maize.n).toBe(124);
    expect(maize.beats_b1).toBe(true);
    expect(maize.beats_b2).toBe(true);
    expect(maize.diff_vs_b1_ci95?.[0]).toBeGreaterThan(0);
    expect(maize.diff_vs_b2_ci95?.[0]).toBeGreaterThan(0);

    // Sorghum beats B1 and B2 under SSURGO [E] TAW
    const sorghum = primary.by_crop.sorghum;
    expect(sorghum.n).toBe(142);
    expect(sorghum.beats_b1).toBe(true);
    expect(sorghum.beats_b2).toBe(true);
    expect(sorghum.diff_vs_b1_ci95?.[0]).toBeGreaterThan(0);
    expect(sorghum.diff_vs_b2_ci95?.[0]).toBeGreaterThan(0);

    // Winter wheat baselines evaluated in SSURGO-backed T7.3/T7 diagnosis
    const wheat = primary.by_crop.winter_wheat;
    expect(wheat.n).toBe(197);
    expect(wheat.status).toBe("evaluated");
    expect(wheat.beats_b1).toBe(true);
    expect(wheat.beats_b2).toBe(true);

    // Fallow is too few to judge (n = 0)
    const fallow = primary.by_crop.fallow;
    expect(fallow.n).toBe(0);
    expect(fallow.status).toBe("too few to judge");
  });

  it("enforces n < 20 sample floor rule on exploratory dimensions", () => {
    const exp = DIAGNOSIS_DATA.exploratory_breakdowns;
    const allCells = [
      ...exp.by_crop,
      ...exp.by_year,
      ...exp.by_field_size,
      ...exp.by_grade,
      ...exp.by_hls_obs,
    ];

    for (const cell of allCells) {
      if (cell.n < 20) {
        expect(cell.status).toBe("too few to judge");
      } else {
        expect(cell.status).not.toBe("too few to judge");
        expect(cell.fw_crps_mean).toBeGreaterThan(0);
        expect(cell.fw_crps_ci95?.[0]).toBeLessThanOrEqual(cell.fw_crps_ci95?.[1]!);
      }
    }
  });

  it("upholds causal claim standards with honest 'cause not established' fallbacks", () => {
    const findings = DIAGNOSIS_DATA.findings;
    expect(findings.length).toBeGreaterThanOrEqual(5);

    const cropFinding = findings.find((f) => f.dimension === "crop");
    expect(cropFinding?.cause).toBe("cause not established");

    const yearFinding = findings.find((f) => f.dimension === "year");
    expect(yearFinding?.cause).toBe("cause not established");

    const sizeFinding = findings.find((f) => f.dimension === "field_size");
    expect(sizeFinding?.cause).toBe("cause not established");

    const gradeFinding = findings.find((f) => f.dimension === "grade");
    expect(gradeFinding?.cause).toBe("cause not established");

    // Winter wheat timing anomaly is described empirically
    const timingFinding = findings.find((f) => f.dimension === "crop_timing_anomaly");
    expect(timingFinding?.cause).toContain("late May vs July");
    expect(timingFinding?.cause).toContain("separate decision");
  });
});
