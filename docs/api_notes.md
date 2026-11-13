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

## CMR facts for the census (T0.5 planning, 2026-11-04)

- HLS granule cloud cover: `umm.AdditionalAttributes[Name="CLOUD_COVERAGE"].Values[0]` (string, percent of the tile); `umm.CloudCover` is absent. Also useful: `SPATIAL_COVERAGE` (percent of the tile with data), `MGRS_TILE_ID`, `SENSING_TIME`.
- MGRS tiles at candidate points (HLSS30_VI search, June 2023): Beauce (1.60, 48.25) → `T31UCP`; Punjab/Jagraon (75.47, 30.79) → `T43REQ`; central Ukraine (32.26, 48.51) → `T36UVU`; Nile Delta (31.00, 30.79) → `T36RTV` and `T36RUV` (overlap).
- FTW Egypt partition: `.../admin:country_code=EG/Egypt.parquet` (size not yet read).
- **ECOSTRESS `ECO_L3T_JET` v003 is a partial archive**: 378,068 granules, earliest 2019-08-23, latest 2026-10-28, and zero granules in June 2023 (no spatial filter). v002: 4,803,551 granules, 2018-07-10 → 2026-10-31. At the Kansas point (−100.9, 38.0), all time: v003 66, v002 850. `point=` and `bounding_box=` searches work for both.

## NASA POWER — daily point API (Gate 0, for T1.2)

Checked 2026-11-04 (docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/).

- Request: `GET https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR&community=AG&longitude=-100.6604&latitude=38.3425&start=20230101&end=20231231&format=JSON` (Kansas T14SLH tile centre). Max 20 parameters per point request; dates `YYYYMMDD`.
- Response: HTTP 200, 36,856 bytes. Top keys: `type`, `geometry`, `properties`, `header`, `messages`, `parameters`, `times`.
  - `geometry.coordinates` = `[-100.66, 38.343, 852.2]` (lon, lat, **elevation m** — needed for ETo).
  - `properties.parameter.<NAME>` = `{ "YYYYMMDD": value, ... }` — 365 days each for 2023.
  - `parameters.<NAME>` = `{units, longname}`: T2M_MAX / T2M_MIN `C`; RH2M `%`; WS2M `m/s`; ALLSKY_SFC_SW_DWN `MJ/m^2/day`; PRECTOTCORR `mm/day`.
  - `header.fill_value` = −999.0 (no fill values in this year); `header.sources` = MERRA2, SYN1DEG, POWER.
- All six parameter names in PLAN.md T1.2 are valid (RH2M used; dew point not needed).

## ISRIC SoilGrids — REST properties/query (Gate 0, for T1.3)

Checked 2026-11-04: **service unavailable.** `GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-100.6604&lat=38.3425&property=sand&property=clay&property=soc&property=bdod&depth=0-5cm&depth=30-60cm&value=mean&value=Q0.05&value=Q0.5&value=Q0.95` → HTTP 503 "Service Temporarily Unavailable" (nginx); the OpenAPI document and the docs page also failed (503 / timeout). ISRIC's map server `https://maps.isric.org/` answers HTTP 200 (WCS/WMS) — candidate fallback for T1.3, not yet verified from its docs. Retry 1 at 2026-11-04T02:56Z: no response within 90 s (curl timeout). Retry 2 scheduled for 2026-11-05; if still down, check the WCS fallback (docs and licence first).

## Kansas WIMAS (Gate 0, for T1.7)

Checked 2026-11-04: `https://geohydro.kgs.ku.edu/geohydro/wimas/` is public (no registration) but opens on a **disclaimer page that must be accepted ("I ACCEPT")** before any query. Terms (from the page): DWR and KGS offer "no warranty or guarantee of the accuracy or completeness"; data reflect files as of 11/01/2026; products must not be used in violation of K.S.A 45-220(c)(2). No bulk download without the disclaimer was found (the KGS High Plains data page links only to WIMAS). **Not queried: accepting the terms is the user's decision.**

## OpenET (Gate 0)

**Removed from the MVP and moved to stretch S6 (user, 2026-11-04), pending the user's reading of its terms. Not accessed.**

## HLS direct COG read via earthaccess (Gate 0; T1.5b fallback)

Checked 2026-11-04 with `scripts/check_hls_cog.py` (rasterio 1.5.2 / GDAL 3.12.2, rioxarray 0.23.0).

- Auth: `earthaccess.login(strategy="netrc")`, then `fs = earthaccess.get_fsspec_https_session()` and `rasterio.open(url, opener=fs.open)` (rasterio's `opener` serves GDAL through Python file objects). **No credentials, cookies or tokens are written to disk**; no GDAL netrc/cookie settings are used.
- Test: granule `HLS-VI.S30.T14SLH.2023185T172901.v2.0`, 256 × 256 window at (−100.90, 38.00).
  - `…NDVI.tif`: EPSG:32614, 3660 × 3660, int16, nodata −19999, `scale_factor` 0.0001, `add_offset` 0, **block shape 1 × 3660 (striped, not tiled) and no overviews** → a window reads whole rows: 1.68 MB for 256 rows.
  - `HLS.S30.…Fmask.tif` (from the HLSS30 SR product): uint8, nodata 255, **256 × 256 tiles, overviews 2/4/8/16**; window read ≈ 0.04 MB. Most common values in the window: 64, 128, 192, 96, 160.
  - Total transferred: **1.72 MB**.

### T1.5b fallback (direct COG reads) — how to use it

1. Find granules: `earthaccess.search_data(short_name="HLS{L,S}30_VI", version="2.0", granule_name="HLS-VI.*.T<tile>.*", temporal=(start, end))`.
2. For each granule take the `NDVI`/`EVI` links (HLS*_VI.020) and the `Fmask` link (HLS*30.020 — it is in the VI granule's `data_links()`).
3. Open with `rasterio.open(url, opener=fs.open)` and read **one window per granule spanning all pilot fields of the tile** (row range from the fields' bounds), not one window per field: the VI files are striped, so cost grows with the number of rows and nearby fields share rows. Cost ≈ 6.6 KB per row per band (1.68 MB / 256 rows); a full tile ≈ 24 MB per band per date.
4. Apply scale 0.0001 and fill −19999 (VI), fill 255 (Fmask); decode Fmask bits with the HLS lookup (AppEEARS ships one per product; confirm against the HLS user guide in T1.5).
5. Join VI and Fmask **by date**: some dates have Fmask but no VI granule (47-vs-33 gap above).
6. Use AppEEARS (task route, T0.3) for many fields over many years; use this route for small or urgent reads.

## GBIF species match and USDA PLANTS (crop families, T0.6)

Checked 2026-11-04 with one call each, then `scripts/check_families.py`.

- GBIF: `GET https://api.gbif.org/v1/species/match?name=Zea%20mays&kingdom=Plantae` → keys `usageKey, scientificName, canonicalName, rank, status, confidence, matchType, kingdom, phylum, class, order, family, genus, species` (+ `*Key`). Zea mays: usageKey 5290052, ACCEPTED, EXACT, confidence 100, family Poaceae.
- USDA PLANTS (no key needed): `GET https://plantsservices.sc.egov.usda.gov/api/PlantSearch?searchText=<name>` → list of `{Text, Plant{Id, Symbol, ScientificName (HTML), CommonName, Rank, ...}}`; `GET .../api/PlantProfile?symbol=<SYMBOL>` → profile with `Ancestors` (family rank, e.g. "Poaceae Barnhart", authority included).
- Results: 8 crops (scientific names from FAO-66): GBIF and USDA families agree — Poaceae (maize, sorghum, wheat, barley), Asteraceae (sunflower), Fabaceae (soybean). Rapeseed and the oat cover-crop proxy (no FAO-66 chapter): names specified by the user, *Brassica napus* → Brassicaceae (GBIF 3042636, USDA BRNA) and *Avena sativa* → Poaceae (GBIF 2705290, USDA AVSA); GBIF and USDA agree for all 10 crops.

## SoilGrids 2.0 via WCS (T1.3; REST fallback)

Checked 2026-11-04 (docs: https://docs.isric.org/globaldata/soilgrids/wcs.html; units table: https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html; licence: ISRIC data policy v2024-1, CC-BY 4.0 for SoilGrids).

- GetCapabilities: `GET https://maps.isric.org/mapserv?map=/map/<property>.map&SERVICE=WCS&VERSION=2.0.0&REQUEST=GetCapabilities` → 30 coverage ids per property: `<property>_<depth>_<stat>` with depths 0-5cm, 5-15cm, 15-30cm, 30-60cm, 60-100cm, 100-200cm and stats Q0.05, Q0.5, Q0.95, mean, uncertainty.
- GetCoverage: `SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=sand_0-5cm_mean&FORMAT=GEOTIFF_INT16&SUBSET=X(w,e)&SUBSET=Y(s,n)&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326` → `image/tiff`, int16, EPSG:4326, ≈ 0.0023° cells (server reprojects from the native EPSG:152160 Homolosine 250 m grid); ≈ 200 KB for the Kansas tile.
- DescribeCoverage: `swe:nilValues` is empty (no declared nodata). Raw 0 appears outside soil (water/urban); we mask a cell when the property's `mean` coverage is 0 there.
- Units (mapped → conventional): bdod cg/cm3 ÷ 100 → kg/dm3; clay, sand, silt g/kg ÷ 10 → %; soc dg/kg ÷ 10 → g/kg.

## Context datasets (T1.8)

Checked 2026-11-04 in CMR, then downloaded with earthaccess.

- NASADEM_HGT v001 (`C2763264762-LPCLOUD`): granules `NASADEM_HGT_n37w101`, `n37w102`, `n38w101`, `n38w102` (≈ 6.5 MB zip each) cover T14SLH; each zip holds `<tile>.hgt`, `.num`, `.swb`; read via `zip://…!<tile>.hgt` (GDAL SRTMHGT). Also available: `NASADEM_SC` (slope/curvature), not used.
- TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 (`C3195527175-POCLOUD`): one granule `GRCTellus.JPL.200204_202608.GLO.RL06.3M.MSCNv04CRI.nc` (46 MB). Dims time 260 × lat 360 × lon 720 (0.5°, lon 0.25–359.75). Variables: `lwe_thickness` (cm), `uncertainty`, `land_mask`, `scale_factor` ("to be used with mascon solution that has the CRI filter applied; based on CLM data from 2002-2009"), `mascon_ID`, `GAD`, bounds. Global attributes: `time_mean_removed` 2004.000–2009.999; licence link https://science.nasa.gov/earth-science/earth-science-data/data-information-policy.
- SPL4SMGP v008 (`C3480440870-NSIDC_CPRD`): 3-hourly 9 km granules; used through AppEEARS product `SPL4SMGP.008`, layer `Geophysical_Data_sm_rootzone` ("Root zone soil moisture (0-100 cm)", m^3/m^3, fill −9999).
  - Result (task `b5e1ec71…`, downloaded 2026-11-04): 3 points (one per region), 2015-04-01..2024-12-31, 3-hourly, 28,504 rows each (85,512 total), no fills or negatives, range 0.158–0.376. Results CSV columns: Category, ID, Latitude, Longitude, Date (`YYYY-MM-DD HH:MM:SS UTC`), SMAP_Tile, SPL4SMGP_008_Line_Y_9.00805km, SPL4SMGP_008_Sample_X_9.00805km, SPL4SMGP_008_Geophysical_Data_sm_rootzone. 9 km cell: context only, scale flag. Cached in `data/context/smap/` (gitignored).

## DoubleML for Python (T5.2)

Checked 2026-11-07 (PyPI JSON `https://pypi.org/pypi/doubleml/json`; docs `https://docs.doubleml.org/stable/`, pages `api/generated/doubleml.plm.DoubleMLPLR.html` and `api/generated/doubleml.data.DoubleMLData.html`; source `https://github.com/DoubleML/doubleml-for-py`).

- **Licence:** BSD 3-Clause (PyPI `license` text, "Copyright (c) 2019-2023 Philipp Bach, Victor Chernozhukov, Sven Klaassen, Malte S. Kurz, Martin Spindler"; classifier `License :: OSI Approved :: BSD License`). Compatible with this repo; keep the notice when redistributing.
- **Latest release on PyPI:** 0.11.4, `requires_python >= 3.10`.
- **Required runtime dependencies (not optional):** joblib ≥ 1.2, numpy ≥ 2.0, pandas ≥ 2.0, scipy ≥ 1.7, scikit-learn ≥ 1.6, statsmodels ≥ 0.14, optuna ≥ 4.6, matplotlib ≥ 3.9, seaborn ≥ 0.13, plotly ≥ 5.0, mypy ≥ 1.18. Extras: `rdd` (rdrobust), `dev`.
- **Data backend:** `doubleml.data.DoubleMLData(data, y_col, d_cols, x_cols=None, z_cols=None, cluster_cols=None, use_other_treat_as_covariate=True, force_all_x_finite=True, force_all_d_finite=True)`; `data` is a `pandas.DataFrame`; `x_cols=None` uses every column that is not y, d, z or cluster.
- **Partially linear model:** `doubleml.plm.DoubleMLPLR(obj_dml_data, ml_l, ml_m, ml_g=None, n_folds=5, n_rep=1, score='partialling out', draw_sample_splitting=True)`. `ml_l` learns E[Y|X], `ml_m` learns E[D|X] (a classifier with `predict_proba` is allowed for binary D); `ml_g` only for `score='IV-type'`.
- **Methods / attributes:** `fit(n_jobs_cv=None, store_predictions=True, external_predictions=None, store_models=False)`; `confint(joint=False, level=0.95)`; `coef`, `se`, `pval`, `summary`; also `sensitivity_analysis(...)`, `tune(...)`.
- **Own folds (rule 7, spatial blocks):** `set_sample_splitting(all_smpls, all_smpls_cluster=None)` is documented: `all_smpls` is a nested list (one entry per repetition) of `(train_idx, test_idx)` tuples; `n_folds` and `n_rep` are derived from it. Use with `draw_sample_splitting=False`.
- **Installed 2026-11-07:** doubleml 0.11.4, scikit-learn 1.9.1 (`uv add` by the user). `inspect.signature` of the installed `DoubleMLData.__init__`, `DoubleMLPLR.__init__`, `fit`, `set_sample_splitting`, `confint` matches the docs above.
- **Test call** (synthetic, seed 20261114, n = 400, true effect 0.5, `RandomForestRegressor(50)` for `ml_l` and `ml_m`, 5 own folds via `set_sample_splitting([folds])` with `draw_sample_splitting=False`): `coef` and `se` are `numpy.ndarray` of length 1 (0.428, 0.051); `n_folds` 5, `n_rep` 1; `confint(level=0.95)` returns a `pandas.DataFrame` indexed by the treatment name with columns `2.5 %` and `97.5 %` (0.328, 0.528).

## USDA-NRCS Soil Data Access (SSURGO) — Phase 12 soil check

Checked 2026-11-11 from the official pages: `https://sdmdataaccess.sc.egov.usda.gov/WebServiceHelp.aspx` (POST REST), `https://sdmdataaccess.sc.egov.usda.gov/documents/AdvancedQueries.html` (spatial macros), `https://sdmdataaccess.sc.egov.usda.gov/Citation.htm`, and the SDM "Table Column Descriptions" report (`https://sdmdataaccess.sc.egov.usda.gov/documents/TableColumnDescriptionsReport.pdf`, read with pypdf). Used only by `scripts/check_ssurgo.py`; never a simulation input.

- **Endpoint:** `POST https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest`, body JSON `{"query": "<SQL>", "format": "JSON+COLUMNNAME"}` (parameter names case-insensitive; `QUERY` required; `FORMAT` one of `XML` (default), `JSON`, `JSON+COLUMNNAME`, `JSON+COLUMNNAME+METADATA`, `~`). Max 100,000 rows per query. No rate limit is stated; we send one point per request, sequentially, with a 1 s pause, and cache every reply.
- **Point lookup:** `SDA_Get_Mukey_from_intersection_with_WktWgs84('point(<lon> <lat>)')` is a table function returning the `mukey` of every map unit the WKT geometry intersects (docs example uses lon then lat).
- **Response shape (real test call, point −101.1035 38.3885):** HTTP 200, `application/json; charset=utf-8`, body `{"Table": [["mukey","muname",…], ["2668839","Ulysses silt loam, 0 to 1 percent slopes","27965171","Ulysses","99","Yes","0","20","0.22","26","20"], …]}`. Row 1 is column names; every value is a string. A point with no map unit (test: `point(0 0)`) returns `{}`. A bad table name returns HTTP 400 with an OGC `ServiceExceptionReport` XML body (`mdstattabcols` is not exposed through SDA).
- **Columns and units** (column-description report): `component.comppct_r` "The percentage of the component of the mapunit"; `majcompflag` major component flag; `chorizon.hzdept_r` / `hzdepb_r` depth from the soil surface to the upper / lower horizon boundary; `awc_r` "expressed as a volume fraction" (cm/cm), "commonly estimated as the difference between the water contents at 1/10 or 1/3 bar (field capacity) and 15 bars (permanent wilting point)"; `claytotal_r`, `sandtotal_r` weight percent of the < 2 mm fraction. `muaggatt.aws0100wta` is available water storage 0–100 cm, "weighted average of all components in the map unit", in cm of water.
- **Unit check:** the report does not print a unit for `hzdept_r`; the values (0–200) and the cross-check below confirm cm. For map unit 2668839: Ulysses (99 %) Σ awc_r·dz over 0–100 cm = 21.50 cm, Ness (1 %) = 15.25 cm, weighted = 21.44 cm = NRCS `aws0100wta` 21.44 (and `aws0150wta` 32.42). So AWS_mm = 10 · Σ awc_r[cm/cm] · dz[cm], and component-percent weighting reproduces NRCS's own aggregate.
- **Citation (Citation.htm):** Soil Survey Staff, Natural Resources Conservation Service, United States Department of Agriculture. Soil Survey Geographic (SSURGO) Database. Available online at https://sdmdataaccess.sc.egov.usda.gov. Accessed 11/11/2026.
- **Terms:** the SDA pages state no data licence. The site "Disclaimer" (a JavaScript alert on the home page) is the standard USDA computer-system notice: the system "may be accessed and used only for official Government business (or as otherwise permitted by regulation) by authorized personnel", and use implies consent to monitoring. Public-domain status of SSURGO was not confirmed from an official page today (the NRCS SSURGO page timed out): UNVERIFIED.

## LLM chat proxy: Google Gemini (OpenAI-compatible) and Groq — chatbot, 2026-11-13

Checked 2026-11-13 from the official pages. No test call made (every call needs a key; rule: never read or ask for keys).

- **Gemini, OpenAI-compatible** (`https://ai.google.dev/gemini-api/docs/openai` → redirects to `https://aistudio.google.com/docs/openai`): base URL `https://generativelanguage.googleapis.com/v1beta/openai/`, POST `chat/completions`, header `Authorization: Bearer $GEMINI_API_KEY`, body `{"model", "messages": [{"role","content"}]}` plus optional `reasoning_effort`, `stream`. Reply read from `choices[0].message.content` (the page shows SDK access paths, not a full JSON reply: full shape UNVERIFIED).
- **Gemini free tier** (`https://aistudio.google.com/docs/pricing`): text models listed "Free of charge" include `gemini-4-hydrogen`, `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-flash-lite` (`gemini-2.5-flash` and `gemini-2.5-pro` are marked deprecated). Free plan card: "Content used to improve our products". Chosen default: `gemini-3.5-flash-lite` (free, non-deprecated, light). Per-model free RPM/RPD: `https://aistudio.google.com/docs/rate-limits` says limits "can be viewed in Google AI Studio" — not stated on the page: UNVERIFIED.
- **Groq** (`https://console.groq.com/docs/openai`): base URL `https://api.groq.com/openai/v1` (key passed as the API key; Bearer header is the OpenAI-SDK convention, UNVERIFIED on that page). Production chat models (`/docs/models`): `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`. Rate limits page refers to the account's limits page: free limits UNVERIFIED. Groq data-use terms not checked: UNVERIFIED.
- **Cloudflare Workers Rate Limiting binding** (`developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/`): `[[ratelimits]] name, namespace_id (string, positive integer), [ratelimits.simple] limit, period (10 or 60)`; `await env.X.limit({ key })` → `{ success }`; counts approximate, per location, eventually consistent. Free-plan availability not stated on that page or the pricing page: UNVERIFIED.
- **Workers KV Free plan** (`developers.cloudflare.com/kv/platform/limits/`): 100,000 reads/day, 1,000 writes/day (different keys), 1 write/s to the same key. Namespace: `npx wrangler kv namespace create <BINDING>`; binding `[[kv_namespaces]] binding, id`.
- **Workers Free plan**: 100,000 requests/day (`/workers/platform/pricing/`).
