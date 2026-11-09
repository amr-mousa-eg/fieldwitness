import { describe, expect, it } from "vitest";
import { GRADE_VALIDITY } from "../src/gradeValidity";
import en from "../src/strings/en.json";

describe("Grade & Credibility Validity (Kansas Pilot)", () => {
  it("has valid pre-registered parameters and sample sizes", () => {
    expect(GRADE_VALIDITY.as_of_cutoff).toBe("2021-12-31");
    expect(GRADE_VALIDITY.total_scored_field_seasons).toBe(463);
    expect(GRADE_VALIDITY.primary_test.passed).toBe(false);
    expect(GRADE_VALIDITY.primary_test.diff_d_minus_b_ci95[0]).toBeLessThan(0);
    expect(GRADE_VALIDITY.primary_test.diff_d_minus_b_ci95[1]).toBeGreaterThan(0);

    for (const g of ["B", "C", "D"] as const) {
      const stats = GRADE_VALIDITY.grades[g];
      expect(stats.n).toBeGreaterThanOrEqual(20);
      expect(stats.too_few_to_judge).toBe(false);
      expect(stats.forecast_ci_crps_mean).toBeGreaterThan(0);
      expect(stats.forecast_ci_crps_ci95.length).toBe(2);
    }
  });

  it("contains all required translation strings for Scoreboard and Methods", () => {
    const strings = en as Record<string, string>;
    expect(strings["score.gradeValidity.heading"]).toBeTruthy();
    expect(strings["score.gradeValidity.verdict"]).toContain("Grades did not predict accuracy in our test");
    expect(strings["score.gradeValidity.bDesc"]).toBeTruthy();
    expect(strings["score.gradeValidity.cDesc"]).toBeTruthy();
    expect(strings["score.gradeValidity.dDesc"]).toBeTruthy();
    expect(strings["methods.limits.7"]).toContain("Evidence grades did not predict accuracy in our pre-registered test");
  });
});
