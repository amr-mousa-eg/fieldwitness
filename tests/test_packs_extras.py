from datetime import date

import numpy as np
import pandas as pd
import xarray as xr

from fieldwitness.packs import extras as X
from fieldwitness.schemas import check_tagged


def test_bare_by_option_fallow_always_bare_and_crop_not():
    fallow = np.zeros(2 * 365)
    crop = np.ones(2 * 365)
    out = X.bare_by_option({"fallow": fallow, "crop": crop})
    assert out["fallow"].values == [1.0] * 12
    assert out["crop"].values == [0.0] * 12
    assert out["fallow"].tag == "D" and len(out["fallow"].x) == 12


def test_worst_month_share_none_when_empty():
    assert X.worst_month_share([], "frost") is None


def test_regions_list_and_smap_layer_tagged():
    rl = X.regions_list([("ks_t14slh", "Kansas", 1)])
    assert rl.regions[0].tier == 1
    rows = [
        {"region_id": "r", "month": f"{y}-{m:02d}", "anomaly": 0.01 * (y - 2016)}
        for y in (2016, 2017, 2018)
        for m in range(1, 13)
    ]
    lay = X.smap_layer(pd.DataFrame(rows), -100.0, 38.0)
    assert lay.scale_flag and lay.grid.years == [2016, 2017, 2018]
    assert abs(lay.trend.value - 0.01) < 1e-6
    assert check_tagged(lay) == []


def test_grace_csr_layer_synthetic_netcdf(tmp_path):
    dates = pd.date_range("2002-06-15", "2006-12-15", freq="MS")
    days_since = (dates - pd.Timestamp("2002-01-01")).days.astype(float)
    lats = np.array([47.875, 48.125])
    lons = np.array([31.875, 32.125])
    # Cell (i, j=0) is land (1.0), cell (i, j=1) is ocean (0.0)
    mask_arr = np.array([[1.0, 0.0], [1.0, 0.0]])
    data_arr = np.zeros((len(days_since), 2, 2), dtype=float)
    for k, dt_k in enumerate(dates):
        data_arr[k, :, 0] = -2.0 * (dt_k.year - 2003)
        data_arr[k, :, 1] = 999.0  # ocean cell must be excluded

    nc = tmp_path / "csr.nc"
    mk = tmp_path / "mask.nc"
    xr.Dataset(
        {"lwe_thickness": (("time", "lat", "lon"), data_arr)},
        coords={"time": days_since, "lat": lats, "lon": lons},
    ).to_netcdf(nc, engine="h5netcdf")
    xr.Dataset(
        {"LO_val": (("lat", "lon"), mask_arr)},
        coords={"lat": lats, "lon": lons},
    ).to_netcdf(mk, engine="h5netcdf")

    lay = X.grace_csr_layer(
        str(nc), str(mk), (31.7, 47.7, 32.3, 48.3), cutoff_date=date(2005, 12, 31)
    )
    assert lay.layer_id == "grace_tws"
    assert lay.scale_flag
    assert len(lay.grid.cells) == 2  # ocean cells excluded
    assert lay.grid.years == [2003, 2004, 2005]  # 2002 partial dropped, 2006 past cutoff
    assert lay.region_mean.values == [0.0, -2.0, -4.0]
    assert abs(lay.trend.value - (-2.0)) < 1e-6
    assert check_tagged(lay) == []


def test_heatwave_layer_merra2_cells_and_cutoff():
    cells = X.merra2_cells((31.7, 47.8, 32.1, 48.1))
    assert len(cells) == 1
    lon_c, lat_c, box = cells[0]
    assert (lon_c, lat_c) == (31.875, 48.0)
    assert box == (31.5625, 47.75, 32.1875, 48.25)

    idx = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    tmax = np.full(len(idx), 20.0)
    for y, n_hot in ((2020, 5), (2021, 10), (2022, 15), (2023, 30)):
        mask = idx.year == y
        hot_pos = np.where(mask)[0][:n_hot]
        tmax[hot_pos] = 36.0
    df = pd.DataFrame({"T2M_MAX": tmax}, index=idx)

    lay = X.heatwave_layer(
        (31.7, 47.8, 32.1, 48.1),
        threshold_c=35.0,
        cutoff_date=date(2022, 12, 31),
        loader=lambda _lo, _la: (df, 100.0),
    )
    assert lay.layer_id == "heatwave_days"
    assert lay.scale_flag
    assert lay.grid.years == [2020, 2021, 2022]
    assert lay.region_mean.values == [5.0, 10.0, 15.0]
    assert abs(lay.trend.value - 5.0) < 1e-6
    assert check_tagged(lay) == []


def test_vulnerability_skips_unconfigured_region_crops():
    idx = pd.date_range("2020-01-01", "2021-12-31", freq="D")
    wx = pd.DataFrame(
        {
            "T2M_MAX": np.full(len(idx), 28.0),
            "T2M_MIN": np.full(len(idx), 10.0),
            "PRECTOTCORR": np.full(len(idx), 2.0),
        },
        index=idx,
    )
    eto = pd.Series(3.5, index=idx)
    cfg = X.load_vuln_cfg()

    ua = X.vulnerability(
        wx,
        eto,
        ["winter_wheat", "maize", "sunflower", "soybean", "winter_barley", "rapeseed"],
        "ua_central_t36uvu",
        cfg,
        taw_mm=200.0,
        kc_scale=1.0,
    )
    assert [v.crop for v in ua] == ["winter_wheat", "maize", "sunflower", "soybean"]
    assert check_tagged(ua) == []

    ks = X.vulnerability(
        wx,
        eto,
        ["winter_wheat", "maize", "sunflower", "soybean"],
        "ks_t14slh",
        cfg,
        taw_mm=280.0,
        kc_scale=1.0,
    )
    assert [v.crop for v in ks] == ["winter_wheat", "maize"]


def test_obs_checks_series_and_field_calendar_tagged():
    lst_df = pd.DataFrame(
        [
            {"field_id": "f1", "date": "2020-07-10", "lst_c": 37.5},
            {"field_id": "f1", "date": "2021-07-12", "lst_c": 32.0},
            {"field_id": "f1", "date": "2020-08-05", "lst_c": 38.2},
        ]
    )
    era_dates = pd.date_range("2020-01-01", "2021-12-31", freq="D")
    rain = np.zeros(len(era_dates), dtype=float)
    rain[(era_dates.year == 2020) & (era_dates.month == 6) & (era_dates.day == 15)] = 42.0
    era_df = pd.DataFrame({"date": era_dates, "rain_mm": rain})

    checks = X.obs_checks_series(field_lst=lst_df, era5_df=era_df, heat_threshold_c=35.0)
    assert checks is not None
    assert set(checks.keys()) == {"lst_heat", "extreme_rain_era5"}
    # Month 7 has 2 years (2020 hot, 2021 cool -> 0.5); Month 8 has only 1 year -> None
    assert checks["lst_heat"].tag == "O"
    assert checks["lst_heat"].values[6] == 0.5
    assert checks["lst_heat"].values[7] is None
    # June extreme rain occurred in 1 of 2 years -> 0.5
    assert checks["extreme_rain_era5"].tag == "E"
    assert checks["extreme_rain_era5"].values[5] == 0.5

    cal = X.field_calendar(
        "f1",
        bare_obs=[],
        obs_years=(2017, 2024),
        by_option={},
        vuln=[],
        as_of=date(2024, 12, 31),
        obs_checks=checks,
    )
    assert check_tagged(cal) == []


def test_build_option_deltas_for_demo_packs():
    from pathlib import Path

    for region_id in ("ks_t14slh", "ua_central_t36uvu"):
        rdir = Path("packs/demo") / region_id
        od_path = rdir / "option_deltas.json"
        if not od_path.exists():
            continue
        built = X.build_option_deltas_for_region(rdir)
        loaded = X.RegionOptionDeltas.model_validate_json(od_path.read_bytes())
        assert loaded == built
        assert check_tagged(loaded) == []
        assert len(loaded.fields) == loaded.n_fields
        for fid, entry in loaded.fields.items():
            assert entry.field_id == fid
            assert set(entry.deltas.keys()) == {
                "delta_water_use_mm",
                "delta_bad_year_water_mm",
                "delta_bare_months",
                "delta_ryi",
                "delta_erosion_exposure",
            }
            for tag_v in entry.deltas.values():
                assert tag_v.tag in ("O", "D", "E", "A")
                assert tag_v.source
        for s in loaded.summary.values():
            assert 0 <= s.improved_count <= s.valid_count <= loaded.n_fields
