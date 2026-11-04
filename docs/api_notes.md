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
