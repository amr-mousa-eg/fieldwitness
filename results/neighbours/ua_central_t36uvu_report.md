# Neighbours Witness Evaluation — Central Ukraine (`ua_central_t36uvu`) vs Kansas (`ks_t14slh`)

Executed with `scripts/run_ukraine_neighbours.py`.

## Provenance & Tier 3 Caveat

- **Region:** `ua_central_t36uvu` (Central Ukraine, Kirovohrad oblast area, HLS/S2 tile `EPSG:32636`, Tier 3).
- **Sample:** 395 unique FTW pilot fields inside 2×2 Sentinel-2 L2A 20 m COG window `tx in {1,2}, ty in {7,8}` spanning 8 10 km spatial blocks (area ≥ 5 ha, 0 scale-flagged).
- **Labels (`crop_source = "classifier"`, tag D):** Zero public multi-year ground labels exist (`labels.source == "none"`). Annual crop sequences (`winter_wheat`, `sunflower`, `maize`, `fallow`) were inferred strictly causally (`<= year-12-31`) from Sentinel-2 L2A 20 m NDVI via Savitzky–Golay phenology + Phase 1 TWDTW.
- **Winter Wheat Outcome Coverage Note:** Under frozen `table.py`'s window rule (`WINDOWS["winter_wheat"] = (1, 196)` requiring ≥ 80% coverage across Jan 1–Jul 15), `crop == "winter_wheat"` outcome rows have `n = 0` in Central Ukraine because snow/winter cloud at `48.2°N` leaves Dec–Feb clear S2 observations sparse until ~Mar 1 (DOY 60). Rather than loosening frozen thresholds, `winter_wheat` is tested extensively as a preceding treatment (`prev_crop == winter_wheat`: `n = 434` across 2018–2024, `n = 193` pre-cutoff `<= 2021`; `prev2_crop == winter_wheat`: `n = 292`).
- **Kansas baseline (`ks_t14slh`, Tier 1):** 200 CSB fields across 30 spatial blocks with USDA CSB ground labels (`crop_source = "label"`, tag E).

## Headline Summary (Pre-cutoff `year <= 2021` vs Full `2018–2024` & Kansas)

| Design | Region & Period | Fitted rows | Overlap pass | Balance pass | Placebo pass | NegCtrl pass | **Evidence (all 4 pass)** |
|---|---|---:|---:|---:|---:|---:|---:|
| Primary DML (`dml.py`) | Kansas `ks_t14slh` (2018–2024) | 92 | 60/92 | 0/92 | 50/56 | 23/28 | **0** |
| Primary DML (`dml.py`) | Ukraine `ua_central_t36uvu` (`<=2021`) | 64 | 52/64 | 12/64 | 23/44 | 16/32 | **7** |
| Primary DML (`dml.py`) | Ukraine `ua_central_t36uvu` (2018–2024) | 72 | 64/72 | 48/72 | 36/64 | 31/60 | **11** |
| Matching DML (`matching.py`) | Kansas `ks_t14slh` (2018–2024) | 32 | 32/32 | 8/32 | 7/12 | 23/28 | **0** |
| Matching DML (`matching.py`) | Ukraine `ua_central_t36uvu` (`<=2021`) | 108 | 84/108 | 12/108 | 26/44 | 35/60 | **4** |
| Matching DML (`matching.py`) | Ukraine `ua_central_t36uvu` (2018–2024) | 172 | 144/172 | 36/172 | 107/144 | 73/112 | **13** |
| DAPSM (`dapsm.py`) | Kansas `ks_t14slh` (`<=2021`, `w*=0.0`) | 4 | 4/4 | 0/4 | 0/0 (4 untested) | 0/0 (4 untested) | **0** |
| DAPSM (`dapsm.py`) | Ukraine `ua_central_t36uvu` (`<=2021`, `w*=0.8`) | 108 | 84/108 | 0/108 | 22/44 | 46/60 | **0** |
| DAPSM (`dapsm.py`) | Ukraine `ua_central_t36uvu` (2018–2024, `w*=0.4`) | 172 | 144/172 | 8/172 | 92/144 | 67/112 | **1** |

## DAPSM w-Grid (`ua_central_t36uvu`, pre-cutoff `<= 2021`)

| w | Median max \|SMD\| | Mean max \|SMD\| | Balance pass (≤ 0.25) |
|---:|---:|---:|---:|
| 0.0 | 0.745 | 1.408 | 0/108 |
| 0.1 | 0.747 | 1.185 | 0/108 |
| 0.2 | 0.586 | 1.004 | 0/108 |
| 0.3 | 0.585 | 0.981 | 0/108 |
| 0.4 | 0.582 | 0.975 | 0/108 |
| 0.5 | 0.578 | 0.955 | 4/108 |
| 0.6 | 0.606 | 0.969 | 4/108 |
| 0.7 | 0.557 | 0.938 | 0/108 |
| 0.8 | 0.534 | 0.918 | 0/108 |
| 0.9 | 0.555 | 0.925 | 4/108 |
| 1.0 | 0.625 | 0.990 | 4/108 |

## Witness Status Verdict

- **Pre-registered gates cleared in Ukraine:** 11 pre-cutoff (`<= 2021`) and 25 full-period (`2018–2024`) contrast-outcome-stratum rows passed all four checks (overlap, balance, placebo, negative control).
- **Critical Tier 3 Disclosure:** Because Ukraine crop states are inferred by an unvalidated NDVI classifier (`crop_source = "classifier"`, tag `D`) rather than ground labels, and `config/grading.yaml` + production Kansas packs (`app/public/packs/ks_t14slh/`) are locked, Neighbours stays OFF in grading until cross-validated against ground truth and explicitly approved.

### Contrasts Passing All Four Gates

#### primary_dml (18 rows)
- `pre_cutoff_le_2021` | `sunflower`: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-6.296** (95% CI [-10.082, -2.511])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.838** (95% CI [-2.841, -0.835])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`dry`): **-1.495** (95% CI [-2.841, -0.150])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.016** (95% CI [-0.029, -0.003])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`dry`): **-0.025** (95% CI [-0.043, -0.007])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`all`): **-3.726** (95% CI [-6.441, -1.010])
- `pre_cutoff_le_2021` | `sunflower`: `maize` vs `sunflower` on `cover_days` (`dry`): **-3.576** (95% CI [-6.803, -0.348])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `canopy_integral` (`wet`): **-1.015** (95% CI [-2.605, +0.575])
- `full_2018_2024` | `sunflower`: `sunflower` vs `winter_wheat` on `cover_days` (`dry`): **-7.384** (95% CI [-11.148, -3.621])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.077** (95% CI [-1.932, -0.221])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`wet`): **-0.266** (95% CI [-1.480, +0.948])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_integral` (`dry`): **-1.267** (95% CI [-2.444, -0.090])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.008** (95% CI [-0.018, +0.002])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `peak_ndvi` (`dry`): **-0.008** (95% CI [-0.022, +0.007])
- `full_2018_2024` | `sunflower`: `maize` vs `sunflower` on `canopy_drop` (`dry`): **-0.012** (95% CI [-0.029, +0.005])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `canopy_integral` (`wet`): **-1.442** (95% CI [-2.723, -0.162])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `peak_ndvi` (`wet`): **-0.048** (95% CI [-0.060, -0.036])
- `full_2018_2024` | `sunflower`: `maize` vs `winter_wheat` on `cover_days` (`wet`): **+10.402** (95% CI [+6.205, +14.600])

#### matching_dml (17 rows)
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-2.489** (95% CI [-4.597, -0.381])
- `pre_cutoff_le_2021` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.029** (95% CI [-0.056, -0.003])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-1.642** (95% CI [-3.225, -0.060])
- `pre_cutoff_le_2021` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.015** (95% CI [-0.037, +0.006])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_integral` (`all`): **-0.938** (95% CI [-2.267, +0.390])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `cover_days` (`all`): **-2.390** (95% CI [-6.385, +1.604])
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.010** (95% CI [-0.028, +0.007])
- `full_2018_2024` | `sunflower` [prev2=maize]: `sunflower` vs `winter_wheat` on `cover_days` (`all`): **-3.543** (95% CI [-8.288, +1.203])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `peak_ndvi` (`all`): **-0.004** (95% CI [-0.021, +0.013])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.003** (95% CI [-0.023, +0.018])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `cover_days` (`all`): **+2.744** (95% CI [-2.314, +7.802])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `maize` vs `winter_wheat` on `canopy_drop` (`all`): **-0.090** (95% CI [-0.113, -0.067])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_integral` (`dry`): **-6.139** (95% CI [-8.162, -4.116])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`all`): **-0.053** (95% CI [-0.069, -0.037])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `peak_ndvi` (`dry`): **-0.075** (95% CI [-0.098, -0.053])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_drop` (`all`): **-0.061** (95% CI [-0.080, -0.042])
- `full_2018_2024` | `sunflower` [prev2=sunflower]: `sunflower` vs `winter_wheat` on `canopy_drop` (`dry`): **-0.083** (95% CI [-0.110, -0.056])

#### dapsm (1 rows)
- `full_2018_2024` | `sunflower` [prev2=maize]: `maize` vs `sunflower` on `canopy_drop` (`all`): **-0.032** (95% CI [-0.066, -0.010])

