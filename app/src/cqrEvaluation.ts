/**
 * Phase 4 Split-CQR Conformal Calibration Evaluation (Kansas Pilot, T14SLH).
 * Cut-off as_of(2021-12-31), evaluated out-of-sample across 109 spatial blocks (2022-2024).
 *
 * Source: results/hindcast/conformal/cqr_evaluation.json
 */

export interface CqrForecastRow {
  crop: "winter_wheat" | "maize" | "sorghum";
  metric: "sos" | "peak" | "cover_days" | "canopy_integral";
  n: number;
  storedCov90: number;
  storedWinkler90: number;
  cqrSymCov90: number;
  cqrSymWinkler90: number;
  cqrAsymCov90: number;
  cqrAsymWinkler90: number;
  gate8595: "pass" | "fail";
}

export const CQR_EVALUATION = {
  nCalRows: 3424,
  nTestRows: 3704,
  nSpatialBlocks: 109,
  rows: [
    {
      crop: "winter_wheat",
      metric: "sos",
      n: 197,
      storedCov90: 0.1878,
      storedWinkler90: 1083.4777,
      cqrSymCov90: 0.8629,
      cqrSymWinkler90: 274.1457,
      cqrAsymCov90: 0.802,
      cqrAsymWinkler90: 236.1201,
      gate8595: "fail",
    },
    {
      crop: "maize",
      metric: "sos",
      n: 124,
      storedCov90: 0.3306,
      storedWinkler90: 246.6718,
      cqrSymCov90: 0.9113,
      cqrSymWinkler90: 139.4056,
      cqrAsymCov90: 0.9113,
      cqrAsymWinkler90: 147.6754,
      gate8595: "pass",
    },
    {
      crop: "sorghum",
      metric: "sos",
      n: 142,
      storedCov90: 0.6408,
      storedWinkler90: 351.2944,
      cqrSymCov90: 0.8944,
      cqrSymWinkler90: 283.7754,
      cqrAsymCov90: 0.8944,
      cqrAsymWinkler90: 234.4662,
      gate8595: "pass",
    },
    {
      crop: "winter_wheat",
      metric: "cover_days",
      n: 197,
      storedCov90: 0.0305,
      storedWinkler90: 831.8401,
      cqrSymCov90: 0.9594,
      cqrSymWinkler90: 242.4239,
      cqrAsymCov90: 0.8883,
      cqrAsymWinkler90: 246.2081,
      gate8595: "pass",
    },
    {
      crop: "maize",
      metric: "cover_days",
      n: 124,
      storedCov90: 0.1048,
      storedWinkler90: 585.7294,
      cqrSymCov90: 0.8145,
      cqrSymWinkler90: 196.781,
      cqrAsymCov90: 0.7742,
      cqrAsymWinkler90: 210.6867,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "cover_days",
      n: 142,
      storedCov90: 0.0563,
      storedWinkler90: 559.7489,
      cqrSymCov90: 0.8873,
      cqrSymWinkler90: 226.6011,
      cqrAsymCov90: 0.7958,
      cqrAsymWinkler90: 213.1732,
      gate8595: "fail",
    },
    {
      crop: "winter_wheat",
      metric: "canopy_integral",
      n: 197,
      storedCov90: 0.2538,
      storedWinkler90: 319.0366,
      cqrSymCov90: 0.7614,
      cqrSymWinkler90: 121.845,
      cqrAsymCov90: 0.6954,
      cqrAsymWinkler90: 114.8939,
      gate8595: "fail",
    },
    {
      crop: "maize",
      metric: "canopy_integral",
      n: 124,
      storedCov90: 0.2339,
      storedWinkler90: 279.8438,
      cqrSymCov90: 0.7903,
      cqrSymWinkler90: 114.7108,
      cqrAsymCov90: 0.7823,
      cqrAsymWinkler90: 114.5583,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "canopy_integral",
      n: 142,
      storedCov90: 0.3732,
      storedWinkler90: 182.1033,
      cqrSymCov90: 0.7183,
      cqrSymWinkler90: 117.2448,
      cqrAsymCov90: 0.6972,
      cqrAsymWinkler90: 119.694,
      gate8595: "fail",
    },
    {
      crop: "winter_wheat",
      metric: "peak",
      n: 197,
      storedCov90: 0.3452,
      storedWinkler90: 670.4025,
      cqrSymCov90: 0.7817,
      cqrSymWinkler90: 427.7655,
      cqrAsymCov90: 0.7817,
      cqrAsymWinkler90: 432.1538,
      gate8595: "fail",
    },
    {
      crop: "maize",
      metric: "peak",
      n: 124,
      storedCov90: 0.9113,
      storedWinkler90: 89.3871,
      cqrSymCov90: 0.9597,
      cqrSymWinkler90: 95.5,
      cqrAsymCov90: 0.9677,
      cqrAsymWinkler90: 104.3952,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "peak",
      n: 142,
      storedCov90: 0.8451,
      storedWinkler90: 112.325,
      cqrSymCov90: 0.8662,
      cqrSymWinkler90: 106.832,
      cqrAsymCov90: 0.8803,
      cqrAsymWinkler90: 130.5715,
      gate8595: "fail",
    },
  ] satisfies CqrForecastRow[],
};
