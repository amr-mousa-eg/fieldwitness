# Census — Beauce (France) (`fr_beauce_t31ucp`, Tier 2)

Generated 2026-11-04T02:33:22+00:00 by `fieldwitness.cli census`. Tile **T31UCP** (EPSG:32631). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): winter months 9–7; summer months 4–10

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| winter | 145 | 50 | 98 | 48 | 34 | 7 | 30 | 4 | 109.5 | 0.0 |
| summer | 107 | 36 | 68 | 34 | 21 | 10 | 19 | 8 | 106.5 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T31UCP

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| winter | 2016 | 80 | 54 | 26 | 18 | 7 | 4 | 86.5 | 72.0 |
| winter | 2017 | 96 | 45 | 51 | 36 | 23 | 16 | 73.0 | 73.0 |
| winter | 2018 | 139 | 40 | 99 | 41 | 26 | 23 | 79.0 | 73.0 |
| winter | 2019 | 150 | 50 | 100 | 52 | 34 | 30 | 74.0 | 73.0 |
| winter | 2020 | 143 | 48 | 95 | 60 | 42 | 37 | 63.0 | 73.0 |
| winter | 2021 | 145 | 47 | 98 | 48 | 35 | 31 | 76.0 | 73.0 |
| winter | 2022 | 187 | 78 | 109 | 80 | 51 | 46 | 61.0 | 73.0 |
| winter | 2023 | 193 | 93 | 100 | 65 | 46 | 37 | 76.0 | 73.0 |
| winter | 2024 | 180 | 89 | 91 | 28 | 15 | 13 | 85.0 | 73.0 |
| summer | 2016 | 64 | 37 | 27 | 20 | 10 | 9 | 80.0 | 72.0 |
| summer | 2017 | 84 | 34 | 50 | 25 | 14 | 8 | 73.0 | 73.0 |
| summer | 2018 | 112 | 33 | 79 | 49 | 34 | 30 | 61.5 | 73.0 |
| summer | 2019 | 103 | 35 | 68 | 34 | 21 | 19 | 75.0 | 73.0 |
| summer | 2020 | 103 | 34 | 69 | 43 | 35 | 30 | 62.0 | 73.0 |
| summer | 2021 | 107 | 36 | 71 | 30 | 18 | 16 | 80.0 | 73.0 |
| summer | 2022 | 142 | 70 | 72 | 67 | 48 | 39 | 51.5 | 73.0 |
| summer | 2023 | 133 | 66 | 67 | 47 | 33 | 28 | 75.0 | 73.0 |
| summer | 2024 | 122 | 57 | 65 | 27 | 15 | 15 | 77.5 | 73.0 |


Monthly means 2016–2024 (T31UCP):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 10.6 | 1.2 |
| 2 | 10.4 | 2.8 |
| 3 | 12.3 | 2.7 |
| 4 | 13.8 | 3.4 |
| 5 | 14.8 | 4.1 |
| 6 | 15.1 | 3.8 |
| 7 | 16.9 | 3.8 |
| 8 | 16.3 | 3.6 |
| 9 | 15.6 | 4.2 |
| 10 | 15.3 | 2.4 |
| 11 | 13.3 | 1.7 |
| 12 | 11.2 | 1.4 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| winter | 2018 | 1 | 0 |
| winter | 2019 | 35 | 0 |
| winter | 2020 | 88 | 0 |
| winter | 2021 | 131 | 0 |
| winter | 2022 | 144 | 0 |
| winter | 2023 | 239 | 0 |
| winter | 2024 | 58 | 0 |
| summer | 2018 | 43 | 0 |
| summer | 2019 | 35 | 0 |
| summer | 2020 | 99 | 0 |
| summer | 2021 | 114 | 0 |
| summer | 2022 | 129 | 0 |
| summer | 2023 | 207 | 0 |
| summer | 2024 | 30 | 0 |


## Field sizes and interior pixels (French RPG (IGN) / EuroCrops V2)

### Sample `box20km`

```json
{
 "read": {
  "key": "ftw/harmonized-field-data/fr/year=2024/fr-2024.parquet",
  "rows": 9671682,
  "row_groups": 387,
  "row_groups_hit": 2,
  "estimated_mb": 12.6,
  "cap_mb": 200.0,
  "crs": "RGF93 v1 / Lambert-93",
  "columns": "all"
 },
 "sample_box_lonlat": [
  1.4651,
  48.1602,
  1.7349,
  48.3398
 ],
 "sample_area_km2": 414.7,
 "fields": 3656,
 "area_ha_p10_p25_p50_p75_p90": [
  0.81,
  3.13,
  7.58,
  12.2,
  19.09
 ],
 "area_ha_mean": 9.12,
 "field_cover_fraction": 0.804,
 "share_scale_flag_lt_0p36ha": 0.05,
 "share_ge4_interior_px_buf30": 0.801,
 "share_ge4_interior_px_buf15": 0.872,
 "median_interior_px_buf30": 44.0,
 "field_definition": "annual arable (HCAT3, fieldwitness.data.hcat)",
 "arable_filter": {
  "parcels_all": 5977,
  "parcels_kept": 3656,
  "excluded_by_hcat_group": {
   "3301": 1759,
   "3302": 83,
   "3303": 9,
   "3304": 4,
   "3399": 319
  },
  "excluded_missing_code": 147
 }
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (old rule) or 15 m (PLAN.md T1.4 since 2026-11-04), on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
