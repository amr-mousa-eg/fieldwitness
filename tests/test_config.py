import pytest

from fieldwitness.config import (
    CropsFile,
    Param,
    _params,
    load_crops,
    load_grading,
    load_regions,
    rotation_options,
)

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


def test_rotation_options_have_verified_ky_and_stage_lengths():
    """A crop offered as an MVP rotation option needs a verified Ky (for RYI) and verified stage
    lengths in every selected region that lists it (user decisions 2026-11-04)."""
    crops = load_crops()
    regions = load_regions()
    for rid in SELECTED:
        for c in rotation_options(crops, regions[rid].crops or []):
            crop = crops.crops[c]
            if crop.mvp_role == "rotation_no_yield":
                continue
            assert crop.ky is not None and crop.ky.verified, f"{c}: rotation option without Ky"
            stages = crop.stage_lengths_days.get(rid)
            assert stages is not None and stages.verified, f"{rid}/{c}: no verified stages"


def test_barley_and_rapeseed_are_not_rotation_options():
    crops = load_crops()
    assert crops.crops["rapeseed"].mvp_role == "history_only"
    assert crops.crops["winter_barley"].mvp_role == "prediction_only"
    assert crops.crops["spring_barley"].mvp_role == "prediction_only"
    toulouse = load_regions()["fr_toulouse_t31tcj"].crops
    assert "rapeseed" not in rotation_options(crops, toulouse)
    assert "winter_barley" not in rotation_options(crops, toulouse)
