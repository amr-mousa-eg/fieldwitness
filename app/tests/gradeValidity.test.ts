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
    expect(strings["score.gradeValidity.verdict"]).toBe(
      "We could not show that evidence grades predict accuracy (n = 463 field-seasons): grade-B fields had lower average error than grade-D (CRPS 17.0 vs 24.0), but the difference is within the uncertainty (95% CI of the difference −3.3 to 14.3). Grade D had only 25 field-seasons."
    );
    expect(strings["score.gradeValidity.bDesc"]).toBeTruthy();
    expect(strings["score.gradeValidity.cDesc"]).toBeTruthy();
    expect(strings["score.gradeValidity.dDesc"]).toBeTruthy();
    expect(strings["methods.limits.7"]).toBe(
      "We could not show that evidence grades predict accuracy (n = 463 field-seasons): grade-B fields had lower average error than grade-D (CRPS 17.0 vs 24.0), but the difference is within the uncertainty (95% CI of the difference −3.3 to 14.3). Grade D had only 25 field-seasons."
    );
  });
});
