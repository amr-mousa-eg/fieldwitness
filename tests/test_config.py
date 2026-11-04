import pytest

from fieldwitness.config import CropsFile, Param, _params, load_crops, load_grading, load_regions

SELECTED = ("ks_t14slh", "fr_toulouse_t31tcj", "ua_central_t36uvu")


def test_crops_yaml_validates_and_every_number_has_provenance():
    crops = load_crops()
    for key, crop in crops.crops.items():
        for p in _params(crop):
            if p.verified:
                assert p.ref is not None, key
            else:
                assert p.value is None and p.range is None and p.note, key


def test_regions_reference_existing_crops_and_stage_lengths():
    crops = load_crops().crops
    regions = load_regions()
    for rid in SELECTED:
        r = regions[rid]
        assert r.status == "selected" and r.bbox_lonlat and len(r.bbox_lonlat) == 4
        for c in r.crops or []:
            assert c in crops, f"{rid}: unknown crop {c}"
            if c not in ("fallow", "cover_crop"):
                assert rid in crops[c].stage_lengths_days, f"{rid}: no stage lengths for {c}"


def test_grading_has_scale_flag_and_interior_rule():
    g = load_grading()
    assert g["scale_flag"]["pixel_area_ratio"] == 4
    assert g["interior_pixels"] == {"buffer_m": 15, "min_pixels": 4}


def test_unverified_parameter_with_a_number_is_rejected():
    with pytest.raises(ValueError):
        Param(value=1.0, verified=False, note="from memory")


def test_verified_parameter_without_ref_is_rejected():
    with pytest.raises(ValueError):
        Param(value=1.0, verified=True)


def test_crops_file_rejects_unknown_source():
    raw = {
        "sources": {},
        "crops": {
            "x": {
                "name": "x",
                "hcat3": [],
                "kc_ini": {
                    "value": 0.3,
                    "verified": True,
                    "ref": {"source": "nope", "table": 12, "row": "r"},
                },
                "kc_mid": {"verified": False, "note": "n"},
                "kc_end": {"verified": False, "note": "n"},
                "stage_lengths_days": {},
            }
        },
    }
    with pytest.raises(ValueError):
        CropsFile.model_validate(raw)
