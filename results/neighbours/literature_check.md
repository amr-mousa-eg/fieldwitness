# T5.4 literature check: signs of previous-crop effects (Kansas pilot fields)

Source: `scripts/t54_literature.py` (reads `effects.csv`, `diagnostics.csv`).

## Sources

- Kluger, Di Tommaso & Lobell, *Precrop Payoffs: Causal machine learning reveals large but
  variable yield benefits of crop rotation in major breadbaskets*, arXiv:2506.02384v2 (14 Oct 2025),
  Environ. Res. Lett. 20 (2025) 114037. Table S9, column Eff_2-year, US rows (precrop A on crop B
  vs B after B, % of mean US yield of B, all significant at p < 0.05). v1 (3 Jun 2025) was titled
  *Evaluating crop rotations around the world using satellite imagery and causal machine learning*.
- NASA Earth Observatory, *How to Rotate Crops* (A. Voiland, 28 Jul 2025),
  <https://science.nasa.gov/earth/earth-observatory/how-to-rotate-crops-154601/>.
  It reports the same study (corn after winter wheat +0.9 %, soybean then winter wheat about
  -12 %, rotation helps more in rainier conditions). It does not mention sorghum or fallow.

Values were read from the arXiv HTML through a page-reading tool, twice, and the two corn rows match
the NASA article. They were not checked against the PDF.

## What is compared, and the caveats

- Only transitions among maize, winter wheat, sorghum and fallow (our Kansas crops). The paper
  has no sorghum and no fallow outcome; US rows used: F->WW +8.3 %, C->WW +4.0 %, WW->C +0.9 %.
- **Their outcome is yield** (a peak-GCVI proxy calibrated to county yields). **Ours are canopy
  and season outcomes** from HLS NDVI (peak NDVI, canopy integral, cover days, canopy drop).
  Peak NDVI is the closest analogue. A sign match is not a yield claim.
- Their control is the outcome crop after itself. Ours is a named reference previous crop; the
  F vs C contrast on wheat is an indirect comparison (difference of two published estimates).
- Their scope is US-wide (CDL masks, 2009-2021); ours is 200 fields in one HLS tile
  (T14SLH, Kansas).
- **None of our contrasts passes the T5.3 diagnostics** (`show_as_evidence` is False for all),
  so any agreement below is descriptive only and does not enter grading.
- Expected sign for `canopy_drop` is flipped (a larger drop is the worse direction).

## Summary (counts per stratum)

- all: DISAGREE 1, agree 2, inconclusive 13
- wet: inconclusive 8, not fitted 8
- dry: agree 4, inconclusive 12

## Comparisons

| crop | contrast (ours) | literature | outcome | stratum | n treated/ref | effect [95% CI] | expected sign | verdict | evidence (T5.3) |
|---|---|---|---|---|---|---|---|---|---|
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | peak_ndvi | all | 307/50 | -0.00589 [-0.0432, 0.0314] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | peak_ndvi | wet | 131/20 | 0.0342 [-0.00418, 0.0725] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | peak_ndvi | dry | 176/30 | -0.037 [-0.0985, 0.0245] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_integral | all | 307/50 | 4.35 [-0.514, 9.22] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_integral | wet | 131/20 | 4.74 [-2.67, 12.2] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_integral | dry | 176/30 | 1.21 [-6.25, 8.67] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | cover_days | all | 307/50 | -4.4 [-16.2, 7.39] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | cover_days | wet | 131/20 | -5.59 [-23.7, 12.5] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | cover_days | dry | 176/30 | -4.25 [-21.4, 12.9] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_drop | all | 307/50 | 0.00557 [-0.0401, 0.0513] | - | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_drop | wet | 131/20 | 0.018 [-0.0277, 0.0638] | - | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs winter_wheat | F->WW +8.3 % (direct) | canopy_drop | dry | 176/30 | 0.00087 [-0.0724, 0.0741] | - | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | peak_ndvi | all | 67/50 | -0.0153 [-0.0639, 0.0334] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | peak_ndvi | wet | 18/20 |  | + | not fitted | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | peak_ndvi | dry | 49/30 | -0.0166 [-0.0963, 0.0631] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_integral | all | 67/50 | -4.66 [-11.6, 2.29] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_integral | wet | 18/20 |  | + | not fitted | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_integral | dry | 49/30 | -0.842 [-11.1, 9.43] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | cover_days | all | 67/50 | -26.2 [-42.7, -9.73] | + | DISAGREE | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | cover_days | wet | 18/20 |  | + | not fitted | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | cover_days | dry | 49/30 | -6.76 [-28.1, 14.6] | + | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_drop | all | 67/50 | -0.0182 [-0.0837, 0.0474] | - | inconclusive (CI includes 0), sign same | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_drop | wet | 18/20 |  | - | not fitted | False |
| winter_wheat | maize vs winter_wheat | C->WW +4.0 % (direct) | canopy_drop | dry | 49/30 | 0.0232 [-0.0706, 0.117] | - | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | peak_ndvi | all | 307/67 | 0.00865 [-0.0355, 0.0528] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | peak_ndvi | wet | 131/18 |  | + | not fitted | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | peak_ndvi | dry | 176/49 | 0.0255 [-0.0339, 0.0849] | + | inconclusive (CI includes 0), sign same | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_integral | all | 307/67 | 8.2 [2.61, 13.8] | + | agree | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_integral | wet | 131/18 |  | + | not fitted | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_integral | dry | 176/49 | 8.86 [1.89, 15.8] | + | agree | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | cover_days | all | 307/67 | 19.3 [5.72, 32.9] | + | agree | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | cover_days | wet | 131/18 |  | + | not fitted | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | cover_days | dry | 176/49 | 16.4 [0.423, 32.3] | + | agree | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_drop | all | 307/67 | 0.00822 [-0.0397, 0.0561] | - | inconclusive (CI includes 0), sign opposite | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_drop | wet | 131/18 |  | - | not fitted | False |
| winter_wheat | fallow vs maize | F->WW +8.3 % minus C->WW +4.0 % = +4.3 % (indirect, difference of two estimates, untested) | canopy_drop | dry | 176/49 | 0.0128 [-0.0478, 0.0734] | - | inconclusive (CI includes 0), sign opposite | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | peak_ndvi | all | 92/111 | -0.0151 [-0.0524, 0.0221] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | peak_ndvi | wet | 59/85 | 0.0034 [-0.0378, 0.0446] | - | inconclusive (CI includes 0), sign opposite | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | peak_ndvi | dry | 33/26 | -0.0661 [-0.149, 0.0167] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_integral | all | 92/111 | -3.94 [-8.88, 1.01] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_integral | wet | 59/85 | -1.65 [-7.53, 4.23] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_integral | dry | 33/26 | -13.6 [-22.4, -4.77] | - | agree | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | cover_days | all | 92/111 | -7.29 [-14.6, 0.0391] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | cover_days | wet | 59/85 | -6.09 [-15.1, 2.89] | - | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | cover_days | dry | 33/26 | -14.1 [-28, -0.0962] | - | agree | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_drop | all | 92/111 | -0.00654 [-0.0439, 0.0308] | + | inconclusive (CI includes 0), sign opposite | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_drop | wet | 59/85 | 0.0185 [-0.0222, 0.0591] | + | inconclusive (CI includes 0), sign same | False |
| maize | maize vs winter_wheat | WW->C +0.9 % vs C->C, so C->C minus WW->C < 0 (direct) | canopy_drop | dry | 33/26 | -0.0508 [-0.133, 0.0316] | + | inconclusive (CI includes 0), sign opposite | False |

## Not compared (no literature counterpart among our crops)

- fallow: maize vs sorghum
- fallow: maize vs winter_wheat
- fallow: sorghum vs winter_wheat
- maize: maize vs sorghum
- maize: sorghum vs winter_wheat
- sorghum: maize vs sorghum
- sorghum: maize vs winter_wheat
- sorghum: sorghum vs winter_wheat
