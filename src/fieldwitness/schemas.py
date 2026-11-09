"""Data contracts: PLAN.md §3 (field pack) and §3b (app data files), as Pydantic v2 models.

Source: `scripts/fixture_schemas.py` on branch `app` (commit dd97bf5), the canonical code of the
§3 extension approved by the user on 2026-11-04 (`docs/schema_ext_proposal.md` §5, Q1–Q7;
DECISIONS.md). §3's `Field` keeps its PLAN name here (the app copy calls it `FieldModel`), so
pydantic's `Field` is imported as `PydanticField`.

Tag rule: every user-facing number is inside `Tagged` (one number) or `TaggedSeries` /
`TaggedGrid` (one tag, unit and source for a whole array). `check_tagged` walks a model and returns
the path of every float outside those containers whose field name is not in `EXEMPT_FIELDS`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, model_validator
from pydantic import Field as PydanticField

# ---------------------------------------------------------------------------------------------
# PLAN.md §3 — field pack
# ---------------------------------------------------------------------------------------------

Tag = Literal["O", "D", "E", "A"]


class Tagged(BaseModel):
    value: float | None
    lo50: float | None = None
    hi50: float | None = None
    lo90: float | None = None
    hi90: float | None = None
    unit: str
    tag: Tag
    source: str


class Field(BaseModel):
    field_id: str
    geometry_wkt: str
    area_ha: float
    region_id: str
    tier: Literal[1, 2, 3]
    boundary_source: Literal["FTW", "CSB", "EuroCrops", "user"]
    scale_flags: dict[str, bool]
    interior_pixels: int


class Season(BaseModel):
    year: int
    index: int = 0
    crop: str | None
    crop_conf: float
    crop_source: Literal["label", "classifier", "user"]
    # day of the harvest year, negative = previous autumn (user decision Q1, 2026-11-04)
    sos: Tagged
    peak: Tagged
    eos: Tagged
    canopy_integral: Tagged
    cover_days: Tagged
    bare_days: Tagged
    clear_obs: int


class WitnessResult(BaseModel):
    witness: Literal["physics", "own_past", "neighbours"]
    metric: str
    estimate: Tagged
    n: int | None = None
    diagnostics: dict[str, float | bool | str]


class Explanation(BaseModel):
    why: list[str]
    evidence: list[str]
    benefits: list[str]
    gaps: list[str]
    risks: list[str]


class Option(BaseModel):
    option_id: str
    sequence: list[str]
    metrics: dict[str, Tagged]
    witnesses: list[WitnessResult]
    grade: Literal["A", "B", "C", "D"]
    grade_reasons: list[str]
    regret: Tagged
    rank: int
    explanation: Explanation


class Advice(BaseModel):
    measure_next: str
    flip_probability: Tagged
    counterfactual_flip: str


class LedgerEntry(BaseModel):
    field_id: str
    as_of: date
    model_version: str
    mode: Literal["forecast", "forced"]
    season_year: int
    season_index: int = 0
    crop: str
    crop_observed_source: Literal["label", "classifier"]
    predicted: dict[str, Tagged]
    observed: dict[str, Tagged] | None = None
    scores: dict[str, float] | None = None


class FieldPack(BaseModel):
    schema_version: str
    field: Field
    story: list[Season]
    credibility: Tagged
    options: list[Option]
    advice: Advice
    ledger: list[LedgerEntry]
    data_as_of: date
    generated_at: datetime


# §3 exempt list, plus the §3b additions marked (ext) (user decision Q3).
EXEMPT_FIELDS = frozenset(
    {
        # §3
        "field_id",
        "area_ha",
        "interior_pixels",
        "clear_obs",
        "crop_conf",
        "n",
        "rank",
        "diagnostics",
        "scores",
        # (ext) geometry and grid coordinates, not claims
        "bbox_lonlat",
        # (ext) scenario grid coordinates: inputs chosen by us, shown as labels
        "dt_c",
        "dp_pct",
        # (ext) dataset metadata from the product docs; shown next to its `resolution_source`
        "resolution_km",
        # (ext) bookkeeping counts
        "years_with_data",
        "clear_frac",
        # (ext) 3D simulation weekly arrays and metadata sharing tag D
        "soil_water_mm",
        "taw_mm",
        "canopy_cover",
        "ks",
        "rain_mm",
        "irrigation_mm",
        "root_depth_m",
        "weather_year",
        "week",
        "week_in_year",
        "month",
    }
)


# ---------------------------------------------------------------------------------------------
# PLAN.md §3b — app data files (approved 2026-11-04)
# ---------------------------------------------------------------------------------------------


class TaggedSeries(BaseModel):
    """Many numbers that share one unit, tag and source (keeps per-field files small)."""

    x: list[date] | list[int]  # dates, or years / months
    values: list[float | None]
    lo90: list[float | None] | None = None
    hi90: list[float | None] | None = None
    unit: str
    tag: Tag
    source: str

    @model_validator(mode="after")
    def _same_length(self) -> TaggedSeries:
        n = len(self.x)
        for name in ("values", "lo90", "hi90"):
            arr = getattr(self, name)
            if arr is not None and len(arr) != n:
                raise ValueError(f"{name} has {len(arr)} items, x has {n}")
        return self


# --- <field_id>.series.json --------------------------------------------------------------------


class FieldSeries(BaseModel):
    schema_version: str
    field_id: str
    ndvi: TaggedSeries  # observed, tag O: median over interior pixels per clear date
    evi: TaggedSeries  # observed, tag O
    clear_frac: list[float]  # clear-pixel fraction per date in `ndvi.x` (bookkeeping)
    ndvi_smooth: TaggedSeries  # smoothed curve, tag D
    # SOS / peak / EOS marks are not repeated here: the app reads them from FieldPack.story (Q2).
    data_as_of: date

    @model_validator(mode="after")
    def _aligned(self) -> FieldSeries:
        if self.evi.x != self.ndvi.x or len(self.clear_frac) != len(self.ndvi.x):
            raise ValueError("ndvi, evi and clear_frac must share the same dates")
        return self


# --- <field_id>.calendar.json ------------------------------------------------------------------

Hazard = Literal["heat", "frost", "water_stress", "extreme_rain_bare"]


class BareMonth(BaseModel):
    month: int = PydanticField(ge=1, le=12)
    bare_share: Tagged | None  # share of years bare in this month; None when insufficient
    clear_obs: int
    years_with_data: int
    insufficient: bool  # T2.5: too few clear observations -> "insufficient data", not filled


class CropVulnerability(BaseModel):
    crop: str
    years: tuple[int, int]  # POWER weather years used, e.g. (2001, 2021)
    thresholds: dict[Hazard, Tagged]  # cited source (tag E) or tag A with a note
    threshold_notes: dict[Hazard, str]
    shares: dict[Hazard, TaggedSeries]  # x = months 1..12, values = share of years, tag D


class FieldCalendar(BaseModel):
    schema_version: str
    field_id: str
    bare_observed: list[BareMonth]  # T2.5, tag O, 12 items
    bare_observed_years: tuple[int, int]
    bare_by_option: dict[str, TaggedSeries]  # simulated bare share per month per option, tag D
    vulnerability: list[CropVulnerability]  # current crops + every option crop (T3.6)
    data_as_of: date


# --- <field_id>.scenarios.json -----------------------------------------------------------------


# T6.7 metrics defined only by the crop sequence: identical in every weather scenario, so they live
# once in the pack's Option.metrics and are not repeated in scenarios (user decision Q6).
SEQUENCE_ONLY_METRICS = frozenset(
    {"legume_share", "family_breaks", "forage_value", "deep_root_share"}
)


class Scenario(BaseModel):
    scenario_id: str  # e.g. "t+1_p-10"
    dt_c: float  # temperature change, °C (grid coordinate)
    dp_pct: float  # rainfall change, % (grid coordinate)
    metrics: dict[str, dict[str, Tagged]]  # option_id -> weather-sensitive metric -> value (Q6)
    ranks: dict[str, int]  # option_id -> rank under default weights


class FieldScenarios(BaseModel):
    schema_version: str
    field_id: str
    baseline_id: str  # "t+0_p+0" = the pack's own Option metrics
    note: str  # "Sensitivity tests on past weather, not climate projections."
    scenarios: list[Scenario]  # 3 temperatures x 4 rainfall = 12 (T6.8)
    data_as_of: date

    @model_validator(mode="after")
    def _grid(self) -> FieldScenarios:
        if len(self.scenarios) != 12:
            raise ValueError(f"T6.8 needs 12 scenarios, got {len(self.scenarios)}")
        if self.baseline_id not in {s.scenario_id for s in self.scenarios}:
            raise ValueError("baseline_id is not one of the scenarios")
        for s in self.scenarios:
            for oid, m in s.metrics.items():
                if fixed := SEQUENCE_ONLY_METRICS & m.keys():
                    raise ValueError(f"{s.scenario_id}/{oid}: weather-independent {sorted(fixed)}")
        return self


# --- <field_id>.sim3d.json --------------------------------------------------------------------


class Sim3DScenario(BaseModel):
    soil_water_mm: list[float]  # available root-zone water (TAW - Dr), mm
    taw_mm: list[float]  # total available water, mm
    canopy_cover: list[float]  # canopy proxy (Kc / Kc_max), 0..1
    ks: list[float]  # FAO-56 water stress coefficient, 0..1
    rain_mm: list[float]  # weekly rain, mm
    irrigation_mm: list[float]  # weekly irrigation, mm


class Sim3DOption(BaseModel):
    option_id: str
    sequence: list[str]
    rank: int  # 0 for Current, 1..3 for default top alternatives
    label: str  # human-readable label
    crops: list[str]  # crop name for each week (156 items)
    stages: list[str]  # growth stage for each week: "initial", "dev", "mid", "late", "fallow"
    root_depth_m: list[float]  # root depth in meters (156 items)
    scenarios: dict[str, Sim3DScenario]  # 12 scenarios


class Sim3DWeek(BaseModel):
    week: int  # 0..155
    year: int  # 2022, 2023, 2024
    week_in_year: int  # 1..52
    week_start: str  # YYYY-MM-DD
    month: int  # 1..12
    label: str  # e.g. "Week 42 (Oct 2024)"


class FieldSim3D(BaseModel):
    schema_version: str = "1.0"
    field_id: str
    weather_year: int  # real past year with median growing-season rain
    weather_label: str  # e.g. "Weather of 2013 (median-rain year)"
    tag: Tag = "D"
    source: str = "FAO-56 daily water balance on median-rain weather year"
    weeks: list[Sim3DWeek]
    current: Sim3DOption
    alternatives: list[Sim3DOption]  # top 3 alternatives under default ranking


# --- packs/<region>/layers.json ----------------------------------------------------------------


class GridCell(BaseModel):
    bbox_lonlat: tuple[float, float, float, float]  # W, S, E, N
    values: list[float | None]  # one per year in the parent layer's `years`


class TaggedGrid(BaseModel):
    """A coarse raster as cells; one unit, tag and source for every value."""

    years: list[int]
    cells: list[GridCell]
    unit: str
    tag: Tag
    source: str


class RegionalLayer(BaseModel):
    layer_id: Literal["grace_tws", "smap_anomaly", "heatwave_days"]
    resolution_km: float
    resolution_source: str  # product doc the resolution comes from
    scale_flag: bool  # True whenever a pixel is larger than field area / 4 (CLAUDE.md rule 5)
    grid: TaggedGrid  # map layer with year slider (T9.11b)
    region_mean: TaggedSeries  # x = years; context strip (T9.9)
    trend: Tagged  # slope per year over `region_mean`, tag D


FieldColourMetric = Literal["erosion_exposure", "water_stress_share", "frost_share"]


class RegionLayers(BaseModel):
    schema_version: str
    region_id: str
    layers: list[RegionalLayer]
    # metric -> field_id -> value, always for the Current option (Q5; alternatives = stretch)
    field_colouring: dict[FieldColourMetric, dict[str, Tagged]]
    data_as_of: date


# --- packs/<region>/index.json and hindcast.json (named in §3, not specified there) -------------


class FieldSummary(BaseModel):
    field_id: str
    geometry_wkt: str
    area_ha: float
    current_sequence: list[str]
    top_option_id: str
    top_grade: Literal["A", "B", "C", "D"]


class RegionIndex(BaseModel):
    schema_version: str
    region_id: str
    name: str
    tier: Literal[1, 2, 3]
    bbox_lonlat: tuple[float, float, float, float]
    basemap: str | None  # path of the HLS true-colour composite (T9.1), None = neutral fallback
    fields: list[FieldSummary]
    data_as_of: date


class RegionEntry(BaseModel):
    region_id: str
    name: str
    tier: Literal[1, 2, 3]


class RegionList(BaseModel):  # packs/regions.json, for the region switcher (T9.1)
    regions: list[RegionEntry]


HindcastMethod = Literal["fieldwitness", "B0", "B1", "B2", "B3"]


class HindcastRow(BaseModel):
    method: HindcastMethod
    mode: Literal["forecast", "forced"]
    metric: str  # "canopy_integral" | "cover_days" | "sos" | "peak" | "water_use_mm"
    n: int  # scored field-seasons
    scores: dict[str, float]  # crps, covered50, covered90, timing_err_days (as LedgerEntry)


class RegionHindcast(BaseModel):
    schema_version: str
    region_id: str
    cutoff: date
    scored_years: list[int]
    crop_observed_source: Literal["label", "classifier"]
    rows: list[HindcastRow]
    story_field_id: str  # field whose ledger is the predicted-vs-observed chart
    data_as_of: date


# ---------------------------------------------------------------------------------------------
# Tag validator
# ---------------------------------------------------------------------------------------------

TAGGED_CONTAINERS = (Tagged, TaggedSeries, TaggedGrid)


def check_tagged(obj: object, path: str = "$") -> list[str]:
    """Return the paths of floats that sit outside a tagged container and are not exempt."""
    errors: list[str] = []
    if isinstance(obj, TAGGED_CONTAINERS):
        return errors
    if isinstance(obj, BaseModel):
        for name in type(obj).model_fields:
            if name in EXEMPT_FIELDS:
                continue
            errors += check_tagged(getattr(obj, name), f"{path}.{name}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            errors += check_tagged(v, f"{path}[{k!r}]")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            errors += check_tagged(v, f"{path}[{i}]")
    elif isinstance(obj, float):
        errors.append(path)
    return errors
