"""T5.2: run double ML on the T5.1 table -> results/neighbours/effects.csv."""

from pathlib import Path

import pandas as pd

from fieldwitness.neighbours.dml import run_all

TABLE = Path("data/neighbours/ks_t14slh_field_season.parquet")
OUT = Path("results/neighbours/effects.csv")

if __name__ == "__main__":
    df = pd.read_parquet(TABLE)
    res = run_all(df)
    res.to_csv(OUT, index=False)
    ok = res.dropna(subset=["effect"])
    sig = ok[(ok.ci_low > 0) | (ok.ci_high < 0)]
    print(f"rows {len(res)}, fitted {len(ok)}, CI excludes 0: {len(sig)}")
