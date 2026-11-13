"""Unit tests for Tier 3 Ukraine causal crop-sequence classifier (`story.ukraine_seasons`)."""

import numpy as np
import pandas as pd

from fieldwitness.story.ukraine_seasons import classify_season, infer_region_labels, season_features


def _synth_year(year: int, peak_doy: float, peak_ndvi: float = 0.78, spread: float = 28.0):
    dates = pd.date_range(f"{year}-03-01", f"{year}-11-15", freq="8D")
    doy = dates.day_of_year.to_numpy(float)
    ndvi = 0.18 + (peak_ndvi - 0.18) * np.exp(-0.5 * ((doy - peak_doy) / spread) ** 2)
    return dates, ndvi


def test_classifies_winter_wheat_vs_summer_crops_and_fallow():
    # Winter wheat peaking around DOY 150 (late May / early June)
    d_w, v_w = _synth_year(2020, peak_doy=150, peak_ndvi=0.80, spread=25.0)
    f_w = season_features(d_w, v_w, 2020)
    assert f_w is not None
    c_w, conf_w = classify_season(f_w)
    assert c_w == "winter_wheat" and conf_w >= 0.65

    # Sunflower peaking ~DOY 201 and senescing earlier
    d_s, v_s = _synth_year(2020, peak_doy=200, peak_ndvi=0.76, spread=24.0)
    f_s = season_features(d_s, v_s, 2020)
    c_s, _ = classify_season(f_s)
    assert c_s == "sunflower"

    # Maize peaking ~DOY 222 with longer grain-fill tail
    d_m, v_m = _synth_year(2020, peak_doy=225, peak_ndvi=0.82, spread=36.0)
    f_m = season_features(d_m, v_m, 2020)
    c_m, _ = classify_season(f_m)
    assert c_m == "maize"

    # Fallow staying below 0.40 NDVI
    d_f, v_f = _synth_year(2020, peak_doy=180, peak_ndvi=0.28, spread=30.0)
    f_f = season_features(d_f, v_f, 2020)
    c_f, _ = classify_season(f_f)
    assert c_f == "fallow"


def test_classifier_is_strictly_causal_on_past_years():
    # Altering 2022 observations must have zero effect on 2020/2021 inferred labels
    d20, v20 = _synth_year(2020, peak_doy=150)
    d21, v21 = _synth_year(2021, peak_doy=225, spread=36.0)
    d22, v22 = _synth_year(2022, peak_doy=180, peak_ndvi=0.25)
    df_a = pd.DataFrame(
        {
            "field_id": "f1",
            "date": np.concatenate([d20, d21, d22]),
            "ndvi": np.concatenate([v20, v21, v22]),
        }
    )
    df_b = pd.DataFrame(
        {"field_id": "f1", "date": np.concatenate([d20, d21]), "ndvi": np.concatenate([v20, v21])}
    )
    lab_a = infer_region_labels(df_a, years=[2020, 2021])
    lab_b = infer_region_labels(df_b, years=[2020, 2021])
    assert lab_a.equals(lab_b)
    assert (lab_a["crop_source"] == "classifier").all()
