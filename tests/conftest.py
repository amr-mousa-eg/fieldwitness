"""Shared pytest hooks.

`needs_data` marker: tests that read files under `data/` (gitignored, so absent in CI)
declare those files, e.g. `@pytest.mark.needs_data("data/labels/ks_t14slh.parquet")`.
The test is skipped when any listed path is missing. Paths are relative to the repo root.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "needs_data(*paths): skip unless these repo-relative data files exist"
    )


def pytest_runtest_setup(item):
    for mark in item.iter_markers(name="needs_data"):
        if not mark.args:
            raise pytest.UsageError(f"{item.nodeid}: needs_data requires at least one path")
        missing = [p for p in mark.args if not (ROOT / p).exists()]
        if missing:
            pytest.skip(f"local data not on disk: {', '.join(missing)}")
