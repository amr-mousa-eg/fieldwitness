# Advanced Predictive Algorithms: Phenology Extraction & Mapping Benchmark

Empirical evaluation of remote sensing phenological extraction algorithms across the
pre-registered Kansas pilot fields (Harmonized Landsat Sentinel-2, HLS tile `T14SLH`).

## 1. Held-Out Test Set Performance (240 Field-Seasons, 30 Spatial Blocks)

| Algorithm | Core Mechanism | Season Detection Match | Multi-Class Accuracy | Latency |
|---|---|---|---|---|
| **Savitzky-Golay + Thresholds (Baseline)** | Polynomial filter + amplitude thresholds | **78.3%** | 78.3% | 12.4 ms |
| **Standard DTW** | Unconstrained dynamic programming | **88.7%** | 56.2% | 4.8 ms |
| **TWDTW (Modified Logistic)** | Modified Logistic Weight Function (MLWF) | **86.7%** | 72.5% | 5.0 ms |
| **WDDTW (Derivative-Weighted)** | Slope derivatives + logistic time penalty | **82.9%** | 75.4% | 4.8 ms |
| **VDTW (Vector Spectral Angle)** | Spectral angle / cosine distance on [NDVI, EVI] | **70.8%** | 56.7% | 4.6 ms |
| **CropFormer (Self-Attention)** | Multi-head self-attention + temporal DOY encodings | **86.7%** | 75.8% | 1.1 ms |

## 2. Per-Crop Breakdown on Held-Out Test Set

| Algorithm | Winter Wheat (n=77) | Maize (n=41) | Sorghum (n=61) | Fallow (n=60) |
|---|---|---|---|---|
| **Savitzky-Golay + Thresholds (Baseline)** | 66.2% | 82.9% | 90.2% | 80.0% |
| **Standard DTW** | 85.7% | 87.8% | 100.0% | 83.3% |
| **TWDTW (Modified Logistic)** | 77.9% | 80.5% | 100.0% | 90.0% |
| **WDDTW (Derivative-Weighted)** | 72.7% | 75.6% | 91.8% | 93.3% |
| **VDTW (Vector Spectral Angle)** | 64.9% | 87.8% | 77.0% | 61.7% |
| **CropFormer (Self-Attention)** | 85.7% | 87.8% | 96.7% | 78.3% |

## 3. Algorithmic Trade-offs & Theoretical Analysis

1. **Savitzky-Golay + Amplitude Thresholds (Baseline: 78.3%):**
   - Fixed polynomial windows struggle across variable length crop cycles.
   - Winter wheat achieved only 66.2% due to dormancy dip misclassification.

2. **Standard DTW (56.2% Multi-Class):**
   - Disregards temporal coordinates, producing unconstrained warping.
   - Matches late-summer weed pulses to spring wheat profiles.

3. **Time-Weighted DTW (TWDTW: 72.5% Multi-Class, 86.7% Binary):**
   - Logistic penalty exponentially suppresses unconstrained time warping.
   - Winter wheat exact match surged to 72.7% and fallow to 90.0%.

4. **Weighted Derivative DTW (WDDTW: 75.4% Multi-Class, 82.9% Binary):**
   - Evaluates central-difference slopes, eliminating amplitude bias.

5. **Vector DTW (VDTW: 56.7% Multi-Class, 70.8% Binary):**
   - Multi-attribute spectral angle sensitive to semi-arid blue-band noise.

6. **CropFormer / Transformer Self-Attention (1.05 ms/field):**
   - Fully vectorized tensor operations, over 10x faster than Savitzky-Golay.
   - Captures global non-local dependencies directly from irregular time series.