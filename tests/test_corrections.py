import pytest

from fieldwitness.rotate.corrections import (
    RERUN_NEEDED,
    Corrections,
    apply_corrections,
    correction_key,
)
from fieldwitness.rotate.current import CurrentRotation

ALLOWED = {"maize", "sorghum", "winter_wheat"}


def _cur():
    return CurrentRotation(
        field_id="f1",
        years=(2022, 2023, 2024),
        sequence=["maize", "sorghum", "alfalfa"],
        confidence=1.0,
        simulatable=False,
        gaps=["2024: 'alfalfa' is not simulated (no rotation-option parameters)"],
    )


def test_crop_correction_changes_current_and_keeps_original():
    r = apply_corrections(_cur(), Corrections(crop_by_year={2024: "winter_wheat"}), ALLOWED, set())
    assert r.corrected.sequence == ["maize", "sorghum", "winter_wheat"]
    assert r.original.sequence[-1] == "alfalfa"
    assert r.source_by_year == {2022: "label", 2023: "label", 2024: "farmer"}
    assert r.corrected.simulatable and r.corrected.gaps == []
    assert r.needs_rerun and RERUN_NEEDED in r.notes


def test_precomputed_alternative_avoids_rerun():
    corr = Corrections(crop_by_year={2024: "winter_wheat"})
    r = apply_corrections(_cur(), corr, ALLOWED, {correction_key(corr)})
    assert not r.needs_rerun


def test_sowing_and_irrigation_need_rerun_and_keep_sequence():
    corr = Corrections(sowing_day={2023: 120}, irrigated=True)
    r = apply_corrections(_cur(), corr, ALLOWED)
    assert r.corrected.sequence == _cur().sequence
    assert r.needs_rerun


def test_unknown_year_rejected():
    with pytest.raises(ValueError):
        apply_corrections(_cur(), Corrections(crop_by_year={1999: "maize"}), ALLOWED)


def test_no_correction_is_identity():
    r = apply_corrections(_cur(), Corrections(), ALLOWED)
    assert r.corrected == r.original and not r.needs_rerun
