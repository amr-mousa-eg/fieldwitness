/**
 * Field summary comparison thresholds and constants.
 * Matches config/field_summary.yaml.
 *
 * Source: team choice (tag A, UNVERIFIED).
 */

export const SUMMARY_THRESHOLDS = {
  water_use_mm: 25.0, // mm per rotation: differences < 25 mm are "about the same"
  bad_year_water_mm: 25.0, // mm per rotation: differences < 25 mm are "about the same"
  bare_soil_months: 1.0, // months per rotation: differences < 1 month are "about the same"
} as const;

export const ROTATION_DAYS = 1095; // 3 seasons x 365 days
export const DAYS_PER_MONTH = 30.4375; // 365.25 / 12
export const ROTATION_MONTHS = 36; // 3 years x 12 months
