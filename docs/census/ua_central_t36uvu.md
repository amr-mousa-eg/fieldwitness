# Census — Central Ukraine (Kirovohrad oblast area) (`ua_central_t36uvu`, Tier 3)

Generated 2026-11-04T01:55:07+00:00 by `fieldwitness.cli census`. Tile **T36UVU** (EPSG:32636). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): winter months 9–7; summer months 4–10

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| winter | 136 | 54 | 89 | 69 | 45 | 29 | 39 | 22 | 15.0 | 0.0 |
| summer | 113 | 39 | 73 | 62 | 41 | 24 | 34 | 19 | 11.5 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T36UVU

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| winter | 2016 | 80 | 48 | 32 | 36 | 30 | 22 | 64.0 | 60.5 |
| winter | 2017 | 107 | 54 | 53 | 63 | 39 | 29 | 41.0 | 71.0 |
| winter | 2018 | 133 | 47 | 86 | 71 | 50 | 39 | 44.0 | 72.0 |
| winter | 2019 | 136 | 47 | 89 | 69 | 45 | 39 | 48.0 | 73.5 |
| winter | 2020 | 144 | 55 | 89 | 76 | 48 | 42 | 44.5 | 73.5 |
| winter | 2021 | 132 | 43 | 89 | 57 | 40 | 37 | 64.0 | 74.0 |
| winter | 2022 | 185 | 84 | 101 | 95 | 63 | 51 | 48.0 | 63.0 |
| winter | 2023 | 179 | 88 | 91 | 65 | 29 | 22 | 74.0 | 71.0 |
| winter | 2024 | 201 | 103 | 98 | 107 | 64 | 51 | 47.0 | 71.0 |
| summer | 2016 | 72 | 40 | 32 | 34 | 24 | 19 | 56.0 | 72.0 |
| summer | 2017 | 85 | 37 | 48 | 58 | 41 | 34 | 25.0 | 71.0 |
| summer | 2018 | 117 | 37 | 80 | 75 | 53 | 45 | 26.0 | 74.0 |
| summer | 2019 | 105 | 37 | 68 | 64 | 38 | 34 | 39.0 | 74.0 |
| summer | 2020 | 112 | 39 | 73 | 61 | 41 | 38 | 42.5 | 75.0 |
| summer | 2021 | 113 | 35 | 78 | 54 | 31 | 27 | 53.0 | 75.0 |
| summer | 2022 | 143 | 69 | 74 | 62 | 40 | 33 | 64.0 | 71.0 |
| summer | 2023 | 141 | 68 | 73 | 88 | 45 | 36 | 40.0 | 74.0 |
| summer | 2024 | 157 | 78 | 79 | 88 | 54 | 45 | 44.0 | 73.0 |


Monthly means 2016–2024 (T36UVU):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 9.7 | 2.6 |
| 2 | 9.7 | 3.4 |
| 3 | 13.4 | 4.1 |
| 4 | 13.7 | 4.7 |
| 5 | 17.1 | 4.4 |
| 6 | 16.4 | 5.1 |
| 7 | 17.9 | 6.1 |
| 8 | 18.1 | 7.9 |
| 9 | 17.1 | 7.6 |
| 10 | 15.8 | 5.0 |
| 11 | 10.6 | 2.7 |
| 12 | 7.8 | 1.0 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| winter | 2018 | 2 | 0 |
| winter | 2019 | 19 | 0 |
| winter | 2020 | 10 | 0 |
| winter | 2021 | 11 | 0 |
| winter | 2022 | 24 | 0 |
| winter | 2023 | 42 | 0 |
| winter | 2024 | 10 | 0 |
| summer | 2018 | 24 | 0 |
| summer | 2019 | 3 | 0 |
| summer | 2020 | 11 | 0 |
| summer | 2021 | 13 | 0 |
| summer | 2022 | 32 | 0 |
| summer | 2023 | 12 | 0 |
| summer | 2024 | 1 | 0 |


## Field sizes and interior pixels (Fields of the World global predictions (alpha))

### Sample `box10km`

```json
{
 "read": {
  "key": "ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=UA/Ukraine.parquet",
  "rows": 4116875,
  "row_groups": 63,
  "row_groups_hit": 8,
  "estimated_mb": 243.6,
  "cap_mb": 260,
  "crs": "WGS 84 (CRS84)",
  "columns": [
   "geometry",
   "determination:datetime"
  ]
 },
 "sample_box_lonlat": [
  32.3225,
  48.2051,
  32.4575,
  48.2949
 ],
 "sample_area_km2": 101.6,
 "fields": 141,
 "area_ha_p10_p25_p50_p75_p90": [
  0.31,
  0.99,
  3.29,
  88.9,
  148.34
 ],
 "area_ha_mean": 61.13,
 "field_cover_fraction": 0.848,
 "share_scale_flag_lt_0p36ha": 0.106,
 "share_ge4_interior_px_buf30": 0.553,
 "share_ge4_interior_px_buf15": 0.738,
 "median_interior_px_buf30": 8.0
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (old rule) or 15 m (PLAN.md T1.4 since 2026-11-04), on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

none (no crop labels; Tier 3 crops are inferred)
