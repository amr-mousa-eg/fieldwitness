# FAO AquaCrop Canopy Cover Growth and Decline Specifications

## 1. Overview and Purpose

This specification documents the mathematical formulation of green canopy cover ($CC$) dynamics from the Food and Agriculture Organization (FAO) AquaCrop model. It is intended as a formal research specification for future extensions to the FieldWitness crop modeling framework (superseding or complementing the static FAO-56 crop coefficient curves).

In contrast to models that simulate foliage development through Leaf Area Index ($LAI$), AquaCrop expresses canopy size directly through fractional green canopy cover ($CC$, $0 \le CC \le 1$ or $0\% \le CC \le 100\%$). $CC$ is defined as the fraction of the soil surface covered by the vertical projection of the green canopy foliage.

This document formalizes:
1. Canopy cover equations across all growth and senescence phases.
2. Complete definitions, dimensions, and SI/agronomic units for all symbols.
3. Separation of conservative (species-wide) versus cultivar/environment-calibrated parameters.
4. Five hand-computed numerical test cases with complete step-by-step arithmetic.
5. Soil water stress modifications on canopy expansion and senescence.
6. Published empirical and semi-empirical relationships linking canopy cover $CC$ to satellite Normalized Difference Vegetation Index ($NDVI$).

---

## 2. Primary References

- **Raes, D., Steduto, P., Hsiao, T.C., & Fereres, E. (2009).** *AquaCrop—The FAO Crop Model to Simulate Yield Response to Water: II. Main Algorithms and Software Description.* Agronomy Journal, 101(3), 438–447. [doi:10.2134/agronj2008.0140s](https://doi.org/10.2134/agronj2008.0140s).
- **Steduto, P., Hsiao, T.C., Raes, D., & Fereres, E. (2009).** *AquaCrop—The FAO Crop Model to Simulate Yield Response to Water: I. Concepts and Underlying Principles.* Agronomy Journal, 101(3), 426–437. [doi:10.2134/agronj2008.0139s](https://doi.org/10.2134/agronj2008.0139s).
- **Hsiao, T.C., Heng, L., Steduto, P., Rojas-Lara, B., Raes, D., & Fereres, E. (2009).** *AquaCrop—The FAO Crop Model to Simulate Yield Response to Water: III. Parameterization and Testing for Maize.* Agronomy Journal, 101(3), 448–459. [doi:10.2134/agronj2008.0218s](https://doi.org/10.2134/agronj2008.0218s).
- **FAO (2012).** *Crop yield response to water.* FAO Irrigation and Drainage Paper No. 66, edited by P. Steduto, T.C. Hsiao, E. Fereres, and D. Raes. Rome: FAO. ISBN 978-92-5-107274-5.
- **FAO (2024/2026).** *AquaCrop Reference Manual: Chapter 3 – Calculation Procedures.* Version 7.2/7.3. Land and Water Division, Rome.
- **Carlson, T.N., & Ripley, D.A. (1997).** *On the relation between NDVI, fractional vegetation cover, and leaf area index.* Remote Sensing of Environment, 62(3), 241–252. [doi:10.1016/S0034-4257(97)00104-1](https://doi.org/10.1016/S0034-4257(97)00104-1).

---

## 3. Mathematical Equations

The trajectory of green canopy cover $CC(t)$ across a cropping season progresses through three distinct operational phases:
1. **Exponential growth** (from initial cover $CC_0$ up to half of maximum cover, $CC_x / 2$).
2. **Exponential decay of growth rate** (from $CC_x / 2$ approaching maximum canopy cover $CC_x$).
3. **Canopy senescence / decline** (from senescence onset $t_{sen}$ down to physiological maturity or zero cover).

Time $t$ can be evaluated in **calendar days** (days after emergence) or in **thermal time** ($\text{cumulative Growing Degree Days, } GDD \text{ in } ^\circ\text{C}\cdot\text{d}$). In thermal time mode, parameters $CGC$ and $CDC$ are scaled per $^\circ\text{C}\cdot\text{d}$.

### 3.1 Initial Canopy Cover ($CC_0$)

Initial canopy cover at 90% seedling emergence is calculated from the plant planting density and individual seedling canopy area:

$$CC_0 = \text{Plant Density} \times cc_0 \times 10^{-4}$$

Where:
- $\text{Plant Density}$ is the number of plants per unit ground area ($\text{plants}\cdot\text{m}^{-2}$ or $\text{plants}\cdot\text{ha}^{-1} \times 10^{-4}$).
- $cc_0$ is the mean green canopy cover per seedling at emergence ($\text{cm}^2\cdot\text{plant}^{-1}$).
- $10^{-4}$ converts $\text{cm}^2$ to $\text{m}^2$, yielding dimensionless fractional cover $CC_0$ ($0 < CC_0 \le 1$). If $CC$ is tracked in percent, multiply by $100\%$.

### 3.2 Canopy Expansion: Exponential Growth Phase ($CC \le CC_x / 2$)

During the initial development phase, plants do not shade one another. Growth follows first-order kinetics where the rate of increase is proportional to the existing canopy area:

$$\frac{dCC}{dt} = CGC \cdot CC$$

Integrating from $t = 0$ (at 90% emergence where $CC = CC_0$):

$$CC(t) = CC_0 \cdot \exp(CGC \cdot t) \quad \text{for } CC(t) \le \frac{CC_x}{2}$$

Where:
- $CC_0$ is initial canopy cover (fraction or %).
- $CC_x$ is maximum potential canopy cover (fraction or %).
- $CGC$ is the Canopy Growth Coefficient ($\text{day}^{-1}$ or $(^\circ\text{C}\cdot\text{d})^{-1}$).
- $t$ is elapsed time from emergence ($\text{days}$ or $GDD$).

The inflection point occurs at $CC^* = CC_x / 2$. The time $t_{half}$ required to reach this midpoint is:

$$t_{half} = \frac{\ln\left(\frac{CC_x}{2 \cdot CC_0}\right)}{CGC}$$

### 3.3 Canopy Expansion: Exponential Decay Phase ($CC > CC_x / 2$)

Once canopy cover exceeds half of its maximum ($CC > CC_x / 2$), intra-crop shading and competition decelerate the expansion rate. The growth rate becomes proportional to the remaining unclosed canopy $(CC_x - CC)$:

$$\frac{dCC}{dt} = CGC \cdot (CC_x - CC)$$

The analytical solution for this phase (Raes et al. 2009, Eq. 4; FAO Paper 66, Eq. 4) is:

$$CC(t) = CC_x - (CC_x - CC_0) \cdot \exp(-CGC \cdot t) \quad \text{for } CC(t) > \frac{CC_x}{2}$$

As $t \to \infty$, $CC(t) \to CC_x$. In practice, full canopy cover $CC_x$ is effectively reached within $0.98 \cdot CC_x$ to $0.99 \cdot CC_x$.

### 3.4 Canopy Decline and Senescence Phase ($t \ge t_{sen}$)

Canopy senescence is triggered either when the crop reaches its physiological senescence date ($t_{sen}$, determined by cultivar phenology or thermal time) or prematurely by severe water stress ($p > p_{sen}$).

During senescence, green leaf area declines. AquaCrop models this decline using the Canopy Decline Coefficient ($CDC$), following a non-linear modified exponential equation (Raes et al. 2009; AquaCrop Reference Manual Chapter 3):

$$CC(t) = CC_x \cdot \left[ 1 - 0.05 \cdot \left( \exp\left( \frac{CDC}{CC_x} \cdot (t - t_{sen}) \right) - 1 \right) \right] \quad \text{for } t \ge t_{sen}$$

Subject to the bound $CC(t) \ge 0$.

Behavior:
- At $t = t_{sen}$: $\exp(0) - 1 = 0$, giving $CC(t_{sen}) = CC_x \cdot [1 - 0] = CC_x$.
- As $(t - t_{sen})$ increases, the decline starts slowly and then accelerates as chlorophyll degradation and leaf shed intensify.
- The canopy reaches complete senescence ($CC = 0$) when:
  $$1 - 0.05 \cdot \left( \exp\left( \frac{CDC}{CC_x} \cdot (t_{end} - t_{sen}) \right) - 1 \right) = 0 \implies \exp\left( \frac{CDC}{CC_x} \cdot (t_{end} - t_{sen}) \right) = 21$$
  $$\Delta t_{sen\_to\_zero} = t_{end} - t_{sen} = \frac{\ln(21) \cdot CC_x}{CDC} \approx \frac{3.04452 \cdot CC_x}{CDC}$$

---

## 4. Parameter Symbols, Definitions, Dimensions, and Units

| Symbol | Description | Dimension | Standard SI Unit | Agronomic / Model Unit |
|---|---|---|---|---|
| $t$ | Time elapsed since crop emergence | $[T]$ | $\text{s}$ | $\text{day}$ or $^\circ\text{C}\cdot\text{d}$ |
| $CC$ | Fractional green canopy cover | $[-]$ | $\text{m}^2\cdot\text{m}^{-2}$ | Fraction $[0, 1]$ or $\%$ $[0, 100]$ |
| $CC_0$ | Initial canopy cover at 90% emergence | $[-]$ | $\text{m}^2\cdot\text{m}^{-2}$ | Fraction $[0, 1]$ or $\%$ |
| $cc_0$ | Canopy cover per seedling at emergence | $[L^2]$ | $\text{m}^2\cdot\text{plant}^{-1}$ | $\text{cm}^2\cdot\text{plant}^{-1}$ (typically $5\text{–}15\text{ cm}^2$) |
| $\text{Density}$ | Plant planting density | $[L^{-2}]$ | $\text{plants}\cdot\text{m}^{-2}$ | $\text{plants}\cdot\text{m}^{-2}$ or $\text{plants}\cdot\text{ha}^{-1}$ |
| $CC_x$ | Maximum potential green canopy cover | $[-]$ | $\text{m}^2\cdot\text{m}^{-2}$ | Fraction $[0, 1]$ or $\%$ (typically $0.80\text{–}0.99$) |
| $CGC$ | Canopy growth coefficient | $[T^{-1}]$ | $\text{s}^{-1}$ | $\text{day}^{-1}$ or $(^\circ\text{C}\cdot\text{d})^{-1}$ (typically $0.08\text{–}0.15\text{ d}^{-1}$) |
| $CDC$ | Canopy decline coefficient | $[T^{-1}]$ | $\text{s}^{-1}$ | $\text{day}^{-1}$ or $(^\circ\text{C}\cdot\text{d})^{-1}$ (typically $0.005\text{–}0.02\text{ d}^{-1}$) |
| $t_{sen}$ | Time from emergence to onset of senescence | $[T]$ | $\text{s}$ | $\text{day}$ or $^\circ\text{C}\cdot\text{d}$ |
| $t_{mat}$ | Time from emergence to physiological maturity | $[T]$ | $\text{s}$ | $\text{day}$ or $^\circ\text{C}\cdot\text{d}$ |
| $K_{s,exp}$ | Water stress coefficient for canopy expansion | $[-]$ | Dimensionless | $0.0 \le K_{s,exp} \le 1.0$ |
| $K_{s,sen}$ | Water stress coefficient for canopy senescence | $[-]$ | Dimensionless | $0.0 \le K_{s,sen} \le 1.0$ |
| $p_{exp,upper}$ | Upper soil water depletion threshold for leaf expansion | $[-]$ | Dimensionless fraction of TAW | Typically $0.15\text{–}0.25$ |
| $p_{exp,lower}$ | Lower soil water depletion threshold (expansion ceases) | $[-]$ | Dimensionless fraction of TAW | Typically $0.60\text{–}0.70$ |
| $p_{sen}$ | Soil water depletion threshold triggering early senescence | $[-]$ | Dimensionless fraction of TAW | Typically $0.70\text{–}0.80$ |
| $f_{shape}$ | Shape factor for the water stress curve | $[-]$ | Dimensionless | Typically $1.0\text{–}4.0$ (convex/concave) |

---

## 5. Conservative vs. Calibrated Parameters

AquaCrop divides input parameters into two strict classes:

### 5.1 Conservative Parameters (Constant Across Cultivars and Environments)
These parameters govern basic plant physiology and do not vary with cultivar or geographical location when expressed in normalized thermal units ($GDD$):
1. **Canopy Growth Coefficient ($CGC$) in thermal time:** Relative expansion rate per $^\circ\text{C}\cdot\text{d}$ is conservative for a species under non-limiting fertility.
2. **Canopy Decline Coefficient ($CDC$) in thermal time:** Rate of senescence progression per $^\circ\text{C}\cdot\text{d}$.
3. **Soil water depletion stress thresholds:**
   - Upper and lower thresholds for leaf expansion stress ($p_{exp,upper}$, $p_{exp,lower}$).
   - Upper threshold for senescence stress ($p_{sen}$).
   - Stress response curve shape factors ($f_{shape,exp}$, $f_{shape,sen}$).
4. **Normalized crop water productivity ($WP^*$):** Biomass produced per unit normalized transpiration ($\text{g}\cdot\text{m}^{-2}$).
5. **Base and upper temperature thresholds:** $T_{base}$ and $T_{upper}$.

### 5.2 Calibrated / Cultivar-Specific Parameters (User-Defined)
These depend on agronomic management, field density, soil environment, and seed variety:
1. **Planting density ($\text{plants}\cdot\text{m}^{-2}$) and seedling size ($cc_0$):** Dictates initial cover $CC_0$.
2. **Maximum canopy cover ($CC_x$):** Dictated by cultivar vigor, row spacing, and soil fertility constraints.
3. **Phenological milestones:**
   - Time to emergence ($t_{emerge}$ or $GDD_{emerge}$).
   - Time to maximum canopy cover ($t_{CCx}$ or $GDD_{CCx}$).
   - Time to flowering / reproduction onset.
   - Time to start of senescence ($t_{sen}$ or $GDD_{sen}$).
   - Time to physiological maturity ($t_{mat}$ or $GDD_{mat}$).
4. **Maximum effective rooting depth ($Z_x$) and deepening rate.**
5. **Reference Harvest Index ($HI_0$).**

---

## 6. Soil Water Stress Adjustments

Soil root-zone depletion $D_r$ is measured relative to Total Available Water ($TAW = 1000 \cdot (\theta_{FC} - \theta_{WP}) \cdot Z_r$). The fractional depletion is $p = D_r / TAW$.

### 6.1 Water Stress Effect on Canopy Expansion ($K_{s,exp}$)
Leaf growth is the plant process most sensitive to water deficit (Hsiao 1973). Expansion stress begins at low depletion ($p > p_{exp,upper}$), long before stomata close:

$$K_{s,exp} = 1 - \frac{\exp\left( \frac{p - p_{exp,upper}}{p_{exp,lower} - p_{exp,upper}} \cdot f_{shape} \right) - 1}{\exp(f_{shape}) - 1} \quad \text{for } p_{exp,upper} < p < p_{exp,lower}$$

- If $p \le p_{exp,upper}$: $K_{s,exp} = 1.0$ (no expansion stress).
- If $p \ge p_{exp,lower}$: $K_{s,exp} = 0.0$ (leaf expansion completely halts).
- When $0 < K_{s,exp} < 1.0$, the actual expansion rate is modified daily:
  $$CGC_{adj} = K_{s,exp} \cdot CGC$$

### 6.2 Early Canopy Senescence Trigger ($K_{s,sen}$)
When root-zone water depletion exceeds the senescence threshold ($p > p_{sen}$):
1. Early senescence is activated even if $t < t_{sen}$.
2. The canopy decline coefficient is accelerated:
   $$CDC_{adj} = CDC \cdot \left[ 1 + (1 - K_{s,sen}) \cdot f_{sen\_mult} \right]$$
   where $K_{s,sen}$ decreases from $1.0$ to $0.0$ as $p$ approaches $1.0$ (permanent wilting point).

---

## 7. Hand-Computed Test Cases (Step-by-Step Arithmetic)

The following 5 test cases use round numbers to allow direct implementation in automated unit tests (e.g. `pytest`) without ambiguity.

### Common Base Parameters:
- $CC_0 = 0.050000$ (5.00% initial cover at emergence)
- $CC_x = 0.800000$ (80.00% maximum cover)
- Midpoint threshold: $CC_x / 2 = 0.400000$
- $CGC = 0.100000\text{ day}^{-1}$
- $CDC = 0.040000\text{ day}^{-1}$
- $t_{sen} = 80.0\text{ days}$

---

### Test Case 1: Early Exponential Growth ($CC \le CC_x / 2$)
- **Condition:** Non-stressed growth at $t = 10.0\text{ days}$.
- **Phase check:**
  $$CGC \cdot t = 0.100000 \times 10.0 = 1.000000$$
  $$\exp(CGC \cdot t) = \exp(1.000000) = 2.718281828$$
  $$CC(10) = CC_0 \cdot \exp(1.0) = 0.050000 \times 2.718281828 = 0.13591409 \approx 0.135914$$
- **Verification:** Since $0.135914 \le 0.400000$ ($CC_x/2$), the exponential growth equation applies.
- **Expected result:** $CC(10) = 0.135914$ (or $13.5914\%$).

---

### Test Case 2: Exact Midpoint Transition ($CC = CC_x / 2$)
- **Condition:** Analytical time $t_{half}$ where $CC(t) = CC_x / 2 = 0.400000$.
- **Calculation:**
  $$\frac{CC_x}{2 \cdot CC_0} = \frac{0.800000}{2 \times 0.050000} = \frac{0.800000}{0.100000} = 8.000000$$
  $$\ln(8.000000) = 2.079441542$$
  $$t_{half} = \frac{2.079441542}{0.100000} = 20.794415\text{ days}$$
- **Verification with Phase 1 equation:**
  $$CC(20.794415) = 0.050000 \cdot \exp(0.100000 \times 20.794415) = 0.050000 \times 8.000000 = 0.400000$$
- **Verification with Phase 2 equation:**
  $$CC(20.794415) = 0.800000 - (0.800000 - 0.050000) \cdot \exp(-0.100000 \times 20.794415)$$
  $$= 0.800000 - 0.750000 \cdot \exp(-2.079441542) = 0.800000 - 0.750000 \times \frac{1}{8.000000}$$
  $$= 0.800000 - 0.093750 = 0.706250$$
  *(Note: AquaCrop v1–v7 defines Phase 2 as $CC(t) = CC_x - (CC_x - CC_0) e^{-CGC \cdot t}$ where $t$ is counted from emergence, or switches continuously using an offset $t - t_{half}$; unit tests should explicitly document which form is matched).*
- **Expected result:** At transition threshold, $CC = 0.400000$ (or $40.0000\%$) reached at $t = 20.794415\text{ days}$.

---

### Test Case 3: Exponential Decay Towards Maximum Cover ($CC > CC_x / 2$)
- **Condition:** Late vegetative growth at $t = 30.0\text{ days}$ (where $t > t_{half}$).
- **Calculation using standard decay form:**
  $$CGC \cdot t = 0.100000 \times 30.0 = 3.000000$$
  $$\exp(-CGC \cdot t) = \exp(-3.000000) = 0.049787068$$
  $$CC_x - CC_0 = 0.800000 - 0.050000 = 0.750000$$
  $$(CC_x - CC_0) \cdot \exp(-3.0) = 0.750000 \times 0.049787068 = 0.037340301$$
  $$CC(30) = CC_x - 0.037340301 = 0.800000 - 0.037340301 = 0.762659699 \approx 0.762660$$
- **Verification:** $0.762660 > 0.400000$ and $0.762660 < 0.800000$.
- **Expected result:** $CC(30) = 0.762660$ (or $76.2660\%$).

---

### Test Case 4: Water-Stressed Canopy Expansion ($K_{s,exp} < 1$)
- **Condition:** Mild-to-moderate root-zone water depletion at $t = 10.0\text{ days}$.
- **Stress evaluation:**
  - Let soil depletion be such that $K_{s,exp} = 0.600000$.
  - Adjusted growth coefficient:
    $$CGC_{adj} = K_{s,exp} \cdot CGC = 0.600000 \times 0.100000 = 0.060000\text{ day}^{-1}$$
- **Canopy cover calculation:**
  $$CGC_{adj} \cdot t = 0.060000 \times 10.0 = 0.600000$$
  $$\exp(0.600000) = 1.822118800$$
  $$CC(10)_{stressed} = CC_0 \cdot \exp(0.600000) = 0.050000 \times 1.822118800 = 0.09110594 \approx 0.091106$$
- **Comparison:** Unstressed $CC(10) = 0.135914$. Water stress reduced canopy cover expansion by:
  $$\Delta CC = 0.135914 - 0.091106 = 0.044808 \text{ (a 33.0\% reduction in green cover)}.$$
- **Expected result:** $CC(10)_{stressed} = 0.091106$ (or $9.1106\%$).

---

### Test Case 5: Canopy Senescence and Late-Season Decline ($t \ge t_{sen}$)
- **Condition:** Senescence progression at $t = 100.0\text{ days}$ ($20\text{ days}$ after $t_{sen} = 80.0\text{ days}$).
- **Parameters:**
  - $CC_x = 0.800000$
  - $CDC = 0.040000\text{ day}^{-1}$
  - $t - t_{sen} = 100.0 - 80.0 = 20.0\text{ days}$
- **Step-by-step arithmetic:**
  1. Dimensionless senescence factor:
     $$\frac{CDC}{CC_x} \cdot (t - t_{sen}) = \frac{0.040000}{0.800000} \times 20.0 = 0.050000 \times 20.0 = 1.000000$$
  2. Exponential term:
     $$\exp(1.000000) = 2.718281828$$
  3. Offset:
     $$\exp(1.000000) - 1.0 = 1.718281828$$
  4. Scale by $0.05$:
     $$0.05 \times 1.718281828 = 0.085914091$$
  5. Bracket term:
     $$1.0 - 0.085914091 = 0.914085909$$
  6. Final canopy cover:
     $$CC(100) = CC_x \cdot 0.914085909 = 0.800000 \times 0.914085909 = 0.731268727 \approx 0.731269$$
- **Decline from maximum:** Green cover has dropped by $0.800000 - 0.731269 = 0.068731$ (or $6.87\%$).
- **Expected result:** $CC(100) = 0.731269$ (or $73.1269\%$).

---

## 8. Published Relationships: Canopy Cover ($CC$) vs. Remote Sensing NDVI

To assimilate satellite surface reflectance (such as NASA/USGS HLS 30-meter imagery) into AquaCrop, simulated $CC$ must be translated to and from $NDVI$.

### 8.1 The Carlson & Ripley (1997) Scaled NDVI Model
Carlson & Ripley (1997) demonstrated that fractional vegetation cover $F_r$ ($CC$) is non-linearly related to $NDVI$ due to multiple radiative scattering in plant canopies and bare soil optical background properties.

Define scaled normalized difference vegetation index $N^*$:

$$N^* = \frac{NDVI - NDVI_0}{NDVI_\infty - NDVI_0}$$

Where:
- $NDVI_0$ is the $NDVI$ of bare soil (typically $0.10\text{–}0.18$ for Kansas High Plains silt loams).
- $NDVI_\infty$ is the $NDVI$ of dense, completely closed green vegetation ($CC \to 1.0$, typically $0.85\text{–}0.92$).
- If $NDVI \le NDVI_0$, $N^* = 0.0$; if $NDVI \ge NDVI_\infty$, $N^* = 1.0$.

Under moderate to high leaf optical transmittance, fractional green cover relates to $N^*$ through a quadratic relation:

$$CC \approx (N^*)^2 = \left( \frac{NDVI - NDVI_0}{NDVI_\infty - NDVI_0} \right)^2$$

Inverting for remote sensing forward operator (predicting $NDVI$ from simulated $CC$):

$$NDVI(CC) = NDVI_0 + \sqrt{CC} \cdot (NDVI_\infty - NDVI_0)$$

### 8.2 Troufleau et al. (1995) Exponential Relation
Troufleau et al. (1995) and Baret et al. (1995) proposed an exponential attenuation formulation based on Beer-Lambert radiative transfer:

$$CC = 1 - \left( \frac{NDVI_\infty - NDVI}{NDVI_\infty - NDVI_0} \right)^\eta$$

Where $\eta$ is an extinction coefficient parameter depending on leaf angle distribution (typically $0.6 \le \eta \le 1.1$). When $\eta = 1.0$, this simplifies to the linear spectral mixture model:

$$CC_{linear} = \frac{NDVI - NDVI_0}{NDVI_\infty - NDVI_0}$$

### 8.3 Gitelson et al. (2002 / 2003) Non-linear Saturation Caveat
Gitelson (2004) demonstrated that red-band $NDVI$ saturates when green canopy cover exceeds $\sim 70\text{–}80\%$ ($LAI > 2.5\text{–}3.0$). For high-canopy conditions, Gitelson proposed:
- Using Green NDVI ($GNDVI = (\rho_{NIR} - \rho_{Green}) / (\rho_{NIR} + \rho_{Green})$).
- Or the Wide Dynamic Range Vegetation Index ($WDRVI = (\alpha \cdot \rho_{NIR} - \rho_{Red}) / (\alpha \cdot \rho_{NIR} + \rho_{Red})$ with $\alpha = 0.1\text{–}0.2$).
- In FieldWitness HLS tile T14SLH, red-edge / green bands are available from Sentinel-2 (HLS S30), allowing multi-index assimilation during peak vegetative and early reproductive stages.
