# Census — Nile Delta (Egypt) (`eg_nile_delta`, Tier 3)

Generated 2026-11-04T01:41:13+00:00 by `fieldwitness.cli census`. Tile **T36RTV** (EPSG:32636). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): winter months 11–5; summer months 5–10

Tile choice (field cover fraction of FTW 2024 polygons in a 20 km box at each tile centre): {'T36RTV': 0.574, 'T36RUV': 0.553} → **T36RTV**.

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| winter | 104 | 26 | 77 | 72 | 46 | 22 | 22 | 9 | 12.5 | 0.0 |
| summer | 96 | 23 | 73 | 86 | 67 | 26 | 32 | 15 | 19.5 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T36RTV

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| winter | 2016 | 55 | 25 | 30 | 37 | 22 | 9 | 27.0 | 24.0 |
| winter | 2017 | 63 | 26 | 37 | 43 | 26 | 13 | 29.0 | 98.0 |
| winter | 2018 | 101 | 26 | 75 | 68 | 40 | 20 | 34.0 | 97.0 |
| winter | 2019 | 104 | 27 | 77 | 77 | 48 | 23 | 25.5 | 24.0 |
| winter | 2020 | 96 | 25 | 71 | 65 | 46 | 22 | 29.0 | 78.5 |
| winter | 2021 | 104 | 25 | 79 | 72 | 46 | 20 | 28.0 | 99.0 |
| winter | 2022 | 128 | 51 | 77 | 84 | 50 | 25 | 35.0 | 96.0 |
| winter | 2023 | 130 | 50 | 80 | 81 | 45 | 22 | 37.5 | 24.0 |
| winter | 2024 | 131 | 52 | 79 | 83 | 47 | 23 | 37.0 | 99.0 |
| summer | 2016 | 55 | 23 | 32 | 47 | 26 | 15 | 24.0 | 23.0 |
| summer | 2017 | 74 | 23 | 51 | 69 | 43 | 19 | 15.0 | 24.0 |
| summer | 2018 | 96 | 23 | 73 | 84 | 47 | 26 | 21.0 | 61.0 |
| summer | 2019 | 94 | 23 | 71 | 86 | 59 | 29 | 10.0 | 24.0 |
| summer | 2020 | 95 | 22 | 73 | 87 | 69 | 34 | 6.0 | 24.0 |
| summer | 2021 | 96 | 23 | 73 | 85 | 67 | 32 | 9.0 | 24.0 |
| summer | 2022 | 118 | 45 | 73 | 110 | 71 | 32 | 15.5 | 25.0 |
| summer | 2023 | 115 | 42 | 73 | 98 | 71 | 32 | 11.0 | 25.0 |
| summer | 2024 | 119 | 46 | 73 | 112 | 77 | 38 | 10.0 | 25.0 |


Monthly means 2016–2024 (T36RTV):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 14.9 | 5.6 |
| 2 | 13.8 | 3.9 |
| 3 | 14.3 | 5.3 |
| 4 | 14.2 | 8.2 |
| 5 | 15.7 | 9.2 |
| 6 | 15.1 | 11.6 |
| 7 | 16.9 | 12.3 |
| 8 | 16.1 | 10.3 |
| 9 | 15.7 | 8.9 |
| 10 | 16.3 | 6.6 |
| 11 | 15.3 | 5.8 |
| 12 | 16.0 | 4.6 |


## HLS-VI observations per season and year — T36RUV

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| winter | 2016 | 54 | 26 | 28 | 36 | 23 | 18 | 35.0 | 77.0 |
| winter | 2017 | 64 | 26 | 38 | 43 | 29 | 20 | 28.0 | 63.0 |
| winter | 2018 | 101 | 27 | 74 | 61 | 43 | 28 | 30.0 | 62.0 |
| winter | 2019 | 101 | 26 | 75 | 71 | 50 | 31 | 21.0 | 77.0 |
| winter | 2020 | 97 | 25 | 72 | 65 | 42 | 27 | 31.0 | 63.0 |
| winter | 2021 | 106 | 25 | 81 | 74 | 47 | 29 | 31.0 | 69.5 |
| winter | 2022 | 129 | 50 | 79 | 70 | 54 | 39 | 36.0 | 62.0 |
| winter | 2023 | 131 | 51 | 80 | 78 | 56 | 39 | 31.0 | 78.0 |
| winter | 2024 | 132 | 53 | 79 | 77 | 53 | 34 | 38.0 | 62.5 |
| summer | 2016 | 56 | 23 | 33 | 48 | 28 | 17 | 23.0 | 69.5 |
| summer | 2017 | 75 | 22 | 53 | 66 | 46 | 33 | 16.0 | 65.0 |
| summer | 2018 | 94 | 23 | 71 | 79 | 49 | 29 | 17.5 | 63.0 |
| summer | 2019 | 94 | 23 | 71 | 82 | 58 | 36 | 12.5 | 69.5 |
| summer | 2020 | 96 | 23 | 73 | 90 | 70 | 43 | 5.0 | 76.0 |
| summer | 2021 | 97 | 23 | 74 | 89 | 64 | 43 | 12.0 | 77.0 |
| summer | 2022 | 120 | 46 | 74 | 104 | 68 | 50 | 12.5 | 69.5 |
| summer | 2023 | 117 | 45 | 72 | 100 | 72 | 52 | 14.0 | 77.0 |
| summer | 2024 | 117 | 46 | 71 | 106 | 78 | 57 | 8.0 | 76.0 |


Monthly means 2016–2024 (T36RUV):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 14.8 | 6.2 |
| 2 | 13.6 | 4.3 |
| 3 | 14.4 | 5.4 |
| 4 | 14.4 | 7.7 |
| 5 | 15.8 | 9.9 |
| 6 | 15.1 | 11.6 |
| 7 | 16.8 | 12.2 |
| 8 | 16.4 | 10.1 |
| 9 | 15.7 | 8.6 |
| 10 | 16.4 | 6.9 |
| 11 | 15.7 | 6.0 |
| 12 | 16.1 | 6.1 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| winter | 2018 | 0 | 0 |
| winter | 2019 | 0 | 0 |
| winter | 2020 | 7 | 0 |
| winter | 2021 | 11 | 0 |
| winter | 2022 | 17 | 0 |
| winter | 2023 | 53 | 0 |
| winter | 2024 | 14 | 0 |
| summer | 2018 | 24 | 0 |
| summer | 2019 | 18 | 0 |
| summer | 2020 | 16 | 0 |
| summer | 2021 | 21 | 0 |
| summer | 2022 | 36 | 0 |
| summer | 2023 | 46 | 0 |
| summer | 2024 | 6 | 0 |


## Field sizes and interior pixels (Fields of the World global predictions (alpha))

### Sample `box20km_tile_centre`

```json
{
 "read": {
  "key": "ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=EG/Egypt.parquet",
  "rows": 9207446,
  "row_groups": 141,
  "row_groups_hit": 10,
  "estimated_mb": 151.1,
  "cap_mb": 200.0,
  "crs": "WGS 84 (CRS84)"
 },
 "sample_box_lonlat": [
  30.3248,
  31.0247,
  30.5346,
  31.2044
 ],
 "sample_area_km2": 417.5,
 "fields": 17027,
 "area_ha_p10_p25_p50_p75_p90": [
  0.15,
  0.36,
  0.88,
  1.88,
  3.28
 ],
 "area_ha_mean": 1.41,
 "field_cover_fraction": 0.574,
 "share_scale_flag_lt_0p36ha": 0.253,
 "share_ge4_interior_px_buf30": 0.069,
 "share_ge4_interior_px_buf15": 0.336,
 "median_interior_px_buf30": 0.0
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (PLAN.md T1.4) or 15 m, on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

none (no crop labels; Tier 3 crops are inferred)
