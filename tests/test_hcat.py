import math

import pandas as pd
import pytest

from fieldwitness.data.hcat import history_state, is_annual_arable, normalise, stays_arable

# Codes and names from the official HCAT3.csv (EuroCrops hcat_core) and fiboa fr.csv.


@pytest.mark.parametrize(
    "code",
    [
        3301010000,  # cereal
        3301160000,  # soy_soybeans
        3301061298,  # unspecified aromatic plants (fiboa fr.csv)
        3301083900,  # safflower (sibling of miscanthus; must stay)
        "3301990000",  # other_arable_land_crops
    ],
)
def test_kept(code):
    assert is_annual_arable(code)


@pytest.mark.parametrize(
    "code",
    [
        3302000000,  # pasture_meadow_grassland_grass
        3303040000,  # citrus_plantations (permanent crop)
        3303120000,  # unspecified_permanent_crops
        3399000000,  # not_known_and_other
        3301110000,  # fallow_land_not_crop
        3301090100,  # temporary_grass
        3301090205,  # lolium_ryegrass
        3301083000,  # miscanthus_silvergrass
        3301200000,  # asparagus
        3301130000,  # strawberries
        None,
        math.nan,
        pd.NA,
    ],
)
def test_excluded(code):
    assert not is_annual_arable(code)


def test_normalise():
    assert normalise(3301010000) == "3301010000"
    assert normalise("  3301010000 ") == "3301010000"
    assert normalise(None) is None


WHEAT = 3301010101  # winter_common_soft_wheat (HCAT3.csv)
FALLOW_CODE = 3301110000  # fallow_land_not_crop
GRASSLAND = 3302000000  # pasture_meadow_grassland_grass


def test_history_wheat_fallow_wheat_keeps_fallow_as_a_state():
    history = [WHEAT, FALLOW_CODE, WHEAT]
    assert [history_state(c) for c in history] == ["3301010101", "fallow", "3301010101"]
    assert stays_arable(history)
    # Selection on the most recent year is unaffected by the fallow year in between.
    assert is_annual_arable(history[-1])


def test_history_temporary_grass_and_unknown_are_states():
    assert history_state(3301090100) == "temporary_grass"
    assert history_state(3301090205) == "temporary_grass"  # lolium_ryegrass ley
    assert history_state(None) == "unknown"
    assert history_state(3301200000) == "other_arable"  # asparagus
    assert stays_arable([WHEAT, 3301090100, None, WHEAT])


def test_field_leaving_arable_use_is_removed_from_history():
    assert history_state(GRASSLAND) is None
    assert not stays_arable([WHEAT, GRASSLAND, WHEAT])


NOT_KNOWN = 3399000000  # not_known_and_other


def test_history_unknown_year_does_not_remove_field():
    assert history_state(NOT_KNOWN) == "unknown"
    assert stays_arable([WHEAT, NOT_KNOWN, WHEAT])
    assert stays_arable([WHEAT, None, WHEAT])


@pytest.mark.parametrize("group_code", [3302000000, 3303040000, 3306000000, 3308000000])
def test_non_arable_groups_remove_field(group_code):
    assert history_state(group_code) is None
    assert not stays_arable([WHEAT, group_code, WHEAT])
