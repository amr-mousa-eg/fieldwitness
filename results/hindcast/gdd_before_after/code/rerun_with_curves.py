"""Re-run scripts/x2_gdd_hindcast.py unchanged, plus a read-only hook that keeps daily curves.

Usage: uv run python -u results/hindcast/gdd_before_after/code/rerun_with_curves.py <calendar|gdd>
Pre-registered in DECISIONS.md (2026-11-12, "GDD before/after presentation").

The runner's source is read and executed with three in-memory text changes, none of which
draws random numbers or changes a score:
  1. records go to a scratch file (the published Experiment 2 records are never written);
  2. `predict` also stores the full daily model NDVI of its S samples;
  3. after each prediction the 5/50/95 % daily quantiles are appended to a list.
Afterwards the scratch records must equal results/hindcast/gdd/records_<mode>.jsonl exactly,
otherwise the curves are discarded. Curves are model canopy NDVI without sensor noise (tag D).
"""

import json
import sys
from pathlib import Path

import numpy as np

MODE = sys.argv[1]
assert MODE in ("calendar", "gdd")
HERE = Path("results/hindcast/gdd_before_after")
SCRATCH = HERE / f"_scratch_records_{MODE}.jsonl"
SCRIPT = Path("scripts/x2_gdd_hindcast.py")

src = SCRIPT.read_text("utf-8")


def rep(old: str, new: str) -> None:
    global src
    assert src.count(old) == 1, old
    src = src.replace(old, new)


rep('REC = OUT / f"records_{MODE}.jsonl"', f"REC = Path({str(SCRATCH)!r})")
rep(
    "    sim = np.zeros((len(doy), S))\n",
    "    sim = np.zeros((len(doy), S))\n    FULL = np.zeros((365, S))\n",
)
rep(
    '        sim[:, m] = out["ndvi"][doy - 1, :]\n',
    '        sim[:, m] = out["ndvi"][doy - 1, :]\n        FULL[:, m] = out["ndvi"]\n',
)
rep(
    "    sim = np.clip(sim + rng.normal(0.0, noise, sim.shape), -1.0, 1.0)\n",
    "    CURVES.append(np.quantile(FULL, [0.05, 0.5, 0.95], axis=1).astype(np.float32))\n"
    "    sim = np.clip(sim + rng.normal(0.0, noise, sim.shape), -1.0, 1.0)\n",
)
if SCRATCH.exists():
    SCRATCH.unlink()
CURVES: list = []
sys.argv = [str(SCRIPT), "2000", "100", "1000000000", MODE]
ns = {"__name__": "__main__", "__file__": str(SCRIPT), "CURVES": CURVES}
exec(compile(src, str(SCRIPT), "exec"), ns)

new = SCRATCH.read_text("utf-8")
old = (Path("results/hindcast/gdd") / f"records_{MODE}.jsonl").read_text("utf-8")
same = new == old
keys = []
for line in new.splitlines():
    if not line:
        continue
    r = json.loads(line)
    for s in r["seasons"]:
        for mode in ("forecast", "forced"):
            if mode in s:
                keys.append(f"{r['field_id']}|{s['year']}|{s['crop']}|{mode}")
assert len(keys) == len(CURVES), (len(keys), len(CURVES))
check = {"mode": MODE, "records_identical_to_experiment_2": same, "n_predictions": len(keys)}
(HERE / f"rerun_check_{MODE}.json").write_text(json.dumps(check, indent=1), "utf-8")
if same:
    np.savez_compressed(HERE / f"curves_{MODE}.npz", keys=np.array(keys), q=np.stack(CURVES))
SCRATCH.unlink()
print(json.dumps(check))
