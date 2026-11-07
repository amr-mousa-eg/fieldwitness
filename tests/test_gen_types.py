"""T8.2: app/src/types.ts must match the Pydantic schemas (regenerate with scripts/gen_types.py)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_types_ts_is_current():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_types.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
