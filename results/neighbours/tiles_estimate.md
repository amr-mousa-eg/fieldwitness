# T5.xb Surrounding Tiles HLS Download Estimation

Source: `scripts/t5xb_estimate_tiles.py` -> `results/neighbours/tiles_estimate.json`.
Rule: CLAUDE.md Rule 11 (1 GB download cap per run). Stop if > 1 GB.

## Baseline (T14SLH)

- Pilot fields: 200
- On-disk HLS data: 330 files, 1255.9 MB (1.23 GB)
- Average per field: 6.28 MB/field (2016-2024, 30 m HLS-VI + Fmask)

## Surrounding Tiles Candidate Grid

- Target MGRS tiles (8 surrounding 100 km squares): 14SLJ, 14SLG, 14SKH, 14SMH, 14SKJ, 14SMJ, 14SKG, 14SMG
- 1 additional tile (200 fields): **1.23 GB** (> 1.0 GB cap)
- 4 cardinal tiles (800 fields): **4.91 GB** (>> 1.0 GB cap)
- 8 full ring tiles (1,600 fields): **9.81 GB**

## Conclusion & Recommendation

**Status: STOP**.
Even a single additional tile (~1.23 GB) exceeds the 1.0 GB download cap (CLAUDE.md rule 11). Full 8-tile ring would require ~9.8 GB.

Without user authorization for a multi-gigabyte download exception (similar to the
2026-11-04 T1.5 exception), tile expansion cannot proceed under the 1 GB cap.
Consequently, T5.xc (re-grading) is skipped because no contrast passed diagnostics.