# DATA.md — datasets, access and licences

Every external dataset FieldWitness reads, with its exact access path, licence and required attribution.

## Field boundaries and crop labels (T0.4)

All three are GeoParquet 1.1 files with a per-feature `bbox` covering column, hosted on Source Cooperative.
Read path: anonymous S3 (`endpoint_override="data.source.coop"`, bucket `ftw`) or HTTPS `https://data.source.coop/<key>`.
Only the row groups whose `bbox` statistics intersect the query box are read (see `scripts/check_fields.py`).

### Fields of the World — global field-boundary predictions (alpha)

- Punjab file (Tier 3 candidate): `https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=IN/IN_PB.parquet`
  (10,396,804 polygons over the 2024 and 2025 layers; CRS OGC:CRS84; 159 row groups, 992 MB).
- Ukraine file (Tier 3 `ua_central_t36uvu`): `https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=UA/Ukraine.parquet`
  (windowed extract for `T36UVU` 2×2 20 m COG tiles `tx in {1,2}, ty in {7,8}`, 40.0 MB downloaded, deduplicated to 395 unique fields ≥ 5 ha across 8 10-km spatial blocks; 0 scale-flagged).
- Kansas file (not used: CSB is the Tier 1 source): `.../admin:country_code=US/US_KS.parquet` (1,103,107 polygons; 17 row groups, 531 MB).
- Other countries: `.../results-by-admin-conf/admin:country_code=<CC>/...`; find files via the STAC catalogue
  `https://data.source.coop/ftw/global-data/predictions/vectors/collection.json`.
- Licence: **CC-BY-4.0**. Attribution: Fields of the World / Taylor Geospatial (polygons from the PRUE model on Sentinel-2).
- Caveat (from the README): a "field" is a predicted remote-sensing field unit, not a cadastral parcel; alpha release. No crop labels (`labels.source == "none"`), so Ukraine crop histories are inferred via causal Sentinel-2 phenology + TWDTW (`crop_source = "classifier"`, tag `D`).

### USDA NASS Crop Sequence Boundaries (CSB), 2017–2024 edition

- GeoParquet copy (one file per year of the same edition):
  `https://data.source.coop/ftw/harmonized-field-data/us_usda_cropland/year=<YYYY>/us_usda_cropland-<YYYY>.parquet`, YYYY = 2017–2024
  (2024: 7,541,673 rows; 302 row groups; 3,118 MB).
- Converted from NASS `https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/datasets/NationalCSB_2017-2024_rev23.zip`.
- CRS: Albers Conical Equal Area (NAD83; parallels 29.5/45.5; central meridian −96; origin 23) — PROJJSON present in the file.
- Licence: NASS metadata Use_Constraints: "provided to the public as is and are considered public domain and free to redistribute."
  Attribution: United States Department of Agriculture, National Agricultural Statistics Service.
- Leakage note: these boundaries come from the 2017–2024 edition (post-2021 imagery); pre-2022 boundaries are not used
  (accepted in PLAN.md Phase 7, logged in DECISIONS.md).

### France — RPG field data with EuroCrops V2 years

- `https://data.source.coop/ftw/harmonized-field-data/fr/year=<YYYY>/fr-<YYYY>.parquet`, YYYY = 2015–2024
  (2024: 9,671,682 rows; 387 row groups; 2,759 MB). CRS: RGF93 v1 / Lambert-93 (EPSG:2154).
- Licences and attribution:
  - 2017, 2019–2024: **Licence Ouverte / Open Licence 2.0** (Etalab). Attribution: IGN — original data from https://geoservices.ign.fr/rpg
  - 2015, 2016, 2018: from **EuroCrops V2**, **CC-BY-4.0**. Attribution: European Commission, Joint Research Centre, EuroCropsV2.

### Crop taxonomy — HCAT3 (EuroCrops)

- Table: `https://github.com/maja601/EuroCrops/blob/main/hcat_core/HCAT3.csv` (Hierarchical Crop and Agriculture Taxonomy v3, 384 classes), used for the annual-arable field definition (`fieldwitness.data.hcat`, `docs/hcat_annual_arable.md`).
- French crop codes → HCAT3 mapping: `https://fiboa.org/code/fr/fr.csv` (referenced by the GeoParquet `crop:code_list`).
- Licence: EuroCrops repository **CC-BY-SA-4.0** (share-alike). Attribution: Schneider, M., Schelte, T., Schmitz, F. & Körner, M. (2023), "EuroCrops: The Largest Harmonized Open Crop Dataset Across the European Union" — HCAT3 taxonomy.
- The derived HCAT class list lives in its own file, `docs/hcat_annual_arable.md`, under **CC-BY-SA-4.0**, separate from the code licence. The code (`fieldwitness.data.hcat`) holds only the prefix rules and cites the HCAT3 table; it does not redistribute the table.

## Satellite data (T0.2, T0.3)

- **Harmonized Landsat Sentinel-2 (HLS)**: Vegetation Indices `HLSL30_VI` v2.0 and `HLSS30_VI` v2.0; Surface Reflectance `HLSL30.020` and `HLSS30.020` (Fmask) — NASA LP DAAC, via earthaccess (CMR) and AppEEARS.
  - DOIs: `HLSL30.002`: https://doi.org/10.5067/HLS/HLSL30.002 ; `HLSS30.002`: https://doi.org/10.5067/HLS/HLSS30.002
  - Citation: Claverie, M., Ju, J., Masek, J. G., et al. (2018). The Harmonized Landsat and Sentinel-2 (HLS) Product. *Remote Sensing of Environment*, 219, 145–161.
  - Licence: NASA Earth Science Data Policy (open and free for all users).
- **Sentinel-2 L2A Collection 1 COGs (Element84 Earth Search v1, Tier 3 `ua_central_t36uvu`)**:
  - Endpoint: `https://earth-search.aws.element84.com/v1/search`, collection `sentinel-2-l2a` (`grid:code = "MGRS-36UVU"`).
  - Access (`fieldwitness.data.s2_cog`): HTTP Range reads of targeted 20 m (`512×512`) COG tiles for `red` (B04 IFD 1), `nir` (B08 IFD 1), and `scl` (SCL IFD 0, keeping clear classes `SCL in {4, 5}`). Computes NDVI and 2-band EVI2 (`2.5 * (NIR - RED) / (NIR + 2.4 * RED + 1.0)`, Jiang et al. 2008, *Remote Sensing of Environment* 112(10):3833–3845) over up to 12 seeded interior pixel centres per field (15 m inward buffer).
  - Radiometric offset caveat: STAC `raster:bands` on baseline 04.00/05.xx scenes advertises `offset = -0.1` even when `earthsearch:boa_offset_applied == true`; `s2_cog.py` applies `-0.1` only when `earthsearch:boa_offset_applied` is falsy to avoid double subtraction.
  - Central Ukraine dataset (`ua_central_t36uvu`): 128 balanced scenes (`2017-03-01` to `2024-11-17`), 48,199 clear field-date rows across 395 fields (`0` saturated `ndvi >= 0.999` values); combined session downloads across FTW (40.0 MB), S2 COG (~595 MB including offset fix re-extraction), NASA POWER (244 points, ~15 MB HTTP), and SoilGrids (35.1 KB) stayed ~650 MB (`< 1 GB` cap).
  - Licence: Copernicus Sentinel Data Terms and Conditions (open and free, attribution to European Union / ESA / Copernicus via Element84 Earth Search AWS Public Dataset).
- **NASA GIBS HLS True-Colour Basemap (T9.1 / P0.1)**:
  - Source: NASA Global Imagery Browse Services (GIBS) / LP DAAC, part of NASA EOSDIS.
  - Layer: `HLS_S30_Nadir_BRDF_Adjusted_Reflectance` (Sentinel-2 MSI true-colour RGB: Red B04, Green B03, Blue B02).
  - Spatial resolution: ~30 m native resolution (WMTS `GoogleMapsCompatible_Level12`, ~29.8 m/pixel at 38°N).
  - Date of imagery: 2023-07-04 (summer peak vegetation growth, 99.88% clear observation across Kansas tile T14SLH).
  - Endpoint: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/2023-07-04/GoogleMapsCompatible_Level12/{z}/{y}/{x}.png` (EPSG:3857). Offline/error behavior: falls back to neutral background.
  - Required attribution: "Imagery: NASA GIBS / LP DAAC (HLS S30, 2023-07-04)".
  - Licence: NASA Earth Science Data Policy (open and free for all users).
- **NASA GPM & IMERG Precipitation**:
  - Products: `GPM_3IMERGDF` v07 (Concept ID `C2723754864-GES_DISC`), half-hourly and daily global calibrated precipitation (0.1° resolution).
  - GIBS Layers: `IMERG_Precipitation_Rate`, `IMERG_Precipitation_Rate_30min` (`GoogleMapsCompatible_Level6`).
  - Licence: NASA Earth Science Data Policy (open and free).
- **Suomi NPP & NOAA-20 / NOAA-21 VIIRS & MODIS Reflectance**:
  - Products: `VNP13A1.002` (500 m 16-day NDVI/EVI, `C2519127224-LPCLOUD`), `VNP09GA.002` (500m/1km daily surface reflectance).
  - GIBS Layers: `MODIS_Terra_CorrectedReflectance_TrueColor`, `VIIRS_SNPP_CorrectedReflectance_TrueColor` (`GoogleMapsCompatible_Level9`).
  - Licence: NASA Earth Science Data Policy (open and free).
- **NASA ECOSTRESS Thermal Evapotranspiration**:
  - Products: `ECO_L3T_JET` v003 (Concept ID `C4057232489-LPCLOUD`, 70 m PT-JPL tiled ETa) and v002 (`C2076106409-LPCLOUD`).
  - Scale: 70 m spatial resolution meets field scale contract (CLAUDE.md Rule 5).
  - Licence: NASA Earth Science Data Policy (open and free).
- **NASA Shuttle Radar Topography Mission (SRTM) & NASADEM**:
  - Products: `NASADEM_HGT` v001 (`C2763264762-LPCLOUD`) and `SRTMGL1` v003 (`C2763266360-LPCLOUD`), 1 arc-second (~30 m global DEM).
  - GIBS Layer: `SRTM_Color_Index` (`GoogleMapsCompatible_Level12`).
  - Licence: NASA Earth Science Data Policy (open and free).
- **NASA SMAP L4 Soil Moisture**:
  - Product: `SPL4SMGP` v008 (Concept ID `C3480440870-NSIDC_CPRD`, 9 km root-zone and surface soil moisture).
  - Scale: 9 km regional context only, scale-flagged (Rule 5).
  - Licence: NASA Earth Science Data Policy (open and free).
- **NASA GRACE / GRACE-FO Mascons**:
  - Product: `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` (PO.DAAC, 0.5° terrestrial water storage anomalies).
  - Scale: Coarse regional context only, scale-flagged.
  - Licence: NASA Earth Science Data Policy.
- **NASA NLDAS & GLDAS Land Data Assimilation Systems**:
  - Products: `NLDAS_FORA0125_H.2.0` (`C2033151148-GES_DISC`, 0.125°), `GLDAS_NOAH025_3H.2.1` (`C1342986035-GES_DISC`, 0.25°).
  - Scale: Coarse regional hydrological forcing/context, scale-flagged.
  - Licence: NASA Earth Science Data Policy.
- **NASA GEDI (Global Ecosystem Dynamics Investigation)**:
  - Products: `GEDI02_A` v003 (`C3974616071-LPCLOUD`).
  - Evaluation: Noted and excluded from annual crop canopy models (sparse footprints primarily calibrated for forest canopy 3D structure, PLAN.md §1b).

## Weather, soil, water use and partner datasets

- **NASA POWER** daily point API, community AG: `https://power.larc.nasa.gov/api/temporal/daily/point` (parameters T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR).
  - Citation: Sparks, A. H. (2018). nasapower: A NASA POWER Global Meteorology, Surface Solar Energy and Climatology Data Client for R. *Journal of Open Source Software*, 3(30), 1035. https://doi.org/10.21105/joss.01035
  - Terms: NASA Open Data Policy (public domain, free reuse with attribution).
- **ECMWF ERA5 & ERA5-Land Reanalysis**:
  - Source: European Centre for Medium-Range Weather Forecasts (ECMWF) Copernicus Climate Change Service.
  - Access: Open-Meteo Historical Archive REST API (`https://archive-api.open-meteo.com/v1/archive`) & Copernicus CDS.
  - Licence: Copernicus Open Access Licence (free reuse with attribution).
- **PRISM Climate Group**:
  - Source: Oregon State University PRISM Climate Group (4 km and 800 m gridded weather).
  - Access: Centralized public web service (`https://services.nacse.org/prism/data/get/us/4km/{var}/{date}`).
  - Licence: Free research/educational use; terms of service apply.
- **USDA-NRCS Web Soil Survey (WSS) / SSURGO & STATSGO2**:
  - Source: USDA Natural Resources Conservation Service via Soil Data Access (SDA) REST API (`https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest`).
  - High-res: SSURGO 1:24,000 mapunits (county catalogs, e.g. `KS055`, median 282.1 mm AWS across pilot).
  - Fallback: STATSGO2 1:250,000 generalized mapping (national catalog `areasymbol = 'US'`).
  - Licence: Public domain.
- **USDA NASS Cropland Data Layer (CDL) & CropScape**:
  - Source: USDA National Agricultural Statistics Service 30 m annual cropland classifications.
  - Access: CropScape Web Service (`https://nassgeodata.gmu.edu/axis2/services/CDLService`).
  - Licence: Public domain.
- **USDA NASS QuickStats**:
  - Source: USDA NASS Agricultural Statistics database (`https://quickstats.nass.usda.gov/api/api_GET/`).
  - Scope: County crop prevalence and harvested acreages. Commodity prices and profit forecasts strictly excluded per CLAUDE.md Rule 4.
  - Licence: Public domain; free API key.
- **USDA Ag Data Commons**:
  - Source: USDA National Agricultural Library (NAL) open access agricultural research catalog (`https://agdatacommons.nal.usda.gov/`).
  - Access: Figshare search API (Institution ID 1146).
  - Licence: Public domain / CC0.
- **USDA NAIP (National Agriculture Imagery Program)**:
  - Source: USDA Farm Service Agency & USGS The National Map (TNM).
  - Access: ArcGIS ImageServer (`https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer`).
  - Resolution: 0.6 m – 1.0 m growing-season aerial orthophotography.
  - Licence: Public domain.
- **USGS NLCD (National Land Cover Database)**:
  - Source: Multi-Resolution Land Characteristics Consortium (MRLC) / USGS.
  - Access: WCS/WMS (`https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/wcs`).
  - Resolution: 30 m land cover classifications.
  - Licence: Public domain.
- **USGS NWIS (National Water Information System)**:
  - Source: US Geological Survey Water Services (`https://waterservices.usgs.gov/nwis/`).
  - Endpoints: Groundwater levels (`/gwlevels/`) and daily discharge streamflow (`/dv/`).
  - Licence: Public domain.
- **USFS / DOI LANDFIRE**:
  - Source: US Forest Service & Department of the Interior (`https://lfps.usgs.gov/api/products`).
  - Resolution: 30 m vegetation, fuels, and disturbance dynamics.
  - Licence: Public domain.
- **FAO GAEZ v4 (Global Agro-Ecological Zones)**:
  - Source: FAO & IIASA (`https://gaez-services.fao.org/server/rest/services`).
  - Resolution: 5 arc-minute (~10 km) regional agro-climatic suitability zones and soil terrain constraints.
  - Licence: CC-BY-4.0.
- **CoCoRaHS (Community Collaborative Rain, Hail & Snow Network)**:
  - Source: Citizen-science volunteer daily rain-gauge network (`https://data.cocorahs.org/export/exportreports.aspx`).
  - Licence: Open educational and research access.
- **ISRIC SoilGrids 2.0**:
  - Access: WCS `https://maps.isric.org/mapserv?map=/map/<property>.map`.
  - Licence: CC-BY 4.0; Poggio et al. (2021).
- **OpenET**:
  - Status: Operational field-scale ET; requires registration, API key and terms acceptance. Excluded from MVP (PLAN.md S6).
- **USDA AMS Market News**:
  - Status: Market presence metadata only. Commodity price and profit forecasting strictly excluded per CLAUDE.md Rule 4 and red-team audit.

## Derived app inputs: 3D replay (Rotation Builder)

`packs/<region>/<field_id>.sim3d_inputs.json` holds no new data source: the median-rain year's NASA POWER rain and FAO-56 ETo (as used by the Field in 3D pack), posterior medians from `results/rotate/posterior_draws.json`, and crop parameters from `config/crops.yaml`. Regenerate with `python -m fieldwitness.packs.sim3d_inputs ks_t14slh`. No downloaded 3D models are used: the glass view and the Farm view (plots, crops, barn, trees, pond, fences, paths) are all procedural geometry, so there is no third-party model licence to credit.
