"""T2.5 bare-soil calendar from HLS history (tag O per PLAN.md T2.5).

Rule (team choice, config/story.yaml): a field-year-month is *bare* when the median NDVI of its
clear observations in that month is below cover.ndvi_threshold. Per calendar month the share is
bare years / years with >= 1 clear observation, over years >= first_year. A month with fewer than
min_clear_obs_per_month observations (all years) or fewer than min_years_with_data years is marked
insufficient and gets no value (never filled).
"""

import pandas as pd

from fieldwitness.schemas import BareMonth, Tagged
from fieldwitness.story.smooth import load_story

SOURCE = "HLS L30/S30 NDVI, clear pixels, monthly median < cover threshold"


def bare_calendar(series: pd.DataFrame, cfg: dict | None = None) -> list[BareMonth]:
    """series: one field, columns date, ndvi (clear-observation field medians). Returns 12 items."""
    cfg = cfg or load_story()
    thr = cfg["cover"]["ndvi_threshold"]
    bc = cfg["bare_calendar"]
    d = series.dropna(subset=["ndvi"]).copy()
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d = d[d["year"] >= bc["first_year"]]
    out: list[BareMonth] = []
    for m in range(1, 13):
        dm = d[d["month"] == m]
        per_year = dm.groupby("year")["ndvi"].median()
        n_obs, n_years = len(dm), len(per_year)
        insufficient = n_obs < bc["min_clear_obs_per_month"] or n_years < bc["min_years_with_data"]
        share = None
        if not insufficient:
            share = Tagged(
                value=float((per_year < thr).mean()),
                unit="share of years",
                tag="O",
                source=SOURCE,
            )
        out.append(
            BareMonth(
                month=m,
                bare_share=share,
                clear_obs=int(n_obs),
                years_with_data=int(n_years),
                insufficient=bool(insufficient),
            )
        )
    return out
