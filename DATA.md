# DATA.md — datasets, access and licences

Every external dataset FieldWitness reads, with its exact access path, licence and required attribution.
Status: Phase 0 (access checks). Entries are added as each source is verified (CLAUDE.md rule 2).

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
- Licence: EuroCrops repository **CC-BY-SA-4.0** (share-alike). Attribution (citation from the repository README): Schneider, M., Schelte, T., Schmitz, F. & Körner, M. (2023), "EuroCrops: The Largest Harmonized Open Crop Dataset Across the European Union" — HCAT3 taxonomy. **Licensing decision (user, 2026-11-04):** the derived HCAT class list lives in its own file, `docs/hcat_annual_arable.md`, under **CC-BY-SA-4.0**, separate from the code licence (chosen in T10.1). The code (`fieldwitness.data.hcat`) holds only the prefix rules and cites the HCAT3 table; it does not redistribute the table.

## Satellite data (T0.2, T0.3)

- HLS Vegetation Indices `HLSL30_VI` v2.0 and `HLSS30_VI` v2.0; HLS surface reflectance `HLSL30` v2.0 and `HLSS30` v2.0 (Fmask) —
  NASA LP DAAC, via earthaccess (CMR) and AppEEARS. NASA Earthdata data: no restrictions on use; cite the product DOIs (to be added in T10.1).
- ECOSTRESS `ECO_L3T_JET` v003 — NASA LP DAAC (verified in CMR; not yet read).

## Crop parameters and statistics (T0.6)

- **FAO-56** — Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56. HTML edition: Chapter 6 `https://www.fao.org/4/x0490e/x0490e0b.htm` (Tables 11, 12), Chapter 8 `https://www.fao.org/4/x0490e/x0490e0e.htm` (Tables 22, 24). Values copied into `config/crops.yaml` with table/row references (`scripts/extract_fao56.py`).
- **FAO-33** (Doorenbos & Kassam, 1979, *Yield response to water*) — not found on fao.org; its seasonal Ky values are used as reproduced in FAO-56 Table 24.
- **FAO-66** — Steduto, P., Hsiao, T.C., Fereres, E., Raes, D. (2012). *Crop yield response to water.* FAO Irrigation and Drainage Paper 66. `https://www.fao.org/4/i2800e/i2800e.pdf`, read with pypdf (dev dependency) on 2026-11-04: no Ky for barley or rapeseed (see `config/crops.yaml`); no values taken from it.
- **FAOSTAT QCL** — FAO. 2025 (last update 2025-12-31). FAOSTAT: Production — Crops and livestock products, bulk file `Production_Crops_Livestock_E_All_Data_(Normalized).zip` from `https://bulks-faostat.fao.org/production/`. Accessed 4 November 2026. Licence: **CC-BY-4.0** (FAO database terms of use). Used for the proposed Ukraine crop list (area harvested, national). The FAOSTAT API needs authentication and is not used.
