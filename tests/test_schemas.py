"""PLAN.md §3/§3b data contracts: validators and the "no untagged numbers" check."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from fieldwitness import schemas as s


def tg(value=1.0, unit="u", tag="D"):
    return s.Tagged(value=value, unit=unit, tag=tag, source="test")


def ts(x, values, **kw):
    return s.TaggedSeries(x=x, values=values, unit="u", tag="O", source="test", **kw)


def scenario(sid, metrics=None):
    return s.Scenario(
        scenario_id=sid,
        dt_c=0.0,
        dp_pct=0.0,
        metrics=metrics or {"current": {"water_use_mm": tg(400.0, "mm/season")}},
        ranks={"current": 1},
    )


GRID_IDS = [f"t+{t}_p{p:+d}" for t in (0, 1, 2) for p in (-20, -10, 0, 10)]


def pack(**over):
    season = s.Season(
        year=2023,
        crop="winter_wheat",
        crop_conf=0.9,
        crop_source="label",
        sos=tg(-77.0, "day of harvest year", "O"),
        peak=tg(123.0, "day of harvest year", "O"),
        eos=tg(168.0, "day of harvest year", "O"),
        canopy_integral=tg(),
        cover_days=tg(),
        bare_days=tg(),
        clear_obs=40,
    )
    option = s.Option(
        option_id="current",
        sequence=["winter_wheat", "sorghum", "fallow"],
        metrics={"water_use_mm": tg(400.0), "legume_share": tg(0.0)},
        witnesses=[
            s.WitnessResult(
                witness="physics",
                metric="water_use_mm",
                estimate=tg(400.0),
                diagnostics={"rmse": 12.5, "converged": True},
            )
        ],
        grade="B",
        grade_reasons=["two witnesses agree"],
        regret=tg(0.0),
        rank=1,
        explanation=s.Explanation(why=[], evidence=[], benefits=[], gaps=[], risks=[]),
    )
    kw = dict(
        schema_version="1.2-ext",
        field=s.Field(
            field_id="f" * 40,
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 0))",
            area_ha=32.5,
            region_id="ks_t14slh",
            tier=1,
            boundary_source="CSB",
            scale_flags={"HLS": False},
            interior_pixels=310,
        ),
        story=[season],
        credibility=tg(0.7),
        options=[option],
        advice=s.Advice(
            measure_next="soil depth", flip_probability=tg(0.2), counterfactual_flip=""
        ),
        ledger=[],
        data_as_of=date(2024, 12, 31),
        generated_at=datetime(2026, 11, 4, 12, 0),
    )
    kw.update(over)
    return s.FieldPack(**kw)


def test_full_pack_is_tagged():
    # floats in exempt fields (area_ha, crop_conf, diagnostics) are allowed
    assert s.check_tagged(pack()) == []


def test_untagged_float_is_reported_with_its_path():
    bad = pack()
    bad.story[0].__dict__["crop"] = 0.5  # simulate a number leaking outside Tagged
    assert s.check_tagged(bad) == ["$.story[0].crop"]


def test_exempt_fields_include_the_six_q3_additions():
    added = {"bbox_lonlat", "dt_c", "dp_pct", "resolution_km", "years_with_data", "clear_frac"}
    assert added <= s.EXEMPT_FIELDS


def test_tagged_series_lengths_must_match_x():
    ts([1, 2, 3], [0.1, None, 0.3], lo90=[0.0, None, 0.2])
    with pytest.raises(ValidationError, match="values has 2 items, x has 3"):
        ts([1, 2, 3], [0.1, 0.2])
    with pytest.raises(ValidationError, match="hi90"):
        ts([1, 2], [0.1, 0.2], hi90=[0.3])


def test_field_series_dates_must_align_and_has_no_marks():
    d = [date(2023, 3, 1), date(2023, 3, 9)]
    ok = dict(
        schema_version="1.2-ext",
        field_id="f",
        ndvi=ts(d, [0.2, 0.3]),
        evi=ts(d, [0.1, 0.2]),
        clear_frac=[0.9, 0.8],
        ndvi_smooth=ts([date(2023, 3, 1)], [0.25]),
        data_as_of=date(2024, 12, 31),
    )
    series = s.FieldSeries(**ok)
    assert s.check_tagged(series) == []  # clear_frac is exempt
    assert "marks" not in s.FieldSeries.model_fields  # Q2: marks come from FieldPack.story
    with pytest.raises(ValidationError, match="same dates"):
        s.FieldSeries(**{**ok, "clear_frac": [0.9]})
    with pytest.raises(ValidationError, match="same dates"):
        s.FieldSeries(**{**ok, "evi": ts(d[:1] + [date(2023, 3, 10)], [0.1, 0.2])})


def test_bare_month_range():
    s.BareMonth(month=12, bare_share=None, clear_obs=3, years_with_data=2, insufficient=True)
    for m in (0, 13):
        with pytest.raises(ValidationError):
            s.BareMonth(month=m, bare_share=None, clear_obs=3, years_with_data=2, insufficient=True)


def test_scenarios_need_the_twelve_point_grid_and_baseline():
    base = dict(schema_version="1.2-ext", field_id="f", note="n", data_as_of=date(2024, 12, 31))
    grid = [scenario(i) for i in GRID_IDS]
    fs = s.FieldScenarios(baseline_id="t+0_p+0", scenarios=grid, **base)
    assert s.check_tagged(fs) == []  # dt_c, dp_pct exempt; ranks are ints
    with pytest.raises(ValidationError, match="12 scenarios"):
        s.FieldScenarios(baseline_id="t+0_p+0", scenarios=grid[:11], **base)
    with pytest.raises(ValidationError, match="baseline_id"):
        s.FieldScenarios(baseline_id="t+3_p+0", scenarios=grid, **base)


@pytest.mark.parametrize("metric", sorted(s.SEQUENCE_ONLY_METRICS))
def test_scenarios_reject_sequence_only_metrics(metric):
    base = dict(schema_version="1.2-ext", field_id="f", note="n", data_as_of=date(2024, 12, 31))
    grid = [scenario(i) for i in GRID_IDS]
    grid[5] = scenario(GRID_IDS[5], {"current": {metric: tg(0.5)}})
    with pytest.raises(ValidationError, match="weather-independent"):
        s.FieldScenarios(baseline_id="t+0_p+0", scenarios=grid, **base)


def test_region_layers_are_tagged_and_current_only():
    years = [2022, 2023]
    layer = s.RegionalLayer(
        layer_id="grace_tws",
        resolution_km=50.0,
        resolution_source="product doc",
        scale_flag=True,
        grid=s.TaggedGrid(
            years=years,
            cells=[s.GridCell(bbox_lonlat=(-101.0, 37.0, -100.5, 37.5), values=[-1.2, None])],
            unit="cm",
            tag="D",
            source="test",
        ),
        region_mean=ts(years, [-1.0, -1.5]),
        trend=tg(-0.5, "cm/yr"),
    )
    rl = s.RegionLayers(
        schema_version="1.2-ext",
        region_id="ks_t14slh",
        layers=[layer],
        field_colouring={"frost_share": {"f": tg(0.1)}},
        data_as_of=date(2024, 12, 31),
    )
    assert s.check_tagged(rl) == []
    assert "colouring_option" not in s.RegionLayers.model_fields  # Q5: Current only


def test_region_files_validate():
    idx = s.RegionIndex(
        schema_version="1.2-ext",
        region_id="ks_t14slh",
        name="Kansas",
        tier=1,
        bbox_lonlat=(-101.3, 37.8, -100.0, 38.8),
        basemap=None,
        fields=[
            s.FieldSummary(
                field_id="f",
                geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 0))",
                area_ha=12.0,
                current_sequence=["maize"],
                top_option_id="current",
                top_grade="A",
            )
        ],
        data_as_of=date(2024, 12, 31),
    )
    hc = s.RegionHindcast(
        schema_version="1.2-ext",
        region_id="ks_t14slh",
        cutoff=date(2021, 12, 31),
        scored_years=[2022, 2023, 2024],
        crop_observed_source="label",
        rows=[
            s.HindcastRow(method="B0", mode="forecast", metric="sos", n=10, scores={"crps": 1.5})
        ],
        story_field_id="f",
        data_as_of=date(2024, 12, 31),
    )
    regions = s.RegionList(regions=[s.RegionEntry(region_id="ks_t14slh", name="Kansas", tier=1)])
    for m in (idx, hc, regions):
        assert s.check_tagged(m) == []
