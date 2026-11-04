from fieldwitness.data.labels import label_of

ALIASES = {"Corn": "maize", "Winter Wheat": "winter_wheat", "Fallow/Idle Cropland": "fallow"}


def test_alias_double_crop_and_states():
    assert label_of("Corn", 3301010600, ALIASES) == ("maize", None)
    assert label_of("Dbl Crop WinWht/Sorghum", 3301010101, ALIASES) == ("winter_wheat", "sorghum")
    assert label_of("Triticale", 3301010800, ALIASES) == ("other_annual", None)
    assert label_of("Grass/Pasture", 3302000000, ALIASES) == ("non_arable", None)
    assert label_of("Alfalfa", 3301090301, ALIASES) == ("perennial_forage", None)
    assert label_of(None, None, ALIASES) == ("unknown", None)
