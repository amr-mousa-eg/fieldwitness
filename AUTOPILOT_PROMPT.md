# Autopilot run — FieldWitness

You are running **unattended** inside a loop (`scripts/autopilot.ps1`). No human will answer questions during this run. Each run is a fresh session: everything you need is in the files below. Work carefully, commit often, and always leave a clean handoff.

## 1. Start of every run

1. Read `CLAUDE.md`, the `## Autopilot handoff` section at the end of `DECISIONS.md` (create it if missing) and only the `PLAN.md` sections for the current task and phase — not whole files (search for the section, then read just that range). The handoff says where the previous run stopped, what runs in the background, and what to do next.
2. Run `git status`. If the previous run left uncommitted work, finish it or revert it to the last commit, and say which in the handoff.
3. Check background work recorded in the handoff (e.g. AppEEARS task IDs): poll their status and download finished results.
4. Be terse; minimise tokens; keep logs and command output short.

## 2. What to work on

- Follow `PLAN.md` §6 (the pre-event schedule) in order. Work on the earliest unticked task whose inputs are ready. While waiting on background downloads, you may work ahead on any task whose inputs are already available (this generalises the logged Phase 3 exception); record each such exception in `DECISIONS.md`.
- Do **one task per run**, or several small ones, then stop. Prefer finishing and committing one task over starting two.
- Pending items carried over from the user (do these first if not done):
  - Start Phase 3 physics (T3.1–T3.5) while HLS downloads run (logged exception: it needs only POWER, soil and crops.yaml).
  - Write the Phase 2 code (T2.1, T2.2, T2.5) and test it on the T0.3 AppEEARS sample; run it on pilot fields when their HLS results arrive.
  - For the Gate 1 review, report: SoilGrids values from the no-data rule (tag A) vs real, per property; whether the irrigated/rainfed stratification was done and the split; the 12-pixel sampling (seeded, pixel centres) and how many fields have fewer than 12 interior pixels.

## 3. Gates

When a phase's tasks are done, write the gate review to `docs/gates/gate-<N>.md`: every acceptance test, with pass / fail / unverified and the evidence.

- If **every** acceptance test passes with evidence, you may continue to the next phase. The user reads the gate file later.
- If any acceptance test fails or is unverified and you cannot fix it within the rules, record it as a negative result (§5a) and continue. Write `BLOCKED.md` only for a §5 hard stop.

## 4. Rules for unattended work

All rules in `CLAUDE.md` apply. In addition:

- **Push** after a task when all tests pass and gitleaks is clean. One line per push in the handoff.
- Tests that read data/ must use the needs_data marker so CI stays green without local data.
- **No local process may outlive this run.** Long downloads must be server-side tasks (AppEEARS) whose IDs go into the handoff and are polled next run, or local downloads that finish within this run. Never rely on a background process surviving.
- Keep each command's output short (use `python -u`, log to files under `logs/`, show only summaries).
- Never use bypass permission modes, never edit `.claude/settings.json`, never change the loop script.
- **Development subset.** During development, run on a fixed seeded subset of 20 Kansas fields (`SEED = 20261114`; record the field IDs in `DECISIONS.md` the first time). Run all 200 fields only once per task: for its acceptance check and for the packs.
- **Cache simulations by input hash.** Key each field's simulation result on a hash of all its inputs (field data, configs, code version of the physics). A field whose inputs did not change is never recomputed.
- **Keep the packs current (early integration).** The T8.1 pack writer exists (`packs/ks_t14slh/`, all 200 fields). When a task changes anything a pack shows (e.g. T6.9, T7.x), rebuild the packs and validate them (`cli validate-packs`) in the same task. A metric not yet computed is `null` with a "not yet computed" note and must stay schema-valid. For a new region, write a thin pack (story + Current + ranked options) for its 20-field subset right after T6.3 passes, then extend it as T6.4–T6.9 land.

## 5. Stop conditions → write `BLOCKED.md` and end the run

Write `BLOCKED.md` in the repo root (short: what, why, the exact question, options with your recommendation) and end the run if you would need any of:

- a change to `PLAN.md` scope or the §3 schemas beyond what PLAN.md already approves;
- a new dependency not named in `PLAN.md`;
- a download over 1 GB;
- accepting any terms, licence or disclaimer (e.g. WIMAS);
- credentials beyond the allowed `_netrc` use;
- making the repository public, deploying publicly, or anything touching money;
- a decision whose options change the product's meaning when none of them is clearly better (see §5a).

A failed acceptance test is **not** a stop: see §5a. Never weaken a test to make it pass.

## 5a. Decision policy (decide, log, continue)

If a decision is **reversible**, **within `PLAN.md` scope**, and you can name a recommended option with a reason (a cited source or an agronomic argument):

1. Take the recommended option and tag it A (team choice).
2. Log it in `DECISIONS.md`.
3. Append it to `docs/review_queue.md` with: date, question, options, chosen option, reason, how to revert.
4. Continue.

Write `BLOCKED.md` only for the §5 hard stops, or when the options change the product's meaning and none is clearly better.

A **failed acceptance test** is recorded as a negative result (in `results/` and `DECISIONS.md`, rule 9). Do not tune further. Then continue with the next task.

## 6. Waiting

If the only thing left to do is wait for background tasks (nothing else has ready inputs), write the number of minutes to wait (e.g. `60`) into the file `AUTOPILOT_WAIT` and end the run. The loop sleeps that long before the next run.

## 7. End of every run (always, even when blocked)

A run can be cut off at the turn cap at any moment, so update the handoff and commit after every finished task, not only at the end.

1. Commit finished work (and push if green).
2. Replace the `## Autopilot handoff` section at the end of `DECISIONS.md` with: date/time, what this run did, what is in progress, background task IDs and their status, the next task, and any risk the user should know. Commit it.
3. End with a 3-line summary.
