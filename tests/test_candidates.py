from hypothesis import given, settings
from hypothesis import strategies as st

from fieldwitness.config import load_crops
from fieldwitness.rotate import candidates as cd

REGION = "ks_t14slh"
POOL = cd.allowed_crops(REGION)


def test_pool_kansas():
    assert set(POOL) == {"maize", "sorghum", "winter_wheat", "fallow", "cover_crop"}


@settings(deadline=None)  # each call reloads the YAML config
@given(st.sets(st.sampled_from(POOL)))
def test_banned_crop_never_appears(bans):
    for seq in cd.enumerate_candidates(REGION, bans=bans):
        assert not (set(seq) & bans)


def test_family_limit_and_determinism():
    crops = load_crops()
    a = cd.enumerate_candidates(REGION)
    assert a == cd.enumerate_candidates(REGION)
    assert a and all(len(s) == 3 and cd.family_ok(s, crops, 2) for s in a)
    assert ("maize", "sorghum", "winter_wheat") not in a  # three Poaceae in a row
    assert ("maize", "fallow", "sorghum") in a  # fallow breaks the run


@settings(deadline=None)
@given(st.sets(st.sampled_from(POOL)))
def test_non_crop_constraints(bans):
    for seq in cd.enumerate_candidates(REGION, bans=bans):
        nc = [c in cd.NON_CROP_KEYS for c in seq]
        assert not all(nc)
        assert not any(a and b for a, b in zip(nc, nc[1:], strict=False))


def test_non_crop_examples():
    a = cd.enumerate_candidates(REGION)
    assert ("fallow", "fallow", "fallow") not in a
    assert ("maize", "fallow", "cover_crop") not in a
    assert ("fallow", "maize", "fallow") in a


def test_all_banned_gives_empty():
    assert cd.enumerate_candidates(REGION, bans=set(POOL)) == []
