# Census — Lauragais, SE of Toulouse (France) (`fr_toulouse_t31tcj`, Tier 2)

Generated 2026-11-04T02:02:39+00:00 by `fieldwitness.cli census`. Tile **T31TCJ** (EPSG:32631). Numbers are counts from CMR metadata and bbox reads; no imagery downloaded.

Season windows (tag **A**, team assumption, editable in `config/regions.yaml`; named by harvest year): winter months 9–7; summer months 4–10

## Summary (medians over harvest years)

| season | granules | L30 | S30 | cloud_le50 | cloud_le20 | min_cloud_le20 | cloud_le20_spatial_ge50 | min_cloud_le20_spatial_ge50 | eco_v002 | eco_v003 |
|---|---|---|---|---|---|---|---|---|---|---|
| winter | 190 | 40 | 145 | 84 | 58 | 22 | 31 | 14 | 150.0 | 0.0 |
| summer | 130 | 27 | 100 | 66 | 46 | 29 | 25 | 13 | 141.0 | 0.0 |

`cloud_le20` / `cloud_le50`: HLS-VI granules whose tile-level `CLOUD_COVERAGE` ≤ 20 % / ≤ 50 %; `_spatial_ge50` also requires `SPATIAL_COVERAGE` ≥ 50 %. `min_*`: worst year. `eco_v00x`: ECO_L3T_JET overpasses at the region point (2019–2024 medians; v003 is a partial archive).

## HLS-VI observations per season and year — T31TCJ

| season | year | granules | L30 | S30 | cloud_le50 | cloud_le20 | cloud_le20_spatial_ge50 | median_cloud_pct | median_spatial_pct |
|---|---|---|---|---|---|---|---|---|---|
| winter | 2016 | 92 | 40 | 52 | 31 | 22 | 14 | 78.0 | 79.0 |
| winter | 2017 | 121 | 42 | 79 | 56 | 39 | 18 | 62.0 | 77.0 |
| winter | 2018 | 193 | 38 | 155 | 71 | 49 | 23 | 76.0 | 16.0 |
| winter | 2019 | 190 | 39 | 151 | 98 | 72 | 33 | 48.5 | 17.0 |
| winter | 2020 | 181 | 37 | 144 | 84 | 58 | 31 | 58.0 | 17.0 |
| winter | 2021 | 190 | 39 | 151 | 83 | 54 | 19 | 60.0 | 17.0 |
| winter | 2022 | 214 | 69 | 145 | 99 | 77 | 39 | 56.0 | 80.0 |
| winter | 2023 | 232 | 79 | 153 | 96 | 74 | 31 | 69.5 | 77.0 |
| winter | 2024 | 217 | 79 | 138 | 101 | 69 | 31 | 66.0 | 77.0 |
| summer | 2016 | 80 | 26 | 54 | 35 | 29 | 14 | 68.5 | 78.5 |
| summer | 2017 | 97 | 27 | 70 | 46 | 38 | 13 | 55.0 | 17.0 |
| summer | 2018 | 134 | 25 | 109 | 75 | 57 | 31 | 43.0 | 16.0 |
| summer | 2019 | 120 | 22 | 98 | 62 | 46 | 25 | 47.0 | 17.0 |
| summer | 2020 | 127 | 27 | 100 | 66 | 46 | 23 | 49.0 | 17.0 |
| summer | 2021 | 130 | 27 | 103 | 65 | 44 | 16 | 50.5 | 17.0 |
| summer | 2022 | 152 | 49 | 103 | 84 | 70 | 30 | 31.0 | 78.0 |
| summer | 2023 | 153 | 52 | 101 | 81 | 63 | 27 | 43.0 | 75.0 |
| summer | 2024 | 147 | 51 | 96 | 75 | 57 | 27 | 47.0 | 78.0 |


Monthly means 2016–2024 (T31TCJ):

| month | mean_granules | mean_cloud_le20 |
|---|---|---|
| 1 | 14.3 | 2.1 |
| 2 | 14.2 | 5.3 |
| 3 | 17.9 | 5.2 |
| 4 | 15.0 | 5.0 |
| 5 | 17.6 | 5.4 |
| 6 | 16.7 | 4.9 |
| 7 | 20.3 | 9.8 |
| 8 | 20.1 | 9.9 |
| 9 | 18.3 | 8.3 |
| 10 | 18.7 | 6.7 |
| 11 | 17.4 | 3.6 |
| 12 | 17.4 | 2.3 |


## ECOSTRESS ECO_L3T_JET overpasses at the region point

| season | year | v002 | v003 |
|---|---|---|---|
| winter | 2018 | 3 | 0 |
| winter | 2019 | 53 | 0 |
| winter | 2020 | 109 | 0 |
| winter | 2021 | 191 | 0 |
| winter | 2022 | 200 | 0 |
| winter | 2023 | 382 | 0 |
| winter | 2024 | 83 | 0 |
| summer | 2018 | 41 | 0 |
| summer | 2019 | 40 | 0 |
| summer | 2020 | 114 | 0 |
| summer | 2021 | 168 | 0 |
| summer | 2022 | 183 | 0 |
| summer | 2023 | 298 | 0 |
| summer | 2024 | 42 | 0 |


## Field sizes and interior pixels (French RPG (IGN) / EuroCrops V2)

### Sample `box20km`

```json
{
 "read": {
  "key": "ftw/harmonized-field-data/fr/year=2024/fr-2024.parquet",
  "rows": 9671682,
  "row_groups": 387,
  "row_groups_hit": 4,
  "estimated_mb": 30.1,
  "cap_mb": 200.0,
  "crs": "RGF93 v1 / Lambert-93",
  "columns": "all"
 },
 "sample_box_lonlat": [
  1.6263,
  43.3602,
  1.8737,
  43.5398
 ],
 "sample_area_km2": 411.6,
 "fields": 5406,
 "area_ha_p10_p25_p50_p75_p90": [
  0.82,
  1.71,
  3.62,
  7.08,
  11.96
 ],
 "area_ha_mean": 5.31,
 "field_cover_fraction": 0.698,
 "share_scale_flag_lt_0p36ha": 0.026,
 "share_ge4_interior_px_buf30": 0.721,
 "share_ge4_interior_px_buf15": 0.875,
 "median_interior_px_buf30": 14.0,
 "field_definition": "annual arable (HCAT3, fieldwitness.data.hcat)",
 "arable_filter": {
  "parcels_all": 11270,
  "parcels_kept": 5406,
  "excluded_by_hcat_group": {
   "3301": 3093,
   "3302": 532,
   "3303": 42,
   "3304": 5,
   "3305": 3,
   "3306": 3,
   "3399": 2164
  },
  "excluded_missing_code": 22
 }
}
```

Interior pixels: HLS 30 m pixel centres strictly inside the field after an inward buffer of 30 m (old rule) or 15 m (PLAN.md T1.4 since 2026-11-04), on the tile grid (ULX/ULY from CMR). Scale flag: field < 0.36 ha (pixel area > field area / 4, CLAUDE.md rule 5). Fields are counted once, by centroid inside the sample box.

## Label years

[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
