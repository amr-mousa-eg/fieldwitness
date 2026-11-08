# DATA.md — datasets, access and licences

Every external dataset FieldWitness reads, with its exact access path, licence and required attribution.

## Field boundaries and crop labels (T0.4)

All three are GeoParquet 1.1 files with a per-feature `bbox` covering column, hosted on Source Cooperative.
Read path: anonymous S3 (`endpoint_override="data.source.coop"`, bucket `ftw`) or HTTPS `https://data.source.coop/<key>`.
Only the row groups whose `bbox` statistics intersect the query box are read (see `scripts/check_fields.py`).

### Fields of the World — global field-boundary predictions (alpha)

- Punjab file (Tier 3 candidate): `https://data.source.coop/ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=IN/IN_PB.parquet`
  (10,396,804 polygons over the 2024 and 2025 layers; CRS OGC:CRS84; 159 row groups, 992 MB).
- Kansas file (not used: CSB is the Tier 1 source): `.../admin:country_code=US/US_KS.parquet` (1,103,107 polygons; 17 row groups, 531 MB).
- Other countries: `.../results-by-admin-conf/admin:country_code=<CC>/...`; find files via the STAC catalogue
  `https://data.source.coop/ftw/global-data/predictions/vectors/collection.json`.
- Licence: **CC-BY-4.0**. Attribution: Fields of the World / Taylor Geospatial (polygons from the PRUE model on Sentinel-2).
- Caveat (from the README): a "field" is a predicted remote-sensing field unit, not a cadastral parcel; alpha release.

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
- **NASA GIBS HLS True-Colour Basemap (T9.1 / P0.1)**:
  - Source: NASA Global Imagery Browse Services (GIBS) / LP DAAC, part of NASA EOSDIS.
  - Layer: `HLS_S30_Nadir_BRDF_Adjusted_Reflectance` (Sentinel-2 MSI true-colour RGB: Red B04, Green B03, Blue B02).
  - Spatial resolution: ~30 m native resolution (WMTS `GoogleMapsCompatible_Level12`, ~29.8 m/pixel at 38°N).
  - Date of imagery: 2023-07-04 (summer peak vegetation growth, 99.88% clear observation across Kansas tile T14SLH).
  - Endpoint: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/2023-07-04/GoogleMapsCompatible_Level12/{z}/{y}/{x}.png` (EPSG:3857). Offline/error behavior: falls back to neutral background.
  - Required attribution: "Imagery: NASA GIBS / LP DAAC (HLS S30, 2023-07-04)".
  - Licence: NASA Earth Science Data Policy (open and free for all users).
- **ECOSTRESS** `ECO_L3T_JET` v003 — NASA LP DAAC (verified in CMR; access verified for future extensions).

## Crop parameters and statistics (T0.6)

- **FAO-56** — Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56. HTML edition: Chapter 6 `https://www.fao.org/4/x0490e/x0490e0b.htm` (Tables 11, 12), Chapter 8 `https://www.fao.org/4/x0490e/x0490e0e.htm` (Tables 22, 24). Values copied into `config/crops.yaml` with table/row references (`scripts/extract_fao56.py`).
- **FAO-33** (Doorenbos & Kassam, 1979, *Yield response to water*) — seasonal Ky values as reproduced in FAO-56 Table 24.
- **FAO-66** — Steduto, P., Hsiao, T.C., Fereres, E., Raes, D. (2012). *Crop yield response to water.* FAO Irrigation and Drainage Paper 66.
- **FAOSTAT QCL** — FAO. (2025). FAOSTAT: Production — Crops and livestock products, `Production_Crops_Livestock_E_All_Data_(Normalized).zip`. Accessed 4 November 2026. Licence: **CC-BY-4.0** (FAO database terms of use).

## Weather, soil, water use and taxonomy (Gate 0 access checks)

- **NASA POWER** daily point API, community AG: `https://power.larc.nasa.gov/api/temporal/daily/point` (parameters T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR).
  - Citation: Sparks, A. H. (2018). nasapower: A NASA POWER Global Meteorology, Surface Solar Energy and Climatology Data Client for R. *Journal of Open Source Software*, 3(30), 1035. https://doi.org/10.21105/joss.01035
  - Terms: NASA Open Data Policy (public domain, free reuse with attribution).
- **ISRIC SoilGrids 2.0** — WCS `https://maps.isric.org/mapserv?map=/map/<property>.map`.
  - Licence: **CC-BY 4.0** (ISRIC data policy v2024-1).
  - Citation: Poggio, L., de Sousa, L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. *SOIL*, 7(1), 217–240. https://doi.org/10.5194/soil-7-217-2021
- **Kansas WIMAS** (Kansas Geological Survey / Kansas Department of Agriculture, Division of Water Resources): `https://geohydro.kgs.ku.edu/geohydro/wimas/`; requires accepting disclaimer; optional truth comparison.
- **OpenET**: not used; stretch S6 (2026-11-04), terms unread; not accessed in MVP.
- **GBIF Backbone Taxonomy** via `https://api.gbif.org/v1/species/match`:
  - Citation: GBIF Secretariat (2023). GBIF Backbone Taxonomy. Checklist dataset https://doi.org/10.15468/39omei. CC-BY 4.0.
- **USDA NRCS PLANTS Database** via `https://plantsservices.sc.egov.usda.gov/api/`:
  - Citation: USDA, NRCS. (2024). The PLANTS Database (http://plants.usda.gov). National Plant Data Team, Greensboro, NC USA. Public domain.
- **NASADEM** (`NASADEM_HGT` v001, NASA LP DAAC) — slope per pilot field:
  - DOI: https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001
  - Citation: NASA JPL (2020). NASADEM Merged DEM Global 1 arc second V001. NASA EOSDIS Land Processes DAAC.
  - Licence: NASA Open Data Policy.
- **GRACE/GRACE-FO JPL mascons** (`TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`, PO.DAAC) — regional water-storage series:
  - Citations: Watkins et al. (2015), *J. Geophys. Res. Solid Earth*, 120, 2648–2671; Wiese et al. (2016), *Water Resour. Res.*, 52, 7400–7416.
  - Licence: NASA Open Data Policy.
- **SMAP L4** (`SPL4SMGP` v008, NSIDC via AppEEARS) — regional root-zone soil moisture context:
  - DOI: https://doi.org/10.5067/T5RUATAQREF8
  - Citation: Reichle, R., De Lannoy, G., Koster, R. D., et al. (2018). SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root-Zone Soil Moisture Geophysical Data, Version 8. NASA NSIDC DAAC.
  - Licence: NASA Open Data Policy.
