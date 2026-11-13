# Scientific Algorithms & Methodology — FieldWitness

This document provides a complete, self-contained explanation of the **scientific methods, mathematical models, statistical inference frameworks, and validation protocols** used in FieldWitness. Every formula, parameter threshold, and assumption corresponds directly to the implemented equations and experimental benchmarks in the project.

---

## Foundations: The Three-Witness Architecture & Scientific Integrity

Predicting how a crop rotation will perform on an individual agricultural field is difficult because critical field properties—such as **root-zone water-holding capacity**, **exact sowing date**, **whether and how much a farmer irrigates**, and **past soil-borne pest/nutrient carry-over**—are usually unobserved from space. Any single modeling approach is vulnerable to hidden assumptions or confounding variables.

FieldWitness solves this by separating **three independent lines of evidence ("witnesses")** and refusing to let one quietly overwrite another:

1. **Witness 1 — Biophysics & Own Past (Mechanistic Soil–Water–Crop Simulation + Satellite Calibration):** Simulates daily water balance, crop canopy growth, and atmospheric demand from weather data, calibrated against the field's own historical satellite greenness trajectory.
2. **Witness 2 — Neighbours (Quasi-Experimental Spatial Causal Inference):** Estimates how changing the previous crop affected neighbouring fields' satellite canopy vigor after controlling for weather, soil covariates, topography, and geography.
3. **Witness 3 — Controlled Trials & Reference Benchmarks (External Grounding):** Compares simulation internals against independent soil surveys (USDA SSURGO), thermal evapotranspiration overpasses (NASA ECOSTRESS), root-zone soil moisture (NASA SMAP), and agronomic literature.

### Scientific Provenance & Guardrail Rules
Every numerical quantity produced by FieldWitness carries an explicit **epistemic provenance tag** explaining *what kind of truth it represents*:

| Tag | Category | Meaning |
|---|---|---|
| **`O`** | Direct Observation | Measured directly from satellite radiance/reflectance (e.g., HLS NDVI, GPM IMERG rainfall) or ground stations (CoCoRaHS, NWIS). |
| **`D`** | Derived / Model Output | Computed by a physical equation, statistical estimator, or Bayesian posterior simulation (e.g., $\text{ET}_o$, $K_s$, ABC posterior draws, DoubleML effects). |
| **`E`** | External Reference | Authoritative third-party datasets or peer-reviewed look-up tables (e.g., FAO-56 crop coefficients, USDA SSURGO horizons, CropScape CDL). |
| **`A`** | Unverified Assumption | An uncalibrated team choice or wide placeholder prior (e.g., `taw_base_mm = 150 mm`, `kc_fallow = 0.3`, prior bounds). Always counted explicitly in Evidence Grading. |

Three additional structural rules enforce scientific honesty:
- **Spatial Scale Contract:** Coarse gridded datasets (e.g., $25\text{ km}$ POWER weather, $9\text{ km}$ SMAP, $0.5^\circ$ GRACE, $250\text{ m}$ SoilGrids) are explicitly flagged (`scale_flag`) whenever pixel area exceeds $1/4$ of a field's area. They provide regional context or weather forcing, **never** field-specific soil claims.
- **Temporal Causality (`as_of` Cut-off):** During retrospective ("hindcast") testing, a strict date barrier prevents any observation, weather record, or crop label dated after the cut-off (e.g., `2021-12-31`) from entering parameter fitting or feature extraction.
- **Strict Scope Boundary:** FieldWitness never outputs harvest mass (`tonnes/ha`, `bu/acre`), market prices, or financial profit, and never infers soil fertility or soil carbon directly from satellite reflectance. Productivity is expressed strictly as a dimensionless **Relative Yield Index ($\text{RYI} \in [0, 1]$)** driven by water-deficit ratios.

---

## 1. Earth Observation Signal Filtering & Crop Phenology Extraction

Satellite optical sensors (Landsat 8/9 OLI and Sentinel-2 MSI, harmonized at $30\text{ m}$ resolution as **NASA HLS**) measure how strongly a field reflects near-infrared light versus red light. **Phenology** is the timing of a plant's seasonal biological stages—emergence, vegetative green-up, peak canopy, senescence (drying down), and harvest. Extracting clean phenological dates from satellite imagery requires removing geometric edge contamination, clouds, and sensor noise.

### 1.1 Spatial Interior-Pixel Filtering & Cloud Screening
Field polygons often contain roads, fences, grass waterways, or tree lines along their borders. At $30\text{ m}$ pixel resolution, a boundary pixel captures a mixture of crop canopy and surrounding non-crop land (**mixed-pixel contamination**).

- **Inward Buffer (`buffer_m = 15 m`):** Each field boundary is geometrically shrunk inward by half an HLS pixel width ($15\text{ m}$). Only pixel centers falling strictly inside the shrunken polygon are averaged (`field median`), requiring a minimum count (`min_pixels = 4`) to avoid noisy small-parcel estimates.
- **Quality Assurance (Fmask):** Pixels flagged as cloud, cloud shadow, adjacent cloud, snow/ice, or water in the HLS Fmask bitmask are discarded prior to aggregation.

### 1.2 Gap-Filling & Savitzky–Golay Polynomial Smoothing
Because clouds create irregular gaps between clear satellite overpasses, raw Normalized Difference Vegetation Index ($\text{NDVI}$) observations arrive on uneven days.

1. **Regularization & Gap Guard:** Clear observations are linearly interpolated onto a uniform $5\text{-day}$ grid (`grid_days = 5`). However, if the gap between two clear observations exceeds `max_gap_days`, points inside that span remain missing (`NaN`) so the algorithm does not fabricate a crop cycle across a two-month cloudy period.
2. **Savitzky–Golay Filter (Savitzky & Golay, 1964):** Over each contiguous cloud-free segment, a local polynomial of degree $p$ (`savgol_order`) is fitted by unweighted least squares across a symmetric moving window of odd length $W$ (`savgol_window`), built via the Vandermonde design matrix $\mathbf{V}$ and its Moore–Penrose pseudoinverse $\mathbf{V}^+$:
   $$\hat{y}_i = \sum_{k=-h}^{h} c_k \, y_{i+k}, \qquad h = \frac{W - 1}{2}$$
   where the convolution weights $c_k$ come from row $0$ of $\mathbf{V}^+$. Unlike simple moving averages—which flatten and widen narrow crop peaks—fitting a quadratic or cubic polynomial preserves peak height and peak timing while suppressing high-frequency atmospheric noise.

### 1.3 Amplitude-Threshold Season Detection & Dormancy Merging
From the smoothed NDVI curve $\tilde{y}(t)$, individual crop growing seasons are segmented using local extrema and relative amplitude crossings:

- **Peak Identification:** A grid point $i$ is a candidate peak if $\tilde{y}_i \ge \text{peak\_min\_ndvi}$ and it is the strict maximum within a half-separation window ($\pm \text{min\_peak\_separation\_days} / 2$).
- **Winter Dormancy Merging (Agronomic Rule):** Winter wheat sown in autumn grows a green rosette before winter dormancy (Dec–Feb), dips slightly in mid-winter cold, and surges again in spring. Without adjustment, peak finders split one winter wheat crop into two false seasons. Therefore, if two adjacent peaks are separated by a trough occurring in winter dormancy months (Dec–Feb) whose minimum stays **at or above the bare-soil cover threshold**, they are merged into a single season retaining the higher spring peak.
- **Prominence & Amplitude Screening:** True crop seasons must rise above their surrounding troughs by at least `min_prominence` and `min_crop_amplitude`; minor green-ups caused by post-harvest weeds or volunteer plants are filtered out.
- **Start of Season ($\text{SOS}$) & End of Season ($\text{EOS}$):** Defined by relative amplitude thresholds between the peak value $y_{\text{peak}}$ and the adjacent left/right trough values ($y_{\text{left}}, y_{\text{right}}$):
  $$\text{SOS}: \text{first crossing after left trough where } \tilde{y}(t) \ge y_{\text{left}} + f_{\text{sos}} (y_{\text{peak}} - y_{\text{left}})$$
  $$\text{EOS}: \text{first crossing after peak where } \tilde{y}(t) \le y_{\text{right}} + f_{\text{eos}} (y_{\text{peak}} - y_{\text{right}})$$
- **Canopy Integral & Cover Days:** Inside $[\text{SOS}, \text{EOS}]$, the **canopy integral** sums greenness above base across the season, providing an optical proxy for total cumulative canopy photosynthetic activity, while **cover days** counts days where $\tilde{y}(t) \ge \text{cover\_threshold}$.

### 1.4 Advanced Phenology Extraction & Sequence-Alignment Methods (Phase 1)
Empirical testing on Kansas fields showed that fixed-window Savitzky–Golay thresholding misses winter wheat dormancy variations and fallow anomalies ($78.3\%$ test accuracy). To overcome static smoothing limits, five advanced sequence-classification and deep-learning methods were implemented and benchmarked (`src/fieldwitness/story/phenology_algorithms.py`):

1. **Standard Dynamic Time Warping (DTW):**
   Finds a non-linear warping path minimizing cumulative distance $D(n, m)$ between an observed series $Q$ and an idealized crop template $T$ via dynamic programming:
   $$D(i, j) = |q_i - t_j| + \min\{D(i-1, j),\, D(i, j-1),\, D(i-1, j-1)\}$$
   Normalized distance is $D(n, m) / (n + m)$. Because standard DTW ignores calendar timestamps, it can match a July maize curve onto a May winter wheat curve, reducing accuracy in multi-crop systems.

2. **Time-Weighted Dynamic Time Warping (TWDTW; Maus et al., 2016):**
   Adds a smooth calendar-lag penalty using a normalized **Modified Logistic Weight Function (MLWF)**:
   $$w(t_q, t_t) = \max\!\left(0,\; \frac{\sigma(\alpha(|t_q - t_t| - \beta)) - w_0}{1 - w_0}\right), \qquad \sigma(z) = \frac{1}{1 + e^{-z}}, \quad w_0 = \frac{1}{1 + e^{\alpha\beta}}$$
   with steepness $\alpha = 0.10\text{ d}^{-1}$ and midpoint $\beta = 45\text{ d}$. Local step cost becomes $|q_i - t_j| + \gamma\, w(t_i, t_j)$. Normalization ensures zero time lag ($t_q = t_t$) incurs **exactly zero penalty**, allowing moderate weather-driven shifts ($\pm 2\text{–}3$ weeks) while heavily penalizing cross-season warping.

3. **Weighted Derivative Dynamic Time Warping (WDDTW; Jeong et al., 2011):**
   Instead of matching raw NDVI magnitude—which drops during droughts or shifts upward/downward with dark vs. bright soil background—WDDTW aligns **first-order temporal growth rates (slopes)** computed by central finite differences:
   $$Q'_i = \frac{q_{i+1} - q_{i-1}}{t_{i+1} - t_{i-1}}$$
   paired with the MLWF temporal penalty: $d(i, j) = \lambda_{\text{slope}}|Q'_i - T'_j| + \gamma\, w(t_i, t_j)$. Focusing on *when the crop accelerates green-up and dries down* makes classification invariant to vertical amplitude shifts ($93.3\%$ fallow accuracy in benchmark).

4. **Vector Dynamic Time Warping (VDTW; Guan et al., 2018):**
   Replaces scalar NDVI differences with **spectral angular cosine distance** across multi-band feature vectors $\mathbf{v}_t = [\text{NDVI}_t,\; \text{EVI}_t,\; \Delta\text{NDVI}_t]$:
   $$d_{\text{cos}}(\mathbf{u}, \mathbf{v}) = 1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \, \|\mathbf{v}\|_2}$$
   measuring shifts in the multivariate spectral trajectory rather than single-index brightness.

5. **CropFormer Self-Attention Architecture (Yuan et al., 2024):**
   A temporal Transformer encoder designed specifically for irregularly spaced satellite observations:
   - **Sinusoidal Continuous DOY Positional Encoding:** Encodes exact Day-of-Year timestamps $t \in [1, 365]$ directly into a $d$-dimensional embedding ($\sin / \cos$ pairs at log-spaced frequencies), avoiding discrete grid resampling.
   - **Multi-Head Self-Attention:** Projects spectral features + positional embeddings into Queries ($\mathbf{Q}$), Keys ($\mathbf{K}$), and Values ($\mathbf{V}$), computing pairwise temporal relevance weights $\text{softmax}(\mathbf{Q}\mathbf{K}^\top / \sqrt{d_k})\mathbf{V}$ so clear spring and autumn observations directly attend to each other across winter cloud gaps.
   - **GELU Feed-Forward Block & Attention Pooling:** Passes residual-normalized representations through a Gaussian Error Linear Unit MLP and pools variable-length time series via learned attention weights into crop class logits (~$1.07\text{ ms/field}$ inference).

---

## 2. Biophysical Soil–Water–Crop Simulation (Forward Physics)

Witness 1 simulates the daily water budget and crop stress of every rotation option using the **FAO Irrigation and Drainage Paper No. 56 (Allen et al., 1998)** dual-framework: atmospheric evaporative demand ($\text{ET}_o$), stage-dependent crop demand ($K_c$), root-zone soil moisture storage ($D_r$), and water-stress productivity sensitivity ($K_y$).

### 2.1 Daily Reference Evapotranspiration ($\text{ET}_o$) — FAO-56 Penman–Monteith
**Reference evapotranspiration ($\text{ET}_o$, $\text{mm/day}$)** represents the water loss rate from a hypothetical, well-watered $0.12\text{ m}$ tall grass reference surface with fixed surface resistance ($70\text{ s/m}$) and albedo ($\alpha = 0.23$). It isolates *atmospheric thirst* from crop-specific biology. Using daily weather inputs ($T_{\max}, T_{\min}$ in $^\circ\text{C}$, relative humidity $\text{RH}$, $2\text{ m}$ wind speed $u_2$, incoming shortwave solar radiation $R_s$, latitude $\phi$, and elevation $z$):

$$\text{ET}_o = \frac{0.408\,\Delta(R_n - G) + \gamma\,\frac{900}{T_{\text{mean}} + 273}\,u_2\,(e_s - e_a)}{\Delta + \gamma\,(1 + 0.34\,u_2)}$$

where:
- **$\Delta$ ($\text{kPa}/^\circ\text{C}$):** Slope of the saturation vapour pressure curve at mean temperature (how fast warm air holds more moisture; Eq. 13).
- **$R_n$ ($\text{MJ}\,\text{m}^{-2}\,\text{day}^{-1}$):** Net radiation absorbed by the surface ($R_{ns} - R_{nl}$), combining shortwave solar absorption $(1 - 0.23)R_s$ minus net longwave thermal cooling regulated by cloudiness ratio $R_s / R_{so}$ and humidity (Eq. 38–40). Soil heat flux $G \approx 0$ at daily timesteps (Eq. 42).
- **$\gamma$ ($\text{kPa}/^\circ\text{C}$):** Psychrometric constant proportional to elevation-adjusted atmospheric pressure $P(z)$ (Eq. 7–8).
- **$e_s - e_a$ ($\text{kPa}$):** **Vapour Pressure Deficit (VPD)**—the difference between saturated moisture capacity $e_s$ and actual air vapour pressure $e_a$ (the drying power of dry air; Eq. 11–12, 17, 19).

### 2.2 Crop Coefficient Curve ($K_c$) & Local Climate Adjustment
To convert grass reference $\text{ET}_o$ into an unstressed crop's water demand ($\text{ET}_c = K_c \cdot \text{ET}_o$), FAO-56 models crop canopy development as a **four-stage piecewise-linear curve** (`L_ini`, `L_dev`, `L_mid`, `L_late`):
1. **Initial Stage (`L_ini`):** Flat at $K_{c,\text{ini}}$ from sowing until $10\%$ ground cover.
2. **Development Stage (`L_dev`):** Rises linearly from $K_{c,\text{ini}}$ to $K_{c,\text{mid}}$ as leaves expand to full cover.
3. **Mid-Season Stage (`L_mid`):** Flat plateau at $K_{c,\text{mid}}$ during full canopy / flowering.
4. **Late-Season Stage (`L_late`):** Declines linearly from $K_{c,\text{mid}}$ to $K_{c,\text{end}}$ during maturation and senescence.

Because FAO-56 tabulated $K_{c,\text{mid}}$ and $K_{c,\text{end}}$ values assume a mild standard climate ($u_2 = 2\text{ m/s}$, $\text{RH}_{\min} = 45\%$), FieldWitness adjusts them for windy or arid environments using **FAO-56 Eq. 62 & Eq. 65**:
$$K_{c,\text{adj}} = K_{c,\text{tab}} + \big[0.04(u_2 - 2) - 0.004(\text{RH}_{\min} - 45)\big]\left(\frac{h}{3}\right)^{0.3}$$
where plant height $h$ is clipped to $[0.1, 10]\text{ m}$, wind $u_2$ to $[1, 6]\text{ m/s}$, and $\text{RH}_{\min}$ to $[20, 80]\%$ (for late season, Eq. 65 applies only when $K_{c,\text{end}} \ge 0.45$). Outside the crop growing window (bare fallow), soil evaporation uses a constant baseline `kc_fallow = 0.3` (Tag `A`).

### 2.3 Thermal-Time Phenology Mode (Growing Degree Days, GDD)
As a pre-registered physical alternative to fixed calendar stage lengths (`phenology_mode = "gdd"`), crop stage durations adapt dynamically to seasonal heat accumulation:
- **K-State MF3740 Method 2 (Summer Crops):** Limits daily $T_{\max}$ and $T_{\min}$ to species-specific $[T_{\text{base}}, T_{\text{upper}}]$ bounds before averaging:
  $$\text{GDD}_t = \max\!\left(0,\; \frac{\text{clip}(T_{\max}, T_{\text{base}}, T_{\text{upper}}) + \text{clip}(T_{\min}, T_{\text{base}}, T_{\text{upper}})}{2} - T_{\text{base}}\right)$$
- **Mesonet Uncapped (Winter Wheat):** Averages raw daily temperatures above $T_{\text{base}}$: $\max(0, (T_{\max} + T_{\min})/2 - T_{\text{base}})$.
Each growth stage ends on the first day cumulative GDD from sowing reaches the cultivar's published thermal threshold.

### 2.4 Daily Root-Zone Water Balance (Tipping-Bucket Physics)
The soil root zone acts as a reservoir of depth $Z_r$ ($\text{m}$) with volumetric water content bounded between **Field Capacity ($\theta_{\text{FC}}$)**—the maximum water soil holds against gravity—and **Permanent Wilting Point ($\theta_{\text{WP}}$)**—below which roots cannot extract water:

1. **Total Available Water ($\text{TAW}$, Eq. 82):** Total extractable water capacity in the root zone ($\text{mm}$):
   $$\text{TAW} = 1000 \, (\theta_{\text{FC}} - \theta_{\text{WP}}) \, Z_r$$
2. **Readily Available Water ($\text{RAW}$, Eq. 83):** Fraction $p$ of $\text{TAW}$ a crop extracts before closing stomata and reducing growth:
   $$\text{RAW} = p \cdot \text{TAW}$$
3. **Water Stress Coefficient ($K_s$, Eq. 84):** As daily **root-zone depletion $D_r$** ($\text{mm}$ below field capacity) exceeds $\text{RAW}$, actual transpiration slows linearly to zero at $\text{TAW}$:
   $$K_s(D_r) = \begin{cases} 1 & D_r \le \text{RAW} \\ \dfrac{\text{TAW} - D_r}{\text{TAW} - \text{RAW}} & \text{RAW} < D_r < \text{TAW} \\ 0 & D_r \ge \text{TAW} \end{cases}$$
4. **Daily Mass Balance (Eq. 85, Capillary Rise $CR = 0$):**
   Actual evapotranspiration is $\text{ET}_{a,t} = K_{s,t}\,\text{ET}_{c,t}$. Effective rainfall is $P_{e,t} = P_t - \text{RO}_t$ (with runoff $\text{RO}_t = f_{\text{ro}} P_t$, default $0$). Updating depletion from day $t-1$ to $t$:
   $$D_{r,\text{raw}} = D_{r,t-1} - P_{e,t} - I_t + \text{ET}_{a,t}$$
   - If $D_{r,\text{raw}} < 0$ (rain exceeds field capacity), excess water drains below the root zone as **Deep Percolation**: $\text{DP}_t = -D_{r,\text{raw}}$, and $D_{r,t} = 0$.
   - If $D_{r,\text{raw}} > \text{TAW}$, $\text{ET}_{a,t}$ is reduced by $(D_{r,\text{raw}} - \text{TAW})$ so root-zone depletion never exceeds $\text{TAW}$.

**Irrigation Policies (`I_t`):** Supports `rainfed` ($I_t = 0$), `trigger_at_raw` (refills $D_r \to 0$ when $D_{r,t-1} > \text{RAW}$ inside crop windows, dividing net depth by application efficiency $\eta \in (0, 1]$ for gross pumping), and `fixed_seasonal_mm` (applies trigger refills until an annual seasonal allocation budget is exhausted).

### 2.5 Relative Yield Index ($\text{RYI}$) & Multi-Year Soil Memory Carry-Over
Rather than predicting uncalibrated weight in tonnes, FieldWitness links water uptake directly to relative productivity using **FAO-33 Seasonal Yield Response (FAO-56 Table 24)**:
$$\text{RYI} = \frac{Y_a}{Y_m} = \text{clip}\!\left(1 - K_y \left(1 - \frac{\sum \text{ET}_a}{\sum \text{ET}_c}\right),\; 0,\; 1\right)$$
where **$K_y$** is the crop-specific yield response factor (e.g., high for drought-sensitive maize, lower for drought-tolerant sorghum).

Crucially, in **multi-year rotation simulation (`rotate`)**, the ending soil depletion $D_r(t = 365)$ of Season $s$—after both crop water uptake and post-harvest fallow evaporation—**carries forward as $D_{r,0}$ into Season $s+1$**. Thus, a deep-rooted, heavy-water-using crop leaves a drier soil profile ("soil moisture deficit debt") for the subsequent crop, whereas a short-season crop or fallow period partially recharges root-zone moisture across historical weather sequences.

### 2.6 Agro-Climatic Hazard & Vulnerability Calendar
To expose non-water-balance climate hazards across historical weather records ($20+$ years), the vulnerability module computes the **empirical probability (share of years)** each hazard occurs in each calendar month (`1..12`):
- **Heat Stress:** Days with $T_{\max} > T_{\text{heat}}$ falling specifically inside the flowering/grain-fill mid-season stage (`L_mid`).
- **Post-Emergence Frost:** Days with $T_{\min} \le 0^\circ\text{C}$ occurring *after* green-up (end of `L_ini`) through harvest.
- **Water Stress:** Days inside any crop window where simulated FAO-56 $K_s < 1.0$.
- **Extreme Rain on Bare Soil:** Days where rainfall exceeds the local $99\text{th}$ percentile ($q = 0.99$) while the field has no crop cover ($K_c / K_{c,\text{mid}} < 0.5$), quantifying soil erosion exposure.

---

## 3. Simulation-Based Bayesian Parameter Inference & Uncertainty Quantification

Because field soil water capacity (`taw_scale`), actual planting date shift (`sow_offset_days`), irrigation status (`irrigated`), irrigation volume (`irrigation_mm`), and effective canopy vigour (`kc_mid_scale`) are unknown from orbit, running a single deterministic simulation gives false confidence. FieldWitness infers **posterior parameter distributions** per field using **Approximate Bayesian Computation (ABC)**.

### 3.1 Prior Distributions (Uncertain Physical Parameters)
Wide, weakly informative prior distributions (`config/priors.yaml`, Tag `A`) express initial physical uncertainty before observing satellite NDVI:

| Parameter | Distribution | Range / Support | Physical Meaning |
|---|---|---|---|
| `sow_offset_days` | Uniform integer | $[-21, +21]\text{ days}$ | Shift relative to regional nominal planting date |
| `taw_scale` | Log-uniform | $[0.5, 2.0]$ | Multiplier on base $\text{TAW}$ ($150\text{ mm}$ placeholder $\to 75\text{–}300\text{ mm}$) |
| `irrigated` | Bernoulli | $p = 0.5$ | Probability field receives supplemental irrigation |
| `irrigation_mm` | Uniform | $[50, 400]\text{ mm/season}$ | Seasonal irrigation cap (forced to $0$ when `irrigated = False`) |
| `kc_mid_scale` | Uniform | $[0.85, 1.15]$ | Multiplier on peak canopy demand $K_{c,\text{mid}}$ |

### 3.2 Rejection ABC & Standardized Summary-Statistic Matching
Because the mechanistic water-balance simulator has no tractable analytical likelihood $p(\mathbf{y}_{\text{NDVI}} \mid \theta)$, inference uses **Rejection ABC** (Pritchard et al., 1999):

1. **Reference Table Generation:** Draw $N$ parameter vectors $\theta^{(j)}$ from the priors and simulate daily canopy proxy trajectories $\text{NDVI}_{\text{sim}}^{(j)}(t)$ under the field's historical weather.
2. **Observation Masking & Noise Injection:** Sample each simulated curve *only on the exact Day-of-Year timestamps* when the real field had cloud-free HLS satellite observations, and add realistic satellite observation noise $\epsilon \sim \mathcal{N}(0, \sigma_{\text{HLS}}^2)$ estimated from the HLS empirical census.
3. **Summary Statistic Vector ($\mathbf{S} \in \mathbb{R}^5$):** Both observed and masked simulated series are linearly interpolated to $1\text{..}365$ and compressed into five phenological summary features:
   $$\mathbf{S} = \big[\text{SOS day},\; \text{Peak day},\; \text{EOS day},\; \text{Canopy integral},\; \text{Peak NDVI}\big]$$
   (where $\text{SOS}/\text{EOS}$ are the $50\%$ amplitude threshold crossings; adding `Peak NDVI` prevents irrigation and TAW from becoming unidentifiable).
4. **Standardized Euclidean Distance & Posterior Worlds:** Each statistic is standardized by its reference-table standard deviation $\sigma_r$:
   $$d(\mathbf{S}_{\text{sim}}^{(j)}, \mathbf{S}_{\text{obs}}) = \sqrt{\sum_{r=1}^{5} \left(\frac{S_{\text{sim},r}^{(j)} - S_{\text{obs},r}}{\sigma_r}\right)^2}$$
   The closest $k$ prior draws form an empirical posterior ensemble ("posterior worlds"), preserving parameter correlations and equifinality directly for downstream decision ranking.

### 3.3 Physics Credibility Score
How well does the biophysical model actually explain a field's past? For any field with $n_{\text{fit}}$ pre-cut-off seasons, **Credibility $\in [0, 1]$** blends two independent agreement metrics (`config/grading.yaml`):
$$\text{Credibility} = w_{\rho}\,\max(0, \rho_{\text{Spearman}}) + (1 - w_{\rho})\,\max\!\left(0,\; 1 - \frac{\text{median}(|\text{err}_{\text{peak}}|)}{20\text{ days}}\right)$$
where $\rho_{\text{Spearman}}$ measures whether good vs. bad simulated years match observed satellite canopy-integral rank ordering, and the timing term penalizes median peak-DOY mismatch relative to a $20\text{-day}$ scale ($w_\rho = 0.5$).

### 3.4 Uncertainty Evaluation & Conformal Prediction Calibration
Bayesian posterior intervals from an uncalibrated mechanistic model can still be over-confident (too narrow) under model misspecification or extreme droughts. FieldWitness evaluates and recalibrates intervals using distribution-free statistical tools:

- **Continuous Ranked Probability Score (CRPS):** A strictly proper scoring rule measuring both sharpness and calibration of an entire cumulative forecast distribution $F$:
  $$\text{CRPS}(F, y) = \int_{-\infty}^{\infty} \big(F(x) - \mathbf{1}\{y \le x\}\big)^2\,dx$$
- **Winkler Interval Score (Gneiting & Raftery, 2007):** Evaluates a $(1 - \alpha)$ interval $[L, U]$ by penalizing width plus $2/\alpha$ times any out-of-interval miss:
  $$W_\alpha(L, U, y) = (U - L) + \frac{2}{\alpha}(L - y)\mathbf{1}\{y < L\} + \frac{2}{\alpha}(y - U)\mathbf{1}\{y > U\}$$
- **Split Conformal & Conformalized Quantile Regression (CQR; Romano et al., 2019):** On strictly held-out rolling-origin pseudo-forecasts (`cal` set, leaving out the target spatial block to prevent spatial leakage), **Symmetric CQR** computes conformity residuals $E_i = \max(q_{5,i} - y_i,\; y_i - q_{95,i})$ and expands prediction intervals by the finite-sample quantile $k = \lceil (n + 1)(1 - \alpha) \rceil$. **Asymmetric CQR** computes signed lower and upper margins separately ($E_{\text{lo},i} = q_{5,i} - y_i$, $E_{\text{hi},i} = y_i - q_{95,i}$ at level $1 - \alpha/2$), allowing negatively skewed variables (like drought-stressed canopy integrals) to expand asymmetrically without altering the point median $q_{50}$.

---

## 4. Spatial Causal Inference (The Neighbours Witness)

Because mechanistic physics models omit biological factors like soil-borne root disease, residue allelopathy, and nitrogen carry-over, Witness 2 estimates **empirical crop-rotation effects directly from neighbouring fields** using modern causal inference.

### 4.1 Double Machine Learning — Partially Linear Regression (DoubleML-PLR)
For fields currently growing crop $C$, we want the average causal effect $\theta$ of having grown previous crop $A$ (`D = 1`) versus reference previous crop $B$ (`D = 0`) on satellite outcome $Y$ (e.g., `canopy_integral`, `peak_ndvi`, `cover_days`), controlling for high-dimensional spatial, climatic, and soil confounders $\mathbf{X}$ (`area_ha`, `lon`, `lat`, `clay_pct`, `sand_pct`, `soc_g_kg`, `season_precip_mm`, `season_tmax_c`, `year`).

We specify the **Partially Linear Regression model** (Chernozhukov et al., 2018):
$$Y = \theta D + g(\mathbf{X}) + \varepsilon, \qquad D = m(\mathbf{X}) + \nu$$
using 200-tree **Random Forests** to flexibly learn the outcome nuisance function $\hat{l}(\mathbf{X}) = \mathbb{E}[Y \mid \mathbf{X}]$ and the propensity treatment function $\hat{m}(\mathbf{X}) = \mathbb{P}(D = 1 \mid \mathbf{X})$. Estimating $\theta$ via the **Neyman-orthogonal partialling-out score** regresses residualized outcomes $(Y - \hat{l}(\mathbf{X}))$ on residualized treatments $(D - \hat{m}(\mathbf{X}))$, removing regularization bias while preserving valid $\sqrt{n}$ confidence intervals.

### 4.2 Spatial Block Cross-Fitting (`GroupKFold`)
Standard random $K$-fold cross-fitting leaks spatial autocorrelation when adjacent fields share unmeasured microclimate, aquifer depth, or farmer management. FieldWitness tiles the pilot landscape into disjoint **$10\text{ km} \times 10\text{ km}$ spatial blocks** and holds out **entire blocks** together during nuisance model training (`GroupKFold`), preventing neighbouring fields from appearing in both train and validation folds.

### 4.3 Matched-History Conditioning (`prev2_crop`) & Spatial DAPSM
In early pilot tests, comparing `prev_crop = A` vs `B` suffered severe covariate imbalance because farmers follow multi-year crop sequences (a field that grew sorghum last year had a completely different crop *two* years ago than a field that grew winter wheat). Two refinements address this:
1. **Exact Two-Year History Matching:** Restricts contrasts within identical `(crop, prev2_crop)` strata, eliminating two-year rotation confounding by design.
2. **Distance-Adjusted Propensity Score Matching (DAPSM; Papadogeorgou et al., 2019):** Matches treated field-seasons $i$ 1:1 (with replacement, never to the same field) to reference field-seasons $j$ by minimizing a convex combination of **propensity score similarity** and **normalized Haversine geographic distance**:
   $$\mathcal{D}(i, j) = w \, |\widehat{\text{PS}}_i - \widehat{\text{PS}}_j| + (1 - w)\, \frac{d_{\text{Haversine}}(i, j)}{\max_{a,b} d_{\text{Haversine}}(a, b)}$$
   where $w \in \{0.0, 0.1, \dots, 1.0\}$ is selected via a pre-registered rule minimizing median worst-case covariate imbalance across contrasts. Matching nearby fields explicitly controls for unmeasured spatially varying confounders (like aquifer drawdown or local hail corridors).

### 4.4 Four Mandatory Causal Falsification & Balance Checks
A causal estimate from Witness 2 is **rejected from upgrading an Evidence Grade** unless it clears all four diagnostic gates:
1. **Propensity Overlap:** Estimated propensity scores are clipped to $[0.05, 0.95]$; no more than $10\%$ of rows may fall outside this common-support window.
2. **Covariate Balance ($|\text{SMD}|$):** Inverse-probability-weighted (or matched) Standardized Mean Difference across every confounder must satisfy $\max |\text{SMD}| \le 0.25$.
3. **Placebo Future-Treatment Test:** Re-running the estimator with *next* season's crop as the "treatment" must produce a $95\%$ confidence interval that includes $0$ (future crops cannot physically cause past canopy growth).
4. **Negative-Control Past-Outcome Test:** Predicting the field's *own outcome two seasons earlier* must yield a $95\%$ confidence interval including $0$ (ruling out persistent static field differences masquerading as rotation effects).

---

## 5. Evidence Synthesis, Rotation Ranking & Value-of-Information

For each field, FieldWitness enumerates all **agronomically valid 3-year candidate rotations** (`rotate/candidates.py`) obeying regional crop calendar windows (with $\pm 7\text{-day}$ tolerance), a maximum of $2$ consecutive seasons in the same botanical family (to break pest/pathogen cycles; fallow resets runs), at least $1$ harvested crop, and no consecutive non-crop seasons.

### 5.1 Multi-Criteria Ranking, Pareto Filtering & Tail Risk ($\text{CVaR}_{10}$)
Every candidate rotation is simulated across all combinations of **posterior parameter worlds** $\times$ **historical weather sequences**, summarized by six metrics:

| Metric | Direction | Meaning |
|---|---|---|
| **`ryi`** | Higher is better | Mean Relative Yield Index across posterior draws and weather years |
| **`cvar10_ryi`** | Higher is better | **Bad-Year Yield Floor ($\text{CVaR}_{10}$):** Mean $\text{RYI}$ in the worst $10\%$ of weather years |
| **`cover_days`** | Higher is better | Days per rotation cycle with ground cover proxy $\ge 0.5$ (erosion protection) |
| **`water_use_mm`** | Lower is better | Mean seasonal actual crop water consumption ($\sum \text{ET}_a$) |
| **`irrigation_mm`** | Lower is better | Mean seasonal net irrigation applied |
| **`cvar10_water_mm`** | Lower is better | **Drought-Year Water Peak ($\text{CVaR}_{10}$):** Mean water use in the highest-demand $10\%$ of years |

Ranking proceeds deterministically:
1. **Pareto Frontier Filter:** Option $i$ is marked *dominated* if another candidate is $\ge$ it on all 6 oriented metrics and strictly $>$ on at least one.
2. **Per-Field Min–Max Normalization & Preset Weighting:** Oriented metrics are scaled to $[0, 1]$ across that field's candidates and combined via user-selected priority weights $\mathbf{w}$ (`balanced`, `water_saver`, `yield_first`, `resilient`): $\text{Score}_i = \sum_{m=1}^6 w_m \tilde{M}_{i,m}$. (Non-negative weights mathematically ensure a dominated option never outscores its dominator.)
3. **Minimax Regret:** Measures worst-case $\text{RYI}$ opportunity loss across historical weather start years: $\text{Regret}_{i,y} = \max_k \text{RYI}_{k,y} - \text{RYI}_{i,y}$.

### 5.2 Three-Witness Evidence Grading (`A`, `B`, `C`, `D`)
Instead of displaying raw predictions without reliability context, every rotation option receives an **Evidence Grade** (`agree/grade.py`):
- **Grade `D` (Unverified / Missing Physics):** Assigned immediately if $> 50\%$ of decision-driving inputs are unverified assumptions (Tag `A`) or no physics estimate exists.
- **Witness Agreement Count:**
  1. *Physics* is always counted if available.
  2. *Own Past* agrees if historical Credibility $\ge 0.60$.
  3. *Neighbours* (or agronomic *Trials*) agree if the empirical causal effect has the **same sign** as the physics effect *and* their **$90\%$ confidence intervals overlap**.
- **Grade `A`:** Physics and Neighbours agree **AND** Own-Past Credibility $\ge 0.60$ **AND** $0$ key inputs are Tag `A` (no major unverified assumptions). *(Without a valid neighbour witness, maximum achievable grade is capped at `B`.)*
- **Grade `B`:** At least **two witnesses agree** (e.g., Physics + Own Past agree, or Physics + Neighbours agree with some Tag `A` inputs).
- **Grade `C`:** Only one witness supports the option, or witnesses actively disagree.

### 5.3 Sensitivity ("What to Measure Next") & Counterfactual Analysis
Because a top ranking could depend on uncertain parameters (soil $\text{TAW}$, $K_c$ scale, or irrigation budget), FieldWitness computes two decision-analytic diagnostics across the posterior worlds:
- **`flip_share[x]` (Value of Information):** Fixes uncertain parameter $x \in \{\text{TAW}, K_c\text{ scale}, \text{budget}\}$ to its posterior median while allowing all other parameters to vary across posterior worlds, then measures the fraction of worlds whose #1 ranked rotation changes. High `flip_share` identifies which field measurement (e.g., taking a soil core vs. installing a flow meter) would resolve the most decision uncertainty.
- **Smallest Counterfactual Flip:** Starting from the median posterior world, perturbs $x$ alone across discrete relative ($\pm 10\%, 20\%, 30\%, 40\%$) or absolute ($\pm 25, 50, 100, 200\text{ mm}$) steps to report the exact minimum physical change needed to overturn the #1 recommendation.

---

## 6. Independent Validation & Verification Protocols

Scientific claims in FieldWitness are pre-registered before testing and verified out-of-sample:

- **Strict Rolling-Origin Hindcast & Spatial Block Bootstrap:** Models calibrated strictly before `2021-12-31` are scored on held-out `2022–2024` seasons against two simpler baselines (**B1**: uncalibrated FAO-56 calendar engine; **B2**: prior physics). Statistical uncertainty is computed via **1,000 spatial block bootstrap resamples** over $10\text{ km}$ cells so spatially clustered fields do not artificially inflate statistical significance.
- **Independent Soil Survey Cross-Check (USDA SSURGO):** Compares simulated root-zone $\text{TAW}$ against thickness-weighted Available Water Storage ($\text{AWS} = 10 \sum \text{awc}_r \cdot \Delta z$) computed directly from official USDA-NRCS horizon profiles over $135\text{ cm}$ root depth (revealing systematic model under-estimation on deep silt loams: $142\text{ mm}$ median simulated vs. $282.1\text{ mm}$ SSURGO).
- **Satellite ET & Soil-Moisture Cross-Checks:** Evaluates simulated $\text{ET}_a$ against **NASA ECOSTRESS** ($70\text{ m}$ PT-JPL instantaneous/daily thermal retrievals), soil moisture dynamics against **NASA SMAP L4** ($9\text{ km}$ root-zone anomalies via monthly Pearson/Spearman correlation), and precipitation extremes against **NASA GPM IMERG** and **CoCoRaHS** gauges.

---

## Glossary of Technical Terms

| Term | Plain-English Scientific Meaning |
|---|---|
| **Allelopathy / Carry-over** | Biological or chemical effects left in soil by a previous crop (e.g., leftover moisture depletion, root pathogens, or nitrogen fixation) that influence the next crop. |
| **Approximate Bayesian Computation (ABC)** | A parameter-estimation method that finds which hidden field values are plausible by running the physics simulator thousands of times and keeping the parameter sets whose outputs match satellite observations. |
| **$\text{CVaR}_{10}$ (Conditional Value-at-Risk)** | The average outcome across the *worst $10\%$ of weather years*—a direct measure of drought-year downside risk rather than average-year behavior. |
| **Conformalized Quantile Regression (CQR)** | A distribution-free calibration method that adjusts upper and lower prediction bounds using past out-of-sample errors so the true outcome falls inside the interval at the stated probability (e.g., $90\%$). |
| **Confounder** | A variable (such as soil clay content, rainfall, or field location) that influences *both* what crop a farmer planted and how well the next crop grows, potentially creating spurious correlations if left uncontrolled. |
| **CRPS (Continuous Ranked Probability Score)** | A single score measuring how close an entire probabilistic forecast distribution is to reality (penalizing both bias and over/under-confidence; lower is better). |
| **Double Machine Learning (DoubleML)** | A causal inference technique that uses machine learning to strip out predictable variation from both the treatment and the outcome before estimating the causal effect of a crop switch. |
| **Equifinality** | The phenomenon where different combinations of hidden inputs (e.g., slightly shallower soil + slightly more irrigation) produce nearly identical satellite greenness curves. |
| **Evapotranspiration ($\text{ET}_o, \text{ET}_c, \text{ET}_a$)** | Combined water loss from soil evaporation and plant transpiration. $\text{ET}_o$ = grass reference atmospheric demand; $\text{ET}_c$ = unstressed crop demand; $\text{ET}_a$ = actual water consumed under soil moisture limits. |
| **FAO-56 / FAO-33** | International UN Food & Agriculture Organization standard equations for crop water demand (Paper 56) and relative yield response to water deficits (Paper 33). |
| **Growing Degree Days (GDD)** | Accumulated heat units above a crop's base growth temperature; tracks biological development more accurately than calendar days during unusually warm or cool springs. |
| **NDVI / EVI** | Satellite vegetation indices comparing near-infrared vs. red reflectance to measure canopy greenness and density. |
| **Pareto Frontier** | The set of "no-compromise" crop rotations where you cannot improve one goal (e.g., yield stability) without sacrificing another (e.g., water savings). |
| **Propensity Score Overlap & $\|\text{SMD}\|$** | Diagnostics checking whether treated and comparison fields share comparable conditions (overlap) and nearly identical average soil/weather distributions (standardized mean difference $\le 0.25$). |
| **Relative Yield Index ($\text{RYI}$)** | Dimensionless ratio ($0$ to $1$) of actual crop productivity under water stress to maximum water-unstressed productivity—avoiding fabricated tonne/acre claims. |
| **Root-Zone Depletion ($D_r$) / $\text{TAW}$ / $\text{RAW}$** | Water missing from the soil below Field Capacity ($D_r$), total extractable capacity ($\text{TAW}$), and stress-free extractable capacity ($\text{RAW}$). |
| **Spatial Block Cross-Validation** | Grouping nearby fields into $10\text{ km}$ geographic tiles and testing on whole held-out tiles so spatial proximity never leaks answers between training and evaluation sets. |
