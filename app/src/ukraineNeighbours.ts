export interface NeighboursEvalRow {
  design: "primary_dml" | "matching_dml" | "dapsm";
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
  design: "primary_dml" | "matching_dml";
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
  pilotFields: 395,
  spatialBlocks: 8,
  medianAreaHa: 48.678,
  medianInteriorPx: 473,
  scaleFlagged: 0,
  fieldSeasons: 2765,
  fieldSeasonsWithOutcomes: 2145,
  preCutoffEvidenceTotal: 11,
  fullPeriodEvidenceTotal: 25,
  comparisonRows: [
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
      fitted: 64,
      overlapPass: 52,
      balancePass: 12,
      placeboPass: 23,
      placeboTested: 44,
      negCtrlPass: 16,
      negCtrlTested: 32,
      evidencePass: 7,
    },
    {
      design: "primary_dml",
      regionKey: "ukraine_full",
      fitted: 72,
      overlapPass: 64,
      balancePass: 48,
      placeboPass: 36,
      placeboTested: 64,
      negCtrlPass: 31,
      negCtrlTested: 60,
      evidencePass: 11,
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
      fitted: 108,
      overlapPass: 84,
      balancePass: 12,
      placeboPass: 26,
      placeboTested: 44,
      negCtrlPass: 35,
      negCtrlTested: 60,
      evidencePass: 4,
    },
    {
      design: "matching_dml",
      regionKey: "ukraine_full",
      fitted: 172,
      overlapPass: 144,
      balancePass: 36,
      placeboPass: 107,
      placeboTested: 144,
      negCtrlPass: 73,
      negCtrlTested: 112,
      evidencePass: 13,
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
    {
      design: "dapsm",
      regionKey: "ukraine_pre",
      fitted: 108,
      overlapPass: 84,
      balancePass: 0,
      placeboPass: 22,
      placeboTested: 44,
      negCtrlPass: 46,
      negCtrlTested: 60,
      evidencePass: 0,
    },
    {
      design: "dapsm",
      regionKey: "ukraine_full",
      fitted: 172,
      overlapPass: 144,
      balancePass: 8,
      placeboPass: 92,
      placeboTested: 144,
      negCtrlPass: 67,
      negCtrlTested: 112,
      evidencePass: 1,
    },
  ] satisfies NeighboursEvalRow[],
  preCutoffHighlights: [
    {
      design: "primary_dml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "sunflower vs winter_wheat",
      outcome: "cover_days",
      stratum: "all",
      estimate: -6.296,
      ciLo: -10.082,
      ciHi: -2.511,
    },
    {
      design: "primary_dml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "maize vs sunflower",
      outcome: "canopy_integral",
      stratum: "all",
      estimate: -1.838,
      ciLo: -2.841,
      ciHi: -0.835,
    },
    {
      design: "primary_dml",
      crop: "sunflower",
      prev2Crop: null,
      contrast: "maize vs sunflower",
      outcome: "cover_days",
      stratum: "all",
      estimate: -3.726,
      ciLo: -6.441,
      ciHi: -1.01,
    },
    {
      design: "matching_dml",
      crop: "sunflower",
      prev2Crop: "maize",
      contrast: "maize vs sunflower",
      outcome: "canopy_integral",
      stratum: "all",
      estimate: -2.489,
      ciLo: -4.597,
      ciHi: -0.381,
    },
  ] satisfies UkraineContrastHighlight[],
};
