# Gate 6 review (Kansas, 2026-11-07)

**Gate test (PLAN line 425):** a full `FieldPack` (minus ledger) for one field validates against the schema.

| Check | Result | Evidence |
|---|---|---|
| FieldPack validates (all 200 fields) | PASS | `cli validate-packs packs/ks_t14slh`: 0 problems over the whole directory (per-field, series, calendar, scenarios, index, layers, hindcast; `regions.json` is one level up in `packs/`). |
| `check_tagged` (no untagged number) | PASS | Run inside the validator for every file. |
| Each pack < 300 KB | PASS | Largest 279 KB (build output); validator enforces the limit. |
| Ledger present | PASS (beyond gate) | 6 `LedgerEntry` for the story field, from `scripts/t72_export.py`. |
| Validator in CI | PASS | `ci.yml` step runs on `packs/demo` when it exists; unit tests always run. UNVERIFIED on GitHub: no demo pack committed yet. |
| Tests / lint | PASS | 231 tests pass, ruff clean. |

## Honest caveats (negative or open results)

- **T2.2 FAILED** (season detector 78.3 % vs 90 %). Crop windows are team choices (tag A).
- **T5.2 blocked:** needs scikit-learn and doubleml (rule 11, user OK). No neighbour witness, so **no A grades are possible** (B/C/D only).
- **Hindcast skill is weak** (T7.1/T7.2): interval coverage far below nominal (e.g. canopy integral 0.17 at 50 %), and the field's own past mean (B0) ranks fields better (Spearman 0.33) than fieldwitness (0.26). T7.1 and T7.3 are not ticked (no barley/option-wide predictions, no B3, no per-tier table).
- **Recommendations are weather-fragile** (T6.4, T6.8): rank 1 changes in 21–93 % of fields under the what-if scenarios.
- **Heat-wave layer not built** (POWER grid size not in the docs read).
- **Only Kansas, only maize/sorghum hindcast;** 13 fields have no simulatable Current; 15 winter-wheat-only fields have no credibility.
- `hindcast.json` and the ledger are not written by `build-packs`; run `scripts/t72_export.py` afterwards.
- WIMAS (T1.7/T4.6) still open for the user.

Verdict: the gate test passes; the science caveats above must be shown in the app.
