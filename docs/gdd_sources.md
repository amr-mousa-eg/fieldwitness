# Thermal-time (GDD) parameters: sources and table locations (Experiment 2)

Read on 2026-11-12. Values are copied into `config/crops.yaml` as new `gdd_phenology` keys (maize, sorghum, winter wheat). The existing FAO-56 values are unchanged. Used only when `phenology_mode: gdd` (experiment branch); packs and the app never use them.

## Sources

1. **K-State Extension MF3740.** Soni, M., Sheshukov, A., Aguilar, J., Simon, L., Lin, X. (June 2026). *Understanding Growing Degree Days: Temperature Limits and Their Role in Crop Growth and Development.* Kansas State University. https://bookstore.ksre.ksu.edu/download/understanding-growing-degree-days_MF3740 (PDF, 8 pages, text read with pypdf).
   - **Table 1** "Temperature thresholds for major crops in Kansas" (p. 1, source given as Luo 2011): T_lower / T_upper in °F. Corn 50 / 86; Sorghum 46 / 100; Winter wheat 32 / 79.
   - **Equations (1)–(2)** (p. 2): GDD = T_avg − T_base, T_avg = (T_max + T_min)/2.
   - **Table 2** (p. 3): three methods. Method 2: limit T_min to T_lower and T_max to T_upper, average, subtract T_base, negatives set to zero. The worked examples (p. 4, corn) are reproduced in `tests/test_phenology_gdd.py` (0, 10 and 29 °F·d).
   - **Table 3** "Corn GDD requirements" (p. 6, °F, ranges): VE 100–200; V6 475–590; VT 1,000–1,170; R1 1,400–1,830; R4 1,925–1,980; R5 2,190–2,450; R6 2,650–2,700.
   - **Table 5** "Sorghum GDD requirements" (p. 6, °F, short- / full-season hybrid): Emergence 200/200; 3-leaf 500/500; 5-leaf 660/660; Panicle initiation 924/1,365; Flag leaf 1,287/1,470; Boot 1,683/1,750; Heading 1,749/1,890; Flowering 1,848/1,995; Soft dough 2,211/2,310; Hard dough 2,508/2,765; Black layer 2,673/3,360.
   - The publication does not state from when to count. Tables 3 and 5 refer to GDD from planting (the text on p. 5 describes tracking "from planting through maturity").
2. **Kansas Mesonet, Wheat Growth Stage tool** (Kansas State University). https://mesonet.k-state.edu/agriculture/wheat/gdd/ (read in a browser).
   - Resources tab: Growing Degrees = (daily max air temp + daily min air temp)/2 − 32, negative values set to 0 (°F, no upper limit).
   - Current Observations panel: the count runs from Jan 1.
   - Map Legend table "GDD °F | Estimated Wheat Growth Stage": 0–600 seedling growth or tillering; 600–800 tillering or strongly upright tillers; 800–1,000 upright tillers or jointing; 1,000–1,200 jointing or approaching flag leaf; 1,200–1,400 flag leaf or boot; 1,400–1,600 boot or heading; 1,600–1,800 heading to flowering; 1,800–2,000 heading or flowering; 2,000–2,200 flowering or watery ripe; 2,200–2,400 watery ripe or milk; 2,400–2,600 milk or dough; 2,600–2,800 and 2,800–3,000 dough or kernels maturing; more than 3,000 physiologically mature or approaching harvest.
   - No citation is given for the bands, and nothing is said about dormancy.
3. **FAO-56, Chapter 5, "Crop growth stages"** (https://www.fao.org/4/x0490e/x0490e0a.htm). Initial: planting to about 10 % ground cover. Development: to effective full cover (for many crops the initiation of flowering; heading for dense cereals). Mid-season: to the start of maturity. Late season: to harvest or full senescence. **Chapter 6** (x0490e0b.htm) allows degree-based prediction of emergence and effective full cover, to be validated locally.

Checked and not used: Montana State MT200103 (Miller, Lanier, Brandt, July 2001), Table 1. Its hard red wheat GDD are counted from seeding and were measured on spring-sown wheat in Saskatchewan, not on Kansas winter wheat. The USA-NPN winter wheat forecast names no source for its stage bands.

## Choices (tag A, approved by the user on 2026-11-12; DECISIONS.md)

| Crop | Formula | Count start | Initial end | Development end | Mid end | Late end |
|---|---|---|---|---|---|---|
| Maize | MF3740 Method 2, 50 / 86 °F | planting | V6 532.5 | R1 1,615 | R5 2,320 | R6 2,675 |
| Sorghum | MF3740 Method 2, 46 / 100 °F | planting | 5-leaf 660 | Flowering 1,848 | Soft dough 2,211 | Black layer 2,673 |
| Winter wheat | Mesonet, base 32 °F, no cap | 1 Jan of harvest year | 600 | 1,600 | 2,600 | 3,000 |

- Values are cumulative °F·d. Maize uses range midpoints and sorghum the short-season hybrid column.
- Winter wheat: the days from sowing to 31 December stay in the calendar initial stage. The source gives no dormancy rule.
- MF3740 gives 32 / 79 °F for wheat. That cap is not used, because the Mesonet bands were built with the uncapped formula.
- Conversion to °C (NASA POWER units): T °C = (T °F − 32)·5/9, and Δ°C·d = 5/9 Δ°F·d.
