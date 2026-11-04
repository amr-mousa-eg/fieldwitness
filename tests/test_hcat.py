import math

import pandas as pd
import pytest

from fieldwitness.data.hcat import is_annual_arable, normalise

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
