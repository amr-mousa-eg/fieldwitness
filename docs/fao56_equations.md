# FAO-56 equations used in Phase 3 (transcribed 2026-11-04)

Source: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56, **HTML edition (1998)**. The 2nd edition (2025) exists but is **not used**, for consistency with `config/crops.yaml` (values from the 1998 tables).

Equations were read visually from the equation images of the chapter pages (or from the page text where the equation is printed as text). Local copies of the pages and images are in `docs/refs/fao56_eq/` (gitignored, licence unclear — not redistributed); `docs/refs/fao56_eq/index.json` maps each image to its equation number. The HTML has no page numbers: cite **equation number + page URL**. The HTML text garbles Greek letters (`j` = φ, `d` = δ, `w` = ω, `a` = α, `q` = θ, `l` = λ).

| Eq. | Formula | Page | Form |
|---|---|---|---|
| 6 | ETo = [0.408 Δ (Rn − G) + γ · 900/(T + 273) · u2 (es − ea)] / [Δ + γ (1 + 0.34 u2)] | [Ch. 4](https://www.fao.org/4/x0490e/x0490e08.htm) (also Ch. 2) | image `ch4/x0490e1o.gif` |
| 7 | P = 101.3 ((293 − 0.0065 z)/293)^5.26 | [Ch. 3](https://www.fao.org/4/x0490e/x0490e07.htm) | image `ch3/x0490e0c.gif` |
| 8 | γ = cp P/(ε λ) = 0.665 × 10⁻³ P | Ch. 3 | image `ch3/x0490e0d.gif` |
| 11 | e°(T) = 0.6108 exp[17.27 T/(T + 237.3)] | Ch. 3 | image `ch3/x0490e0g.gif` |
| 12 | es = [e°(Tmax) + e°(Tmin)]/2 | Ch. 3 | image `ch3/x0490e0h.gif` |
| 13 | Δ = 4098 [0.6108 exp(17.27 T/(T + 237.3))]/(T + 237.3)² | Ch. 3 | image `ch3/x0490e0i.gif` |
| 17 | ea = [e°(Tmin) RHmax/100 + e°(Tmax) RHmin/100]/2 | Ch. 3 | image `ch3/x0490e0k.gif` |
| 19 | ea = RHmean/100 · [e°(Tmax) + e°(Tmin)]/2 | Ch. 3 | image `ch3/x0490e0m.gif` |
| 21 | Ra = 24(60)/π · Gsc dr [ωs sin φ sin δ + cos φ cos δ sin ωs] | Ch. 3 | image `ch3/x0490e0u.gif` |
| 22 | radians = π/180 · decimal degrees | Ch. 3 | image (stated in text) |
| 23 | dr = 1 + 0.033 cos(2π J/365) | Ch. 3 | image `ch3/x0490e0w.gif` |
| 24 | δ = 0.409 sin(2π J/365 − 1.39) | Ch. 3 | image `ch3/x0490e0x.gif` |
| 25 | ωs = arccos[−tan φ tan δ] | Ch. 3 | text |
| 34 | N = 24/π · ωs | Ch. 3 | image `ch3/x0490e14.gif` |
| 35 | Rs = (as + bs n/N) Ra; as = 0.25, bs = 0.50 recommended without calibration | Ch. 3 | image `ch3/x0490e17.gif` + text |
| 37 | Rso = (0.75 + 2 × 10⁻⁵ z) Ra | Ch. 3 | text |
| 38 | Rns = (1 − α) Rs, α = 0.23 for the grass reference | Ch. 3 | text |
| 39 | Rnl = σ [(Tmax,K⁴ + Tmin,K⁴)/2] (0.34 − 0.14 √ea) (1.35 Rs/Rso − 0.35); K = °C + 273.16 | Ch. 3 | image `ch3/x0490e18.gif` + text |
| 40 | Rn = Rns − Rnl | Ch. 3 | text |
| 42 | G_day ≈ 0 | Ch. 3 | text |
| 62 | Kc mid = Kc mid (Tab) + [0.04 (u2 − 2) − 0.004 (RHmin − 45)] (h/3)^0.3 | [Ch. 6](https://www.fao.org/4/x0490e/x0490e0b.htm) | image `ch6/x0490e2d.gif` |
| 82 | TAW = 1000 (θFC − θWP) Zr | [Ch. 8](https://www.fao.org/4/x0490e/x0490e0e.htm) | text |
| 83 | RAW = p TAW | Ch. 8 | text |
| 84 | Ks = (TAW − Dr)/(TAW − RAW) = (TAW − Dr)/((1 − p) TAW), for Dr > RAW | Ch. 8 | image `ch8/x0490e2w.gif` + text |
| 85 | Dr,i = Dr,i−1 − (P − RO)i − Ii − CRi + ETc,i + DPi | Ch. 8 | text |

Constants (Ch. 3 symbol lists): Gsc = 0.0820 MJ m⁻² min⁻¹; σ = 4.903 × 10⁻⁹ MJ K⁻⁴ m⁻² day⁻¹.

**Check:** Example 18 (Uccle, 6 July, Ch. 4) is reproduced by `src/fieldwitness/physics/eto.py` in `tests/test_eto.py`: ETo = 3.88 mm/day (printed: 3.88 ≈ 3.9), Ra = 41.09, Rs = 22.07, Rso = 30.90, Rnl = 3.71 MJ m⁻² day⁻¹.

Not yet transcribed (not needed so far): Annex 2 tables (Table 2.5 day numbers etc.; the page has no numbered equations), Eq. 47 (wind at 2 m; POWER WS2M is already at 2 m), other Ch. 3/6/8 equations. Read them from the same pages when a task needs them.
