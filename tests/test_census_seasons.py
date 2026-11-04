import datetime as dt

from fieldwitness.census import season_window


def test_same_year_season():
    assert season_window(4, 10, 2020) == (dt.date(2020, 4, 1), dt.date(2020, 10, 31))


def test_cross_year_season_is_named_by_harvest_year():
    # Winter wheat Sep-Jul harvested in 2020 starts in Sep 2019 (PLAN.md T2.2 harvest-year rule).
    assert season_window(9, 7, 2020) == (dt.date(2019, 9, 1), dt.date(2020, 7, 31))
    assert season_window(11, 4, 2020) == (dt.date(2019, 11, 1), dt.date(2020, 4, 30))


def test_month_end_handles_february_and_leap_years():
    assert season_window(1, 2, 2020)[1] == dt.date(2020, 2, 29)
    assert season_window(1, 2, 2021)[1] == dt.date(2021, 2, 28)
