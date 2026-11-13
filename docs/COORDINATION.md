# Coordination between AI agents

Two AI coding agents work on this repository: Claude Code (laptop 1) and Google Antigravity (laptop 2).
This file says who works on what, so the two never edit the same files at the same time.
Read it on `origin/main` before every task and before every push.

## Rules (both agents)

1. Before each task and before each push: `git fetch --all --prune`, read this file on `origin/main`, then rebase your branch on `origin/main`.
2. Work only on your own branches (prefixes below). Never touch the other agent's branches.
3. Keep the "Active work" table up to date: add a row when you start a task; update it when you finish.
4. `DECISIONS.md` is append-only. Add entries only under your own dated heading tagged `[claude-code]` or `[antigravity]`. Never rewrite another agent's entries.
5. Never push to `main`, force-push or touch tags unless the owner says so for that specific action.
6. If a conflict appears in files you did not intend to change, stop and tell the owner.

## Branch naming

| Prefix | Agent |
|---|---|
| `claude/`, `experiment/`, `docs/` | Claude Code |
| `ag/` | Google Antigravity |

`main` changes only through pull requests that the owner merges.

## Hotspot files

These files are edited often by both sides. Claim them in the table before you edit them, and keep the edits small:
`PLAN.md`, `DECISIONS.md` (append-only, see rule 4), `README.md`, `docs/COORDINATION.md`, `config/*.yaml`, `app/src/strings`, `package-lock.json`, `uv.lock`.

## Active work

| Agent | Branch | Files or folders claimed | Status | Date |
|---|---|---|---|---|
| Claude Code | `experiment/algo-upgrade` (draft PR #13) | DAPSM and GDD experiments: `src/fieldwitness/physics/`, `src/fieldwitness/neighbours/`, `src/fieldwitness/experimental/`, `scripts/x*`, `results/neighbours/dapsm*`, `results/hindcast/gdd*`, `results/hindcast/clean2025/`, `docs/GDD_BEFORE_AFTER.md` | Draft, not adopted; do not merge | 2026-11-12 |
| Claude Code | `experiment/algo-upgrade` (local `x3-clean2025`) | Experiment 3, the clean 2025 test: `scripts/x3_*`, `results/hindcast/clean2025/`, `data/` 2025 files (not in git) | In progress (waiting for AppEEARS 2025 downloads) | 2026-11-12 |
| Claude Code | `experiment/conformal` (draft PR #14) | Conformal recalibration of the intervals | Draft, gate failed, not adopted; do not merge | 2026-11-12 |
| Claude Code | `experiment/reliability-grades` (draft PR #15) | Reliability tiers learned from measured error | Draft, not adopted; do not merge | 2026-11-12 |
| Antigravity | `ag/consistency-audit` | `docs/drafts/consistency_audit_ag.md` | Merged (#17) | 2026-11-12 |
| Antigravity | `ag/model-specs` | `docs/research/aquacrop_canopy_cover.md`, `docs/research/phenology_priors.md` | Merged (#18) | 2026-11-12 |
| Antigravity | `ag/safety-audit-fixes` | `README.md`, `app/src/strings/en.json`, `docs/drafts/submission.md`, `DECISIONS.md` | Merged (#24) | 2026-11-12 |
| Antigravity | `ag/print-dossier` | `app/src/PrintDossier.tsx`, `app/src/FieldPage.tsx`, `app/src/styles.css`, `app/src/strings/en.json`, `PLAN.md`, `DECISIONS.md` | Merged (#25) | 2026-11-12 |
| Antigravity | `ag/external-data-engine` | `config/crops.yaml`, `src/fieldwitness/agree/trials.py`, `src/fieldwitness/data/ssurgo_taw.py`, `scripts/t73_baselines.py`, `app/src/liveSim.ts`, `DECISIONS.md` | Merged (#26) | 2026-11-12 |
| Antigravity | `ag/multi-source-solutions` | `src/fieldwitness/agree/grade.py`, `scripts/t65_grade.py`, `scripts/t73_baselines.py`, `app/src/advisor.ts`, `app/src/AdvisorConsole.tsx`, `app/src/liveClimateApi.ts`, `DECISIONS.md` | Merged (#27) | 2026-11-13 |
| Antigravity | `ag/final-polish` | `scripts/t62_draws.py`, `app/src/PrintDossier.tsx`, `docs/COORDINATION.md`, `DECISIONS.md` | Merged (#28) | 2026-11-13 |
| Antigravity | `ag/context-chatbot` | `app/src/chatbotContext.ts`, `app/src/FieldChatbot.tsx`, `app/src/App.tsx`, `app/src/FieldPage.tsx`, `app/src/styles.css`, `app/tests/chatbot.test.ts`, `workers/` | Merged (#29, #30, #31) | 2026-11-13 |
| Antigravity | `ag/enhancement-phase1` | `app/src/strings/en.json`, `app/src/FieldChatbot.tsx`, `app/src/chatbotContext.ts`, `app/src/liveClimateApi.ts`, `app/src/AddFieldPage.tsx`, `app/src/FieldPage.tsx`, `app/src/Scoreboard.tsx`, `app/src/styles.css`, `app/tests/`, `docs/COORDINATION.md`, `DECISIONS.md` | In progress (Enhancement Phases 1–2) | 2026-11-13 |
| Claude Code | `claude/app-fixes` | `app/src/fieldSummary.ts`, `app/src/FieldSummaryPanel.tsx`, `app/tests/fieldSummary.test.ts` | Merged (#19) | 2026-11-12 |
| Claude Code | `docs/how-we-built-bilingual` | `docs/HOW_WE_BUILT_FIELDWITNESS.en.md`, `docs/HOW_WE_BUILT_FIELDWITNESS.ar.md`, `README.md` (2 links) | Merged (#20) | 2026-11-12 |
| Claude Code | `experiment/bias-diagnosis` (draft PR #21) | `scripts/x4_bias_diagnosis.py`, `src/fieldwitness/experimental/bias.py`, `tests/test_bias_diagnosis.py`, `results/hindcast/bias_diagnosis/`, `docs/BIAS_DIAGNOSIS.md` | Draft, gate failed, not adopted; do not merge | 2026-11-12 |
| Claude Code | `docs/housekeeping` | `DECISIONS.md` (append), `docs/COORDINATION.md` | Open PR | 2026-11-12 |
| Claude Code | `experiment/bias-diagnosis` (draft PR) | `scripts/x4_bias_diagnosis.py`, `src/fieldwitness/experimental/bias.py`, `tests/test_bias_diagnosis.py`, `results/hindcast/bias_diagnosis/`, `docs/BIAS_DIAGNOSIS.md`, `DECISIONS.md` (append) | Draft PR, gate failed, not adopted; do not merge | 2026-11-12 |
| Claude Code | `claude/app-fixes` | `app/src/fieldSummary.ts`, `app/src/FieldSummaryPanel.tsx`, `app/tests/fieldSummary.test.ts` | Merged (#19) | 2026-11-12 |
| Claude Code | `claude/app-fixes` | `app/src/fieldSummary.ts`, `app/src/FieldSummaryPanel.tsx`, `app/tests/fieldSummary.test.ts` | Open PR, not merged | 2026-11-12 |
| Claude Code | `claude/cover-crop-3d` | `app/src/Field3DScene.tsx`, `app/src/Field3DView.tsx` | Open PR, not merged | 2026-11-12 |

## Sync check

Run this before you start and before you push:

```
git fetch --all --prune ; git status -sb ; git log --oneline HEAD..origin/main
```

If the last command prints any commits, rebase on `origin/main` before you continue.
