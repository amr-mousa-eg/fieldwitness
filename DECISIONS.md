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
- Added dependency `earthaccess` 0.19.0 (named in PLAN.md T0.2).
- Verified via CMR (no login): `HLSL30_VI` v`2.0` (`C3246892554-LPCLOUD`), `HLSS30_VI` v`2.0` (`C3246894861-LPCLOUD`), `ECO_L3T_JET` v`003` (`C4057232489-LPCLOUD`; v002 also live, so searches must pin the version). Details in `docs/api_notes.md`.
- Blocked: no netrc file found in `C:\Users\Amr 13_03` (neither `.netrc` nor `_netrc`). earthaccess on Windows reads `~/_netrc` by default (or `$NETRC`). Login + granule search not run yet.
