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
- France crop classes: every year 2015–2024 has `hcat:code`. It is null for 53,056 rows in 2023 and 60,765 rows in 2024 (~0.6 %; `crop:code` has no nulls), and `hcat:name_en` is null for 56 rows in 2015. **T1.6 must map the unmapped `crop:code` values** for those years.
- Added dependency `earthaccess` 0.19.0 (named in PLAN.md T0.2).
- Verified via CMR (no login): `HLSL30_VI` v`2.0` (`C3246892554-LPCLOUD`), `HLSS30_VI` v`2.0` (`C3246894861-LPCLOUD`), `ECO_L3T_JET` v`003` (`C4057232489-LPCLOUD`; v002 also live, so searches must pin the version). Details in `docs/api_notes.md`.
- Blocked: no netrc file found in `C:\Users\Amr 13_03` (neither `.netrc` nor `_netrc`). earthaccess on Windows reads `~/_netrc` by default (or `$NETRC`). Login + granule search not run yet.
