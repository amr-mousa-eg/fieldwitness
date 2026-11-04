# Census — Punjab around Jagraon (India) (`pb_jagraon_t43req`, Tier 3)

Generated 2026-11-04T01:35:10+00:00 by `fieldwitness.cli census`. Tile **T43REQ** (EPSG:32643). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): kharif months 6–10; rabi months 11–4

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| kharif | 71 | 19 | 51 | 46 | 29 | 17 | 14 | 10 | 19.0 | 0.0 |
| rabi | 80 | 23 | 55 | 54 | 45 | 19 | 20 | 9 | 19.0 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T43REQ

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| kharif | 2016 | 37 | 18 | 19 | 28 | 17 | 10 | 25.0 | 96.0 |
| kharif | 2017 | 51 | 19 | 32 | 36 | 27 | 20 | 17.0 | 95.0 |
| kharif | 2018 | 70 | 17 | 53 | 40 | 28 | 13 | 45.0 | 15.0 |
| kharif | 2019 | 71 | 19 | 52 | 44 | 27 | 13 | 33.0 | 17.0 |
| kharif | 2020 | 76 | 20 | 56 | 47 | 37 | 15 | 24.0 | 17.0 |
| kharif | 2021 | 66 | 18 | 48 | 46 | 29 | 12 | 29.5 | 99.0 |
| kharif | 2022 | 89 | 37 | 52 | 58 | 46 | 22 | 16.0 | 49.0 |
| kharif | 2023 | 87 | 36 | 51 | 56 | 40 | 17 | 25.0 | 99.0 |
| kharif | 2024 | 86 | 36 | 50 | 51 | 36 | 14 | 42.0 | 34.5 |
| rabi | 2016 | 37 | 23 | 14 | 21 | 19 | 11 | 11.0 | 93.0 |
| rabi | 2017 | 51 | 23 | 28 | 32 | 22 | 9 | 23.0 | 93.0 |
| rabi | 2018 | 77 | 22 | 55 | 54 | 45 | 24 | 9.0 | 99.0 |
| rabi | 2019 | 80 | 21 | 59 | 57 | 46 | 20 | 12.5 | 74.5 |
| rabi | 2020 | 64 | 20 | 44 | 48 | 34 | 17 | 10.5 | 16.5 |
| rabi | 2021 | 81 | 20 | 61 | 51 | 43 | 20 | 13.0 | 18.0 |
| rabi | 2022 | 98 | 39 | 59 | 78 | 68 | 38 | 2.0 | 80.0 |
| rabi | 2023 | 108 | 45 | 63 | 74 | 62 | 32 | 12.5 | 99.0 |
| rabi | 2024 | 91 | 40 | 51 | 61 | 52 | 24 | 3.0 | 81.0 |


Monthly means 2016–2024 (T43REQ):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 9.8 | 3.4 |
| 2 | 12.8 | 7.3 |
| 3 | 14.0 | 8.9 |
| 4 | 13.7 | 9.7 |
| 5 | 14.1 | 10.6 |
| 6 | 13.4 | 8.1 |
| 7 | 13.1 | 2.2 |
| 8 | 13.6 | 2.0 |
| 9 | 14.3 | 7.2 |
| 10 | 15.9 | 12.3 |
| 11 | 14.2 | 8.2 |
| 12 | 14.9 | 7.8 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| kharif | 2018 | 18 | 0 |
| kharif | 2019 | 7 | 0 |
| kharif | 2020 | 16 | 0 |
| kharif | 2021 | 22 | 0 |
| kharif | 2022 | 27 | 0 |
| kharif | 2023 | 28 | 0 |
| kharif | 2024 | 10 | 0 |
| rabi | 2018 | 0 | 0 |
| rabi | 2019 | 3 | 0 |
| rabi | 2020 | 13 | 0 |
| rabi | 2021 | 25 | 0 |
| rabi | 2022 | 25 | 0 |
| rabi | 2023 | 46 | 0 |
| rabi | 2024 | 7 | 0 |


## Field sizes and interior pixels (Fields of the World global predictions (alpha))

### Sample `box20km`

```json
{
 "read": {
  "key": "ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=IN/IN_PB.parquet",
  "rows": 10396804,
  "row_groups": 159,
  "row_groups_hit": 8,
  "estimated_mb": 59.9,
  "cap_mb": 200.0,
  "crs": "WGS 84 (CRS84)"
 },
 "sample_box_lonlat": [
  75.3654,
  30.7002,
  75.5746,
  30.8798
 ],
 "sample_area_km2": 401.8,
 "fields": 38712,
 "area_ha_p10_p25_p50_p75_p90": [
  0.1,
  0.21,
  0.44,
  0.8,
  1.32
 ],
 "area_ha_mean": 0.61,
 "field_cover_fraction": 0.588,
 "share_scale_flag_lt_0p36ha": 0.433,
 "share_ge4_interior_px_buf30": 0.024,
 "share_ge4_interior_px_buf15": 0.183,
 "median_interior_px_buf30": 0.0
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (PLAN.md T1.4) or 15 m, on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

none (no crop labels; Tier 3 crops are inferred)
