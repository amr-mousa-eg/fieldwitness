# FieldWitness

**Crop-rotation decision support for a field, with three independent witnesses behind every
option.** Built for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting
Farms with NASA Data".

FieldWitness does not decide for the farmer. It shows evidence, says how strong that evidence is,
and turns each recommendation into a prediction that next season's satellite data can check.

- **Live application:** https://amr-mousa-eg.github.io/fieldwitness/
- **Region in this release:** Kansas, USA (HLS tile T14SLH), 200 pilot fields. Two further regions
  (France T31TCJ, Ukraine T36UVU) are planned in the multi-region architecture.
- **Repository:** https://github.com/amr-mousa-eg/fieldwitness

## What it shows

For each field:

- **Field story.** The field's seasons since 2015, from 30 m Harmonized Landsat Sentinel-2 (HLS)
  vegetation indices, with each season's green-up, peak, and end.
- **Rotation options.** The current rotation plus 3-season alternatives. Each option shows water
  use, bad-year water use, ground cover, Relative Yield Index (0–1, no tonnes), erosion and other
  priority measures, and an A–D evidence grade. You can move priority sliders, set constraints
  ("crops I can't plant", irrigation, water cap) and run weather what-ifs (temperature and rainfall
  shifts on past weather; not climate projections).
- **"Why this ranking?" explainer.** Full score contribution breakdown comparing the top-ranked option
  against the next-best alternative under the user's active priority weights, with deterministic plain-language
  attribution.
- **Calendar.** Months when the field is bare (observed, and simulated per option), and months when
  each crop is vulnerable to heat, frost, water stress and extreme rain.
- **Field in 3D.** Interactive 3D soil water balance and crop canopy simulation over median historical
  weather and what-if scenarios, visualizing root-zone water depletion, canopy cover, and water stress (Ks)
  with a 2D canvas fallback.
- **Advisor console.** Credibility of the physics for this field, what to measure next, the
  smallest change that would flip the top option, and a back-test of past predictions.
- **Map layers and scoreboard.** Fields coloured by erosion, water stress or frost share. Regional
  GRACE water-storage and SMAP soil-moisture layers. A hindcast scoreboard against simpler
  baselines, including diagnostic breakdowns and grade-validity checks.
- **Add my field (v0).** Client-side zero-server field digitizer and rotation evaluator running locally in
  browser storage.
- **Guided tour.** 7-step interactive walkthrough introducing the field card, priority weights,
  what-ifs, 3D simulation, and scientific methods.

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
   previous-crop effects. In this release, the neighbour witness remains OFF in grading because
   structural rotation history imbalance and placebo/control tests failed pre-registered
   diagnostics (T5.3, T5.xa), so no option reaches grade A.

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
- The neighbour-only baseline B3 was not run (pending valid neighbour evidence).
- These are weak results, and we report them honestly as they are (`results/hindcast/`).

## Known issues & honest limits

- The season detector missed its pre-registered target: 78.3 % on held-out test (74.6 % in pilot check) against a 90 % target (T2.2,
  `results/story/`).
- Only maize and sorghum have calibrated physics. Winter wheat fields cannot get a credibility score.
- Double ML neighbour effects failed covariate balance across differing rotation histories (T5.3).
  Matching two-year histories improved balance (T5.xa), but placebo/control checks failed; neighbour
  evidence remains off in grading.
- Evidence grade validity: We could not show that evidence grades predict accuracy (n = 463 field-seasons): grade-B fields had lower average error than grade-D (CRPS 17.0 vs 24.0), but the difference is within the uncertainty (95% CI of the difference −3.3 to 14.3). Grade D had only 25 field-seasons. Pre-registered verdict: not shown.
- Hindcast skill diagnosis (pre-registered in `DECISIONS.md`, commit `e021f3e`, `results/hindcast/diagnosis.md`): FieldWitness forecast-mode canopy integral CRPS beats B1 (diff +1.23, 95% CI [0.48, 1.99]) and B2 (diff +1.35, 95% CI [0.74, 1.90]) overall and for maize, but does not strictly beat baselines for sorghum (diff +0.77 [-0.10, 1.64], 95% CI spans 0). Winter wheat has no baseline run (existing baseline code handles single-calendar years only) and exhibits a peak timing error about 36 days late (absolute error 58.9 d [52.2, 66.3] d; signed median offset +36.0 d; proposed explanation, not tested: uncalibrated phenology prior stage lengths).

## Coverage and roadmap

Before expanding coverage beyond the Kansas High Plains pilot (HLS tile T14SLH), FieldWitness tests three pre-registered validation gates:
1. **Census and scale gate:** Field size and interior-pixel share (>= 4 interior 30 m pixels with a 15 m buffer) to ensure field observations are not dominated by boundary mix.
2. **Season detection gate:** Accuracy target of 90 % against ground data. Kansas achieved 78.3 % on held-out test data (missing the target).
3. **Hindcast skill gate:** Weak hindcast skill across fields (canopy integral 90 % interval coverage was 35.0 %, cover days 9.0 %, Spearman r = 0.264).

Because Kansas missed the season detection target and shows weak hindcast skill, it is published strictly as a pilot with limits visible, not as a general product. Evidence grades are capped at B (Grade A disabled), neighbour evidence is inactive, and we make no yield hindcast claims.

**Privacy & "Add my field" (Version 0):** Farm locations and management histories are sensitive. The "Add my field" feature operates entirely on the client side (zero server calls, static build). Coordinates, crop histories, and constraints stay strictly on your local device (in `localStorage`). A future server-side pipeline will store data only with explicit farmer consent.

## Run it

Requirements:
- Python 3.12 managed with `uv`;
- Node 20.19+ or 22.12+ / 24+;
- NASA Earthdata login in `~/_netrc` (Windows) or `~/.netrc`, for the pipeline only.

```bash
uv sync --frozen
uv run pytest -q
uv run python -m fieldwitness.cli validate-packs packs/ks_t14slh

cd app
npm test
npm run build
```

The app runs offline from precomputed packs, with no login and no server. See `app/README.md`
and `app/deploy/README.md`.

## Repository

- `src/fieldwitness/`: pipeline (data access with an `as_of` leakage guard, field story, physics,
  inference, neighbours, grading, rotation, ledger, packs).
- `app/`: React + Vite + TypeScript + MapLibre web app.
- `results/`: validation outputs, including negative results.
- `PLAN.md`, `DECISIONS.md`, `DATA.md`, `AI_USE.md`: plan, decision log, datasets and licences, AI disclosure.

## Not claimed

FieldWitness does not give yields in tonnes, prices or profits. It does not measure soil fertility
from space. It does not let a language model make the decision. It supports local expertise and
does not replace it.

## Licence

[MIT License](LICENSE). Data licences and attribution: [`DATA.md`](DATA.md).
