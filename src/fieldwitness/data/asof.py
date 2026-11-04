"""The `as_of` guard (PLAN.md T1.1, CLAUDE.md rule 6): no data dated after the cut-off may be read.

Usage:
    with as_of(date(2021, 12, 31)):
        df = power.read(...)          # readers clip their request and call guard()

Readers must (1) clip what they request with `limit_end`, and (2) call `guard` on the dates they
return; `guard` raises LeakageError for any record after the cut-off. The single exception is the
forced-mode hindcast weather (PLAN.md Phase 7): inside `forcing_weather()`, readers registered as
weather readers may return post-cut-off records, through that explicitly named channel only.
"""

import datetime as dt
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from contextvars import ContextVar

_CUTOFF: ContextVar[dt.date | None] = ContextVar("as_of_cutoff", default=None)
_FORCING: ContextVar[bool] = ContextVar("forcing_weather", default=False)

#: Registry of data readers checked by tests/test_leakage.py: name -> (callable, is_weather).
READERS: dict[str, tuple[Callable, bool]] = {}


class LeakageError(RuntimeError):
    """A reader returned data dated after the active `as_of` cut-off."""


@contextmanager
def as_of(cutoff: dt.date):
    token = _CUTOFF.set(cutoff)
    try:
        yield cutoff
    finally:
        _CUTOFF.reset(token)


@contextmanager
def forcing_weather():
    """Phase 7 forced mode: weather readers may return post-cut-off days in this block only."""
    token = _FORCING.set(True)
    try:
        yield
    finally:
        _FORCING.reset(token)


def cutoff() -> dt.date | None:
    return _CUTOFF.get()


def limit_end(end: dt.date, weather: bool = False) -> dt.date:
    """Clip a requested end date to the active cut-off (no-op outside `as_of`, and for weather
    readers inside `forcing_weather()`)."""
    c = _CUTOFF.get()
    if c is None or end <= c or (weather and _FORCING.get()):
        return end
    return c


def guard(dates: Iterable[dt.date], source: str, weather: bool = False) -> None:
    """Raise LeakageError if any date is after the active cut-off (weather readers are exempt
    only inside `forcing_weather()`)."""
    c = _CUTOFF.get()
    if c is None or (weather and _FORCING.get()):
        return
    late = [d for d in dates if d > c]
    if late:
        raise LeakageError(f"{source}: {len(late)} records after cut-off {c} (first {min(late)})")


def register(name: str, weather: bool = False):
    """Decorator: register a reader for the leakage tests."""

    def deco(fn):
        READERS[name] = (fn, weather)
        return fn

    return deco
