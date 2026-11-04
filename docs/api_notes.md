# API notes

Real request and response shapes for every external API, recorded from one small test call (CLAUDE.md rule 2). One section per API: date checked, endpoint, request, response shape, gotchas.

## NASA CMR — collection search (no login)

Checked 2026-11-04.

- Endpoint: `GET https://cmr.earthdata.nasa.gov/search/collections.json?short_name=<SN>&page_size=<n>`
- Optional wildcard: `short_name=ECO_L3T_JET*&options[short_name][pattern]=true` (needs `curl -g`).
- Response headers: `Content-Type: application/json;charset=utf-8`; `cmr-hits: <total matches>`.
- Body: `{"feed": {"updated", "id", "title", "entry": [...]}}`. Each `entry` has (among others):
  `id` (concept ID, str), `short_name`, `version_id`, `title`, `dataset_id`, `entry_id` (`<SN>_<version>`),
  `data_center`, `archive_center`, `time_start` (ISO str), `time_end` (absent/None if ongoing),
  `cloud_hosted` (bool), `online_access_flag`, `processing_level_id`, `boxes` (list of bbox strings),
  `links` (list), `platforms` (list), `summary`, `updated`, plus flags `has_variables`,
  `has_spatial_subsetting`, `has_temporal_subsetting`, `has_formats`, `has_transforms`, `has_combine`.
- Gotcha: the body contains non-ASCII bytes; on Windows open saved responses with `encoding="utf-8"`.

### Verified collections

| Short name | `version_id` | Concept ID | Provider | `time_start` | Title |
|---|---|---|---|---|---|
| `HLSL30_VI` | `2.0` | `C3246892554-LPCLOUD` | LPCLOUD (cloud-hosted) | 2013-04-11 | HLS Operational Land Imager Vegetation Indices Daily Global 30 m V2.0 |
| `HLSS30_VI` | `2.0` | `C3246894861-LPCLOUD` | LPCLOUD (cloud-hosted) | 2015-11-28 | HLS Sentinel-2 Multi-spectral Instrument Vegetation Indices Daily Global 30 m V2.0 |
| `ECO_L3T_JET` | `003` | `C4057232489-LPCLOUD` | LPCLOUD (cloud-hosted) | 2018-07-09 | ECOSTRESS Tiled Evapotranspiration PT-JPL Instantaneous and Daytime L3 Global 70 m v003 |
| `ECO_L3T_JET` | `002` | `C2076106409-LPCLOUD` | LPCLOUD (cloud-hosted) | 2018-07-10 | ECOSTRESS Tiled Evapotranspiration Instantaneous and Daytime L3 Global 70 m V002 |

Notes:
- PLAN.md's "HLSL30_VI.002 / HLSS30_VI.002" is the LP DAAC product name; the CMR `version_id` to search with is `"2.0"`.
- Both ECOSTRESS JET versions are live; PLAN.md T1.7 uses `003`. Search must pin `version="003"`, otherwise both come back.
- All collections have no `time_end` (ongoing).

## earthaccess 0.19.0 — login (read from installed source)

Checked 2026-11-04 in `.venv/Lib/site-packages/earthaccess/{api,auth,system}.py`.

- `earthaccess.login(strategy="all")` tries `"environment"` → `"netrc"` → `"interactive"`.
  - `environment`: `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD`, or `EARTHDATA_TOKEN`.
  - `netrc`: file from `auth.netrc_path()` = `$NETRC` if set, else **`~/_netrc` on Windows** and `~/.netrc` elsewhere.
- Machine entry it looks up: `urs.earthdata.nasa.gov` (production; `uat.urs.earthdata.nasa.gov` for UAT).
- Gotcha: on Windows a file named `~/.netrc` is **not** found unless `NETRC` points to it.
- Granule search: `earthaccess.search_data(count=-1, **kwargs)`; kwargs include `short_name`, `version`,
  `provider`/`daac`, `cloud_hosted`, `granule_name` (wildcards), `temporal=(from, to)`,
  `bounding_box=(ll_lon, ll_lat, ur_lon, ur_lat)`, `point=(lon, lat)`, `polygon`, `cloud_cover=(lo, hi)`.
- `granule_name` maps to CMR `readable_granule_name` with `options[readable_granule_name][pattern]=true`.
- Counting without downloading: `earthaccess.DataGranules(earthaccess.__auth__).parameters(**kw).hits()`
  sends `page_size=0` and returns the `CMR-Hits` response header as an int.

## HLS-VI granule search — test results (T0.2)

Checked 2026-11-04 with `scripts/check_earthdata.py` (login via `_netrc`: `authenticated: True`).
Search box (access test only): `bounding_box=(-100.95, 37.95, -100.85, 38.05)`, SW Kansas → MGRS tile **T14SLH**.

- One tile, one date (`granule_name="HLS-VI.*.T14SLH.2023185*"`, 2023-07-04): `HLSS30_VI` → 1 granule
  `HLS-VI.S30.T14SLH.2023185T172901.v2.0` (begin 2023-07-04T17:43:21.617Z); `HLSL30_VI` → 0 (no Landsat pass that day).
- Window 2023-06-01..2023-08-31, same box: `HLSL30_VI` 17 granules (all T14SLH, e.g. `HLS-VI.L30.T14SLH.2023156T171836.v2.0`), `HLSS30_VI` 16 granules.

### Granule naming

- VI: `HLS-VI.<L30|S30>.T<tile>.<YYYYDOY>T<hhmmss>.v2.0` (DOY = day of year).
- Surface reflectance: `HLS.<L30|S30>.T<tile>.<YYYYDOY>T<hhmmss>.v2.0` (same timestamp as the VI granule).

### Granule object shape (`earthaccess.DataGranule`, a dict subclass)

- Top keys: `meta`, `size`, `umm`.
- `meta`: `collection-concept-id`, `concept-id`, `concept-type`, `format`, `native-id`, `provider-id`, `revision-date`, `revision-id`.
- `umm`: `AdditionalAttributes`, `CollectionReference`, `DataGranule`, `GranuleUR`, `MetadataSpecification`,
  `Platforms`, `ProviderDates`, `RelatedUrls`, `SpatialExtent`, `TemporalExtent`.
- Used fields: `umm["GranuleUR"]`; `umm["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]`.
- `g.data_links()` → 10 HTTPS GeoTIFF links: EVI, MSAVI, NBR, NBR2, NDMI, NDVI, NDWI, SAVI, TVI and Fmask.
  VI files: `https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/HLSS30_VI.020/<granule>/<granule>.<VI>.tif`.

### Fmask lives in the surface-reflectance products

The Fmask link of a VI granule points to the **SR** product, not the VI product (seen for both sensors):

- S30: `.../lp-prod-protected/HLSS30.020/HLS.S30.T14SLH.2023185T172901.v2.0/HLS.S30.T14SLH.2023185T172901.v2.0.Fmask.tif`
- L30: `.../lp-prod-protected/HLSL30.020/HLS.L30.T14SLH.2023156T171836.v2.0/HLS.L30.T14SLH.2023156T171836.v2.0.Fmask.tif`

So a cloud-masked VI series reads files from two products: `HLS{L,S}30_VI` (VIs) and `HLS{L,S}30` (Fmask).
SR collections verified in CMR: `HLSL30` v`2.0` (`C2021957657-LPCLOUD`, from 2013-04-11), `HLSS30` v`2.0` (`C2021957295-LPCLOUD`, from 2015-11-28).

### Archive depth, tile T14SLH (granule counts per calendar year, CMR hits only)

| Year | HLSL30_VI | HLSS30_VI | HLSL30 | HLSS30 |
|---|---|---|---|---|
| 2016 | 41 | 24 | 41 | 24 |
| 2017 | 39 | 44 | 39 | 44 |
| 2018 | 45 | 120 | 45 | 120 |
| 2019 | 43 | 113 | 43 | 117 |
| 2020 | 40 | 113 | 40 | 113 |
| 2021 | 53 | 122 | 53 | 122 |
| 2022 | 81 | 124 | 81 | 124 |
| 2023 | 77 | 122 | 79 | 123 |
| 2024 | 81 | 122 | 81 | 122 |

- No empty year. VI counts equal SR counts except 2019 S30 (113 vs 117), 2023 L30 (77 vs 79), 2023 S30 (122 vs 123).
- 2016–2017 are thinner (65 and 83 granules in total vs ~160–205 later), driven by S30 (24 and 44). L30 roughly doubles from 2022.
- Counts are all granules, before any cloud masking; clear observations per season come from the census (T0.5).

## AppEEARS API (T0.3)

Checked 2026-11-04 against the official docs at `https://appeears.earthdatacloud.nasa.gov/api/` and live calls.
Script: `scripts/check_appeears.py`.

### Endpoints used

| Call | Auth | Notes |
|---|---|---|
| `GET /product` | none | list of 193 products; each entry has `Available`, `DOI`, `Deleted`, `Description`, `DocLink`, `Info`, `Platform`, `Product`, `ProductAndVersion`, `RasterType`, `Resolution`, `Source`, `TemporalExtentStart`, `TemporalExtentEnd`, `TemporalGranularity`, `Version` |
| `GET /product/{ProductAndVersion}` | none | dict keyed by layer name; each layer has `AddOffset`, `Available`, `DataType`, `Description`, `Dimensions`, `FillValue`, `FillValueAll`, `Group`, `Info`, `IsQA`, `Layer`, `OrigDataType`, `OrigValidMax`, `OrigValidMin`, `QualityLayers`, `QualityProductAndVersion`, `ScaleFactor`, `Units`, `ValidMax`, `ValidMin`, `XSize`, `YSize` |
| `POST /login` | HTTP Basic (Earthdata user/password) | returns `{"token_type": "Bearer", "token": ..., "expiration": ...}`; token lasts ~48 h; 403 means expired |
| `POST /logout` | Bearer | 204 on success; disposes the token |
| `POST /task` | Bearer | JSON task body (below); 202 + `{"task_id", "status": "pending"}` and `Location: /api/status/{id}` |
| `GET /task/{task_id}` | Bearer | task object; `status` ∈ `pending`, `processing`, `done`, `error`; `summary` present when no output files |
| `GET /status/{task_id}` | Bearer | progress steps; returns 303 to `/api/task/{id}` once done |
| `GET /bundle/{task_id}` | Bearer | `{"files": [{"sha256", "file_id", "file_name", "file_size", "file_type"}, ...]}` |
| `GET /bundle/{task_id}/{file_id}` | Bearer | file download (follows a redirect) |

### Area task body

```json
{"task_type": "area", "task_name": "...",
 "params": {"dates": [{"startDate": "MM-DD-YYYY", "endDate": "MM-DD-YYYY"}],
            "layers": [{"product": "<ProductAndVersion>", "layer": "<layer>"}, ...],
            "geo": {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[lon, lat], ...]]}, "properties": {}}]},
            "output": {"format": {"type": "geotiff" | "netcdf4"}, "projection": "native"}}}
```

- Dates are `MM-DD-YYYY` (or `MM-DD` with `"recurring": true` and `yearRange`).
- `layers` may mix products in one task (the docs' own example mixes `MOD16A2GF.061` and `MYD17A3HGF.061`).
- Coordinates must be geographic (lon/lat).

### HLS products in AppEEARS (temporal extent as reported by `GET /product`)

| ProductAndVersion | Description | TemporalExtentStart | TemporalExtentEnd | Resolution | Granularity |
|---|---|---|---|---|---|
| `HLSL30_VI.020` | Vegetation Indices | 2013-04-11 | Present | 30m | Daily |
| `HLSS30_VI.020` | Vegetation Indices | 2015-11-28 | Present | 30m | Daily |
| `HLSL30.020` | Land Surface Reflectance | 2013-04-11 | Present | 30m | Daily |
| `HLSS30.020` | Land Surface Reflectance | 2015-11-28 | Present | 30m | Daily |

Layers:
- `HLSL30_VI.020` / `HLSS30_VI.020`: `EVI`, `MSAVI`, `NBR`, `NBR2`, `NDMI`, `NDVI`, `NDWI`, `SAVI`, `TVI`.
  NDVI and EVI: `int16`, `FillValue` -19999, `ScaleFactor` 0.0001, valid -1..1.
  **`QualityLayers` and `QualityProductAndVersion` are empty**: AppEEARS links no QA layer to the VIs.
- `HLSL30.020`: `B01`–`B07`, `B09`–`B11`, `Fmask`, `SAA`, `SZA`, `VAA`, `VZA`.
- `HLSS30.020`: `B01`–`B12`, `B8A`, `Fmask`, `SAA`, `SZA`, `VAA`, `VZA`.
- `Fmask`: `uint8`, `FillValue` 255, `IsQA` true, units "Bit Field".

So VI + cloud mask in one task = VI layers from `HLS{L,S}30_VI.020` plus `Fmask` from `HLS{L,S}30.020`.
The surface-reflectance fallback was **not needed**: AppEEARS serves both HLS-VI products.

### AppEEARS task result (T0.3)

- Task `09338e93-d3fa-493d-bc4a-476ac22a2b88`: created 2026-11-04T00:30:31Z, `processing` from ~00:52, `done` at 00:53:07Z (~22.5 min, mostly `pending`).
- `GET /task/{id}` keys when done: `api_version`, `attempts`, `cached_files`, `completed`, `crashed`, `created`, `error`, `estimate`, `expires_on`, `has_nsidc_daac`, `has_swath`, `params`, `retry_at`, `status`, `svc_version`, `task_id`, `task_name`, `task_type`, `tier`, `updated`, `user_id`, `web_version`, `worker_version`.
- Bundle: 17 files, all sha256-verified — one NetCDF per product (`<Product>.020_30m_aid0001_14N.nc`, NetCDF4/HDF5, 33–68 KB),
  per-date statistics CSVs (`HLS{L,S}30-VI-020-Statistics.csv`: File Name, Dataset, aid, Date, UTM Zone, Count, Minimum, Maximum, Range, Mean, Standard Deviation, Variance, Upper Quartile, Upper 1.5 IQR, Median, Lower 1.5 IQR, Lower Quartile),
  Fmask QA statistics (`HLS{L,S}30-020-Fmask-Statistics-QA.csv`: per date, pixel counts per Fmask value), Fmask lookup tables
  (`Value` → Aerosol level, Water, Snow/ice, Cloud shadow, Adjacent to cloud/shadow, Cloud, Cirrus), granule list, request JSON, per-product metadata XML, README.
- 2023-04-01..10-31 over the ~500 m box: L30 VI 33 dates, S30 VI 26 dates, L30 Fmask 47 dates. Full clear scene = 306 pixels (17 × 18).
- NetCDF (opened with `xarray` + `h5netcdf[h5py]`): dims `time × ydim (17) × xdim (18)`; VI file variables `NDVI`, `EVI` (float64, `_FillValue` −19999), `crs`; SR file `Fmask` (`_FillValue` 255), `crs`.
- **Time axis gotcha:** `time` has `units: "days since 2013-04-11 00:00:00"` and `calendar: "julian"`. Read as plain (Gregorian) day counts, the dates match the statistics CSV exactly. Do **not** decode with a real Julian calendar (cftime) — that shifts dates by ~13 days. Open with `decode_times=False` and add days to 2013-04-11.

### Gap: 47 L30 Fmask dates vs 33 L30 VI dates (investigated 2026-11-04)

The 14 dates in the Fmask file but not in the VI file (NetCDF and statistics CSV agree):

| Date | Fmask cloud fraction | cloud ∪ shadow ∪ adjacent | `HLSL30_VI` granule in CMR | `HLSL30` (SR) granule |
|---|---|---|---|---|
| 2023-04-02 | 0.86 | 1.00 | yes (T14SLH) | yes |
| 2023-04-17 | 1.00 | 1.00 | yes | yes |
| 2023-04-18 | 0.04 | 1.00 | yes | yes |
| 2023-04-25 | 1.00 | 1.00 | yes | yes |
| 2023-05-03 | 1.00 | 1.00 | yes | yes |
| 2023-05-12 | 1.00 | 1.00 | yes | yes |
| 2023-05-19 | 1.00 | 1.00 | yes | yes |
| 2023-05-27 | 1.00 | 1.00 | yes | yes |
| 2023-05-28 | 1.00 | 1.00 | yes | yes |
| 2023-06-20 | 0.87 | 1.00 | yes | yes |
| 2023-06-21 | 1.00 | 1.00 | yes | yes |
| 2023-08-08 | 1.00 | 1.00 | yes | yes |
| 2023-10-02 | 0.00 | 0.68 | **no** | yes |
| 2023-10-03 | 0.00 | 0.50 | **no** | yes |

Explanation:
- 12 dates: the VI granule exists but every pixel in the box is flagged cloud, cloud shadow or adjacent; AppEEARS drops VI dates with no valid pixel (kept VI dates have ≥ 4 valid NDVI pixels). *Inferred from the data, not stated in the AppEEARS docs.*
- 2 dates (2023-10-02, 2023-10-03): no `HLSL30_VI` granule exists in CMR although the SR granule does — a gap in the VI product itself, consistent with the archive-depth table (2023: 77 L30_VI vs 79 L30). **Why** those VI granules are missing is unexplained.
- Consequence for T1.5: VI series and Fmask series must be joined by date; a missing VI date is not evidence of a clear-sky gap.
- Login `expiration` was 24 h after login (docs say ~48 h).

## Source Cooperative GeoParquet via pyarrow / geopandas (T0.4)

Checked 2026-11-04 (geopandas 1.2.0, pyarrow 26.0.1, from installed source).

- `pyarrow.fs.S3FileSystem(anonymous=True, endpoint_override="data.source.coop", scheme="https", region="us-east-1")` works: path = `<account>/<key>` (e.g. `ftw/harmonized-field-data/...`). HTTPS fallback (`fsspec.filesystem("https")` + `https://data.source.coop/<key>`) was not needed.
- `geopandas.read_parquet(path, bbox=(xmin, ymin, xmax, ymax), filesystem=fs)`: needs the GeoParquet `bbox` covering column; the box must be in the **file's CRS**. It reads whole column chunks of matching row groups.
- `pq.ParquetFile(path, filesystem=fs).metadata` reads only the footer: `row_group(r).column(i).statistics.min/max` on `bbox.xmin|ymin|xmax|ymax` and `total_compressed_size` give a byte estimate before any data read.
- GeoParquet `geo` metadata: version 1.1.0 in all three files; CSB and France carry PROJJSON CRS (the CSB README's "CRS None" is out of date); FTW has no `crs` key (= OGC:CRS84).
- DuckDB httpfs/spatial extensions are blocked on this network (DECISIONS.md); not used.
- T0.4 results (footer-based estimates, compressed column chunks of matching row groups):

| Source | Box | Row groups hit | Est. read | Polygons in box |
|---|---|---|---|---|
| FTW `IN_PB.parquet` (992 MB, 159 RGs) | Punjab 10 km (75.418, 30.745, 75.522, 30.835) | 7 / 159 | 53.1 MB | 15,529 (2024 + 2025 layers together) |
| USDA CSB 2024 (3,118 MB, 302 RGs) | T14SLH footprint | 4 / 302 | 43.9 MB | 20,190 |
| France RPG 2024 (2,759 MB, 387 RGs) | Beauce 20 km (1.465, 48.16, 1.735, 48.34) | 2 / 387 | 12.6 MB | 6,198 |
| FTW `US_KS.parquet` (531 MB, 17 RGs) | T14SLH footprint | 5 / 17 | 204.1 MB | not run (> 200 MB cap) |

- FTW `Ukraine.parquet`: 4,116,875 rows, 63 row groups, 1,985 MB (~32 MB per row group) — larger row groups than Punjab (~6 MB).
