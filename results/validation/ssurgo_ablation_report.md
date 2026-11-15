# Phase P1 (E1.2): Observed USDA SSURGO [E] Upgrade Report (Kansas `ks_t14slh`)

Switched all 200 Kansas pilot fields from the `150 mm [A]` prior TAW assumption to empirical USDA-NRCS SSURGO AWS `0–135 cm` (`[E]`, `n=198`, median `282.1 mm`) with ISRIC SoilGrids 2.0 Saxton & Rawls (`[E]`) fallback on the `2` shallow profiles (`71b9fde5`: `149.8 mm`, `189e2365`: `187.1 mm`).

## Before (150 mm [A]) vs After (SSURGO [E]) Summary

| Metric | Before (`150 mm [A]`) | After (`SSURGO [E]`) |
|---|---|---|
| In-sample credibility median | `0.5` (`42.7%` >= 0.6) | `0.483` (`38.9%` >= 0.6) |
| Option grades (`B / C / D`) | `2772 / 3600 / 360` | `2912 / 3532 / 396` |
| Top option grade counts (`B / C / D`) | `—` | `77 / 102 / 11` |
| Canopy integral Spearman rho (`forecast`) | `0.264` (`n=266`) | `0.262` (`n=463`) |
| Canopy integral CRPS (`forecast`) | `14.87` | `17.86` |
| Peak timing CRPS / MAE (`forecast`) | `11.47` / `15.5 d` | `27.31` / `33.5 d` |
| Grade B vs D CRPS diff CI95 | `[-3.2777, 14.3151]` | `[-1.5354, 13.9383]` |
