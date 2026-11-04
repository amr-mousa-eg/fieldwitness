"""Load and validate config/regions.yaml, crops.yaml and grading.yaml (PLAN.md §4, T0.6)."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONFIG = Path("config")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Ref(_Strict):
    source: str
    table: int
    row: str
    footnote: int | None = None
    note: str | None = None


class Param(_Strict):
    """One crop parameter. Verified values cite a table; unverified ones carry no number."""

    value: float | list[float] | None = None
    range: list[float] | None = None
    ref: Ref | None = None
    verified: bool
    choice: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _provenance(self):
        if self.verified:
            if self.ref is None:
                raise ValueError("verified parameter needs a ref")
            if self.value is None and self.range is None:
                raise ValueError("verified parameter needs a value or a range")
        else:
            if self.value is not None or self.range is not None:
                raise ValueError("unverified parameter must not carry a number (tag A, no memory)")
            if not self.note:
                raise ValueError("unverified parameter needs a note")
        return self


class FamilyParam(_Strict):
    value: str | None = None
    verified: bool
    note: str | None = None


class KcIniByRegion(_Strict):
    frozen_soils: Param
    non_frozen_soils: Param
    by_region: dict[str, Literal["frozen_soils", "non_frozen_soils"]]
    choice: str


class Crop(_Strict):
    name: str
    hcat3: list[str]
    label_aliases: dict[str, list[str]] = Field(default_factory=dict)
    proxy_for: str | None = None
    kc_ini: Param | KcIniByRegion
    kc_mid: Param
    kc_end: Param
    h_max_m: Param | None = None
    root_depth_m: Param | None = None
    p: Param | None = None
    ky: Param | None = None
    stage_lengths_days: dict[str, Param]
    family: FamilyParam | None = None

    @model_validator(mode="after")
    def _stages(self):
        for region, p in self.stage_lengths_days.items():
            if p.value is not None:
                v = p.value
                if not (isinstance(v, list) and len(v) == 4 and all(x > 0 for x in v)):
                    raise ValueError(f"{region}: stage lengths must be 4 positive numbers")
        return self


class Source(_Strict):
    citation: str
    url: str


class CropsFile(_Strict):
    sources: dict[str, Source]
    crops: dict[str, Crop]

    @model_validator(mode="after")
    def _refs_point_to_sources(self):
        for key, crop in self.crops.items():
            for p in _params(crop):
                if p.ref is not None and p.ref.source not in self.sources:
                    raise ValueError(f"{key}: unknown source {p.ref.source}")
        return self


def _params(crop: Crop) -> list[Param]:
    out = [crop.kc_mid, crop.kc_end]
    if isinstance(crop.kc_ini, Param):
        out.append(crop.kc_ini)
    else:
        out += [crop.kc_ini.frozen_soils, crop.kc_ini.non_frozen_soils]
    out += [p for p in (crop.h_max_m, crop.root_depth_m, crop.p, crop.ky) if p is not None]
    out += list(crop.stage_lengths_days.values())
    return out


class Season(_Strict):
    start: int = Field(ge=1, le=12)
    end: int = Field(ge=1, le=12)
    tag: Literal["A"]


class Region(BaseModel):
    model_config = ConfigDict(extra="allow")  # census keys (boundary, labels, ...) stay flexible
    status: str
    tier: Literal[1, 2, 3]
    name: str
    tiles: list[str]
    point: list[float]
    seasons: dict[str, Season]
    bbox_lonlat: list[float] | None = None
    crops: list[str] | None = None


def load_crops(path: Path = CONFIG / "crops.yaml") -> CropsFile:
    return CropsFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_regions(path: Path = CONFIG / "regions.yaml") -> dict[str, Region]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))["regions"]
    return {k: Region.model_validate(v) for k, v in raw.items()}


def load_grading(path: Path = CONFIG / "grading.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
