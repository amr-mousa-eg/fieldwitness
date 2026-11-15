/**
 * Empirical Grade & Credibility Validity Check Results.
 * Pre-registered in DECISIONS.md (2026-11-09) and evaluated under cut-off as_of(2021-12-31).
 *
 * Source: results/hindcast/grade_validity.json
 */

export interface GradeStats {
  n: number;
  too_few_to_judge: boolean;
  forecast_ci_crps_mean: number;
  forecast_peak_abs_err_mean: number;
  forecast_ci_covered90_share: number;
  forecast_peak_covered90_share: number;
  forecast_ci_crps_ci95: [number, number];
}

export interface PrimaryTest {
  target: string;
  comparison: string;
  decision_rule: string;
  diff_d_minus_b_mean: number;
  diff_d_minus_b_ci95: [number, number];
  passed: boolean;
  verdict: string;
}

export interface CredibilityCorrelation {
  n_field_seasons: number;
  spearman_rho_crps: number;
  p_value_crps: number;
  spearman_rho_peak_timing_error: number;
  p_value_peak_timing_error: number;
  note: string;
}

export interface GradeValidityData {
  analysis: string;
  as_of_cutoff: string;
  scored_seasons: string;
  total_scored_field_seasons: number;
  primary_test: PrimaryTest;
  grades: {
    B: GradeStats;
    C: GradeStats;
    D: GradeStats;
  };
  credibility_rank_correlation: CredibilityCorrelation;
}

export const GRADE_VALIDITY: GradeValidityData = {
  analysis: "Grade & Credibility Empirical Validity Check (Kansas Pilot, SSURGO [E] TAW)",
  as_of_cutoff: "2021-12-31",
  scored_seasons: "2022-2024",
  total_scored_field_seasons: 463,
  primary_test: {
    target: "forecast_ci_crps (canopy integral)",
    comparison: "Grade B vs Grade D",
    decision_rule: "Success iff B mean < D mean and 95% CI of (D - B) strictly > 0",
    diff_d_minus_b_mean: 6.8837,
    diff_d_minus_b_ci95: [-1.5354, 13.9383],
    passed: false,
    verdict: "DID NOT PASS: Evidence grades did not show a statistically significant difference in predictive accuracy.",
  },
  grades: {
    B: {
      n: 139,
      too_few_to_judge: false,
      forecast_ci_crps_mean: 17.9313,
      forecast_peak_abs_err_mean: 28.68,
      forecast_ci_covered90_share: 0.259,
      forecast_peak_covered90_share: 0.705,
      forecast_ci_crps_ci95: [15.6752, 20.5772],
    },
    C: {
      n: 299,
      too_few_to_judge: false,
      forecast_ci_crps_mean: 17.2519,
      forecast_peak_abs_err_mean: 35.57,
      forecast_ci_covered90_share: 0.301,
      forecast_peak_covered90_share: 0.6288,
      forecast_ci_crps_ci95: [15.7796, 18.8743],
    },
    D: {
      n: 25,
      too_few_to_judge: false,
      forecast_ci_crps_mean: 24.815,
      forecast_peak_abs_err_mean: 34.92,
      forecast_ci_covered90_share: 0.24,
      forecast_peak_covered90_share: 0.6,
      forecast_ci_crps_ci95: [16.2797, 31.5345],
    },
  },
  credibility_rank_correlation: {
    n_field_seasons: 417,
    spearman_rho_crps: -0.0039,
    p_value_crps: 0.9369,
    spearman_rho_peak_timing_error: -0.1022,
    p_value_peak_timing_error: 0.037,
    note: "Negative rho means higher credibility predicts lower error (better skill).",
  },
};
