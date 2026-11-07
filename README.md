<!-- DRAFT (moved from docs/drafts/ at the Gate 6 merge, 2026-11-07). Before release:
     - fill the deployed URL (not deployed yet) and add screenshots from real packs;
     - re-check every number against results/ on main (numbers below: packs/ks_t14slh/hindcast.json, 7 Nov);
     - remove the "Known issues" items that main has fixed. -->

# FieldWitness

**Crop-rotation decision support for a field, with three independent witnesses behind every
option.** It was built for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting
Farms with NASA Data".

FieldWitness does not decide for the farmer. It shows evidence, says how strong that evidence is,
and turns each recommendation into a prediction that next season's satellite data can check.

- **Live app:** _not deployed yet_
- **Region in this release:** Kansas, USA (HLS tile T14SLH), 200 pilot fields. Two further regions
  (France T31TCJ, Ukraine T36UVU) are planned but not built.

## What it shows

For each field:

- **Field story.** The field's seasons since 2013, from 30 m Harmonized Landsat Sentinel-2 (HLS)
  vegetation index, with each season's green-up, peak and end.
- **Rotation options.** The current rotation plus 3-season alternatives. Each option shows water
  use, bad-year water use, ground cover, Relative Yield Index (0–1, no tonnes), erosion and other
  priority measures, and an A–D evidence grade. You can move priority sliders, set constraints
  ("crops I can't plant", irrigation, water cap) and run weather what-ifs (temperature and rainfall
  shifts on past weather; not climate projections).
- **Calendar.** Months when the field is bare (observed, and simulated per option), and months when
  each crop is vulnerable to heat, frost, water stress and extreme rain.
- **Advisor console.** Credibility of the physics for this field, what to measure next, the
  smallest change that would flip the top option, and a back-test of past predictions.
- **Map layers and scoreboard.** Fields coloured by erosion, water stress or frost share. Regional
  GRACE water-storage and SMAP soil-moisture layers. A hindcast scoreboard against simpler
  baselines.

Every number carries a source tag:
- **O:** observed by satellite;
- **D:** derived by a model from satellite data;
- **E:** external non-NASA data;
- **A:** assumption.

## The three witnesses

1. **Physics:** an FAO-56 root-zone water balance driven by NASA POWER daily weather.
2. **The field's own past:** its HLS history calibrates the physics (approximate Bayesian
   computation) and gives a credibility score.
3. **Neighbours:** natural experiments across similar fields, using double machine learning on
   previous-crop effects. **Not available in this release** (T5.2 open), so no option reaches grade A.

An agreement engine turns the witnesses into grades A–D. A rotation engine ranks the options.
A prediction ledger stores every forecast so it can be scored later.

## Results (Kansas hindcast, honest version)

All data was frozen on 31 Dec 2021. We predicted the 2022–2024 seasons of 266 labelled
maize and sorghum field-seasons, then scored them against what HLS observed. Forecast mode used
past weather only.

| Measure | FieldWitness CRPS | Best baseline CRPS | Inside 90 % range (FieldWitness) |
|---|---|---|---|
| Green-up date | 19.3 | 20.7 (B0, field mean) | 52 % |
| Peak date | 11.5 | 12.7 (B2, uncalibrated physics) | 89 % |
| Season greenness total | 14.9 | 15.1 (B0) | 35 % |
| Ground cover days | 30.4 | 25.3 (B0, better than FieldWitness) | 9 % |

What this means:
- FieldWitness has the lowest CRPS on three of four measures, but the margins are small.
- Its uncertainty ranges are too narrow for green-up, greenness and cover days: they should hold
  90 % of seasons.
- The neighbour-only baseline B3 was not run.
- These are weak results, and we report them as they are (`results/hindcast/`).

## Known issues

- The season detector missed its pre-registered target: 78 % against a 90 % target (T2.2,
  `results/story/`).
- Only maize and sorghum have calibrated physics. Winter wheat fields cannot get a credibility score.
- Some dataset licences are still to be confirmed (see `DATA.md`).

## Run it

Requirements:
- Python 3.12 managed with `uv`;
- Node 20.19+ or 22.12+;
- NASA Earthdata login in `~/_netrc` (Windows) or `~/.netrc`, for the pipeline only.

```
uv sync
uv run pytest -q
uv run python -m fieldwitness.cli build-packs --region ks_t14slh   # writes packs/ks_t14slh

cd app
npm ci
node scripts/sync-packs.mjs ../packs     # copy packs for the app
npm run dev                              # dev server (SYNTHETIC demo data by default)
npm run build                            # static build into app/dist, real packs only
```

The app runs offline from precomputed packs, with no login and no server. See `app/README.md`
and `app/deploy/README.md`.

## Repository

- `src/fieldwitness/`: pipeline (data access with an `as_of` leakage guard, field story, physics,
  inference, neighbours, grading, rotation, ledger, packs).
- `app/`: React + Vite + TypeScript + MapLibre web app.
- `results/`: validation outputs, including negative results.
- `PLAN.md`, `DECISIONS.md`, `DATA.md`, `AI_USE.md`: plan, decision log, datasets and licences, AI use.

## Not claimed

FieldWitness does not give yields in tonnes, prices or profits. It does not measure soil fertility
from space. It does not let a language model make the decision. It supports local expertise and
does not replace it.

## Licence

_To be added (MIT or Apache-2.0, PLAN T10.1)._ Data licences: `DATA.md`.
