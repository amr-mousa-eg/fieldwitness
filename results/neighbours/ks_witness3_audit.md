# Kansas (`ks_t14slh`) Witness 3 Causal Diagnostics & Safety Audit (E2.2)

- **Witness 3 Production Status:** **`OFF`** (verified `0` active neighbours witnesses across all `200` shipped `packs/demo/ks_t14slh` packs; Grade A blocked by design -> max **Grade B**).

| Causal Design | Rows | Fitted | Balance Pass | All 4 Gates Passing |
|---|---|---|---|---|
| Primary DoubleML (`T5.3`) | 144 | 92 | 0/92 | **0** |
| Matching-History DoubleML (`T5.xa`) | 72 | 32 | 8/32 | **0** |
| DAPSM Spatial Matching (`T5.xb`, w*=0.0) | 12 | 4 | 0/4 | **0** |

## Honest Verdict (`CLAUDE.md` Rule 9)

Kansas Witness 3 stays strictly OFF (0/92 primary DML, 0/32 matching DML, 0/4 DAPSM). Rotational crop-history autocorrelation and missing irrigation ground labels violate balance and placebo checks. Panel-OBDML (<=t-3 residual + explicit year + ATO weighting) succeeded in Central Ukraine (30 pre-cutoff contrasts) and requires the local Kansas field_season parquet to test on KS.
