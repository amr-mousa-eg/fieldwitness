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
