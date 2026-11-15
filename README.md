# FieldWitness

**Crop-rotation decision support for a field, with three independent witnesses behind every
option.** Built for the NASA Space Apps Challenge 2026, challenge "Field Shift: Adapting
Farms with NASA Data".

FieldWitness does not decide for the farmer. It shows evidence, says how strong that evidence is,
and turns each recommendation into a prediction that next season's satellite data can check.

- **Live application:** https://amr-mousa-eg.github.io/fieldwitness/
- **Regions in this release:** Kansas High Plains, USA (HLS tile T14SLH, 200 pilot fields) and Central Ukraine (Sentinel-2 tile T36UVU, 400 FTW pilot fields / 120 calibrated demo packs across 6 crops). Toulouse, France (T31TCJ) is planned in the multi-region architecture.
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
  with a 2D canvas fallback. "Illustration of simulated values — not a photo."
- **Rotation Builder.** In Field in 3D, press "Build your own rotation": put a crop in each of three
  seasons (tap, drag or keyboard) and press Grow. Only the field's 36 ranked rotations can be built; a
  disabled card says which rule it breaks. The table (water use, bad-year water, bare-soil months,
  evidence grade, all tagged) comes from the ranking in the pack; the 3D replay re-runs the same FAO-56
  water balance in the browser (parity-tested: 20 fields x 36 rotations x 3 weathers, max difference
  0.0000057 mm, `results/validation/sim3d_parity.json`).
- **Farm view.** An illustrated isometric farm with two fenced plots, the current rotation and yours,
  on the same field, weeks and weather. Plants, bare soil, sprinklers, rain and sky follow the weekly
  simulated values; the barn, trees, pond, fences and paths are labelled "Scenery, not data". Soil X-ray
  switches to the glass soil view. Kill switches: `?builder=0`, `?farm=0`.
- **Advisor console.** Credibility of the physics for this field, what to measure next, the
  smallest change that would flip the top option, and a back-test of past predictions.
- **Map layers and scoreboard.** Fields coloured by erosion, water stress or frost share. Regional
  GRACE water-storage and SMAP soil-moisture layers. A hindcast scoreboard against simpler
  baselines, including diagnostic breakdowns and grade-validity checks.
- **Add my field (v0).** Client-side zero-server field digitizer and rotation evaluator running locally in
  browser storage.
- **Ask FieldWitness (optional assistant).** A chat drawer that explains the project and the open
  field from a tested set of facts. If a chat proxy is configured (`workers/chat-proxy/`), other
  questions go to a third-party LLM (Gemini or Groq free tier); those replies are labelled
  "AI-generated … Not a recommendation". The LLM never ranks options; the decision engine is
  deterministic. Fields you add yourself are sent to it only if you tick "Share this field with the assistant".
- **Guided tour.** 8-step "try it" walkthrough: field card, season, priority weights, ranking
  explainer, 3D simulation, building a rotation, limits, and adding a field.

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

## Results (Kansas & Ukraine hindcasts, honest version)

All data was frozen on 31 Dec 2021. We predicted the 2022–2024 seasons of **463** labelled Kansas
maize, sorghum, and winter-wheat field-seasons (using observed USDA SSURGO 0–135 cm TAW `[E]`
across 198 fields + ISRIC SoilGrids 2.0 `[E]` fallback on 2 shallow fields) and **329** Central
Ukraine seasons (`sunflower`, `maize`, `winter_wheat`), then scored them against satellite
observations. Forecast mode used past weather only.

| Kansas measure (`n = 463`) | FieldWitness CRPS | Best baseline CRPS | Inside 90 % range (raw → Split-CQR) |
|---|---|---|---|
| Green-up date (SOS) | 37.9 | 35.1 (B0, field mean) | 36.5 % → 80.2–91.1 % asym (86.3–91.1 % sym) |
| Peak date | 27.3 | 29.3 (B2, uncalibrated) | 65.0 % |
| Season greenness total | 17.9 | 16.6 (B0; B1 19.7, B2 20.4) | 28.5 % → 71.8–79.0 % sym |
| Ground cover days | 36.1 | 35.2 (B0) | 5.8 % → 77.4–88.8 % asym (wheat 88.8 %) |

What this means:
- Under observed SSURGO `[E]` soil TAW, FieldWitness beats baselines B1 and B2 overall (`17.86 vs 19.67 / 20.45`) and across all three crops individually, and beats all baselines on peak timing (`27.3` vs `29.3` d).
- Uncalibrated uncertainty ranges are too narrow for green-up, greenness and cover days; Phase 4 Split-CQR lifts 90 % coverage sharply (`86.3–91.1 %` sym SOS, `88.8 %` wheat cover days, `71.8–79.0 %` sym canopy integral; Winkler scores reduced up to `78 %`).
- In Central Ukraine (`ua_central_t36uvu`, `n = 329`), FieldWitness beats `B0`/`B1`/`B2` on SOS (`12.2` vs `18.1`/`15.7`/`13.4` d), peak (`14.7` vs `18.3`/`23.6`/`17.5` d), and canopy-integral rank correlation (`ρ = 0.247` vs `0.185`/`0.203`/`0.150`), while trailing `B0` on canopy-integral CRPS (`14.8` vs `13.2`) and cover-days CRPS (`44.6` vs `40.1` d).
- The neighbour-only baseline B3 was not run. These limits are reported honestly in `results/hindcast/`.

## Known issues & honest limits

- Rotation Builder and Farm view: the 3D replay is one median-rain weather year (normal, dry -20 % rain
  or hot +2 °C), not a forecast; history-only seasons (e.g. perennial forage) show "not simulated";
  cover-crop weeks are recognised from the canopy proxy; frame rates were measured with headless
  software rendering, not on real phones or GPUs.

- The season detector missed its pre-registered 90 % target: Phase 1 TWDTW reaches 86.7 % season match (88.7 % DTW binary, 75.4 % WDDTW multi-class, 93.3 % fallow; CropFormer 1.07 ms/field) across 240 held-out test field-seasons (`results/story/phenology_benchmark.json`).
- Kansas grades top out at B (77 B / 102 C / 21 D top; 6,840 candidate options) even after switching soil TAW from `150 mm [A]` to observed `SSURGO [E]`, because Witness 3 stays OFF and sowing dates carry team-choice tag `[A]`.
- Double ML neighbour effects failed covariate balance across differing rotation histories in Kansas (`0/92` primary, `0/32` matched, `0/4` DAPSM) and remain OFF. In Central Ukraine, Panel-OBDML and Exact-Year DAPSM pass `30` pre-cutoff contrasts (unlocking `44` Grade A candidate options across 6 crops: `winter_wheat`, `maize`, `sunflower`, `soybean`, `fallow`, `cover_crop`; WorldCereal 2021 cropland agreement `98.25 %`, wheat–maize confusion `0.0 %`, while maize-vs-sunflower separation remains weak at `κ = 0.035`).
- Evidence grade validity: We could not show that evidence grades predict accuracy (`n = 463` field-seasons): grade-B fields had lower average error than grade-D (CRPS `17.9` vs `24.8`), but the difference is within the uncertainty (95% CI of the difference `−1.5` to `13.9`, `[-1.54, 13.94]`, Spearman `ρ = -0.004`, `p = 0.937`). Grade D had only 25 field-seasons. Pre-registered verdict: not shown.
- Hindcast skill diagnosis (pre-registered in `DECISIONS.md`, commit `e021f3e`, `results/hindcast/diagnosis.md`): Under SSURGO `[E]` TAW (`n = 463`), FieldWitness forecast-mode canopy integral CRPS beats B1 (diff `+1.81`, 95% CI `[1.39, 2.22]`) and B2 (diff `+2.59`, 95% CI `[2.04, 3.10]`) overall and in all three crops (`maize 18.23`, `sorghum 12.70`, `winter_wheat 21.36`). Winter wheat still exhibits a peak timing error about 30 days late (absolute error 56.0 d `[48.6, 63.9]` d; signed median offset +30.0 d; proposed explanation, not tested: uncalibrated phenology prior stage lengths).

## What we got wrong (and what changed)

A record of issues encountered during development, how they were caught, and what was changed:

- **Season detection missed target:** Legacy Savitzky–Golay achieved 78.3 % accuracy on held-out test data (188/240 field-seasons; 74.6 % in pilot checks), falling short of the pre-registered 90.0 % target. Replaced in Phase 1 benchmarks with TWDTW (86.7 % match), DTW (88.7 %), WDDTW (75.4 % multi-class, 93.3 % fallow), and CropFormer (1.07 ms/field) (`results/story/phenology_benchmark.json`, `DECISIONS.md`).
- **Neighbour witness failed all diagnostics in Kansas:** Causal Double Machine Learning on previous-crop contrasts failed covariate balance across historical sequences and failed negative control checks (0 of 92 primary contrasts in `results/neighbours/diagnostics.md`, 0 of 32 in `results/neighbours/matching_diagnostics.md`). Kept strictly OFF in Kansas grading as an automated safety circuit breaker; active in Central Ukraine where 30 pre-cutoff Panel-OBDML/DAPSM contrasts pass (`DECISIONS.md`).
- **Ranking rewarded fallow:** Early ranking iterations scored bare fallow as optimal because it consumed zero crop transpiration, ignoring soil degradation. Fixed by introducing bare-soil month penalties and crop diversity constraints (`config/ranking.yaml`, `DECISIONS.md`).
- **Rank-order bug in packs and mis-tracked T6.8 metrics:** In commit `ce69ebf`, packs had rank indices assigned prior to constraint filtering, and manual audit revealed T6.8 metric counts were tracked from intermediate script output. Corrected and covered with automated pack assertions (commit `ce69ebf`, `DECISIONS.md`).
- **Broken DOIs in data documentation:** Automated link validation detected malformed and unreachable DOI URLs in early drafts of `DATA.md`. Replaced with verified persistent identifiers from official NASA DAAC and ISRIC registries (`DATA.md`, `DECISIONS.md`).
- **Invented datasets purged, then real SSURGO SDA integrated:** Early AI exploration proposed unverified POLARIS/SSURGO endpoints that were purged at Gate 0. Real USDA-NRCS Soil Data Access (SDA) REST integration (`ssurgo_taw.py`) later measured a `-119.3 mm` TAW bias on 198 Kansas fields and replaced the `150 mm [A]` prior in Phase P1 (`DECISIONS.md`).
- **Circularity trap avoided in grade validity:** Evaluating whether evidence grades predicted accuracy using current grades (derived with 2022–2024 data) would have caused outcome leakage. Caught during pre-registration and strictly evaluated against cut-off grades frozen as_of(2021-12-31) (`DECISIONS.md`, commit `e021f3e`).
- **Reconciled grade counts between pages:** Grade B field-seasons differed between grade validity ($n = 170$) and diagnostic breakdowns ($n = 97$) because exploratory diagnostics dropped rows without baseline runs. Fixed to evaluate the full cohort across all pages (`results/hindcast/diagnosis.md`, `scripts/t7_diagnosis.py`).
- **Performance regression measured, not assumed:** Adding 3D simulation and guided tour caused initial Lighthouse desktop score to drop from 88 to 31 (LCP 9.7 s). Instead of assuming test machine jitter, performance tracing identified eager bundle imports; resolved via dynamic code-splitting (commit `0662f39`, `DECISIONS.md`).

## Coverage and roadmap

Before expanding coverage beyond the Kansas High Plains pilot (HLS tile T14SLH), FieldWitness tests three pre-registered validation gates:
1. **Census and scale gate:** Field size and interior-pixel share (>= 4 interior 30 m pixels with a 15 m buffer) to ensure field observations are not dominated by boundary mix.
2. **Season detection gate:** Accuracy target of 90 % against ground data (TWDTW reaches 86.7 % in Kansas; WorldCereal confirms 98.25 % cropland / 0.0 % wheat–maize confusion in Ukraine, with κ = 0.035 maize-vs-sunflower).
3. **Hindcast skill gate:** Under SSURGO `[E]` TAW (`n = 463`), Split-CQR lifts Kansas 90 % coverage to 86.3–91.1 % sym / 80.2–91.1 % asym (SOS) and 88.8 % asym (wheat cover days), while canopy-integral CRPS beats B1/B2 overall (`17.86` vs `19.67`/`20.45`).

Because Kansas missed the season detection target and Witness 3 stays OFF there, it is published strictly as a pilot with limits visible, not as a general product. Kansas evidence grades are capped at B (Grade A disabled); in Central Ukraine, Panel-OBDML + SoilGrids 0–135 cm TAW + 6-crop expansion unlock Grades A–C across candidate options (`44 A`).

### Post-freeze roadmap

Items scheduled for subsequent milestones following the code freeze:
- **Arabic interface (i18n / RTL):** Full right-to-left layout and localized agricultural terminology for regional usability.
- **Compare two fields side by side:** Direct side-by-side comparison of rotation rankings, water requirements, and evidence grades across separate parcels.
- **Independent soil water and rainfall cross-checks:** Cross-validation of modeled root-zone soil water and precipitation against NASA SMAP L4 soil moisture and GPM IMERG precipitation data.
- **Evapotranspiration and irrigation checks:** Cross-checking simulated crop evapotranspiration against NASA ECOSTRESS thermal data and irrigation diversion records against the Kansas WIMAS database.
- **Expanding coverage tile-by-tile:** Rolling out to further agricultural regions tile-by-tile, requiring every new tile to satisfy the census, season-detection, and hindcast gates before publication.

### Future work (not implemented)

Planned research directions, not part of the current results. Nothing below exists in the pipeline or the app; the code folders hold docstring-only stubs that raise `NotImplementedError`.
- **Physics-informed water balance (`src/fieldwitness/experimental/neural_physics/`):** a neural network trained on SMAP L4 and ECOSTRESS data with a Richards-equation penalty. Not built: it needs training time, a new dependency and its own validation.
- **Amortised calibration (`src/fieldwitness/experimental/neural_infer/`):** neural posterior estimation (the `sbi` library, a masked autoregressive flow, an active-learning loop) as a possible replacement for ABC rejection at regional scale. A research direction, not a decision.

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
- Plain-language guide to how FieldWitness was built and how its prediction works: [English](docs/HOW_WE_BUILT_FIELDWITNESS.en.md) · [العربية (machine-assisted draft)](docs/HOW_WE_BUILT_FIELDWITNESS.ar.md).

## Not claimed

FieldWitness does not give yields in tonnes, prices or profits. It does not measure soil fertility
from space. It does not let a language model make the decision. It supports local expertise and
does not replace it.

## Licence

[MIT License](LICENSE). Data licences and attribution: [`DATA.md`](DATA.md).
