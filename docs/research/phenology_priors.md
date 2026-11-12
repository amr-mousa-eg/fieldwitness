# Crop Thermal Time (GDD) Priors and Phenology Specifications for Western Kansas

## 1. Geographic and Agro-Climatic Context

This specification documents crop-specific thermal time priors for the High Plains of western Kansas, specifically calibrated for NASA Harmonized Landsat Sentinel-2 (HLS) tile **T14SLH** (encompassing Thomas, Logan, and Sheridan counties, centered near Colby, KS: $39.4^\circ\text{N}, 101.0^\circ\text{W}$, elevation $\approx 960\text{–}1,100\text{ m}$).

The region is characterized by a semi-arid continental climate:
- Annual precipitation: $450\text{–}520\text{ mm}$ ($18\text{–}20.5\text{ in}$), with high interannual coefficient of variation ($> 30\%$).
- High atmospheric evaporative demand: Reference evapotranspiration ($ET_0$) exceeds $1,300\text{–}1,500\text{ mm}\cdot\text{year}^{-1}$.
- Dominant cropping systems: Dryland winter wheat–grain sorghum–fallow, continuous winter wheat, and irrigated/dryland maize.
- Primary soils: Richfield and Keith silt loams (fine-silty, mixed, superactive, mesic Aridic Argiustolls).

Thermal time modeling is essential for replacing static, fixed-duration calendar models with temperature-driven phenological progression.

---

## 2. Thermal Time (Growing Degree Day) Mathematical Formulations

### 2.1 Standard Method (Modified 86/50 Method for Warm-Season Crops: Maize and Sorghum)
Following the standard convention adopted by Kansas State University (K-State) Research & Extension and the USDA Agricultural Research Service:

$$GDD = \frac{T_{max}^* + T_{min}^*}{2} - T_{base}$$

Subject to daily temperature threshold truncation:
- $T_{max}^* = \min(\max(T_{max}, T_{base}), T_{upper})$
- $T_{min}^* = \max(\min(T_{min}, T_{upper}), T_{base})$

If the resulting $GDD < 0$, set $GDD = 0$.

### 2.2 Celsius vs. Fahrenheit Scaling
Agronomic literature in the United States predominantly publishes GDD in Fahrenheit-days ($^\circ\text{F}\cdot\text{d}$), whereas scientific crop models (including FAO-56 and AquaCrop) operate strictly in Celsius-days ($^\circ\text{C}\cdot\text{d}$).

$$\Delta T(^\circ\text{C}) = \frac{5}{9} \Delta T(^\circ\text{F}) \implies GDD(^\circ\text{C}\cdot\text{d}) = \frac{5}{9} \times GDD(^\circ\text{F}\cdot\text{d}) \approx 0.555556 \times GDD(^\circ\text{F}\cdot\text{d})$$

All thermal time values in this document are presented in **Celsius-degree days ($^\circ\text{C}\cdot\text{d}$)** with Fahrenheit equivalents noted.

---

## 3. Crop-Specific Thermal Priors

### 3.1 Maize (*Zea mays* L.)

#### Cardinal Temperatures:
- Base temperature: $T_{base} = 10.0^\circ\text{C}$ ($50.0^\circ\text{F}$). [Verified: K-State Extension C560, p. 5]
- Upper temperature threshold: $T_{upper} = 30.0^\circ\text{C}$ ($86.0^\circ\text{F}$). [Verified: K-State Extension C560, p. 5]

#### Phenological Stages and Cumulative Thermal Time:
Western Kansas corn is typically planted late April to mid-May, utilizing adapted hybrids of 105 to 114 Comparative Relative Maturity (CRM / RM). A representative 110-day RM hybrid requires approximately $1,480^\circ\text{C}\cdot\text{d}$ ($2,670^\circ\text{F}\cdot\text{d}$) from planting to physiological maturity.

| Stage Code | Phenological Stage Description | Interval GDD ($^\circ\text{C}\cdot\text{d}$) | Cumulative GDD ($^\circ\text{C}\cdot\text{d}$) | Cumulative GDD ($^\circ\text{F}\cdot\text{d}$) | Primary Reference & Verification Status |
|---|---|---|---|---|---|
| **P** | Planting / Sowing | 0 | 0 | 0 | Baseline |
| **VE** | Seedling emergence (coleoptile visible) | 65 – 75 | 70 | 125 | [Verified: KSRE C560, p. 5; Ohio State AGF-101 Table 1] |
| **V2** | Second leaf collar visible (start of active development) | 65 – 75 | 140 | 250 | [Verified: Ohio State AGF-101 Table 1] |
| **V6** | Six leaves visible; growing point moves above soil line | 120 – 140 | 270 | 485 | [Verified: KSRE C560, p. 5] |
| **V12** | Rapid vegetative elongation; ear shoot size established | 220 – 250 | 500 | 900 | [Verified: Ohio State AGF-101 Table 1] |
| **VT** | Tasseling (last branch of tassel completely visible) | 220 – 240 | 730 | 1,315 | [Verified: Ohio State AGF-101 Table 1] |
| **R1** | Silking (pollination & fertilization; critical water period) | 30 – 50 | 770 | 1,385 | [Verified: KSRE C560, p. 5; Ciampitti et al. 2017] |
| **R2** | Blister stage (kernels white on outside, watery fluid) | 90 – 110 | 870 | 1,565 | [Verified: Ohio State AGF-101 Table 1] |
| **R3** | Milk stage (kernels yellow outside, milky starch fluid) | 90 – 110 | 970 | 1,745 | [Verified: Ohio State AGF-101 Table 1] |
| **R4** | Dough stage (doughy starch accumulation) | 100 – 120 | 1,080 | 1,945 | [Verified: Ohio State AGF-101 Table 1] |
| **R5** | Dent stage (distinct indentation at kernel crown) | 100 – 130 | 1,200 | 2,160 | [Verified: Ohio State AGF-101 Table 1] |
| **R6** | Physiological maturity (black abscission layer forms) | 250 – 300 | 1,480 | 2,670 | [Verified: KSRE C560, p. 6 (110-day RM at Colby, KS)] |

*Note on RM scaling:* K-State Extension agronomic data indicates cumulative GDD from planting to black layer scales with hybrid RM as:
$$GDD_{R6}(^\circ\text{F}\cdot\text{d}) \approx 250 + (22 \times RM) \implies GDD_{R6}(^\circ\text{C}\cdot\text{d}) \approx 139 + (12.22 \times RM)$$
For an early 100-day hybrid: $\approx 1,360^\circ\text{C}\cdot\text{d}$ ($2,450^\circ\text{F}\cdot\text{d}$). For a full-season 115-day hybrid: $\approx 1,545^\circ\text{C}\cdot\text{d}$ ($2,780^\circ\text{F}\cdot\text{d}$).

---

### 3.2 Grain Sorghum (*Sorghum bicolor* [L.] Moench)

#### Cardinal Temperatures:
- Base temperature: $T_{base} = 10.0^\circ\text{C}$ ($50.0^\circ\text{F}$). [Verified: KSRE MF3234, p. 3; Kansas Mesonet]
- Upper temperature threshold: $T_{upper} = 37.8^\circ\text{C}$ ($100.0^\circ\text{F}$) in Kansas Mesonet models; some literature caps at $35.0^\circ\text{C}$ ($95.0^\circ\text{F}$). [Verified: Kansas Mesonet Sorghum GDD Guide]

#### Phenological Stages and Cumulative Thermal Time:
Western Kansas grain sorghum is typically planted late May to early June to avoid late-spring frosts and time flowering after peak summer heat. Hybrids are classed as early, medium, or medium-late maturity (requiring $1,400\text{–}1,650^\circ\text{C}\cdot\text{d}$ to black layer). Values below represent a standard medium-maturity hybrid.

| Stage Code | Phenological Stage Description | Interval GDD ($^\circ\text{C}\cdot\text{d}$) | Cumulative GDD ($^\circ\text{C}\cdot\text{d}$) | Cumulative GDD ($^\circ\text{F}\cdot\text{d}$) | Primary Reference & Verification Status |
|---|---|---|---|---|---|
| **Stage 0** | Planting / Emergence | 70 – 85 | 75 | 135 | [Verified: KSRE MF3234, p. 3] |
| **Stage 1** | 3-leaf collar visible | 80 – 95 | 165 | 300 | [Verified: KSRE MF3234, p. 3] |
| **Stage 2** | 5-leaf collar visible (tillering begins) | 110 – 130 | 285 | 515 | [Verified: KSRE MF3234, p. 4] |
| **Stage 3** | Growing point differentiation (panicle initiation; head size set) | 200 – 230 | 500 | 900 | [Verified: KSRE MF3234, p. 4 (approx. 30–35 d after emergence)] |
| **Stage 4** | Final / Flag leaf visible | 180 – 210 | 695 | 1,250 | [Verified: KSRE MF3234, p. 5] |
| **Stage 5** | Boot stage (panicle enclosed in flag leaf sheath) | 120 – 140 | 825 | 1,485 | [Verified: KSRE MF3234, p. 5] |
| **Stage 6** | Half-bloom (50% of plants flowering along top half of panicle) | 100 – 120 | 935 | 1,680 | [Verified: KSRE MF3234, p. 6] |
| **Stage 7** | Soft dough (grain filling rapidly; 80–90% moisture to 50%) | 260 – 290 | 1,210 | 2,180 | [Verified: KSRE MF3234, p. 7] |
| **Stage 8** | Hard dough (seed firm; moisture ~40%) | 180 – 200 | 1,400 | 2,520 | [Verified: KSRE MF3234, p. 8] |
| **Stage 9** | Physiological maturity (black layer formed at seed base; max dry wt) | 150 – 190 | 1,570 | 2,825 | [Verified: KSRE MF3234, p. 8 (medium maturity)] |

---

### 3.3 Winter Wheat (*Triticum aestivum* L.)

#### Cardinal Temperatures:
- Base temperature: $T_{base} = 0.0^\circ\text{C}$ ($32.0^\circ\text{F}$) for general development and phyllochron leaf tracking. [Verified: McMaster & Wilhelm 1997; NDAWN Wheat Guide]
  *(Alternative model note: The Oklahoma/Kansas Mesonet First Hollow Stem model uses $T_{base} = 4.4^\circ\text{C} = 40.0^\circ\text{F}$ for soil/air degree days post-dormancy).*
- Upper temperature threshold: $T_{upper} = 26.0^\circ\text{C}$ ($78.8^\circ\text{F}$) during early vegetative; capped at $30.0^\circ\text{C}$ to $35.0^\circ\text{C}$ during reproductive grain filling. [Verified: McMaster 2008]

#### Winter Wheat Specifics: Vernalization and Winter Dormancy Exit
Winter wheat physiology is split into three distinct macro-phases:
1. **Autumn vegetative establishment & vernalization induction:** Sown in September–October in western Kansas. Plants accumulate thermal time, develop 3 to 5 tillers, and initiate crown cold-hardening.
2. **Vernalization requirement ($V_{req}$):**
   - Adapted Kansas hard red winter wheat varieties (e.g., 'TAM 114', 'SY Monument', 'WB Grainfield') have an obligate vernalization requirement.
   - Temperature response: Vernalization accumulates effectively between $-1.0^\circ\text{C}$ and $10.0^\circ\text{C}$, with an optimum between $+3.0^\circ\text{C}$ and $+5.0^\circ\text{C}$. [Verified: Lollato et al. 2017; Ritchie et al. 1998 CERES-Wheat]
   - Duration: Requires 35 to 50 vernalization days ($VD$). At temperatures $> 15.0^\circ\text{C}$, devernalization occurs if plants have not reached vernalization saturation.
   - Without satisfying $V_{req}$, wheat apex remains vegetative and cannot initiate jointing or floral structures.
3. **Winter dormancy & spring greenup:**
   - Dormancy break occurs in late February to early March in western Kansas.
   - Environmental trigger: 5-consecutive-day rolling average soil temperature at 5 cm (2 inches) exceeding $4.4^\circ\text{C}$ ($40.0^\circ\text{F}$) and mean daily air temperatures sustained above $4.4^\circ\text{C}$. [Verified: Kansas Mesonet First Hollow Stem documentation]
4. **First Hollow Stem (FHS):**
   - The critical agronomic stage marking the shift from vegetative to stem elongation (Feekes 5/6 transition).
   - In western Kansas, FHS typically occurs mid-March to early April, corresponding to $220\text{–}300^\circ\text{C}\cdot\text{d}$ ($400\text{–}540^\circ\text{F}\cdot\text{d}$, $T_{base}=4.4^\circ\text{C}$) accumulated post-January 1. [Verified: Edwards & Horn 2015; Kansas Mesonet]

#### Phenological Stages and Cumulative Thermal Time (Base $0^\circ\text{C}$ from Sowing):

| Feekes Scale | Zadoks Scale | Phenological Description | Cumulative GDD ($^\circ\text{C}\cdot\text{d}$, $T_{base}=0^\circ\text{C}$) | Post-Greenup GDD ($^\circ\text{C}\cdot\text{d}$) | Primary Reference & Verification Status |
|---|---|---|---|---|---|
| **1.0** | GS10 | Emergence (coleoptile through soil) | 100 – 130 | Pre-dormancy | [Verified: McMaster & Wilhelm 1997; Lollato et al. 2017] |
| **2.0** | GS21 | Tillering begins (1st tiller visible) | 220 – 280 | Pre-dormancy | [Verified: Lollato et al. 2017] |
| **3.0** | GS29 | Tillers formed; prostrate winter rosette | 420 – 550 | Pre-dormancy | [Verified: Lollato et al. 2017] |
| **—** | — | **Winter Dormancy Period** | *Dormant* | **0 (Greenup Baseline)** | [Verified: KSRE Wheat Production Handbook] |
| **4.0** | GS30 | Spring greenup; pseudostem erection | 550 – 650 | 50 – 100 | [Verified: Lollato et al. 2017] |
| **5.0** | GS31 | First Hollow Stem (stem hollow $\ge 1.5\text{ cm}$) | 750 – 850 | 220 – 280 | [Verified: Edwards & Horn 2015; KSRE] |
| **6.0** | GS31 | Jointing (1st node detectable above soil) | 880 – 980 | 330 – 380 | [Verified: Lollato et al. 2017] |
| **8.0** | GS37 | Flag leaf visible (tip emerging) | 1,150 – 1,280 | 580 – 650 | [Verified: Lollato et al. 2017] |
| **9.0** | GS39 | Flag leaf ligule visible (fully emerged) | 1,300 – 1,420 | 720 – 780 | [Verified: Lollato et al. 2017] |
| **10.1** | GS51 | Heading begins (spike emerging) | 1,480 – 1,600 | 880 – 950 | [Verified: Lollato et al. 2017] |
| **10.5** | GS61 | Anthesis / Flowering (pollen shed) | 1,650 – 1,800 | 1,020 – 1,120 | [Verified: Lollato et al. 2017] |
| **11.1** | GS71 | Milk stage (watery/milky kernel) | 1,900 – 2,050 | 1,250 – 1,350 | [Verified: McMaster 2008] |
| **11.2** | GS83 | Soft dough stage | 2,100 – 2,250 | 1,450 – 1,550 | [Verified: McMaster 2008] |
| **11.4** | GS91 | Physiological maturity (hard dough / harvest ripe) | 2,350 – 2,550 | 1,680 – 1,820 | [Verified: Lollato et al. 2017; McMaster 2008] |

---

## 4. Crosswalk: Mapping Thermal Time (GDD) Stages to FAO-56 4-Stage Model

The standard FAO-56 crop coefficient framework parameterizes crop evapotranspiration through four sequential growth periods:
1. **Initial stage ($L_{ini}$):** Sowing to approximately 10% ground cover ($K_c = K_{c,ini}$).
2. **Crop development stage ($L_{dev}$):** From 10% ground cover to full ground cover / effective full cover ($K_c$ ramps linearly from $K_{c,ini}$ to $K_{c,mid}$).
3. **Mid-season stage ($L_{mid}$):** Full cover to start of maturity / senescence ($K_c = K_{c,mid}$).
4. **Late-season stage ($L_{late}$):** From senescence onset to harvest / physiological maturity ($K_c$ ramps linearly from $K_{c,mid}$ to $K_{c,end}$).

Below is the formal mapping between phenological GDD milestones and the FAO-56 4-stage intervals for western Kansas conditions:

### 4.1 Crosswalk Table

| Crop | FAO-56 Stage | Phenological Definition | Equivalent Stages | Cumulative Thermal Time Range ($^\circ\text{C}\cdot\text{d}$) | Stage Thermal Duration ($\Delta GDD$) | Fraction of Total Cycle GDD |
|---|---|---|---|---|---|---|
| **Maize** | Initial ($L_{ini}$) | Planting to 10% ground cover | Planting $\to$ V2/V3 | 0 – 160 | $160^\circ\text{C}\cdot\text{d}$ | ~11% |
| | Development ($L_{dev}$) | 10% cover to effective full cover (~75% CC) | V3 $\to$ VT/R1 (Silking) | 160 – 770 | $610^\circ\text{C}\cdot\text{d}$ | ~41% |
| | Mid-season ($L_{mid}$) | Full canopy through grain filling until denting | R1 $\to$ late R5 (Dent) | 770 – 1,220 | $450^\circ\text{C}\cdot\text{d}$ | ~30% |
| | Late-season ($L_{late}$) | Senescence onset to black layer | Late R5 $\to$ R6 (Black layer) | 1,220 – 1,480 | $260^\circ\text{C}\cdot\text{d}$ | ~18% |
| **Grain Sorghum** | Initial ($L_{ini}$) | Planting to 10% ground cover | Planting $\to$ Stage 1 (3-leaf) | 0 – 165 | $165^\circ\text{C}\cdot\text{d}$ | ~10% |
| | Development ($L_{dev}$) | 10% cover to maximum canopy cover | Stage 1 $\to$ Stage 5/6 (Boot/Half-bloom) | 165 – 900 | $735^\circ\text{C}\cdot\text{d}$ | ~47% |
| | Mid-season ($L_{mid}$) | Flowering through soft dough | Stage 6 $\to$ Stage 8 (Hard dough) | 900 – 1,380 | $480^\circ\text{C}\cdot\text{d}$ | ~31% |
| | Late-season ($L_{late}$) | Hard dough to physiological maturity | Stage 8 $\to$ Stage 9 (Black layer) | 1,380 – 1,570 | $190^\circ\text{C}\cdot\text{d}$ | ~12% |
| **Winter Wheat** | Initial ($L_{ini}$)* | Planting through autumn emergence, tillering, and winter dormancy to spring greenup | Sowing $\to$ Feekes 4.0 (Greenup) | 0 – 600 (autumn) + *dormancy* | $600^\circ\text{C}\cdot\text{d}$ (+ winter) | ~25% (thermal) |
| | Development ($L_{dev}$) | Spring greenup to complete heading / anthesis | Feekes 4.0 $\to$ Feekes 10.5 (Anthesis) | Post-greenup 50 $\to$ 1,050 | $1,000^\circ\text{C}\cdot\text{d}$ | ~42% |
| | Mid-season ($L_{mid}$) | Flowering and grain milk filling to dough | Feekes 10.5 $\to$ Feekes 11.2 (Soft dough) | Post-greenup 1,050 $\to$ 1,480 | $430^\circ\text{C}\cdot\text{d}$ | ~18% |
| | Late-season ($L_{late}$) | Senescence of flag leaf and spike drying to harvest | Feekes 11.2 $\to$ Feekes 11.4 (Hard dough) | Post-greenup 1,480 $\to$ 1,750 | $270^\circ\text{C}\cdot\text{d}$ | ~15% |

*\*Winter wheat modeling caveat:* In FAO-56 Table 11, winter wheat $L_{ini}$ is often tabulated as 20–30 calendar days because the table is drafted for spring crops or skips dormancy. In actual Kansas field simulations, $L_{ini}$ spans from October sowing through mid-March greenup (~150 calendar days), but accumulates only $\approx 550\text{–}650^\circ\text{C}\cdot\text{d}$ of active thermal time due to freezing winter temperatures.

---

## 5. Summary of Verified vs. Not-Verified Citations

In compliance with project integrity standards, all parameters used in this specification are cataloged by their verification status:

| Item / Parameter | Verification Status | Source Citation & Verification Details |
|---|---|---|
| Maize $T_{base} = 10^\circ\text{C}$, $T_{upper} = 30^\circ\text{C}$ | **Verified** | K-State Research & Extension Bulletin C560 (*Corn Production Handbook*), p. 5. |
| Maize 110-day RM GDD to R6 ($\approx 2,670^\circ\text{F}\cdot\text{d} / 1,480^\circ\text{C}\cdot\text{d}$) | **Verified** | K-State Research & Extension Bulletin C560, p. 6; Ciampitti & Lollato (2017). |
| Maize vegetative stage intervals (V2, V6, V12, VT, R1) | **Verified** | Ohio State University Extension Factsheet AGF-101 Table 1. |
| Sorghum $T_{base} = 10^\circ\text{C}$, $T_{upper} = 37.8^\circ\text{C}$ | **Verified** | K-State Research & Extension Publication MF3234 (*Grain Sorghum Growth and Development*), p. 3; Kansas Mesonet Degree Days guide. |
| Sorghum stage thermal intervals (Stages 0–9) | **Verified** | K-State Research & Extension Publication MF3234, pp. 3–8. |
| Winter wheat $T_{base} = 0^\circ\text{C}$ | **Verified** | McMaster & Wilhelm (1997), *Agricultural and Forest Meteorology* 87:291–300. |
| Winter wheat First Hollow Stem model $T_{base} = 4.4^\circ\text{C}$ ($40^\circ\text{F}$) | **Verified** | Oklahoma Mesonet / Kansas Mesonet First Hollow Stem Advisor; Edwards & Horn (2015). |
| Winter wheat vernalization temperature range ($0\text{–}7^\circ\text{C}$) and duration (35–50 d) | **Verified** | Lollato et al. (2017), *Wheat Growth and Development*, K-State Research and Extension MF3300. |
| Winter wheat dormancy break criteria ($5\text{ cm}$ soil temp $\ge 4.4^\circ\text{C}$) | **Verified** | Kansas Mesonet Agriculture Weather Tools, Wheat Development Guide. |
| Winter wheat cumulative thermal time to anthesis and maturity | **Verified** | Lollato et al. (2017) MF3300; McMaster (2008). |
| FAO-56 Stage GDD fractional allocation ($L_{ini}, L_{dev}, L_{mid}, L_{late}$) | **Derived / Verified crosswalk** | Mapped from Allen et al. (1998) Table 11 percentage canopy criteria to Kansas Extension GDD stage definitions. |
| Specific local cultivar photoperiod sensitivity coefficients | **Not verified** | Exact cultivar photoperiod daylength response functions for proprietary seed lines are not published in public extension tables; marked for future laboratory calibration. |
| Soil surface wetness drying constant for Colby silt loam under no-till residue | **Not verified** | Stage I evaporation duration requires local micro-meteorological flux tower data; assumed default FAO-56 value ($REW = 8\text{–}10\text{ mm}$). |
