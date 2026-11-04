# CLAUDE.md — FieldWitness (NASA Space Apps 2026, "Field Shift")

Read this file and `PLAN.md` at the start of every session. `PLAN.md` is the source of truth for scope, order and acceptance tests. Log every decision that changes the plan in `DECISIONS.md`.

## What we are building

FieldWitness: a rotation decision-support web app for any field on Earth. Every recommendation is backed by three independent witnesses and becomes a falsifiable prediction that next season's satellite data scores.

- **Witness 1 — Physics:** FAO-56 root-zone water balance forced by NASA POWER weather.
- **Witness 2 — Own past:** the field's HLS 30 m history (2013→) calibrates the physics (ABC) and gives a credibility score.
- **Witness 3 — Neighbours:** natural experiments across similar fields (double ML on previous-crop effects).
- **Agreement engine** → grades A–D. **Rotation engine** → ranked options. **Prediction ledger** → hindcast and live scoring.

Deliverables: (1) a public static web app (no login, offline from precomputed field packs); (2) a public GitHub repo with the pipeline, tests and results.

## Hard rules (never break)

1. **Never fabricate.** No invented data, endpoints, parameter names, coefficients, results or citations. If you do not know, say so and mark it `UNVERIFIED` in code comments and `DECISIONS.md`.
2. **Verify every external API before using it.** Read the official docs or the installed package source. Make one small test call and record the real response shape in `docs/api_notes.md`.
3. **Every number shown to users carries a source tag:** `O` observed by satellite · `D` derived by a model from satellite data · `E` external non-NASA data · `A` assumption. No untagged values in field packs.
4. **Forbidden claims:** yield in tonnes, soil fertility measured from space, price or profit forecasts, any LLM making the decision. We use the Relative Yield Index (0–1) only.
5. **Scale contract:** coarse data (POWER, SMAP, SoilGrids) is context or forcing only. Field-level claims use HLS (30 m) or ECOSTRESS (70 m). Use interior pixels only. Raise a scale flag when pixel area > field area / 4.
6. **No leakage.** Every data access goes through the `as_of` date in `fieldwitness.data.asof`. In hindcast mode nothing dated after the cut-off may be read. Tests enforce this.
7. **Spatially blocked validation.** Train and test splits are separated by HLS tile or by ≥ 10 km blocks, never random field splits.
8. **Formulas cite their source** in the docstring (e.g. `FAO-56 Eq. 6`). Take constants and table values from the papers; do not recall them from memory. If you cannot open the paper, stop and ask.
9. **Report negative results.** If a test or validation fails, record it in `results/` and `DECISIONS.md`. Never tune on the test set or hide a failure.
10. **No secrets in the repo.** Earthdata credentials live in `%USERPROFILE%\_netrc` on Windows (the file earthaccess reads by default), or in environment variables. Never read or print that file. Run the secret scan before every commit.
11. **Ask before** downloading more than 1 GB, adding a dependency not listed in `PLAN.md`, or changing a schema in `PLAN.md §3`.
12. Never extract tokens or passwords from credential managers, keychains or config files. If an action needs authentication you don't already have through a configured tool, ask me.
    Exception: reading `_netrc` programmatically to authenticate to NASA Earthdata services (earthaccess, AppEEARS) is allowed, in memory only. Use only the `urs.earthdata.nasa.gov` entry, pass it only to the login call, never print, log or write the password or any returned token to disk, and log out (or let the token expire) when the task ends.

## Working agreement

- Work one task ID from `PLAN.md` at a time. Before coding a task, state the plan in ≤ 10 lines and wait for approval at the start of each phase.
- Done = the task's acceptance test passes, tests are green, and the checkbox in `PLAN.md` is ticked with a one-line note.
- Prefer the simplest method that passes its acceptance test. ML only where `PLAN.md` asks for it.
- Keep functions pure where possible and seed every random process (`SEED = 20261114`).
- Communicate with the user in clear, simple English. Code, comments, and docs are in English.
- At the end of each session, append a short entry to `DECISIONS.md`: what was done, what is blocked, and the next task ID.

## Environment

- Hardware: Dell Precision 7520, 16 GB RAM, CPU only (GPU unknown; do not assume CUDA).
- Python 3.12 (pinned with `uv python pin 3.12`; the system Python 3.15 is too new for geospatial wheels), managed with `uv`. Node 20+ for the app.
- OS: Windows. The user's home path contains a space (`C:\Users\Amr 13_03`); quote paths in every command.
- Earthdata credentials: `%USERPROFILE%\_netrc` (underscore, no extension), entry `machine urs.earthdata.nasa.gov`. Never read or print it.
- Commands:
  - `uv sync` — install
  - `uv run pytest -q` — tests
  - `uv run ruff check . && uv run ruff format --check .` — lint
  - `uv run python -m fieldwitness.cli <command>` — pipeline
  - `cd app && npm ci && npm run dev` — web app
  - `cd app && npm run build` — static build into `app/dist`

## Repo map

```
CLAUDE.md  PLAN.md  DECISIONS.md  DATA.md  AI_USE.md  LICENSE  README.md  pyproject.toml
config/            regions.yaml  crops.yaml  grading.yaml
src/fieldwitness/  asof · data/ · resolve/ · story/ · physics/ · infer/ · neighbours/ · agree/ · rotate/ · ledger/ · packs/ · api/ · cli.py
app/               React + Vite + TypeScript + MapLibre
tests/             unit + property + leakage tests
packs/             generated field packs (gitignored except demo packs)
results/           validation outputs (tables, figures, JSON)
docs/              api_notes.md, census/, official_challenge.md
```
