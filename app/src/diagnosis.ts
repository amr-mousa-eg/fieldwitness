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
        n_paired_baselines: 266,
        fw_crps_mean: 14.86,
        fw_crps_ci95: [13.20, 16.71],
        b1_crps_mean: 16.10,
        b2_crps_mean: 16.22,
        diff_vs_b1_mean: 1.23,
        diff_vs_b1_ci95: [0.48, 1.99],
        beats_b1: true,
        diff_vs_b2_mean: 1.35,
        diff_vs_b2_ci95: [0.74, 1.90],
        beats_b2: true,
        note: "Baselines B1 and B2 were generated in T7.3 for maize and sorghum (n=266). Winter wheat baselines were omitted in T7.3."
      },
      by_crop: {
        maize: {
          n: 124,
          fw_crps_mean: 17.68,
          fw_crps_ci95: [15.22, 20.38],
          b1_crps_mean: 19.45,
          b2_crps_mean: 19.71,
          diff_vs_b1_mean: 1.77,
          diff_vs_b1_ci95: [0.73, 2.89],
          beats_b1: true,
          diff_vs_b2_mean: 2.03,
          diff_vs_b2_ci95: [1.17, 2.87],
          beats_b2: true,
          status: "evaluated"
        },
        sorghum: {
          n: 142,
          fw_crps_mean: 12.41,
          fw_crps_ci95: [10.01, 14.73],
          b1_crps_mean: 13.17,
          b2_crps_mean: 13.16,
          diff_vs_b1_mean: 0.77,
          diff_vs_b1_ci95: [-0.10, 1.64],
          beats_b1: false,
          diff_vs_b2_mean: 0.76,
          diff_vs_b2_ci95: [-0.06, 1.53],
          beats_b2: false,
          status: "evaluated"
        },
        winter_wheat: {
          n: 197,
          fw_crps_mean: 21.15,
          fw_crps_ci95: [18.78, 23.42],
          b1_crps_mean: null,
          b2_crps_mean: null,
          diff_vs_b1_mean: null,
          diff_vs_b1_ci95: null,
          beats_b1: null,
          diff_vs_b2_mean: null,
          diff_vs_b2_ci95: null,
          beats_b2: null,
          status: "baseline not computed in T7.3"
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
          diff_vs_b2_ci95: null
        }
      }
    }
  },
  exploratory_breakdowns: {
    by_crop: [
      {
        category: "maize",
        n: 124,
        fw_crps_mean: 17.68,
        fw_crps_ci95: [15.22, 20.38],
        fw_peak_err_mean: 14.9,
        fw_peak_err_ci95: [12.3, 18.2],
        fw_cov90_mean: 0.274,
        fw_cov90_ci95: [0.198, 0.351],
        diff_vs_b1_ci95: [0.73, 2.89],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [1.17, 2.87],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: "sorghum",
        n: 142,
        fw_crps_mean: 12.41,
        fw_crps_ci95: [10.01, 14.73],
        fw_peak_err_mean: 16.2,
        fw_peak_err_ci95: [13.5, 18.7],
        fw_cov90_mean: 0.437,
        fw_cov90_ci95: [0.355, 0.533],
        diff_vs_b1_ci95: [-0.10, 1.64],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [-0.06, 1.53],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)"
      },
      {
        category: "winter_wheat",
        n: 197,
        fw_crps_mean: 21.15,
        fw_crps_ci95: [18.78, 23.42],
        fw_peak_err_mean: 58.9,
        fw_peak_err_ci95: [52.2, 66.3],
        fw_cov90_mean: 0.239,
        fw_cov90_ci95: [0.184, 0.299],
        diff_vs_b1_ci95: null,
        verdict_vs_b1: "not evaluated (no baseline)",
        diff_vs_b2_ci95: null,
        verdict_vs_b2: "not evaluated (no baseline)"
      },
      {
        category: "fallow",
        n: 0,
        status: "too few to judge"
      }
    ],
    by_year: [
      {
        category: "2022",
        n: 134,
        fw_crps_mean: 15.28,
        fw_crps_ci95: [12.93, 17.60],
        fw_peak_err_mean: 37.7,
        fw_peak_err_ci95: [30.9, 46.1],
        fw_cov90_mean: 0.269,
        fw_cov90_ci95: [0.200, 0.339],
        diff_vs_b1_ci95: [-0.05, 2.10],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [0.35, 1.95],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: "2023",
        n: 129,
        fw_crps_mean: 12.37,
        fw_crps_ci95: [9.21, 16.08],
        fw_peak_err_mean: 29.9,
        fw_peak_err_ci95: [22.4, 38.0],
        fw_cov90_mean: 0.295,
        fw_cov90_ci95: [0.215, 0.371],
        diff_vs_b1_ci95: [0.55, 2.25],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.65, 2.30],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: "2024",
        n: 200,
        fw_crps_mean: 16.07,
        fw_crps_ci95: [13.26, 19.16],
        fw_peak_err_mean: 34.3,
        fw_peak_err_ci95: [30.9, 38.5],
        fw_cov90_mean: 0.345,
        fw_cov90_ci95: [0.279, 0.413],
        diff_vs_b1_ci95: [0.30, 2.15],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [-0.10, 1.85],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)"
      }
    ],
    by_field_size: [
      {
        category: "<10 ha",
        n: 115,
        fw_crps_mean: 16.88,
        fw_crps_ci95: [13.13, 21.19],
        fw_peak_err_mean: 36.7,
        fw_peak_err_ci95: [29.1, 44.8],
        fw_cov90_mean: 0.287,
        fw_cov90_ci95: [0.209, 0.372],
        diff_vs_b1_ci95: [-0.20, 2.10],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [-0.15, 2.05],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)"
      },
      {
        category: "10-50 ha",
        n: 176,
        fw_crps_mean: 14.20,
        fw_crps_ci95: [11.71, 16.77],
        fw_peak_err_mean: 33.3,
        fw_peak_err_ci95: [27.9, 39.8],
        fw_cov90_mean: 0.318,
        fw_cov90_ci95: [0.256, 0.390],
        diff_vs_b1_ci95: [0.35, 1.85],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.55, 1.95],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: ">50 ha",
        n: 172,
        fw_crps_mean: 14.17,
        fw_crps_ci95: [11.99, 16.38],
        fw_peak_err_mean: 33.0,
        fw_peak_err_ci95: [26.9, 39.8],
        fw_cov90_mean: 0.314,
        fw_cov90_ci95: [0.242, 0.386],
        diff_vs_b1_ci95: [0.45, 1.90],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.60, 2.00],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      }
    ],
    by_grade: [
      {
        category: "B",
        n: 170,
        fw_crps_mean: 14.76,
        fw_crps_ci95: [12.36, 17.12],
        fw_peak_err_mean: 29.2,
        fw_peak_err_ci95: [24.5, 34.5],
        fw_cov90_mean: 0.324,
        fw_cov90_ci95: [0.253, 0.394],
        diff_vs_b1_ci95: [-0.15, 1.80],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [0.20, 1.75],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: "C",
        n: 268,
        fw_crps_mean: 14.40,
        fw_crps_ci95: [12.47, 16.52],
        fw_peak_err_mean: 37.1,
        fw_peak_err_ci95: [32.2, 42.6],
        fw_cov90_mean: 0.306,
        fw_cov90_ci95: [0.250, 0.359],
        diff_vs_b1_ci95: [0.40, 1.85],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.55, 1.90],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      },
      {
        category: "D",
        n: 25,
        fw_crps_mean: 19.97,
        fw_crps_ci95: [10.20, 29.20],
        fw_peak_err_mean: 34.4,
        fw_peak_err_ci95: [23.5, 45.1],
        fw_cov90_mean: 0.240,
        fw_cov90_ci95: [0.071, 0.474],
        diff_vs_b1_ci95: [-0.50, 3.20],
        verdict_vs_b1: "comparable within uncertainty (CI spans 0)",
        diff_vs_b2_ci95: [-0.40, 3.10],
        verdict_vs_b2: "comparable within uncertainty (CI spans 0)"
      }
    ],
    by_hls_obs: [
      {
        category: "<10",
        n: 0,
        status: "too few to judge"
      },
      {
        category: "10-19",
        n: 0,
        status: "too few to judge"
      },
      {
        category: ">=20",
        n: 463,
        fw_crps_mean: 14.86,
        fw_crps_ci95: [13.20, 16.71],
        fw_peak_err_mean: 34.0,
        fw_peak_err_ci95: [30.4, 37.9],
        fw_cov90_mean: 0.309,
        fw_cov90_ci95: [0.268, 0.351],
        diff_vs_b1_ci95: [0.48, 1.99],
        verdict_vs_b1: "FieldWitness beats baseline (CI > 0)",
        diff_vs_b2_ci95: [0.74, 1.90],
        verdict_vs_b2: "FieldWitness beats baseline (CI > 0)"
      }
    ]
  },
  findings: [
    {
      dimension: "crop",
      finding: "Skill is highest (lowest CRPS) for sorghum (CRPS 12.41, 95% CI [10.01, 14.73]), followed by maize (CRPS 17.68, 95% CI [15.22, 20.38]), and lowest for winter wheat (CRPS 21.15, 95% CI [18.78, 23.42]).",
      cause: "cause not established"
    },
    {
      dimension: "crop_timing_anomaly",
      finding: "Winter wheat displays a severe timing error (peak timing absolute error 58.9 d, 95% CI [52.2, 66.3] d; median signed timing error +36.0 d).",
      cause: "Predicted peak DOY is systematically ~36 days later than observed heading in Kansas (late May vs July model peak). Phenology prior stage lengths for winter wheat require calibration (proposed as a separate decision)."
    },
    {
      dimension: "year",
      finding: "Skill is higher in 2024 (CRPS 16.07, 95% CI [13.26, 19.16]) than in 2022 (CRPS 15.28, 95% CI [12.93, 17.60]) and 2023 (CRPS 12.37, 95% CI [9.21, 16.08]), with intervals broadly overlapping.",
      cause: "cause not established"
    },
    {
      dimension: "field_size",
      finding: "Skill is comparable across all field size classes (<10 ha: CRPS 16.88, 95% CI [13.13, 21.19]; 10–50 ha: CRPS 14.20, 95% CI [11.71, 16.77]; >50 ha: CRPS 14.17, 95% CI [11.99, 16.38]).",
      cause: "cause not established"
    },
    {
      dimension: "grade",
      finding: "Evidence Grade B exhibits average CRPS of 14.76 [12.36, 17.12] vs Grade C of 14.40 [12.47, 16.52] and Grade D of 19.97 [10.20, 29.20], but differences remain within spatial bootstrap uncertainty.",
      cause: "cause not established"
    },
    {
      dimension: "hls_observations",
      finding: "All 463 Kansas field-seasons had >=20 clear HLS observations (bins <10 and 10–19 had n=0, too few to judge).",
      cause: "Semi-arid clear skies and dual Sentinel-2 / Landsat coverage over tile T14SLH produced dense time series across all fields."
    }
  ]
};
