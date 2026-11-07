<!-- DRAFT (branch app, 2026-11-07). Moves to /AI_USE.md at the merge. Before that:
     - check the 2026 Space Apps Project Submission Guide (released 13 Nov 2026) for the
       required AI disclosure and file-marking rules, and adjust this file to them;
     - the owner confirms the "What the people did" section. -->

# Use of AI in FieldWitness

## Summary

- An AI coding assistant wrote most of the code and documents in this repository, under the team's
  direction and review.
- The product itself contains **no AI model that makes or ranks recommendations**. Every number
  comes from documented formulas, statistics and satellite data, and every sentence the app shows
  comes from fixed templates over those numbers.

## Tools

- **Claude Code** (Anthropic), an AI coding assistant that runs in the terminal and in VS Code,
  using Anthropic Claude models. Exact model versions changed during the project and are not
  listed per session (UNVERIFIED).
- It was used for the pipeline code, tests, the web app, documentation drafts and API checks.
- It also ran unattended "autopilot" sessions. Each session worked on one task from `PLAN.md` and
  logged what it did in `DECISIONS.md`.

## How AI-written work is marked

- Commits that AI helped write carry the trailer `Co-Authored-By: Claude …`. On 7 Nov 2026, 89 of
  the 92 commits on `main` had it.
- `DECISIONS.md` records every AI session: what was done, what failed and what is blocked.

## Rules the AI worked under (from `CLAUDE.md`)

- **No fabrication.** No invented data, endpoints, coefficients, results or citations. Anything
  unknown is marked `UNVERIFIED`.
- **Verify every external API.** Read the official documentation and make a small test call first;
  the real response shapes are in `docs/api_notes.md`.
- **Constants from the source.** Formula constants and table values come from the papers, which
  docstrings cite (for example FAO-56 equation numbers), not from the model's memory.
- **Report negative results.** Failed checks stay on record in `results/` and `DECISIONS.md`,
  for example the T2.2 season detector at 78 % against a 90 % target, and the weak hindcast skill.
- **No leakage.** An `as_of` guard and tests stop hindcast code from reading data after the
  cut-off date.
- **No secrets.** A secret scan (gitleaks) runs before every commit. Earthdata credentials stay
  outside the repo.
- **Ask first.** The AI asks the team before it adds a dependency, downloads more than 1 GB or
  changes a data schema.

## What the people did

_To be confirmed by the team:_
- chose the challenge approach, the regions, the scope and the plan;
- approved every dependency, schema change and plan change;
- reviewed the code at each gate;
- made the judgment calls recorded in `DECISIONS.md` as "user decision".

## Inside the product

- **Physics.** FAO-56 water balance (Allen et al. 1998), cited by equation.
- **Calibration.** Approximate Bayesian computation against the field's own HLS history.
- **Neighbours.** Double machine learning (a statistical method for causal effects) on similar
  fields. This is planned and not in this release.
- **Ranking.** A Pareto filter plus weighted scores. The default weights are tagged A (assumption),
  and users can change them in the app.
- **Explanations.** Fixed text templates over computed numbers (`rotate/explain.py`: "No LLM").
