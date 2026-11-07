# Gate 5 — Phase 5 (neighbour witness), 2026-11-07

**Gate test (PLAN §5): at least one Tier 1 contrast passes diagnostics. Result: FAIL.**

| Task | Acceptance | Result | Evidence |
|---|---|---|---|
| T5.1 | Table + row counts per precrop contrast | PASS | `data/neighbours/ks_t14slh_field_season.parquet` (1400 rows, 1040 with outcomes, 200 fields); `results/neighbours/precrop_contrast_counts.csv` |
| T5.2 | Effects with 95% CIs in `effects.csv` | PASS | `results/neighbours/effects.csv`: 144 rows, 92 fitted, 20 CIs exclude 0. No multiple-testing correction (about 5 false positives expected). Learners untuned (A, UNVERIFIED). |
| T5.3 | Contrasts failing diagnostics flagged, not shown as evidence | PASS (the flagging works) | `results/neighbours/diagnostics.md`: 0 of 92 contrasts pass all four checks. Placebo: 6 fail, 36 untested. Negative control: 5 fail, 64 untested. Overlap: 32 fail. Balance: 92 fail (crop two years back is tied to the previous crop). Thresholds fixed beforehand, not tuned. |
| T5.4 | `results/neighbours/literature_check.md` | UNVERIFIED, BLOCKED | arXiv:2506.02384 could not be opened in this unattended run (WebFetch and curl both need approval). Rule 8: no numbers from memory. |

## Consequences (negative result, rule 9)
- The neighbour witness stays off. No neighbour effect is shown as evidence. Grades stay physics + own-past only, so grade A is not possible.
- T7.3 baseline B3 (neighbour-only) is not meaningful.
- Likely causes (not tested): only 200 pilot fields; a two-year rotation history is nearly collinear with the previous crop; outcomes are canopy/water, not yield.

## Open for the user
- Open arXiv:2506.02384 interactively (or allow WebFetch) so T5.4 can be done.
- Decide whether to enlarge the field-season table beyond the 200 pilot fields (T5.1 allows surrounding tiles), which needs a data download and your OK if over 1 GB.
