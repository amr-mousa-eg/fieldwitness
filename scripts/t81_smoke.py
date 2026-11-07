"""T8.1 smoke run: build 3 fields into logs/packtest and print the summary."""

from pathlib import Path

from fieldwitness.packs.run import build_region

print(build_region("ks_t14slh", Path("logs/packtest"), limit=3))
