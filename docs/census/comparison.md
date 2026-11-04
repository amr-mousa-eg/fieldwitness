# Census comparison (T0.5)

One row per region and season. Observation counts are medians over harvest years 2016–2024 of HLS-VI granules (L30 + S30) on the region tile, from CMR metadata; `obs_cloud<=20` counts granules with tile-level cloud ≤ 20 %; `_cov>=50` additionally requires `SPATIAL_COVERAGE` ≥ 50 % of the tile (many granules cover only part of a tile, so raw counts overstate observations at a given field). ECOSTRESS: median overpasses per season 2019–2024 at the region point. Field statistics: first sample box per region (20 km; Ukraine 10 km; FTW: 2024 layer only). Season windows: tag **A**. Per-region details: `docs/census/<region>.md`. Region status (user decision): `ks_t14slh` selected; `fr_beauce_t31ucp` comparison; `pb_jagraon_t43req` rejected; `ua_central_t36uvu` selected; `eg_nile_delta` showcase; `fr_toulouse_t31tcj` selected.

| region | tier | tile | season | obs | obs_cloud<=20 | worst_year_cloud<=20 | obs_cloud<=20_cov>=50 | worst_year_cloud<=20_cov>=50 | eco_v002 | eco_v003 | median_field_ha | share>=4px_buf30 | share>=4px_buf15 | share_scale_flag | label_years |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ks_t14slh | 1 | T14SLH | summer | 98 | 51 | 17 | 46 | 15 | 73.0 | 0.0 | 5.98 | 0.842 | 0.986 | 0.0 | 8 |
| ks_t14slh | 1 | T14SLH | winter_wheat | 141 | 70 | 22 | 63 | 19 | 88.5 | 0.0 | 5.98 | 0.842 | 0.986 | 0.0 | 8 |
| fr_beauce_t31ucp | 2 | T31UCP | winter | 145 | 34 | 7 | 30 | 4 | 109.5 | 0.0 | 7.58 | 0.801 | 0.872 | 0.05 | 10 |
| fr_beauce_t31ucp | 2 | T31UCP | summer | 107 | 21 | 10 | 19 | 8 | 106.5 | 0.0 | 7.58 | 0.801 | 0.872 | 0.05 | 10 |
| pb_jagraon_t43req | 3 | T43REQ | kharif | 71 | 29 | 17 | 14 | 10 | 19.0 | 0.0 | 0.44 | 0.024 | 0.183 | 0.433 | 0 |
| pb_jagraon_t43req | 3 | T43REQ | rabi | 80 | 45 | 19 | 20 | 9 | 19.0 | 0.0 | 0.44 | 0.024 | 0.183 | 0.433 | 0 |
| ua_central_t36uvu | 3 | T36UVU | winter | 136 | 45 | 29 | 39 | 22 | 15.0 | 0.0 | 3.29 | 0.553 | 0.738 | 0.106 | 0 |
| ua_central_t36uvu | 3 | T36UVU | summer | 113 | 41 | 24 | 34 | 19 | 11.5 | 0.0 | 3.29 | 0.553 | 0.738 | 0.106 | 0 |
| eg_nile_delta | 3 | T36RTV | winter | 104 | 46 | 22 | 22 | 9 | 12.5 | 0.0 | 0.88 | 0.069 | 0.336 | 0.253 | 0 |
| eg_nile_delta | 3 | T36RTV | summer | 96 | 67 | 26 | 32 | 15 | 19.5 | 0.0 | 0.88 | 0.069 | 0.336 | 0.253 | 0 |
| fr_toulouse_t31tcj | 2 | T31TCJ | winter | 190 | 58 | 22 | 31 | 14 | 150.0 | 0.0 | 3.76 | 0.738 | 0.886 | 0.022 | 10 |
| fr_toulouse_t31tcj | 2 | T31TCJ | summer | 130 | 46 | 29 | 25 | 13 | 141.0 | 0.0 | 3.76 | 0.738 | 0.886 | 0.022 | 10 |


## Recommendation (Claude Code, 2026-11-04 — for the user to decide)

**Tier 1 — Kansas `T14SLH`: recommend.** 8 label years (CSB 2017–2024); the most clear observations (summer 46, winter-wheat 63 granules with cloud ≤ 20 % and coverage ≥ 50 %; worst year 15 / 19). Full-tile CSB sample: 18,739 fields, median 24.8 ha, 88.6 % with ≥ 4 interior pixels at the 30 m buffer, none below the 0.36 ha scale flag. (The 20 km box in the table sits near Garden City and has smaller fields, median 6.0 ha.) ECOSTRESS v002: 73–89 overpasses per season.

**Tier 2 — Beauce `T31UCP`: recommend, with a cloud warning.** 10 label years (2015–2024). It is the cloudiest candidate: 19 (summer) and 30 (winter) clear, well-covered granules per season, worst years 8 and 4 (the worst years are 2016–2017, before Sentinel-2B). Fields are mixed: median 3.0 ha, 54 % with ≥ 4 interior pixels at 30 m (61 % at 15 m), 24 % below the scale flag. Tier 2 is last in the build order (PLAN.md §1), so this risk is contained.

**Tier 3 — decide between Ukraine and the Nile Delta; do not pick Punjab.**
- Punjab `T43REQ` fails the scale contract for most fields: median 0.44 ha, only 2.4 % with ≥ 4 interior pixels at 30 m (18 % at 15 m), 43 % below the scale flag; and only 14 (kharif) / 20 (rabi) clear, well-covered granules per season.
- Nile Delta `T36RTV` (chosen over `T36RUV`: field cover 0.574 vs 0.553): median field 0.88 ha, 6.9 % with ≥ 4 interior pixels at 30 m (33.6 % at 15 m), 25 % below the scale flag; 22 (winter) / 32 (summer) clear, well-covered granules.
- Central Ukraine `T36UVU`: the best Tier 3 sky (39 winter / 34 summer clear, well-covered granules; worst year 22 / 19) but **field sizes are not measured**. The FTW file's row groups overlap heavily: the 20 km box is est. 313.6 MB, the 10 km box 254.1 MB (8 row groups, 524,288 rows), and even a 1 km box hits the same 8 row groups. A footer-only scan of 81 10 km boxes across the tile found none under 200 MB (245.6–324.5 MB).
- **User decision 2026-11-04 (pending the field-size check):** Tier 1 Kansas `T14SLH`, Tier 2 Beauce `T31UCP`, Tier 3 central Ukraine `T36UVU`; Nile Delta `T36RTV` kept only as a data-confidence-map showcase. The Ukraine check (median field ≥ ~2 ha and ≥ 50 % of fields qualifying at the 15 m buffer) needs a one-off read of ≥ ~246 MB.

**Interior-pixel rule (user decision 2026-11-04):** T1.4 now uses a 15 m inward buffer (pixel centre ≥ half a pixel inside the edge); the `share>=4px_buf15` column is the one that applies from now on.

**Southern France comparison (CMR only):** Lauragais `T31TCJ` near Toulouse has a somewhat better sky than the Beauce: 31 (winter) / 25 (summer) clear, well-covered granules per season vs 30 / 19, and much better worst years (14 / 13 vs 4 / 8). No boundary or label data were read for it.

**ECOSTRESS (input for T1.7):** `ECO_L3T_JET` v003 has a median of 0 overpasses per season in every region (2019–2024); v002 has 11.5–110. History must come from v002 unless v003 is backfilled.

**Caveats.** Cloud is tile-level `CLOUD_COVERAGE`, not field-level clear observations (those come from Fmask in T1.5). `SPATIAL_COVERAGE` is the share of the tile with data, not proof that a given field is covered. Season windows are tag A. Field statistics are one 20 km sample per region (Kansas also full tile).

**Field-size checks (2026-11-04).** Ukraine `T36UVU` 10 km box (one-off 243.6 MB read, FTW 2024): 141 fields, median 3.29 ha, 73.8 % qualify at 15 m → passes. Toulouse `T31TCJ` 20 km box (France RPG 2024): 11,270 fields, median 0.86 ha, 48.1 % qualify at 15 m → fails the same thresholds; Beauce passes them (3.01 ha, 61.2 %). Tier 2 choice pending the user.

**Arable-parcel check and final decision (2026-11-04).** On annual arable crop parcels only (HCAT3 rule, `docs/hcat_annual_arable.md`): Toulouse `T31TCJ` median 3.62 ha, 87.5 % at 15 m → passes; Beauce 7.55 ha, 87.0 %. Per the user's rule the **final regions are Tier 1 Kansas `T14SLH`, Tier 2 Toulouse `T31TCJ`, Tier 3 central Ukraine `T36UVU`**, with the Nile Delta `T36RTV` as a confidence-map showcase only. (The French rows in the table above use arable parcels only; the other regions use all polygons — FTW and CSB carry no HCAT classes.)
