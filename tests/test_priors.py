import numpy as np
import pytest

from fieldwitness.infer import priors


def test_bounds_and_types():
    cfg = priors.load()
    s = priors.sample(5000)
    assert set(s) == set(priors.VARIABLES)
    assert s["sow_offset_days"].min() >= cfg["sow_offset_days"]["low"]
    assert s["sow_offset_days"].max() <= cfg["sow_offset_days"]["high"]
    assert s["taw_scale"].min() >= cfg["taw_scale"]["low"]
    assert s["taw_scale"].max() <= cfg["taw_scale"]["high"]
    assert s["kc_mid_scale"].min() >= cfg["kc_mid_scale"]["low"]
    assert s["kc_mid_scale"].max() <= cfg["kc_mid_scale"]["high"]


def test_irrigation_consistent():
    s = priors.sample(5000)
    assert np.all(s["irrigation_mm"][~s["irrigated"]] == 0)
    assert np.all(s["irrigation_mm"][s["irrigated"]] >= 50)
    assert abs(s["irrigated"].mean() - 0.5) < 0.03


def test_taw_scale_symmetric_on_log_scale():
    s = priors.sample(20000)
    assert abs(np.median(np.log(s["taw_scale"]))) < 0.03


def test_seeded():
    a, b = priors.sample(100), priors.sample(100)
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert not np.array_equal(a["taw_scale"], priors.sample(100, seed=1)["taw_scale"])


def test_reason_required(tmp_path):
    p = tmp_path / "p.yaml"
    cfg = priors.load()
    cfg["taw_scale"].pop("reason")
    import yaml

    p.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):
        priors.load(p)
