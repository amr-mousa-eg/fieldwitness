"""T8.1 pack validator: every file in a pack directory against its schema model.

File name -> model: `regions.json` RegionList, `index.json` RegionIndex, `layers.json`
RegionLayers, `hindcast.json` RegionHindcast, `<id>.series.json` FieldSeries,
`<id>.calendar.json` FieldCalendar, `<id>.scenarios.json` FieldScenarios, `<id>.json` FieldPack.
Also runs `check_tagged` (no untagged user-facing number) and the per-file size limit.
"""

from __future__ import annotations

from pathlib import Path

from fieldwitness.schemas import (
    FieldCalendar,
    FieldPack,
    FieldScenarios,
    FieldSeries,
    FieldSim3D,
    FieldSim3DInputs,
    RegionHindcast,
    RegionIndex,
    RegionLayers,
    RegionList,
    check_tagged,
)

MAX_BYTES = 300_000  # PLAN T8.1: each pack < 300 KB (decimal KB)
_BY_NAME = {
    "regions.json": RegionList,
    "index.json": RegionIndex,
    "layers.json": RegionLayers,
    "hindcast.json": RegionHindcast,
}
_BY_SUFFIX = {
    ".series.json": FieldSeries,
    ".calendar.json": FieldCalendar,
    ".scenarios.json": FieldScenarios,
    ".sim3d.json": FieldSim3D,
    ".sim3d_inputs.json": FieldSim3DInputs,
}


def model_for(name: str):
    """Schema model for a pack file name."""
    if name in _BY_NAME:
        return _BY_NAME[name]
    for suffix, model in _BY_SUFFIX.items():
        if name.endswith(suffix):
            return model
    return FieldPack


def validate_dir(root: Path) -> list[str]:
    """Return problems for every *.json under `root` (empty list = valid)."""
    problems: list[str] = []
    files = sorted(root.rglob("*.json"))
    if not files:
        return [f"no pack files under {root}"]
    for f in files:
        rel = f.relative_to(root).as_posix()
        if f.stat().st_size >= MAX_BYTES:
            problems.append(f"{rel}: {f.stat().st_size} bytes >= {MAX_BYTES}")
        try:
            obj = model_for(f.name).model_validate_json(f.read_bytes())
        except Exception as e:  # pydantic ValidationError or bad JSON
            problems.append(f"{rel}: {str(e).splitlines()[0]}")
            continue
        problems += [f"{rel}: untagged number at {p}" for p in check_tagged(obj)]
    return problems
