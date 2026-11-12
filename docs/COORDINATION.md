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
| Claude Code | `docs/coordination` | `docs/COORDINATION.md`, `DECISIONS.md` (append) | Open PR | 2026-11-12 |
| Antigravity | `ag/consistency-audit` | `docs/drafts/consistency_audit_ag.md` | In progress (AG-1 consistency audit) | 2026-11-12 |

## Sync check

Run this before you start and before you push:

```
git fetch --all --prune ; git status -sb ; git log --oneline HEAD..origin/main
```

If the last command prints any commits, rebase on `origin/main` before you continue.
