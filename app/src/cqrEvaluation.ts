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
      storedCov90: 0.2081,
      storedWinkler90: 1082.9556,
      cqrSymCov90: 0.8985,
      cqrSymWinkler90: 274.9277,
      cqrAsymCov90: 0.8579,
      cqrAsymWinkler90: 231.3251,
      gate8595: "pass",
    },
    {
      crop: "maize",
      metric: "sos",
      n: 124,
      storedCov90: 0.3145,
      storedWinkler90: 235.2984,
      cqrSymCov90: 0.8952,
      cqrSymWinkler90: 138.7597,
      cqrAsymCov90: 0.9032,
      cqrAsymWinkler90: 148.169,
      gate8595: "pass",
    },
    {
      crop: "sorghum",
      metric: "sos",
      n: 142,
      storedCov90: 0.662,
      storedWinkler90: 351.3049,
      cqrSymCov90: 0.8944,
      cqrSymWinkler90: 283.3261,
      cqrAsymCov90: 0.8873,
      cqrAsymWinkler90: 233.3613,
      gate8595: "pass",
    },
    {
      crop: "winter_wheat",
      metric: "cover_days",
      n: 197,
      storedCov90: 0.0457,
      storedWinkler90: 822.9244,
      cqrSymCov90: 0.9594,
      cqrSymWinkler90: 244.1782,
      cqrAsymCov90: 0.8934,
      cqrAsymWinkler90: 246.8761,
      gate8595: "pass",
    },
    {
      crop: "maize",
      metric: "cover_days",
      n: 124,
      storedCov90: 0.1129,
      storedWinkler90: 577.9782,
      cqrSymCov90: 0.8226,
      cqrSymWinkler90: 196.8734,
      cqrAsymCov90: 0.7581,
      cqrAsymWinkler90: 212.1952,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "cover_days",
      n: 142,
      storedCov90: 0.0634,
      storedWinkler90: 559.8331,
      cqrSymCov90: 0.8873,
      cqrSymWinkler90: 226.6923,
      cqrAsymCov90: 0.7958,
      cqrAsymWinkler90: 213.3894,
      gate8595: "fail",
    },
    {
      crop: "winter_wheat",
      metric: "canopy_integral",
      n: 197,
      storedCov90: 0.2386,
      storedWinkler90: 317.9957,
      cqrSymCov90: 0.736,
      cqrSymWinkler90: 121.9803,
      cqrAsymCov90: 0.6853,
      cqrAsymWinkler90: 120.379,
      gate8595: "fail",
    },
    {
      crop: "maize",
      metric: "canopy_integral",
      n: 124,
      storedCov90: 0.2742,
      storedWinkler90: 271.6735,
      cqrSymCov90: 0.7742,
      cqrSymWinkler90: 116.1868,
      cqrAsymCov90: 0.7661,
      cqrAsymWinkler90: 116.7626,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "canopy_integral",
      n: 142,
      storedCov90: 0.4366,
      storedWinkler90: 179.9053,
      cqrSymCov90: 0.7042,
      cqrSymWinkler90: 120.9134,
      cqrAsymCov90: 0.662,
      cqrAsymWinkler90: 122.8249,
      gate8595: "fail",
    },
    {
      crop: "winter_wheat",
      metric: "peak",
      n: 197,
      storedCov90: 0.3452,
      storedWinkler90: 672.6896,
      cqrSymCov90: 0.8071,
      cqrSymWinkler90: 409.9769,
      cqrAsymCov90: 0.7817,
      cqrAsymWinkler90: 423.3381,
      gate8595: "fail",
    },
    {
      crop: "maize",
      metric: "peak",
      n: 124,
      storedCov90: 0.9274,
      storedWinkler90: 85.8016,
      cqrSymCov90: 0.9355,
      cqrSymWinkler90: 86.8661,
      cqrAsymCov90: 0.9355,
      cqrAsymWinkler90: 100.5113,
      gate8595: "fail",
    },
    {
      crop: "sorghum",
      metric: "peak",
      n: 142,
      storedCov90: 0.8451,
      storedWinkler90: 112.1479,
      cqrSymCov90: 0.8732,
      cqrSymWinkler90: 105.8859,
      cqrAsymCov90: 0.8944,
      cqrAsymWinkler90: 127.5282,
      gate8595: "fail",
    },
  ] satisfies CqrForecastRow[],
};
