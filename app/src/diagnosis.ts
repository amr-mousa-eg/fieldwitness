/**
 * Diagnostic Breakdown of Hindcast Skill (Kansas Pilot).
 * Pre-registered in DECISIONS.md (commit e021f3e).
 *
 * Source: results/hindcast/diagnosis.json
 */

export interface BaselineComparison {
  n_total?: number;
  n_paired_baselines?: number;
  n?: number;
  fw_crps_mean: number;
  fw_crps_ci95: [number, number];
  b1_crps_mean: number | null;
  b2_crps_mean: number | null;
  diff_vs_b1_mean: number | null;
  diff_vs_b1_ci95: [number, number] | null;
  beats_b1: boolean | null;
  diff_vs_b2_mean: number | null;
  diff_vs_b2_ci95: [number, number] | null;
  beats_b2: boolean | null;
  status?: string;
  note?: string;
}

export interface ExploratoryCell {
  category: string;
  n: number;
  status?: string;
  fw_crps_mean?: number;
  fw_crps_ci95?: [number, number];
  fw_peak_err_mean?: number;
  fw_peak_err_ci95?: [number, number];
  fw_cov90_mean?: number;
  fw_cov90_ci95?: [number, number];
  diff_vs_b1_ci95?: [number, number] | null;
  verdict_vs_b1?: string;
  diff_vs_b2_ci95?: [number, number] | null;
  verdict_vs_b2?: string;
}

export interface DiagnosticFinding {
  dimension: string;
  finding: string;
  cause: string;
}

export interface DiagnosisData {
  analysis: string;
  pre_registration: string;
  cut_off_date: string;
  sample_size: number;
  primary_question: {
    hypothesis: string;
    success_criterion: string;
    results: {
      overall: BaselineComparison;
      by_crop: Record<string, BaselineComparison>;
    };
  };
  exploratory_breakdowns: {
    by_crop: ExploratoryCell[];
    by_year: ExploratoryCell[];
    by_field_size: ExploratoryCell[];
    by_grade: ExploratoryCell[];
    by_hls_obs: ExploratoryCell[];
  };
  findings: DiagnosticFinding[];
}

export const DIAGNOSIS_DATA: DiagnosisData = {
  analysis: "Diagnostic breakdown of forecast-mode hindcast errors (Kansas pilot)",
  pre_registration: "DECISIONS.md commit e021f3e",
  cut_off_date: "2021-12-31",
  sample_size: 463,
  primary_question: {
    hypothesis: "FieldWitness beats B1 (FAO table) and B2 (prior) on forecast-mode canopy-integral CRPS overall and in each crop",
    success_criterion: "95% bootstrap CI of (Baseline CRPS - FieldWitness CRPS) strictly > 0",
    results: {
      overall: {
        n_total: 463,
        n_paired_baselines: 463,
        fw_crps_mean: 17.86,
        fw_crps_ci95: [16.42, 19.35],
        b1_crps_mean: 19.67,
        b2_crps_mean: 20.45,
        diff_vs_b1_mean: 1.81,
        diff_vs_b1_ci95: [1.39, 2.22],
        beats_b1: true,
        diff_vs_b2_mean: 2.59,
        diff_vs_b2_ci95: [2.04, 3.1],
        beats_b2: true,
        note: "Baselines B1 and B2 evaluated across n=463 paired field-seasons (maize, sorghum, winter_wheat).",
      },
      by_crop: {
        maize: {
          n: 124,
          fw_crps_mean: 18.23,
          fw_crps_ci95: [15.99, 20.72],
          b1_crps_mean: 20.68,
          b2_crps_mean: 21.24,
          diff_vs_b1_mean: 2.45,
          diff_vs_b1_ci95: [1.59, 3.32],
          beats_b1: true,
          diff_vs_b2_mean: 3.01,
          diff_vs_b2_ci95: [1.91, 4.04],
          beats_b2: true,
          status: "evaluated",
        },
        sorghum: {
          n: 142,
          fw_crps_mean: 12.7,
          fw_crps_ci95: [10.58, 15.16],
          b1_crps_mean: 14.07,
          b2_crps_mean: 14.5,
          diff_vs_b1_mean: 1.37,
          diff_vs_b1_ci95: [0.56, 2.18],
          beats_b1: true,
          diff_vs_b2_mean: 1.8,
          diff_vs_b2_ci95: [0.97, 2.56],
          beats_b2: true,
          status: "evaluated",
        },
        winter_wheat: {
          n: 197,
          fw_crps_mean: 21.36,
          fw_crps_ci95: [19.39, 23.5],
          b1_crps_mean: 23.08,
          b2_crps_mean: 24.24,
          diff_vs_b1_mean: 1.73,
          diff_vs_b1_ci95: [1.22, 2.14],
          beats_b1: true,
          diff_vs_b2_mean: 2.89,
          diff_vs_b2_ci95: [2.06, 3.64],
          beats_b2: true,
          status: "evaluated",
        },
        fallow: {
          n: 0,
          status: "too few to judge",
          beats_b1: null,
          beats_b2: null,
          fw_crps_mean: 0,
          fw_crps_ci95: [0, 0],
          b1_crps_mean: null,
          b2_crps_mean: null,
          diff_vs_b1_mean: null,
          diff_vs_b1_ci95: null,
          diff_vs_b2_mean: null,
          diff_vs_b2_ci95: null,
        },
      },
    },
  },
  exploratory_breakdowns: {
    by_crop: [
      {
        category: "maize",
        n: 124,
        fw_crps_mean: 18.23,
        fw_crps_ci95: [15.99, 20.72],
        fw_peak_err_mean: 17.2,
        fw_peak_err_ci95: [14.1, 21.1],
        fw_cov90_mean: 0.234,
        fw_cov90_ci95: [0.151, 0.321],
        diff_vs_b1_ci95: [1.59, 3.32],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [1.91, 4.04],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "sorghum",
        n: 142,
        fw_crps_mean: 12.7,
        fw_crps_ci95: [10.58, 15.16],
        fw_peak_err_mean: 16.3,
        fw_peak_err_ci95: [13.7, 19.5],
        fw_cov90_mean: 0.373,
        fw_cov90_ci95: [0.28, 0.465],
        diff_vs_b1_ci95: [0.56, 2.18],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.97, 2.56],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "winter_wheat",
        n: 197,
        fw_crps_mean: 21.36,
        fw_crps_ci95: [19.39, 23.5],
        fw_peak_err_mean: 56.0,
        fw_peak_err_ci95: [48.6, 63.9],
        fw_cov90_mean: 0.254,
        fw_cov90_ci95: [0.194, 0.318],
        diff_vs_b1_ci95: [1.22, 2.14],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [2.06, 3.64],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "fallow",
        n: 0,
        status: "too few to judge",
      },
    ],
    by_year: [
      {
        category: "2022",
        n: 134,
        fw_crps_mean: 19.31,
        fw_crps_ci95: [16.87, 21.73],
        fw_peak_err_mean: 37.7,
        fw_peak_err_ci95: [30.0, 46.4],
        fw_cov90_mean: 0.224,
        fw_cov90_ci95: [0.157, 0.296],
        diff_vs_b1_ci95: [1.28, 2.8],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [3.15, 4.67],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "2023",
        n: 129,
        fw_crps_mean: 18.75,
        fw_crps_ci95: [16.25, 21.63],
        fw_peak_err_mean: 30.6,
        fw_peak_err_ci95: [22.6, 40.0],
        fw_cov90_mean: 0.279,
        fw_cov90_ci95: [0.207, 0.352],
        diff_vs_b1_ci95: [1.67, 2.97],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [3.33, 4.64],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "2024",
        n: 200,
        fw_crps_mean: 16.32,
        fw_crps_ci95: [14.21, 18.49],
        fw_peak_err_mean: 32.5,
        fw_peak_err_ci95: [28.0, 37.2],
        fw_cov90_mean: 0.33,
        fw_cov90_ci95: [0.262, 0.4],
        diff_vs_b1_ci95: [0.81, 1.92],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [-0.15, 1.67],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)",
      },
    ],
    by_field_size: [
      {
        category: "<10 ha",
        n: 115,
        fw_crps_mean: 20.28,
        fw_crps_ci95: [16.95, 23.93],
        fw_peak_err_mean: 37.1,
        fw_peak_err_ci95: [30.3, 45.2],
        fw_cov90_mean: 0.235,
        fw_cov90_ci95: [0.159, 0.311],
        diff_vs_b1_ci95: [0.48, 1.83],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [1.34, 2.97],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "10-50 ha",
        n: 176,
        fw_crps_mean: 16.45,
        fw_crps_ci95: [14.44, 18.3],
        fw_peak_err_mean: 31.5,
        fw_peak_err_ci95: [25.8, 37.9],
        fw_cov90_mean: 0.318,
        fw_cov90_ci95: [0.254, 0.387],
        diff_vs_b1_ci95: [1.38, 2.76],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [1.52, 3.2],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: ">50 ha",
        n: 172,
        fw_crps_mean: 17.69,
        fw_crps_ci95: [15.78, 19.72],
        fw_peak_err_mean: 33.0,
        fw_peak_err_ci95: [27.0, 39.9],
        fw_cov90_mean: 0.285,
        fw_cov90_ci95: [0.223, 0.347],
        diff_vs_b1_ci95: [1.25, 2.81],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [2.08, 3.96],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
    ],
    by_grade: [
      {
        category: "B",
        n: 139,
        fw_crps_mean: 17.93,
        fw_crps_ci95: [15.55, 20.43],
        fw_peak_err_mean: 28.7,
        fw_peak_err_ci95: [22.5, 35.4],
        fw_cov90_mean: 0.259,
        fw_cov90_ci95: [0.185, 0.327],
        diff_vs_b1_ci95: [0.61, 2.27],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.74, 2.34],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "C",
        n: 299,
        fw_crps_mean: 17.25,
        fw_crps_ci95: [15.62, 18.76],
        fw_peak_err_mean: 35.6,
        fw_peak_err_ci95: [30.3, 41.4],
        fw_cov90_mean: 0.301,
        fw_cov90_ci95: [0.253, 0.347],
        diff_vs_b1_ci95: [1.58, 2.57],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [2.57, 3.99],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
      {
        category: "D",
        n: 25,
        fw_crps_mean: 24.81,
        fw_crps_ci95: [16.8, 30.85],
        fw_peak_err_mean: 34.9,
        fw_peak_err_ci95: [23.4, 45.9],
        fw_cov90_mean: 0.24,
        fw_cov90_ci95: [0.071, 0.474],
        diff_vs_b1_ci95: [-0.99, 3.01],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [-0.18, 0.11],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)",
      },
    ],
    by_hls_obs: [
      {
        category: "<10",
        n: 0,
        status: "too few to judge",
      },
      {
        category: "10-19",
        n: 0,
        status: "too few to judge",
      },
      {
        category: ">=20",
        n: 463,
        fw_crps_mean: 17.86,
        fw_crps_ci95: [16.42, 19.35],
        fw_peak_err_mean: 33.5,
        fw_peak_err_ci95: [29.3, 38.0],
        fw_cov90_mean: 0.285,
        fw_cov90_ci95: [0.245, 0.323],
        diff_vs_b1_ci95: [1.39, 2.22],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [2.04, 3.1],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)",
      },
    ],
  },
  findings: [
    {
      dimension: "crop",
      finding: "Skill is highest (lowest CRPS) for sorghum (CRPS 12.70, 95% CI [10.58, 15.16]), followed by maize (CRPS 18.23, 95% CI [15.99, 20.72]), and lowest for winter wheat (CRPS 21.36, 95% CI [19.39, 23.50]).",
      cause: "cause not established",
    },
    {
      dimension: "crop_timing_anomaly",
      finding: "Winter wheat displays a severe timing error (peak timing absolute error 56.0 d, 95% CI [48.6, 63.9] d; median signed timing error +30.0 d).",
      cause: "Proposed explanation (not tested): Predicted peak DOY is systematically ~30 days later than observed heading in Kansas (late May vs July model peak). Phenology prior stage lengths for winter wheat require calibration (proposed as a separate decision).",
    },
    {
      dimension: "year",
      finding: "By year: 2024 (CRPS 16.32, 95% CI [14.21, 18.49]), 2023 (CRPS 18.75, 95% CI [16.25, 21.63]), and 2022 (CRPS 19.31, 95% CI [16.87, 21.73]), with overlapping bootstrap intervals.",
      cause: "cause not established",
    },
    {
      dimension: "field_size",
      finding: "Skill is comparable across all field size classes (<10 ha: CRPS 20.28, 95% CI [16.95, 23.93]; 10-50 ha: CRPS 16.45, 95% CI [14.44, 18.30]; >50 ha: CRPS 17.69, 95% CI [15.78, 19.72]).",
      cause: "cause not established",
    },
    {
      dimension: "grade",
      finding: "Evidence Grade B exhibits average CRPS of 17.93 [15.55, 20.43], Grade C exhibits average CRPS of 17.25 [15.62, 18.76], Grade D exhibits average CRPS of 24.81 [16.80, 30.85], with overlapping spatial bootstrap uncertainty.",
      cause: "cause not established",
    },
    {
      dimension: "hls_observations",
      finding: "463 of 463 Kansas field-seasons had >=20 clear HLS observations (bins <10 and 10-19 had n<20, too few to judge).",
      cause: "Semi-arid clear skies and dual Sentinel-2 / Landsat coverage over tile T14SLH produced dense time series across all fields.",
    },
  ],
};
