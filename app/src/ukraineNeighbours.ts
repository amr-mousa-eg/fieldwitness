export type NeighboursDesignId =
  | "panel_obdml"
  | "panel_obdml_matching"
  | "exact_year_dapsm"
  | "primary_dml"
  | "matching_dml"
  | "dapsm";

export interface NeighboursEvalRow {
  design: NeighboursDesignId;
  regionKey: "kansas" | "ukraine_pre" | "ukraine_full";
  fitted: number;
  overlapPass: number;
  balancePass: number;
  placeboPass: number;
  placeboTested: number;
  negCtrlPass: number;
  negCtrlTested: number;
  evidencePass: number;
}

export interface UkraineContrastHighlight {
  design: "panel_obdml" | "panel_obdml_matching";
  crop: string;
  prev2Crop: string | null;
  contrast: string;
  outcome: string;
  stratum: string;
  estimate: number;
  ciLo: number;
  ciHi: number;
}

export const UKRAINE_NEIGHBOURS_DATA = {
  regionId: "ua_central_t36uvu",
  tileId: "T36UVU",
  tier: 3 as const,
  pilotFields: 400,
  spatialBlocks: 8,
  medianAreaHa: 49.415,
  medianInteriorPx: 479,
  scaleFlagged: 0,
  fieldSeasons: 2800,
  fieldSeasonsWithOutcomes: 2642,
  winterWheatRecovered: 467,
  winterWheatPreCutoffRecovered: 278,
  preCutoffEvidenceTotal: 30,
  fullPeriodEvidenceTotal: 70,
  legacyPreCutoffEvidenceTotal: 14,
  legacyFullPeriodEvidenceTotal: 42,
  worldCerealCheck: {
    croplandAgreement2021Pct: 98.25,
    winterWheatFalseMaizePct: 0.0,
    maizeKappa2021: 0.035,
  },
  comparisonRows: [
    {
      design: "panel_obdml",
      regionKey: "ukraine_pre",
      fitted: 88,
      overlapPass: 64,
      balancePass: 42,
      placeboPass: 62,
      placeboTested: 72,
      negCtrlPass: 75,
      negCtrlTested: 84,
      evidencePass: 14,
    },
    {
      design: "panel_obdml",
      regionKey: "ukraine_full",
      fitted: 92,
      overlapPass: 69,
      balancePass: 69,
      placeboPass: 82,
      placeboTested: 92,
      negCtrlPass: 81,
      negCtrlTested: 88,
      evidencePass: 44,
    },
    {
      design: "panel_obdml_matching",
      regionKey: "ukraine_pre",
      fitted: 132,
      overlapPass: 93,
      balancePass: 24,
      placeboPass: 52,
      placeboTested: 64,
      negCtrlPass: 119,
      negCtrlTested: 128,
      evidencePass: 13,
    },
    {
      design: "panel_obdml_matching",
      regionKey: "ukraine_full",
      fitted: 240,
      overlapPass: 155,
      balancePass: 43,
      placeboPass: 173,
      placeboTested: 192,
      negCtrlPass: 216,
      negCtrlTested: 240,
      evidencePass: 12,
    },
    {
      design: "exact_year_dapsm",
      regionKey: "ukraine_pre",
      fitted: 132,
      overlapPass: 100,
      balancePass: 16,
      placeboPass: 36,
      placeboTested: 64,
      negCtrlPass: 83,
      negCtrlTested: 128,
      evidencePass: 3,
    },
    {
      design: "exact_year_dapsm",
      regionKey: "ukraine_full",
      fitted: 240,
      overlapPass: 204,
      balancePass: 44,
      placeboPass: 124,
      placeboTested: 184,
      negCtrlPass: 151,
      negCtrlTested: 240,
      evidencePass: 14,
    },
    {
      design: "primary_dml",
      regionKey: "kansas",
      fitted: 92,
      overlapPass: 60,
      balancePass: 0,
      placeboPass: 50,
      placeboTested: 56,
      negCtrlPass: 23,
      negCtrlTested: 28,
      evidencePass: 0,
    },
    {
      design: "primary_dml",
      regionKey: "ukraine_pre",
      fitted: 88,
      overlapPass: 76,
      balancePass: 24,
      placeboPass: 45,
      placeboTested: 72,
      negCtrlPass: 26,
      negCtrlTested: 32,
      evidencePass: 8,
    },
    {
      design: "primary_dml",
      regionKey: "ukraine_full",
      fitted: 92,
      overlapPass: 84,
      balancePass: 52,
      placeboPass: 65,
      placeboTested: 92,
      negCtrlPass: 68,
      negCtrlTested: 88,
      evidencePass: 26,
    },
    {
      design: "matching_dml",
      regionKey: "kansas",
      fitted: 32,
      overlapPass: 32,
      balancePass: 8,
      placeboPass: 7,
      placeboTested: 12,
      negCtrlPass: 23,
      negCtrlTested: 28,
      evidencePass: 0,
    },
    {
      design: "matching_dml",
      regionKey: "ukraine_pre",
      fitted: 132,
      overlapPass: 100,
      balancePass: 8,
      placeboPass: 41,
      placeboTested: 64,
      negCtrlPass: 58,
      negCtrlTested: 64,
      evidencePass: 6,
    },
    {
      design: "matching_dml",
      regionKey: "ukraine_full",
      fitted: 240,
      overlapPass: 204,
      balancePass: 40,
      placeboPass: 142,
      placeboTested: 192,
      negCtrlPass: 155,
      negCtrlTested: 224,
      evidencePass: 16,
    },
    {
      design: "dapsm",
      regionKey: "kansas",
      fitted: 4,
      overlapPass: 4,
      balancePass: 0,
      placeboPass: 0,
      placeboTested: 0,
      negCtrlPass: 0,
      negCtrlTested: 0,
      evidencePass: 0,
    },
  ] satisfies NeighboursEvalRow[],
  preCutoffHighlights: [
    {
      design: "panel_obdml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "sunflower vs winter_wheat",
      outcome: "cover_days",
      stratum: "all",
      estimate: -4.808,
      ciLo: -8.58,
      ciHi: -1.037,
    },
    {
      design: "panel_obdml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "sunflower vs winter_wheat",
      outcome: "canopy_integral",
      stratum: "all",
      estimate: -4.509,
      ciLo: -4.961,
      ciHi: -4.058,
    },
    {
      design: "panel_obdml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "maize vs winter_wheat",
      outcome: "cover_days",
      stratum: "all",
      estimate: -9.473,
      ciLo: -14.061,
      ciHi: -4.885,
    },
    {
      design: "panel_obdml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "maize vs sunflower",
      outcome: "canopy_integral",
      stratum: "all",
      estimate: -1.611,
      ciLo: -3.069,
      ciHi: -0.154,
    },
    {
      design: "panel_obdml_matching",
      crop: "sunflower",
      prev2Crop: "maize",
      contrast: "maize vs sunflower",
      outcome: "cover_days",
      stratum: "all",
      estimate: -6.083,
      ciLo: -11.536,
      ciHi: -0.629,
    },
  ] satisfies UkraineContrastHighlight[],
};
