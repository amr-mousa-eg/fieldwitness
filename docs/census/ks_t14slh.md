# Census — Kansas High Plains (SW Kansas) (`ks_t14slh`, Tier 1)

Generated 2026-11-04T01:32:34+00:00 by `fieldwitness.cli census`. Tile **T14SLH** (EPSG:32614). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): summer months 4–10; winter_wheat months 9–7

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| summer | 98 | 26 | 72 | 69 | 51 | 17 | 46 | 15 | 73.0 | 0.0 |
| winter_wheat | 141 | 39 | 102 | 98 | 70 | 22 | 63 | 19 | 88.5 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T14SLH

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| summer | 2016 | 36 | 24 | 12 | 23 | 17 | 15 | 23.5 | 97.0 |
| summer | 2017 | 47 | 23 | 24 | 29 | 22 | 21 | 23.0 | 55.0 |
| summer | 2018 | 98 | 26 | 72 | 69 | 51 | 46 | 17.5 | 55.0 |
| summer | 2019 | 97 | 25 | 72 | 67 | 48 | 44 | 22.0 | 57.0 |
| summer | 2020 | 94 | 25 | 69 | 76 | 53 | 51 | 11.0 | 55.0 |
| summer | 2021 | 102 | 27 | 75 | 66 | 48 | 43 | 25.5 | 77.0 |
| summer | 2022 | 120 | 47 | 73 | 97 | 81 | 66 | 3.5 | 55.5 |
| summer | 2023 | 121 | 47 | 74 | 87 | 70 | 60 | 7.0 | 56.0 |
| summer | 2024 | 128 | 50 | 78 | 94 | 71 | 63 | 9.5 | 96.0 |
| winter_wheat | 2016 | 52 | 37 | 15 | 30 | 22 | 19 | 36.0 | 63.5 |
| winter_wheat | 2017 | 68 | 37 | 31 | 44 | 38 | 31 | 13.0 | 55.0 |
| winter_wheat | 2018 | 126 | 38 | 88 | 86 | 65 | 56 | 18.0 | 56.0 |
| winter_wheat | 2019 | 141 | 39 | 102 | 87 | 63 | 56 | 30.0 | 55.0 |
| winter_wheat | 2020 | 137 | 40 | 97 | 102 | 78 | 71 | 11.0 | 69.0 |
| winter_wheat | 2021 | 147 | 36 | 111 | 98 | 70 | 63 | 23.0 | 57.0 |
| winter_wheat | 2022 | 183 | 69 | 114 | 132 | 102 | 88 | 13.0 | 62.0 |
| winter_wheat | 2023 | 183 | 73 | 110 | 121 | 93 | 80 | 18.0 | 71.0 |
| winter_wheat | 2024 | 184 | 71 | 113 | 143 | 111 | 92 | 8.0 | 56.0 |


Monthly means 2016–2024 (T14SLH):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 11.4 | 6.2 |
| 2 | 11.4 | 5.6 |
| 3 | 12.8 | 7.2 |
| 4 | 11.9 | 6.0 |
| 5 | 12.4 | 5.1 |
| 6 | 12.9 | 6.7 |
| 7 | 15.0 | 7.7 |
| 8 | 14.4 | 8.6 |
| 9 | 13.3 | 8.8 |
| 10 | 13.7 | 8.4 |
| 11 | 13.3 | 7.6 |
| 12 | 13.3 | 6.1 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| summer | 2018 | 20 | 0 |
| summer | 2019 | 31 | 0 |
| summer | 2020 | 80 | 0 |
| summer | 2021 | 82 | 0 |
| summer | 2022 | 66 | 0 |
| summer | 2023 | 157 | 0 |
| summer | 2024 | 21 | 0 |
| winter_wheat | 2018 | 0 | 0 |
| winter_wheat | 2019 | 24 | 0 |
| winter_wheat | 2020 | 90 | 0 |
| winter_wheat | 2021 | 102 | 0 |
| winter_wheat | 2022 | 87 | 0 |
| winter_wheat | 2023 | 163 | 0 |
| winter_wheat | 2024 | 62 | 0 |


## Field sizes and interior pixels (CSB 2017-2024 edition (USDA NASS))

### Sample `box20km`

```json
{
 "read": {
  "key": "ftw/harmonized-field-data/us_usda_cropland/year=2024/us_usda_cropland-2024.parquet",
  "rows": 7541673,
  "row_groups": 302,
  "row_groups_hit": 1,
  "estimated_mb": 11.2,
  "cap_mb": 200.0,
  "crs": "Albers_Conic_Equal_Area"
 },
 "sample_box_lonlat": [
  -101.014,
  37.9102,
  -100.786,
  38.0898
 ],
 "sample_area_km2": 415.6,
 "fields": 1134,
 "area_ha_p10_p25_p50_p75_p90": [
  1.57,
  2.42,
  5.98,
  30.18,
  55.92
 ],
 "area_ha_mean": 21.17,
 "field_cover_fraction": 0.578,
 "share_scale_flag_lt_0p36ha": 0.0,
 "share_ge4_interior_px_buf30": 0.842,
 "share_ge4_interior_px_buf15": 0.986,
 "median_interior_px_buf30": 27.0
}
```

### Sample `full_tile`

```json
{
 "read": {
  "key": "ftw/harmonized-field-data/us_usda_cropland/year=2024/us_usda_cropland-2024.parquet",
  "rows": 7541673,
  "row_groups": 302,
  "row_groups_hit": 4,
  "estimated_mb": 43.9,
  "cap_mb": 200.0,
  "crs": "Albers_Conic_Equal_Area"
 },
 "sample_box_lonlat": [
  -101.3039,
  37.8375,
  -100.0253,
  38.8444
 ],
 "sample_area_km2": 12939.6,
 "fields": 18739,
 "area_ha_p10_p25_p50_p75_p90": [
  1.89,
  4.09,
  24.82,
  60.11,
  107.64
 ],
 "area_ha_mean": 43.39,
 "field_cover_fraction": 0.628,
 "share_scale_flag_lt_0p36ha": 0.0,
 "share_ge4_interior_px_buf30": 0.886,
 "share_ge4_interior_px_buf15": 0.981,
 "median_interior_px_buf30": 190.0
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (PLAN.md T1.4) or 15 m, on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

[2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
