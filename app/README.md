# FieldWitness web app (Phase 9)

React + Vite + TypeScript. Built on the `app` branch against **SYNTHETIC** fixtures until the
pipeline produces real packs (Gate 6); then the branch merges into `main` and switches to real packs.

## Run

```
cd app
npm ci            # after the first install (see "Dependencies")
npm run dev       # dev server, SYNTHETIC demo data, red "DEMO DATA" banner
npm test          # build-guard tests
npm run build     # production build into app/dist (real packs only)
```

## Data

- The app fetches `/packs/regions.json`, `/packs/<region>/index.json`, `<field_id>.json`, and the
  proposed `.series` / `.calendar` / `.scenarios` / `layers` / `hindcast` files
  (`docs/schema_ext_proposal.md`).
- **Fixtures:** `app/fixtures/**/*.SYNTHETIC.json`, written by
  `uv run python scripts/make_synthetic_fixtures.py` (seeded, validated against
  `scripts/fixture_schemas.py`, every number tagged, every `source` = `SYNTHETIC:fixture@0.1`).
  The dev server maps `/packs/<path>.json` to `fixtures/<path>.SYNTHETIC.json`.
- **Build guard** (`vite.config.ts`, tested in `tests/build-guard.test.ts`): a build refuses
  `VITE_DATA=fixtures`, and fails if any `*.SYNTHETIC.json` file or the `SYNTHETIC:fixture` marker
  ends up in the output.
- Types: `src/types.ts` is a hand-written mirror of PLAN.md §3 + the PROPOSED extension; T8.2
  replaces it with generated types at merge.

## Branch notes (copy into DECISIONS.md at merge)

- 2026-11-04 (user): Track 2 on worktree `D:\NASA Project-app`, branch `app`; only `app/`, the
  fixture scripts and `docs/schema_ext_proposal.md` change here. No merge before Gate 6.
- 2026-11-04 (user): missing data goes into per-field `.series`, `.calendar`, `.scenarios` files
  and a per-region `layers.json`; PROPOSED types in the app; the §3 extension is a proposal until
  approved.
- 2026-11-04 (user): approved packages react, react-dom, @types/react, @types/react-dom, vite,
  @vitejs/plugin-react, vitest (MIT), typescript (Apache-2.0); Recharts (MIT) later for charts.
  The user runs `npm install` personally.
- 2026-11-04 (user): §3 extension answers Q1–Q7 approved (`docs/schema_ext_proposal.md` §5):
  harvest-year day for SOS/peak/EOS; no marks in `series`; six exempt fields; `bare_by_option`;
  map colouring = Current only (alternative = stretch item); scenarios hold weather-sensitive
  metrics only; `packs/regions.json`.
- Dev server: run from `app/` (`npm run dev`). `npm --prefix "<path with space>"` fails on this
  machine (cmd splits `C:\Users\Amr 13_03`).

## Browser checks (local Chrome, no extra packages)

```
node scripts/screenshot.mjs http://localhost:5173/ '.map[data-state="ready"]' map.png 1280 800 light
node scripts/keyboard-check.mjs http://localhost:5173/
npm run build && npx vite preview --port 5180   # then:
node scripts/offline-check.mjs http://localhost:5180/ offline.png
```

`screenshot.mjs` waits for a selector (e.g. the map's `data-state="ready"` marker), prints console
errors, and emulates the exact viewport (so `380 800` is a real 380 px phone width). An optional 7th
argument is JS run in the page first, e.g. `'document.querySelector(".explain-btn").click()'`.
`keyboard-check.mjs` drives the app at 380 px with real Tab / Enter / Escape key events (skip link,
field list, focus on page change, field tabs, explainers, option details, no page overflow; T9.7).
`offline-check.mjs` visits once, goes offline, reloads and checks the app shell renders (T9.1).
Set `CHROME=<path>` if Chrome is not in the default Windows location.

## Views (Phase 9, on SYNTHETIC fixtures)

- Header nav: Map (T9.1, T9.11 layers), Scoreboard (T9.5), Methods & data (T9.6).
- Field tabs: Field story (T9.2), Options (T9.3), Calendar (T9.9), Advisor console (T9.4).
- Explainers (T9.10): text and cited sources in `src/strings/en.json` (`explain.<id>.*`).
- Accessibility (T9.7): skip link; focus moves to `<main>` on page change; colour always has a
  text twin (values printed in lists, tables and legends; marker shapes differ in charts).
