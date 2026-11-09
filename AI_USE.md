# Use of AI in FieldWitness

## Summary

- AI coding assistants wrote most of the code and documents in this repository, under the team's
  direction, planning mode, and review.
- The product itself contains **no AI model that makes or ranks recommendations**. Every number
  comes from documented formulas, statistics and satellite data, and every sentence the app shows
  comes from fixed deterministic templates over those numbers.

## Tools

- **Claude Code** (Anthropic): an AI coding assistant running in the terminal and VS Code, used
  for initial project scaffolding, data pipeline, physics engine, ABC calibration, web app, and
  pre-event verification sessions.
- **Google Antigravity** (Google DeepMind): agentic coding environment using Gemini models, used for
  laptop migration verification, Phase 5 secondary analyses (T5.xa matching-history design,
  T5.xb tile volume estimation), and Phase 10–12 engineering (UI accessibility, performance code-splitting,
  light/dark theme tokens, interactive 3D root-zone simulation with 2D fallback, 7-step guided tour,
  "Add my field" client-side digitizer v0, "Why this ranking?" score contribution explainer,
  hindcast diagnostic breakdown, and pre-registered grade-validity evaluation).
- Both tools operated under the strict working agreements documented in `CLAUDE.md`, logging all
  actions, failed checks, and negative results in `DECISIONS.md`.

## How AI-written work is marked

- Commits that AI helped write carry the appropriate co-authorship trailers in Git.
- `DECISIONS.md` records every AI session: what was done, what failed and what is blocked.
- No code or text was generated without explicit plan verification and acceptance tests.

## Rules the AI worked under (from `CLAUDE.md`)

- **No fabrication.** No invented data, endpoints, coefficients, results or citations. Anything
  unknown is marked `UNVERIFIED`.
- **Verify every external API.** Read the official documentation and make a small test call first;
  the real response shapes are in `docs/api_notes.md`.
- **Constants from the source.** Formula constants and table values come from published literature
  and papers, which docstrings cite (for example FAO-56 equation numbers), not from model weights.
- **Report negative results.** Failed checks stay on record in `results/` and `DECISIONS.md`,
  such as the T2.2 season detector (74.6% against a 90% target), the weak hindcast skill, and
  the T5.3/T5.xa neighbour diagnostics failures.
- **No leakage.** An `as_of` guard and tests stop hindcast code from reading data after the
  cut-off date (2021-12-31).
- **No secrets.** A secret scan (gitleaks) runs before every commit. Earthdata credentials stay
  outside the repo in `~/_netrc`.
- **Ask first.** The AI asks the team before adding dependencies, downloading more than 1 GB, or
  changing schemas.

## What the people did

- Chose the challenge approach, the pilot regions, the scope, and the plan;
- Approved every dependency, schema change, and plan change;
- Reviewed the code and verification outputs at each gate;
- Made the judgment calls recorded in `DECISIONS.md` as "user decision";
- Supervised and directed all AI agent sessions.

## Inside the product

- **Physics.** FAO-56 root-zone water balance (Allen et al. 1998), cited by equation number.
- **Calibration.** Approximate Bayesian computation (ABC) against the field's own HLS history.
- **Neighbours.** Double machine learning (Chernozhukov et al. 2018) for causal previous-crop effects.
  Because diagnostics failed on Kansas data (T5.3, T5.xa), the neighbour witness remains OFF in grading.
- **Ranking.** A Pareto filter plus weighted regret scores. The default weights are tagged A (assumption),
  and users can adjust them via interactive sliders in the app.
- **Explanations.** Fixed text templates over computed metrics (`rotate/explain.py`: "No LLM").
