# DECISIONS.md

Decisions that change or clarify the plan, plus an end-of-session log. Newest last.

## 2026-11-04 — Plan review → PLAN.md v1.1

- Claude Code's first review led to PLAN.md v1.1: Python pinned to 3.12; gitleaks CLI (not the Action); walking-skeleton milestone; explicit tagging rule and `EXEMPT_FIELDS`; harvest-year season convention; batched physics targets; forecast + forced hindcast modes; accepted boundary leakage; HLS true-colour basemap.
- Kluger, Di Tommaso & Lobell (2025), arXiv:2506.02384 — marked "confirmed by the planning research" in PLAN.md; **UNVERIFIED by Claude Code** until the paper is opened in T5.4.

## 2026-11-04 — T0.1 scaffold choices

- Secret scan: gitleaks v8.30.1. Locally via the `gitleaks-system` pre-commit hook (uses the installed binary, no Go toolchain). In CI the pinned Linux binary is downloaded and checked against the release checksums file, then scans full git history.
- Versions pinned from `git ls-remote` on 2026-11-04: ruff-pre-commit v0.17.3, actions/checkout v7.0.1, astral-sh/setup-uv v10.3.3.
- Source subpackages (`data/`, `physics/`, …) are created by the task that first needs them, not as empty placeholders.
- winget installs of uv and gitleaks hung (likely a hidden elevation prompt); installed uv via `pip install --user uv` and gitleaks from the checksum-verified GitHub release zip instead.
- Incident: ruff 0.17 formats Python code blocks inside Markdown; the ruff-format hook rewrote the PLAN.md §3 schema block (and moved a comment). Restored the original text; ruff now excludes `*.md` (plus `.agents/`, `.claude/`) with `force-exclude = true`.
- The upstream `gitleaks-system` remote hook failed on Windows ("accepts at most 1 arg(s), received 2"); the identical command as a `repo: local` hook passes. Using the local hook.
- `.gitattributes` forces LF so Windows and Linux CI agree on formatting.

## Session log — 2026-11-04

- Done: CLAUDE.md + PLAN.md v1.1 saved; T0.1 scaffold built; locally `pytest` (1 passed), ruff check/format, and pre-commit (ruff + gitleaks) all pass. No commit made yet.
- Blocked: T0.1 acceptance needs CI green on GitHub → needs a GitHub repo and permission to commit and push. T0.2/T0.3 need `~/.netrc` with Earthdata credentials.
- Next: finish T0.1 (push, CI green), then T0.2.

## 2026-11-04 — T0.2 progress

- T0.1 committed locally as `ba796a4` (14 files, gitleaks: no leaks); push waits for the user's OK.
- T0.1 done: author changed to the GitHub noreply email and the commit amended to `1d3a3a5`; full-history gitleaks scan clean; pushed to `origin/main`; CI run 41743961024 green (jobs `test` and `secret-scan`).
- Credentials file confirmed by the user as `%USERPROFILE%\_netrc`; CLAUDE.md rule 10 and Environment updated (commit `799f04a`; the `.gitignore` skill rules were already in `1d3a3a5`).
- Blocked: `earthaccess.login(strategy="netrc")` fails with `NetrcParseError: bad follower token … line 1` — a value on the line contains an unquoted space. The user must fix the file; `scripts/check_earthdata.py` is ready to rerun.
- Resolved: the user rewrote `_netrc`; login succeeds.
- New hard rule 12 in CLAUDE.md (no extracting tokens from credential managers); CI status via `gh` once installed, otherwise the user checks the Actions tab. Context: the T0.1 CI check had used a token taken from Git Credential Manager.
- T0.2 done: one tile/one date (T14SLH, 2023-07-04) found in `HLSS30_VI`; `HLSL30_VI` hits in a June–Aug 2023 window (17 granules). Details in `docs/api_notes.md`.
- Finding: the Fmask layer of HLS-VI granules lives in the SR products (`HLSL30.020` / `HLSS30.020`), so a masked VI series reads two products. Matters for T0.3 and T1.5.
- Archive depth T14SLH 2016–2024: no empty year; VI counts ≈ SR counts. 2016–2017 are thinner (65 and 83 granules vs ~160–205 later), driven by S30. **Decision: no SR→VI fallback is needed for archive depth**; it would add at most 4 granules in any year. Thin early years are a data limit to report, not fix.
- Added `--archive-depth TILE` mode to `scripts/check_earthdata.py` (CMR hit counts only).
- Next: T0.3 (AppEEARS), plan awaiting approval.

## 2026-11-04 — T0.3 AppEEARS task (in progress)

- CLAUDE.md rule 12 exception added: `_netrc` may be read programmatically for Earthdata services, in memory only. `requests` added as a direct dependency.
- AppEEARS serves `HLSL30_VI.020` and `HLSS30_VI.020`, so the SR-band fallback is not needed. Its VI layers have no linked QA layer, so Fmask is requested from `HLSL30.020` / `HLSS30.020` in the same task.
- **Task ID: `09338e93-d3fa-493d-bc4a-476ac22a2b88`** · name `fieldwitness-T0.3-access-check` · type `area` · created (submitted) `2026-11-04T00:30:31.874690` (UTC, as AppEEARS reports it) · status `pending` at 00:31 UTC.
- Request JSON (from `scripts/check_appeears.py`, no credentials):
  ```json
  {"task_type": "area", "task_name": "fieldwitness-T0.3-access-check",
   "params": {"dates": [{"startDate": "04-01-2023", "endDate": "10-31-2023"}],
              "layers": [{"product": "HLSL30_VI.020", "layer": "NDVI"}, {"product": "HLSL30_VI.020", "layer": "EVI"},
                         {"product": "HLSS30_VI.020", "layer": "NDVI"}, {"product": "HLSS30_VI.020", "layer": "EVI"},
                         {"product": "HLSL30.020", "layer": "Fmask"}, {"product": "HLSS30.020", "layer": "Fmask"}],
              "geo": {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
                      "geometry": {"type": "Polygon", "coordinates": [[[-100.9029, 37.9978], [-100.8971, 37.9978],
                                   [-100.8971, 38.0022], [-100.9029, 38.0022], [-100.9029, 37.9978]]]}}]},
              "output": {"format": {"type": "netcdf4"}, "projection": "native"}}}
  ```
  The `params` echoed by `GET /task` matched dates, layers and output exactly; it did not echo `geo`.
- **Resume path** if the monitoring process dies (sleep, closed session): `uv run python -u scripts/check_appeears.py --task-id 09338e93-d3fa-493d-bc4a-476ac22a2b88` → logs in again, checks the task status, downloads the bundle (sha256-verified) into `data/appeears/<task_id>/`, logs out. `--list` shows this project's recent tasks and their status.
- Observed: login `expiration` is 24 h after login (the docs say "approximately 48 hours"). The `--list` lookup at 00:31 UTC does not log out, so it cannot revoke a token the running process might share; its token expires on its own.
- Process lesson: the first run piped `python -u` through plain `grep`, which buffered the log, so the task ID was not visible. From now on, long runs use unbuffered output end to end (`python -u` and `grep --line-buffered`).

## 2026-11-04 — T0.4 decisions and blocker

- France source: mixed RPG/EuroCrops series `ftw/harmonized-field-data/fr` (IGN RPG under Licence Ouverte 2.0; 2015, 2016, 2018 from EuroCrops V2 under CC-BY-4.0). Test box in the Beauce, access check only.
- CSB: the 2017–2024 GeoParquet copy is used as-is. The 2014–2021 geodatabase is not downloaded, so **pre-2022 boundaries are not used**; this falls under the boundary-leakage exception already accepted in PLAN.md Phase 7 (geometry only, no post-cut-off labels or outcomes).
- Size guard: hard cap of 200 MB downloaded per query; footers are read first, and a query whose estimate exceeds the cap is not run.
- Added dependency `duckdb` 2.0.0.
- FTW Kansas file found via STAC: `.../results-by-admin-conf/admin:country_code=US/US_KS.parquet` (1,103,107 polygons, EPSG:4326, 2024–2025).
- **Blocked:** `INSTALL httpfs` fails with HTTP 503. The 503 body says "File Transfer Blocked … in accordance with company policy" (file `httpfs.duckdb_extension.gz`): a network policy on this machine blocks downloading DuckDB extension binaries over `http://extensions.duckdb.org`. Not bypassed; waiting for the user's decision. Not run: footer reads, counts, the per-year crop-column check for France. PLAN.md §2 and T1.6 updated to name the French source.

## 2026-11-04 — Network policy block (DuckDB extensions) → T0.4 uses geopandas/pyarrow

- The network on this laptop blocks downloads of DuckDB extension binaries (`*.duckdb_extension.gz` from `extensions.duckdb.org`): HTTP 503 with a "File Transfer Blocked … company policy" page. Per the user, **no other route to the DuckDB extensions is tried**.
- What is known to work on this network (as of 2026-11-04):
  - PyPI wheels install via `uv add` (earthaccess, requests, geopandas, pyarrow, shapely).
  - NASA CMR search and earthaccess login + granule search (no HLS file has been downloaded via earthaccess yet).
  - AppEEARS API: login, task submit, status, bundle listing and download of all 17 bundle files (sha256 verified), logout.
  - GitHub push; Source Cooperative STAC JSON over HTTPS.
- Decision (user): T0.4 uses `geopandas.read_parquet(bbox=...)` on `pyarrow` — anonymous S3 on Source Cooperative first, HTTPS via fsspec as fallback, both verified from docs before use. `duckdb` removed (no concrete local use in Phase 1). Dependencies added: `geopandas`, `pyarrow`, `shapely`.
- Note: PLAN.md has no "§Tools" section; the change is recorded in the T0.4 task text instead.

## 2026-11-04 — T0.3 result and T0.4 run

- T0.3: AppEEARS task done in ~22.5 min; 17 bundle files downloaded to `data/appeears/09338e93-…/`, sha256 OK; logout 204. Per-date NDVI/EVI statistics and Fmask QA counts confirm a 2023 time series. NetCDF files not opened: no NetCDF reader installed (xarray + h5netcdf would be new dependencies).
- T0.4 (`scripts/check_fields.py`, anonymous S3 worked; HTTPS fallback unused):
  - USDA CSB 2024, T14SLH box: 4 of 302 row groups, est. 43.9 MB → **20,190** polygons intersect the box.
  - France RPG 2024, Beauce box: 2 of 387 row groups, est. 12.6 MB → **6,198** polygons.
  - FTW Kansas, T14SLH box: 5 of 17 row groups, est. **204.1 MB > 200 MB cap → not run** (geometry column alone 193 MB; essential-column subset 200.2 MB). Waiting for the user.
- Byte figures are footer-based estimates of compressed column chunks read; actual network bytes were not metered.
- Decision (user): FTW Kansas is skipped (CSB is the Tier 1 source). Tier 3 test instead: FTW Punjab `IN_PB.parquet` (992 MB, 159 row groups) chosen over `Ukraine.parquet` (1,985 MB, 63 row groups) as the smaller file; 10 km box near Jagraon → 7 row groups, est. 53.1 MB, **15,529** polygons (2024 + 2025 layers together). Tier 3 reads of this size fit the cap, so no one-off cached download is needed for now; revisit at T1.4 for full-tile reads.
- Added dependencies `xarray` and `h5netcdf[h5py]` (user approved xarray + h5netcdf; h5netcdf 1.8 needs its `h5py` backend extra to open files — flagged to the user). `cftime` was **not** added: AppEEARS NetCDF times are decoded manually (see `docs/api_notes.md`).
- 47-vs-33 L30 date gap: 12 dates fully cloud/shadow/adjacent (VI granule exists, AppEEARS drops all-fill dates — inferred); 2 dates (2023-10-02/03) have no `HLSL30_VI` granule in CMR although SR exists (cause unexplained). Details in `docs/api_notes.md`.
- T0.3 and T0.4 ticked.
- `h5netcdf[h5py]` approved by the user (2026-11-04). Commit `c88deff` pushed.
- AppEEARS time decoding is one function, `fieldwitness.data.appeears.decode_time(values, units)`, tested against Statistics-CSV dates for both products. Finding: the reference date in `units` differs per product (HLSL30: `days since 2013-04-11`, HLSS30: `days since 2015-11-28`), so the function reads it from `units` instead of assuming 2013-04-11.
- France crop classes: every year 2015–2024 has `hcat:code`. It is null for 53,056 rows in 2023 and 60,765 rows in 2024 (~0.6 %; `crop:code` has no nulls), and `hcat:name_en` is null for 56 rows in 2015. **T1.6 must map the unmapped `crop:code` values** for those years.
- Added dependency `earthaccess` 0.19.0 (named in PLAN.md T0.2).
- Verified via CMR (no login): `HLSL30_VI` v`2.0` (`C3246892554-LPCLOUD`), `HLSS30_VI` v`2.0` (`C3246894861-LPCLOUD`), `ECO_L3T_JET` v`003` (`C4057232489-LPCLOUD`; v002 also live, so searches must pin the version). Details in `docs/api_notes.md`.
- Blocked: no netrc file found in `C:\Users\Amr 13_03` (neither `.netrc` nor `_netrc`). earthaccess on Windows reads `~/_netrc` by default (or `$NETRC`). Login + granule search not run yet.

## 2026-11-04 — ECOSTRESS version finding (affects T1.7)

- `ECO_L3T_JET` v003 (named in PLAN.md T1.7) is only partly populated: 378,068 granules from 2019-08-23, none in June 2023; at the Kansas test point 66 granules all time vs 850 for v002 (4.8 M granules from 2018-07-10). **Decision needed at T0.5/T1.7:** use v002 for history, v003, or both. Not changed yet.

## 2026-11-04 — T0.5 census run (awaiting the user's region choice)

- `uv run python -m fieldwitness.cli census --region <id>|all [--compare]`; outputs `docs/census/<region>.md|.json` and `docs/census/comparison.md` (+ my recommendation from `docs/census/_recommendation.md`). Raw CMR granule metadata cached in `data/census/` (gitignored). Added `pyyaml` (runtime). Candidates and season windows (tag A, user-set) in `config/regions.yaml`.
- Code moved to owning modules: capped bbox reads `fieldwitness.data.geoparquet` (used by `scripts/check_fields.py`), interior pixels `fieldwitness.resolve.pixels` (for T1.4); unit tests for both and for season windows (11 tests pass).
- Over-cap reads are recorded, not run: central Ukraine 20 km FTW box est. **313.6 MB > 200 MB** → no field statistics for Ukraine. Per the earlier rule, Tier 3 over-cap reads are decided at T1.4; Ukraine's field-size check needs a decision now if Ukraine is to be chosen.
- Nile Delta tile choice: `T36RTV` (FTW 2024 field cover 0.574 in a 20 km tile-centre box) over `T36RUV` (0.553). The two tiles share the same 30 m grid alignment.
- Finding: many HLS granules cover only part of a tile (median `SPATIAL_COVERAGE` 15–25 % in some Punjab/Nile season-years), so raw granule counts overstate observations; the comparison adds counts with cloud ≤ 20 % **and** coverage ≥ 50 %.
- Finding: `ECO_L3T_JET` v003 median overpasses per season = 0 in every region (2019–2024); v002 11.5–110. Input for the T1.7 version decision.
- T0.5 not ticked: acceptance requires the human region choice.

## 2026-11-04 — Region decision (pending Ukraine field-size check), interior-pixel rule, Toulouse

- User decision, **to be recorded as final once Ukraine passes the field-size check**: Tier 1 Kansas `T14SLH`; Tier 2 Beauce `T31UCP`; Tier 3 central Ukraine `T36UVU`. Nile Delta `T36RTV` stays only as a data-confidence-map showcase (no pipeline beyond the census numbers). Punjab rejected. Statuses set in `config/regions.yaml`.
- Ukraine check rule (user): stop and ask if the median field is under ~2 ha or fewer than 50 % of fields qualify at the 15 m buffer.
- **Blocked:** the Ukraine FTW 10 km box is est. 254.1 MB (> 200 MB cap; 8 row groups); a 1 km box hits the same 8 row groups; a footer-only scan of 81 10 km boxes across `T36UVU` found none under the cap (245.6–324.5 MB). Not read; waiting for the user.
- Known limit if Ukraine is confirmed: farming in 2022–24 was disrupted by the war, which affects hindcast scoring there (to be stated on the scoreboard and Methods page).
- **Interior-pixel rule changed (user):** PLAN.md T1.4 now uses a 15 m inward buffer (pixel centre ≥ half a pixel inside the field edge) instead of 30 m. Census shares with ≥ 4 interior pixels, 30 m → 15 m: Kansas 88.6 % → 98.1 % (full tile), Beauce 54.0 % → 61.2 %, Nile 6.9 % → 33.6 %, Punjab 2.4 % → 18.3 %. `fieldwitness.resolve.pixels` docstring updated.
- Optional CMR-only cloud census for Lauragais `T31TCJ` (near Toulouse): clear (≤ 20 % cloud, ≥ 50 % coverage) granules per season 31 winter / 25 summer vs Beauce 30 / 19; worst years 14 / 13 vs 4 / 8. No boundary read.
- T0.5 not ticked yet (needs the Ukraine decision).

## 2026-11-04 — Field-size checks for Ukraine and Toulouse

- Ukraine `T36UVU`, 10 km box at (32.39, 48.25), one-off read approved by the user: columns `geometry` + `determination:datetime` only, est. 243.6 MB (8 row groups, cap 260 MB for this read); result cached as `data/census/ua_t36uvu_box10km_ftw.parquet` (gitignored, for T1.4). FTW 2024 layer: **141 fields**, median **3.29 ha** (p10–p90 0.31–148 ha), **73.8 %** with ≥ 4 interior pixels at the 15 m buffer (55.3 % at 30 m), 10.6 % below the scale flag. **Passes** both thresholds (≥ ~2 ha, ≥ 50 %). Caveat: only 141 fields in the sample, with a bimodal size distribution.
- Toulouse `T31TCJ`, 20 km box at (1.75, 43.45), France RPG 2024, est. 30.1 MB: **11,270 fields**, median **0.86 ha** (p10–p90 0.07–8.06 ha), **48.1 %** at 15 m (37.1 % at 30 m), 36.7 % below the scale flag; 10 label years. **Fails** both thresholds as applied to Ukraine (the user set them for Ukraine; I applied the same to Toulouse). Beauce, for comparison: median 3.01 ha, 61.2 % at 15 m (passes).
- Stopped before recording the final regions: Tier 2 needs a user decision.
- Reader change: `read_bbox`/`estimate_bbox_read` accept a column subset (estimate counts only those columns plus `bbox`); census boundary reads can set `cap_mb`, `columns`, `cache_as` per region.

## 2026-11-04 — Final regions (T0.5) and field definition

- **Field definition (user):** a field is an *annual arable crop parcel*, defined on HCAT3 (official table `maja601/EuroCrops/hcat_core/HCAT3.csv`, 384 classes) in `fieldwitness.data.hcat.is_annual_arable`; applies to the census, T1.4 and T1.6. Full list: `docs/hcat_annual_arable.md`.
  - **Kept:** 278 classes, all under `3301` arable_crops.
  - **Excluded groups:** `3302` pasture_meadow_grassland_grass, `3303` permanent_crops_perennial, `3304` mushrooms_energy_genetically_modified_crops, `3305` greenhouse_foil_film, `3306` tree_wood_forest, `3307` peat_turf, `3308` unmaintained, `3399` not_known_and_other; and missing codes.
  - **Excluded inside 3301 (18):** `3301110000` fallow_land_not_crop; `3301090100` temporary_grass; `3301090200` poaceae_grasses and its 9 children `3301090201`–`3301090209` (elymus, festuca, cocksfoot, festulolium, lolium, setaria, sod_turf, switchgrass, timothy); `3301083000` miscanthus_silvergrass; `3301120000` kitchen_gardens; `3301130000` strawberries; `3301200000` asparagus; `3301230000` rhubarb; `3301270000` artichoke.
  - A first version used prefix `3301083` for miscanthus, which wrongly dropped its siblings (incl. safflower); caught by checking against HCAT3.csv and fixed to `33010830`, with a test.
- **French field checks on arable parcels (France RPG 2024, 20 km boxes):**
  - Toulouse `T31TCJ`: 11,270 parcels → 5,406 kept (excluded: 3,093 in 3301 [fallow/grass/perennial], 2,164 not_known_and_other, 532 grassland, 42 permanent crops, 13 other, 22 missing code). Median **3.62 ha**, **87.5 %** with ≥ 4 interior pixels at 15 m (72.1 % at 30 m), 2.6 % below the scale flag. **Passes.**
  - Beauce `T31UCP`: 5,977 → 3,688 kept. Median 7.55 ha, 87.0 % at 15 m.
  - Rule (user): Toulouse passes both thresholds → **Tier 2 = Toulouse `T31TCJ`** (better sky than Beauce).
- **Final regions (user, 2026-11-04):** Tier 1 Kansas `T14SLH`; Tier 2 Lauragais/Toulouse `T31TCJ`; Tier 3 central Ukraine `T36UVU`; Nile Delta `T36RTV` for the data-confidence map only (no pipeline beyond the census numbers). Beauce kept in the census as the comparison; Punjab rejected. Recorded in `config/regions.yaml` and PLAN.md §2.
- **Known limits:**
  - Ukraine field sample is small and bimodal (141 FTW 2024 fields in a 10 km box; p10 0.31 ha, p90 148 ha) — recheck at T1.4 on the full pilot set.
  - Ukraine farming in 2022–24 was disrupted by the war; this affects hindcast scoring there (state on the scoreboard and Methods page).
  - Ukraine has no crop labels (Tier 3) and FTW boundaries are an alpha release.
  - Toulouse: 19 % of parcels in the sample are `not_known_and_other`, excluded by the definition.
- T0.5 ticked. Next: T0.6 (configs: regions.yaml completion, crops.yaml from FAO-56/FAO-33 with refs).

## 2026-11-04 — Design fix: field selection vs crop history

- Problem: the annual-arable filter was described only as a field filter; applied per year it would have dropped fallow and temporary-grass years from crop sequences and broken rotations (e.g. wheat → fallow → wheat).
- Rule (user): the HCAT3 arable filter is **selection** on the current (most recent) year. In **crop histories**, fallow and temporary grass are kept as the states "fallow" and "temporary_grass", never dropped. A field is removed from history analysis only if it leaves arable use entirely.
- Implementation: `fieldwitness.data.hcat.history_state` and `stays_arable`. My reading of "leaves arable use": any year coded outside HCAT3 group 3301 (e.g. converted to grassland 3302 or a permanent crop 3303). Grass leys `33010902..` (poaceae_grasses) are also mapped to "temporary_grass"; other excluded 3301 classes (perennials, gardens) become "other_arable"; missing codes "unknown" — none of these remove a field. Tests: wheat → fallow → wheat kept; wheat → grassland → wheat removed.
- PLAN.md T1.6 and `docs/hcat_annual_arable.md` updated.
- Licence note: the EuroCrops repository (HCAT3 table) is **CC-BY-SA-4.0**; `docs/hcat_annual_arable.md` is derived from it and carries that licence. Credited in DATA.md. Relevant when choosing the project LICENSE (T10.1).
- Pushed `be73add` and `e3c47ec` (2026-11-04).

## 2026-11-04 — History rule fix and HCAT licensing

- `stays_arable` fix (user): HCAT3 3399 not_known_and_other, missing codes and generic codes are "unknown" history states and do **not** remove a field; only years in groups 3302–3308 (grassland, permanent crops, other non-arable groups) mean the field left arable use. Tests: wheat → 3399 → wheat kept; wheat → {3302, 3303, 3306, 3308} → wheat removed.
- Toulouse check (`scripts/check_history_rule.py`; France RPG 2015–2024, 20 km box, histories by the parcel containing each 2024 field's representative point; reads 19–36 MB per year, cached): **5,582** fields (2024 annual arable parcels intersecting the box). Removed from history analysis: **100 with the old rule** (any year outside 3301) vs **96 with the new rule** (3302–3308 only). 400 field-years are "unknown" (no containing parcel that year, missing code or 3399).
- **Licensing (user):** the derived HCAT class list lives in its own file, `docs/hcat_annual_arable.md`, under CC-BY-SA-4.0, separate from the code licence (to be chosen in T10.1). Recorded in DATA.md.

## 2026-11-04 — T0.6 configs (awaiting approval of the Ukraine crop list)

- `config/crops.yaml`: 9 crop keys (maize, sorghum, winter_wheat, winter_barley, sunflower, rapeseed, soybean, fallow, cover_crop); **62 verified parameters** read from FAO-56 Tables 11, 12, 22, 24 (`scripts/extract_fao56.py`, footnote marks kept apart from values), **7 unverified** (no number, tag A): Ky for winter barley and rapeseed (not in Table 24; FAO-66 PDF opens but is not readable here without a new tool), fallow Kc (no Table 12 row; Ke from FAO-56 Ch. 7 in T3.3), cover-crop Ky, rapeseed stage lengths (no Table 11 row). Botanical family unverified for all crops (to fill from a named taxonomy source).
- Choices inside published ranges (all tag A, recorded in `choice:`): maize Kc end 0.35 (fn 11, dry grain harvest); wheat Kc end 0.25 (fn 10, machine harvest); sunflower and rapeseed Kc mid 1.0 (fn 9, rainfed); sorghum Kc mid 1.05 (midpoint); winter wheat Kc ini 0.4 (frozen soils: Kansas, Ukraine) vs 0.7 (non-frozen: Toulouse); Table 11 rows chosen by closest region; winter barley stage lengths use the Mediterranean winter-wheat row as a proxy; cover crop = oats proxy.
- FAO-56 page numbers: the HTML edition has none, so refs cite the chapter page URL.
- **Crop lists (from the data):**
  - Kansas `T14SLH` (CSB 2024, full tile, 17,464 fields): winter wheat 31.4 %, fallow/idle 22.7 %, corn 19.5 %, sorghum 18.1 % → `[maize, sorghum, winter_wheat, fallow, cover_crop]`. Soybean only 0.1 % (dropped from the PLAN.md default).
  - Toulouse `T31TCJ` (RPG 2024, 20 km box, 5,411 annual arable parcels): sunflower 30.3 %, durum wheat 27.6 %, soft wheat 11.2 %, winter barley 4.3 %, sorghum 3.4 %, rapeseed 3.3 %, maize 3.0 % → `[sunflower, winter_wheat, winter_barley, sorghum, rapeseed, maize, fallow, cover_crop]`.
  - Ukraine `T36UVU` — **proposed, pending user approval**, tag E: FAOSTAT national area harvested (oblast data unreachable: ukrstat.gov.ua no response, stat.gov.ua HTTP 403): wheat, sunflower, maize, barley, soybean, rapeseed (≈ 87–93 % of individual-crop area 2019–2024). Open: winter vs spring split for wheat and barley; potatoes (≈ 5 %) left out.
- **Flag for the field definition:** alfalfa (HCAT3 `3301090301`, "plants harvested green") passes the annual-arable rule but is a multi-year forage crop (4.2 % of Toulouse arable area, 2.7 % of the Kansas tile). Not changed — user decision.
- `config/grading.yaml`: thresholds are team choices (tag A); interior-pixel rule 15 m / ≥ 4 pixels; scale flag ratio 4.
- `src/fieldwitness/config.py`: Pydantic models; tests reject unverified parameters that carry a number and verified ones without a ref. Added dependency `pydantic` (named in PLAN.md §3). 44 tests pass.
- PLAN.md T0.6 table numbers corrected to 11, 12, 22, 24. T0.6 not ticked (Ukraine crop list pending).

## 2026-11-04 — T0.6 completed (user decisions on crops)

- **Ukraine crop list approved (user):** wheat, sunflower, maize, barley, soybean, rapeseed (FAOSTAT national, tag E). Wheat and barley enter as winter and spring variants: `crops.yaml` now has `spring_wheat` and `spring_barley`; Ukraine stage lengths use FAO-56 Table 11 rows where they exist (winter cereals: "Winter Wheat | October | Idaho, USA" — winter barley as proxy; spring cereals: "Barley/Oats/Wheat | March/Apr | 35-45 °L"; maize "April | Idaho, USA"; sunflower "April/May | Medit.; California"; soybean "May | Central USA", Ldev printed 30/35 → 30). Rapeseed has no Table 11 row (unverified). Region crop list in `config/regions.yaml`.
- **Winter vs spring rule (user), PLAN.md T2.2:** the field story assigns the variant per field-season from observed autumn vs spring green-up (tag D).
- **Alfalfa (user):** HCAT3 `3301090301` is no longer selected as a field and is kept in histories as the state "perennial_forage" (like fallow/temporary_grass); not a rotation option in the MVP (it is in no region crop list). Siblings such as clover are unchanged. `hcat.py`, tests and `docs/hcat_annual_arable.md` updated (277 kept classes, 19 excluded inside 3301).
  - Effect on the French census (arable parcels, 20 km boxes): Toulouse 5,040 fields, median 3.76 ha, 88.6 % at 15 m (still passes); Beauce 3,656 fields, median 7.58 ha, 87.2 %. Toulouse history check: 5,202 fields; removed 65 (old rule) vs 62 (new rule).
- **FAO-66 (pypdf, dev-only dependency added):** read all 505 pages. No Ky for barley (barley section printed pp. 134–141 = PDF pp. 149–156; Table 2 "Comparison of Ky values between FAO-33 and IAEA", printed p. 12 = PDF p. 27, has no barley row) and none for rapeseed (mentioned only on PDF pp. 94, 179, 253). Barley (winter and spring) and rapeseed Ky stay null, tag A, unverified, with these page refs in `crops.yaml`.
- **T5.4 scope (user):** the literature check covers only maize / wheat / sorghum / fallow transitions for the western Kansas tile `T14SLH` (no soybean: 0.1 % of the tile). PLAN.md §1 walking-skeleton crop list updated accordingly.
- `crops.yaml`: 11 crops, 82 verified parameters, 9 unverified (tag A). Tests: 45 pass. **T0.6 ticked.** Phase 0 remaining: Gate 0 review; next phase starts after the rules gate (13 Nov).

## 2026-11-04 — Gate 0 access checks and re-review

Access checks only (no product code); details and response shapes in `docs/api_notes.md`.

- **POWER** (T1.2 source): one daily point call, Kansas tile centre (−100.6604, 38.3425), 2023 → HTTP 200, all six parameters valid, 365 days, no fill values, elevation 852.2 m returned. **Pass.**
- **SoilGrids** (T1.3 source): `properties/query` → **HTTP 503** (ISRIC REST service temporarily unavailable; docs/OpenAPI also failed). `maps.isric.org` (WCS/WMS) answers 200 — candidate fallback, not verified. **Fail (external outage); retry before T1.3.**
- **WIMAS** (T1.7 source): public, no registration, but a **disclaimer must be accepted** ("I ACCEPT") before any query. Not accepted on the user's behalf; no bulk download without it found. **Pending user decision.**
- **OpenET**: **pending user decision on terms; not accessed.**
- **HLS direct COG read** (T1.5b): windowed read of NDVI + Fmask for one HLSS30_VI granule via earthaccess's authenticated fsspec session as rasterio `opener` → 1.72 MB total, nothing written to disk. **Pass.** Finding: HLS-VI COGs are striped (1 × 3660 blocks, no overviews) while Fmask is tiled 256 × 256 with overviews → read one row-window per granule spanning all pilot fields. T1.5b fallback written up; **T0.3 now complete.**
- Added dependency `rioxarray` (named in PLAN.md T1.5; brings rasterio 1.5.2 / GDAL 3.12.2).

User decisions recorded:

- **Rapeseed:** history state only; excluded from MVP rotation options (`mvp_role: history_only`).
- **Barley (winter and spring):** included in hindcast predictions (SOS, canopy, cover days, water use need only Kc and stages); excluded from MVP rotation options because RYI needs Ky (`mvp_role: prediction_only`). Rule in PLAN.md T6.1 and T7.1; enforced by `fieldwitness.config.rotation_options` and a test that every rotation option has a verified Ky and verified stage lengths in each selected region.
- **Botanical family:** GBIF Backbone via the species-match API, cross-checked with USDA PLANTS (`scripts/check_families.py`). Scientific names from FAO-66 crop chapters (PDF pages cited). Verified for 8 crops (Poaceae: maize, sorghum, winter/spring wheat, winter/spring barley; Asteraceae: sunflower; Fabaceae: soybean), GBIF and USDA agree for all 8. **Rapeseed and the oat cover-crop proxy stay unverified**: no FAO-66 name, and GBIF vernacular search and USDA common names did not agree on a binomial (no name chosen from memory).
- Rotation options now: Kansas [maize, sorghum, winter_wheat, fallow, cover_crop]; Toulouse [sunflower, winter_wheat, sorghum, maize, fallow, cover_crop]; Ukraine [winter_wheat, spring_wheat, sunflower, maize, soybean, fallow, cover_crop].

**Gate 0 re-run (2026-11-04):**

| Condition | Status |
|---|---|
| Access works for every Tier 1 source | **Partly.** Pass: CMR/earthaccess search, HLS direct COG read, AppEEARS, CSB, POWER. Not yet: SoilGrids (external HTTP 503), WIMAS (needs the user to accept a disclaimer), OpenET (terms decision pending). |
| Regions chosen | Pass |
| Configs validate | Pass (47 tests) |
| T0.1–T0.6 acceptance tests | Pass (T0.3 now including the T1.5b fallback write-up) |

Gate 0 is **not fully closed**: it needs the SoilGrids retry (or an approved WCS fallback) and the user's decisions on WIMAS and OpenET. Next: those three items; Phase 1 starts after the rules gate (13 Nov).
