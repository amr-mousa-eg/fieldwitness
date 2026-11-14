# Neighbours Witness Evaluation — Central Ukraine (`ua_central_t36uvu`) vs Kansas (`ks_t14slh`)

Executed with `scripts/run_ukraine_neighbours.py` (pre-registered 2026-11-14 in `DECISIONS.md`).

## Provenance & Regional Fixes

- **Region:** `ua_central_t36uvu` (Central Ukraine, Kirovohrad oblast area, Sentinel-2 tile `EPSG:32636`, Tier 3).
- **Sample:** 400 unique FTW pilot fields inside 2×2 Sentinel-2 L2A 20 m COG window `tx in {1,2}, ty in {7,8}` spanning 8 10 km spatial blocks (area >= 5 ha, 0 scale-flagged).
- **Labels (`crop_source = "classifier"`, tag D):** Annual crop sequences (`winter_wheat`, `sunflower`, `maize`, `fallow`) inferred strictly causally (`<= year-12-31`) from S2 L2A NDVI via Savitzky–Golay phenology + TWDTW and cross-checked in T2.4 (`results/story/ua_worldcereal_crosscheck.md`).
- **Winter Wheat Active Window (`WINDOWS_BY_REGION`):** Regional window `(60, 196)` (Mar 1–Jul 15, tag A) bypasses Dec–Feb snow mask at `48.2°N`, recovering `n = 467` (`n = 278` pre-cutoff `<= 2021`) winter-wheat outcome seasons while leaving `ks_t14slh` `(1, 196)` untouched.

## Headline Summary (Pre-cutoff `year <= 2021` vs Full `2018–2024` & Kansas)

| Design | Region & Period | Fitted rows | Overlap pass | Balance pass | Placebo pass | NegCtrl pass | **Evidence (all 4 pass)** |
|---|---|---:|---:|---:|---:|---:|---:|
| **Panel-OBDML (pooled, `panel_obdml.py`)** | Ukraine `ua_central_t36uvu` (`<=2021`) | 88 | 64/88 | 42/88 | 62/72 | 75/84 | **14** |
| **Panel-OBDML (pooled, `panel_obdml.py`)** | Ukraine `ua_central_t36uvu` (2018–2024) | 92 | 69/92 | 69/92 | 82/92 | 81/88 | **44** |
| **Panel-OBDML (`prev2`-matched)** | Ukraine `ua_central_t36uvu` (`<=2021`) | 132 | 93/132 | 24/132 | 52/64 | 119/128 | **13** |
| **Panel-OBDML (`prev2`-matched)** | Ukraine `ua_central_t36uvu` (2018–2024) | 240 | 155/240 | 43/240 | 173/192 | 216/240 | **12** |
| **Exact-Year DAPSM (`dapsm.py`)** | Ukraine `ua_central_t36uvu` (`<=2021`, `w*=0.5`) | 132 | 100/132 | 16/132 | 36/64 | 83/128 | **3** |
| **Exact-Year DAPSM (`dapsm.py`)** | Ukraine `ua_central_t36uvu` (2018–2024, `w*=0.5`) | 240 | 204/240 | 44/240 | 124/184 | 151/240 | **14** |
| Primary DML (legacy, `dml.py`) | Kansas `ks_t14slh` (2018–2024) | 92 | 60/92 | 0/92 | 50/56 | 23/28 | **0** |
| Primary DML (legacy, `dml.py`) | Ukraine `ua_central_t36uvu` (`<=2021`) | 88 | 76/88 | 24/88 | 45/72 | 26/32 | **8** |
| Primary DML (legacy, `dml.py`) | Ukraine `ua_central_t36uvu` (2018–2024) | 92 | 84/92 | 52/92 | 65/92 | 68/88 | **26** |
| Matching DML (legacy, `matching.py`) | Kansas `ks_t14slh` (2018–2024) | 32 | 32/32 | 8/32 | 7/12 | 23/28 | **0** |
| Matching DML (legacy, `matching.py`) | Ukraine `ua_central_t36uvu` (`<=2021`) | 132 | 100/132 | 8/132 | 41/64 | 58/64 | **6** |
| Matching DML (legacy, `matching.py`) | Ukraine `ua_central_t36uvu` (2018–2024) | 240 | 204/240 | 40/240 | 142/192 | 155/224 | **16** |
| DAPSM (legacy, `dapsm.py`) | Kansas `ks_t14slh` (`<=2021`, `w*=0.0`) | 4 | 4/4 | 0/4 | 0/0 (4 untested) | 0/0 (4 untested) | **0** |

## Exact-Year DAPSM w-Grid (`ua_central_t36uvu`, pre-cutoff `<= 2021`)

| w | Median max \|SMD\| | Mean max \|SMD\| | Balance pass (<= 0.25) |
|---:|---:|---:|---:|
| 0.0 | 0.515 | 0.722 | 28/132 |
| 0.1 | 0.522 | 0.630 | 24/132 |
| 0.2 | 0.556 | 0.673 | 16/132 |
| 0.3 | 0.556 | 0.716 | 20/132 |
| 0.4 | 0.501 | 0.676 | 28/132 |
| 0.5 | 0.488 | 0.706 | 16/132 |
| 0.6 | 0.510 | 0.697 | 12/132 |
| 0.7 | 0.523 | 0.772 | 4/132 |
| 0.8 | 0.558 | 0.781 | 4/132 |
| 0.9 | 0.625 | 0.715 | 4/132 |
| 1.0 | 0.752 | 0.778 | 0/132 |

## Witness Status Verdict

- **Pre-registered Panel-OBDML & Exact-Year DAPSM gates cleared:** 30 pre-cutoff (`<= 2021`) and 70 full-period (`2018–2024`) contrast-outcome-stratum rows passed all four causal checks (legacy DML+Matching: 14 pre-cutoff, 42 full-period).
- **Tier 3 Witness Integration:** Passing Panel-OBDML (`cover_days`, `canopy_integral`) witnesses carry uncertainty tag `D` (`crop_source = "classifier"`, T2.4 cross-checked) and are wired into `packs/demo/ua_central_t36uvu/` while Kansas `ks_t14slh` remains frozen OFF.

### Contrasts Passing All Four Gates

#### panel_obdml (58 rows)
- `pre_cutoff_le_2021` | `maize`: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.007** (95% CI [-0.026, +0.011])
- `pre_cutoff_le_2021` | `maize`: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.017** (95% CI [-0.038, +0.004])
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-4.509** (95% CI [-4.961, -4.058])
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.039** (95% CI [-0.054, -0.025])
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-4.808** (95% CI [-8.580, -1.037])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.611** (95% CI [-3.069, -0.154])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`dry`): **-1.714** (95% CI [-3.276, -0.152])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.010** (95% CI [-0.021, +0.000])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`all`): **-4.714** (95% CI [-8.965, -0.463])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`dry`): **-4.372** (95% CI [-7.771, -0.974])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.014** (95% CI [-0.030, +0.001])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `winter_wheat` on `canopy_integral` (`all`): **-5.719** (95% CI [-7.701, -3.738])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `winter_wheat` on `cover_days` (`all`): **-9.473** (95% CI [-14.061, -4.885])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.056** (95% CI [-0.074, -0.037])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_integral` (`all`): **-4.349** (95% CI [-7.331, -1.368])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_integral` (`wet`): **-4.303** (95% CI [-7.966, -0.641])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.011** (95% CI [-0.020, -0.003])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `peak_ndvi` (`wet`): **-0.010** (95% CI [-0.018, -0.001])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.006** (95% CI [-0.027, +0.015])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_drop` (`wet`): **-0.002** (95% CI [-0.029, +0.025])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-5.794** (95% CI [-10.141, -1.448])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `canopy_integral` (`wet`): **-5.577** (95% CI [-11.069, -0.085])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-9.798** (95% CI [-15.628, -3.967])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `cover_days` (`wet`): **-9.040** (95% CI [-19.080, +1.000])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.014** (95% CI [-0.034, +0.005])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `canopy_drop` (`wet`): **-0.013** (95% CI [-0.041, +0.015])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-4.311** (95% CI [-5.049, -3.573])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`dry`): **-5.175** (95% CI [-6.187, -4.164])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.046** (95% CI [-0.063, -0.030])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `peak_ndvi` (`dry`): **-0.053** (95% CI [-0.083, -0.023])
- ... (28 more rows in CSV/JSON)

#### panel_obdml_matching (25 rows)
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.008** (95% CI [-0.045, +0.028])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **-6.083** (95% CI [-11.536, -0.629])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.016** (95% CI [-0.061, +0.028])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-8.027** (95% CI [-13.686, -2.369])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.045** (95% CI [-0.105, +0.015])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-8.729** (95% CI [-22.392, +4.933])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.065** (95% CI [-0.106, -0.025])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.421** (95% CI [-2.487, -0.354])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.010** (95% CI [-0.030, +0.010])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `cover_days` (`all`): **-4.918** (95% CI [-10.412, +0.576])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.008** (95% CI [-0.029, +0.014])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-4.625** (95% CI [-7.224, -2.027])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.033** (95% CI [-0.060, -0.007])
- `full_2018_2024` | `maize` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-3.400** (95% CI [-7.551, +0.752])
- `full_2018_2024` | `maize` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.014** (95% CI [-0.038, +0.009])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.055** (95% CI [-2.107, -0.004])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **+0.249** (95% CI [-3.371, +3.869])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.016** (95% CI [-0.038, +0.007])
- `full_2018_2024` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-5.399** (95% CI [-7.154, -3.644])
- `full_2018_2024` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.060** (95% CI [-0.091, -0.030])
- `full_2018_2024` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-6.220** (95% CI [-12.549, +0.108])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.873** (95% CI [-2.519, -1.227])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.005** (95% CI [-0.026, +0.015])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.000** (95% CI [-0.023, +0.022])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.050** (95% CI [-0.095, -0.006])

#### dapsm (17 rows)
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-6.039** (95% CI [-7.334, -4.670])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.038** (95% CI [-0.056, -0.021])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.037** (95% CI [-0.052, -0.017])
- `full_2018_2024` | `maize` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-2.537** (95% CI [-11.213, +4.501])
- `full_2018_2024` | `maize` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `cover_days` (`wet`): **-2.090** (95% CI [-10.147, +4.334])
- `full_2018_2024` | `maize` [prev2=winter_wheat]: `sunflower` vs `winter_wheat` on `canopy_integral` (`wet`): **-9.346** (95% CI [-19.599, -3.307])
- `full_2018_2024` | `maize` [prev2=winter_wheat]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`wet`): **-0.011** (95% CI [-0.041, +0.022])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.759** (95% CI [-2.293, -0.539])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **-0.902** (95% CI [-5.517, +6.506])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.033** (95% CI [-0.056, -0.018])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `winter_wheat` on `canopy_integral` (`all`): **-7.833** (95% CI [-10.077, -5.844])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.068** (95% CI [-0.093, -0.052])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `winter_wheat` on `cover_days` (`all`): **-10.825** (95% CI [-18.313, +0.048])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.073** (95% CI [-0.112, -0.048])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.045** (95% CI [-0.067, -0.030])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-5.790** (95% CI [-6.765, -4.715])
- `full_2018_2024` | `winter_wheat` [prev2=maize]: `maize` vs `winter_wheat` on `cover_days` (`all`): **-5.000** (95% CI [-15.000, +0.424])

#### primary_dml (34 rows)
- `pre_cutoff_le_2021` | `maize`: `sunflower` vs `winter_wheat` on `cover_days` (`wet`): **-5.688** (95% CI [-12.790, +1.415])
- `pre_cutoff_le_2021` | `maize`: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.004** (95% CI [-0.020, +0.013])
- `pre_cutoff_le_2021` | `maize`: `sunflower` vs `winter_wheat` on `canopy_drop` (`wet`): **-0.008** (95% CI [-0.029, +0.012])
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-4.430** (95% CI [-5.841, -3.018])
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-3.522** (95% CI [-7.167, +0.124])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.331** (95% CI [-2.265, -0.398])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.004** (95% CI [-0.017, +0.010])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`all`): **-4.766** (95% CI [-7.447, -2.084])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_integral` (`all`): **-3.794** (95% CI [-5.462, -2.125])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `canopy_integral` (`wet`): **-3.888** (95% CI [-5.738, -2.038])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `cover_days` (`all`): **-4.570** (95% CI [-8.208, -0.932])
- `full_2018_2024` | `maize`: `maize` vs `winter_wheat` on `cover_days` (`wet`): **-4.828** (95% CI [-8.761, -0.894])
- `full_2018_2024` | `maize`: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-5.925** (95% CI [-11.731, -0.118])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`all`): **-4.429** (95% CI [-5.459, -3.399])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`wet`): **-2.147** (95% CI [-3.491, -0.803])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`dry`): **-5.113** (95% CI [-6.797, -3.429])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `cover_days` (`dry`): **-7.192** (95% CI [-11.604, -2.779])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`wet`): **-1.187** (95% CI [-2.319, -0.054])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`all`): **+0.003** (95% CI [-0.008, +0.013])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`wet`): **+0.005** (95% CI [-0.007, +0.017])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`all`): **-2.688** (95% CI [-5.192, -0.185])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`wet`): **-5.223** (95% CI [-9.079, -1.367])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_drop` (`wet`): **+0.006** (95% CI [-0.008, +0.020])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `canopy_integral` (`wet`): **-3.231** (95% CI [-4.442, -2.021])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `peak_ndvi` (`wet`): **-0.034** (95% CI [-0.045, -0.023])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `cover_days` (`all`): **-2.761** (95% CI [-5.987, +0.465])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `cover_days` (`wet`): **+0.706** (95% CI [-3.122, +4.534])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `canopy_drop` (`wet`): **-0.034** (95% CI [-0.047, -0.021])
- `full_2018_2024` | `winter_wheat`: `maize` vs `sunflower` on `canopy_integral` (`dry`): **-3.470** (95% CI [-6.755, -0.185])
- `full_2018_2024` | `winter_wheat`: `maize` vs `sunflower` on `peak_ndvi` (`dry`): **-0.006** (95% CI [-0.036, +0.025])
- ... (4 more rows in CSV/JSON)

#### matching_dml (22 rows)
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-2.082** (95% CI [-3.894, -0.270])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.014** (95% CI [-0.040, +0.011])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **-6.760** (95% CI [-11.554, -1.966])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.026** (95% CI [-0.055, +0.004])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.051** (95% CI [-0.076, -0.026])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.053** (95% CI [-0.082, -0.023])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-0.921** (95% CI [-2.170, +0.329])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.001** (95% CI [-0.017, +0.015])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **-0.741** (95% CI [-4.593, +3.110])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.004** (95% CI [-0.022, +0.015])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-2.048** (95% CI [-3.361, -0.736])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.008** (95% CI [-0.025, +0.010])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `cover_days` (`all`): **-5.768** (95% CI [-9.580, -1.956])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_integral` (`all`): **-4.231** (95% CI [-6.027, -2.436])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.044** (95% CI [-0.064, -0.024])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `peak_ndvi` (`dry`): **-0.099** (95% CI [-0.141, -0.056])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.040** (95% CI [-0.063, -0.017])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_drop` (`dry`): **-0.057** (95% CI [-0.110, -0.004])
- `full_2018_2024` | `sunflower` [prev2=winter_wheat]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.031** (95% CI [-0.059, -0.003])
- `full_2018_2024` | `sunflower` [prev2=winter_wheat]: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **+0.000** (95% CI [-0.033, +0.033])
- `full_2018_2024` | `winter_wheat` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`dry`): **-0.931** (95% CI [-5.948, +4.087])
- `full_2018_2024` | `winter_wheat` [prev2=maize]: `maize` vs `sunflower` on `peak_ndvi` (`dry`): **+0.011** (95% CI [-0.029, +0.050])

