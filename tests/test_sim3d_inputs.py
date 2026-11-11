"""Rotation Builder inputs (<field_id>.sim3d_inputs.json): they reproduce the shipped 3D packs.

The demo packs are committed, so this runs in CI. `reference()` re-runs `sim3d.simulate_weekly`
from the shipped inputs; for every precomputed alternative it must match the pack's weekly series
within the pack's own rounding (soil water/rain/irrigation 0.1 mm, Ks/canopy 0.01) plus 1e-5
for the shipped inputs being rounded to 1e-6 mm/day (a value can sit on a rounding edge).
The browser port is checked against the same function in app/tests/sim3dPhysics.test.ts.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from fieldwitness.packs.sim3d_inputs import CASES, SIM_KEYS, reference, spread_fields
from fieldwitness.packs.validate import model_for
from fieldwitness.schemas import FieldSim3DInputs, check_tagged

DEMO = Path("packs/demo/ks_t14slh")
FILES = sorted(DEMO.glob("*.sim3d_inputs.json"))
HALF = {"soil_water_mm": 0.05, "rain_mm": 0.05, "irrigation_mm": 0.05, "ks": 0.005}
EPS = 1e-5  # shipped inputs are rounded to 1e-6 mm/day

pytestmark = pytest.mark.skipif(not FILES, reason="demo packs without sim3d_inputs")


def test_schema_tags_and_size():
    assert len(FILES) == 200
    for f in FILES[:20]:
        assert model_for(f.name) is FieldSim3DInputs
        obj = FieldSim3DInputs.model_validate_json(f.read_bytes())
        assert check_tagged(obj) == []
        assert set(obj.slots.crops) == set(SIM_KEYS)
        assert set(obj.weather.series) == set(CASES)
        days = obj.weather.series.values()
        assert all(len(d.rain_mm) == 365 and len(d.eto_mm) == 365 for d in days)
        assert f.stat().st_size < 300_000


@pytest.mark.parametrize("f", FILES[::20], ids=lambda p: p.name[:8])
def test_inputs_reproduce_pack_series(f):
    inp = json.loads(f.read_text("utf-8"))
    pack = json.loads((DEMO / f"{inp['field_id']}.sim3d.json").read_text("utf-8"))
    assert inp["weather_year"] == pack["weather_year"]
    alts = pack["alternatives"]
    ref = reference(inp, [tuple(a["sequence"]) for a in alts], inp["region_id"])
    for alt, o in zip(alts, ref["options"], strict=True):
        assert o["crops"] == alt["crops"] and o["stages"] == alt["stages"]
        assert o["root_depth_m"] == alt["root_depth_m"]
        canopy = alt["scenarios"]["t+0_p+0"]["canopy_cover"]
        assert np.max(np.abs(np.subtract(o["canopy_cover"], canopy))) <= 0.005 + EPS
        for case, sid in CASES.items():
            for k, tol in HALF.items():
                d = np.max(np.abs(np.subtract(o["cases"][case][k], alt["scenarios"][sid][k])))
                assert d <= tol + EPS, (alt["option_id"], case, k, d)


def test_spread_fields_covers_blocks():
    import pandas as pd

    pilot = pd.DataFrame(
        {"field_id": list("abcdef"), "block": [1, 1, 2, 2, 3, 3], "lon": [0, 1, 0, 1, 0, 1]}
    )
    assert spread_fields(pilot, 3) == ["a", "c", "e"]
    assert len(spread_fields(pilot, 10)) == 6
