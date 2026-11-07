"""T5.3: diagnostics for the T5.2 contrasts -> results/neighbours/diagnostics.csv."""

from pathlib import Path

import pandas as pd

from fieldwitness.neighbours.diagnostics import run_diagnostics

TABLE = Path("data/neighbours/ks_t14slh_field_season.parquet")
EFFECTS = Path("results/neighbours/effects.csv")
OUT = Path("results/neighbours/diagnostics.csv")

if __name__ == "__main__":
    res = run_diagnostics(pd.read_parquet(TABLE), pd.read_csv(EFFECTS))
    res.to_csv(OUT, index=False)
    fit = res.dropna(subset=["effect"])
    print(f"fitted {len(fit)}, shown as evidence {int(fit.show_as_evidence.sum())}")
    for k in ("placebo_status", "negctrl_status", "overlap_status", "balance_status"):
        print(k, fit[k].value_counts().to_dict())
