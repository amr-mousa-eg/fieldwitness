"""Write SYNTHETIC fixture packs for the web app (app branch only, PLAN.md Phase 9).

Every number here is invented by a seeded random generator to exercise the UI. Nothing is
observed, modelled or cited. Every Tagged source is "SYNTHETIC:fixture@0.1", every file name
contains ".SYNTHETIC.", and the region is named "DEMO DATA (synthetic)". The production build
refuses to ship these files (app/vite.config.ts, app/tests/build-guard.test.ts).

Run:  uv run python scripts/make_synthetic_fixtures.py
Out:  app/fixtures/<REGION>/*.SYNTHETIC.json (validated against scripts/fixture_schemas.py)
"""

from __future__ import annotations

import math
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import fixture_schemas as S
import shapely
from pyproj import Transformer

from fieldwitness.resolve.fields import SEED, field_id

ROOT = Path(__file__).resolve().parents[1]
REGION = "ks_demo_synthetic"
OUT = ROOT / "app" / "fixtures" / REGION
SRC = "SYNTHETIC:fixture@0.1"
VERSION = "1.2+ext-proposal-SYNTHETIC"
AS_OF = date(2024, 12, 31)
GENERATED = datetime(2026, 11, 4, 12, 0, 0)
YEARS = list(range(2017, 2025))  # harvest years in the story
MAX_PACK_BYTES = 300 * 1024  # PLAN.md §3: one pack < 300 KB
BBOX = (-101.3039, 37.8375, -100.0253, 38.8444)  # config/regions.yaml ks_t14slh

# Synthetic crop timing, as day of the harvest year (negative = previous autumn). Invented.
TIMING = {
    "winter_wheat": (-75, 125, 170),
    "sorghum": (165, 225, 285),
    "maize": (135, 205, 265),
    "cover_crop": (-40, 95, 130),
}
FAMILY = {"winter_wheat": "Poaceae", "sorghum": "Poaceae", "maize": "Poaceae"}
FAMILY |= {"cover_crop": "Poaceae", "fallow": None}

FIELDS = [  # (centre lon, lat, width m, height m, current rotation) — invented
    (-100.92, 38.02, 805, 805, ["winter_wheat", "sorghum", "fallow"]),
    (-100.71, 37.95, 805, 402, ["maize", "maize", "winter_wheat"]),
    (-101.05, 38.31, 1210, 805, ["winter_wheat", "fallow", "winter_wheat"]),
]
ALTERNATIVES = [
    ["winter_wheat", "sorghum", "cover_crop"],
    ["winter_wheat", "maize", "fallow"],
    ["sorghum", "winter_wheat", "fallow"],
    ["winter_wheat", "cover_crop", "sorghum"],
]


def bounds(unit: str) -> tuple[float, float]:
    """Physical range of a synthetic quantity, so bands never show impossible values."""
    if "0–1" in unit or unit.startswith("share") or unit == "probability":
        return (0.0, 1.0)
    if unit.startswith(("mm", "days", "NDVI·day", "relative index", "count")):
        return (0.0, math.inf)
    return (-math.inf, math.inf)


def T(value, unit, tag="D", spread=None, rnd=1):
    """A Tagged synthetic number with optional symmetric 50/90 % bands, clipped to `bounds`."""
    if value is None:
        return S.Tagged(value=None, unit=unit, tag=tag, source=SRC)
    lo, hi = bounds(unit)
    r = lambda x: round(min(hi, max(lo, x)), rnd)  # noqa: E731
    if spread is None:
        return S.Tagged(value=r(value), unit=unit, tag=tag, source=SRC)
    return S.Tagged(
        value=r(value),
        lo50=r(value - 0.67 * spread),
        hi50=r(value + 0.67 * spread),
        lo90=r(value - 1.64 * spread),
        hi90=r(value + 1.64 * spread),
        unit=unit,
        tag=tag,
        source=SRC,
    )


def rect(lon, lat, w, h):
    dlat = h / 2 / 111_320
    dlon = w / 2 / (111_320 * math.cos(math.radians(lat)))
    g = shapely.box(lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    return shapely.set_precision(g, 1e-6)


TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True).transform


def ndvi_at(t_doy_year: list[tuple[int, str]], doy: float, year: int) -> float:
    """Synthetic NDVI: soil base + one double-logistic hump per cropped season."""
    v = 0.14
    for y, crop in t_doy_year:
        if crop not in TIMING:
            continue
        sos, peak, eos = TIMING[crop]
        amp = 0.62 if crop != "cover_crop" else 0.32
        t = doy + 365 * (year - y)  # day relative to 1 Jan of that harvest year
        up = 1 / (1 + math.exp(-(t - sos - 12) / 9))
        down = 1 / (1 + math.exp(-(t - eos + 15) / 8))
        v += amp * max(0.0, up - down)
    return min(v, 0.92)


def crop_for(rotation, year):
    return rotation[(year - YEARS[0]) % len(rotation)]


def make_field(i, spec, rng: random.Random):
    lon, lat, w, h, rotation = spec
    geom = rect(lon, lat, w, h)
    fid = field_id(geom)
    area_ha = round(shapely.transform(geom, TO_UTM, interleaved=False).area / 10_000, 2)
    interior = max(0, int(w / 30) - 2) * max(0, int(h / 30) - 2)
    field = S.FieldModel(
        field_id=fid,
        geometry_wkt=geom.wkt,
        area_ha=area_ha,
        region_id=REGION,
        tier=1,
        boundary_source="CSB",
        scale_flags={"POWER": True, "SMAP": True, "GRACE": True, "HLS": False},
        interior_pixels=interior,
    )
    history = [(y, crop_for(rotation, y)) for y in YEARS]

    # --- series --------------------------------------------------------------------------------
    def smooth(x: date) -> float:
        """Noise-free synthetic curve; autumn days also count toward next harvest year."""
        a = ndvi_at(history, x.timetuple().tm_yday, x.year)
        return round(a, 3)

    start = date(YEARS[0] - 1, 9, 1)
    d, dates, ndvi, evi, clear = start, [], [], [], []
    while d <= AS_OF:
        if rng.random() < 0.35:  # synthetic clear-sky chance per 3-day revisit
            n = round(min(0.95, max(0.05, smooth(d) + rng.gauss(0, 0.03))), 3)
            dates.append(d)
            ndvi.append(n)
            evi.append(round(n * 0.62 + rng.gauss(0, 0.015), 3))
            clear.append(round(rng.uniform(0.7, 1.0), 2))
        d += timedelta(days=3)
    weeks = []
    while start <= AS_OF:
        weeks.append(start)
        start += timedelta(days=7)

    story, marks = [], []
    for y, crop in history:
        cropped = crop in TIMING
        sos, peak, eos = TIMING.get(crop, (None, None, None))
        jit = rng.randint(-6, 6)
        mk = lambda v, s, j=jit: T(None if v is None else v + j, "day of harvest year", "O", s, 0)  # noqa: E731
        season = S.Season(
            year=y,
            crop=crop,
            crop_conf=1.0,
            crop_source="label",
            sos=mk(sos, 5),
            peak=mk(peak, 4),
            eos=mk(eos, 5),
            canopy_integral=T(rng.uniform(38, 62) if cropped else 4.0, "NDVI·day", "O", 3),
            cover_days=T((eos - sos - 30) if cropped else 0, "days", "D", 6, 0),
            bare_days=T((365 - (eos - sos)) if cropped else 330, "days", "D", 6, 0),
            clear_obs=rng.randint(28, 52),
        )
        story.append(season)
        marks.append(S.SeasonMarks(season_year=y, sos=season.sos, peak=season.peak, eos=season.eos))
    series = S.FieldSeries(
        schema_version=VERSION,
        field_id=fid,
        ndvi=S.TaggedSeries(x=dates, values=ndvi, unit="NDVI", tag="O", source=SRC),
        evi=S.TaggedSeries(x=dates, values=evi, unit="EVI", tag="O", source=SRC),
        clear_frac=clear,
        ndvi_smooth=S.TaggedSeries(
            x=weeks, values=[smooth(x) for x in weeks], unit="NDVI", tag="D", source=SRC
        ),
        marks=marks,
        data_as_of=AS_OF,
    )

    # --- options -------------------------------------------------------------------------------
    sequences = [rotation] + [a for a in ALTERNATIVES if a != rotation][:3]
    options, raw = [], []
    for seq in sequences:
        cropped = [c for c in seq if c in TIMING]
        water = 410 + 55 * seq.count("maize") + 25 * seq.count("sorghum") - 20 * seq.count("fallow")
        water += rng.uniform(-15, 15)
        cover = sum(TIMING[c][2] - TIMING[c][0] - 30 for c in cropped) / 3
        breaks = sum(1 for a, b in zip(seq, seq[1:], strict=False) if FAMILY[a] != FAMILY[b])
        m = {
            "water_use_mm": T(water, "mm/season", "D", 28, 0),
            "irrigation_mm": T(max(0.0, water - 380) * 0.6, "mm/season", "D", 15, 0),
            "ryi": T(rng.uniform(0.55, 0.82), "RYI 0–1", "D", 0.07, 2),
            "cover_days": T(cover, "days/year", "D", 8, 0),
            "bad_year_water_mm": T(water * 1.22, "mm/season", "D", 35, 0),
            "bad_year_ryi": T(rng.uniform(0.25, 0.45), "RYI 0–1", "D", 0.08, 2),
            "legume_share": T(0.0, "share of seasons", "D", None, 2),
            "family_breaks": T(breaks, "count", "D", None, 0),
            "erosion_exposure": T(rng.uniform(0.3, 1.0), "relative index", "D", 0.1, 2),
            "residue_proxy": T(rng.uniform(0.4, 0.9), "relative index", "D", 0.08, 2),
            "forage_value": T(seq.count("sorghum") / 3, "share of seasons", "A", None, 2),
            "deep_root_share": T(len(cropped) / 3, "share of seasons", "D", None, 2),
        }
        raw.append((seq, m))
    cur_water = raw[0][1]["water_use_mm"].value
    order = sorted(range(len(raw)), key=lambda j: raw[j][1]["water_use_mm"].value)
    for k, (seq, m) in enumerate(raw):
        oid = "current" if k == 0 else f"alt{k}"
        dw = m["water_use_mm"].value - cur_water
        grade = "B" if m["ryi"].value > 0.65 else "C"
        options.append(
            S.Option(
                option_id=oid,
                sequence=seq,
                metrics=m,
                witnesses=[
                    S.WitnessResult(
                        witness="physics",
                        metric="water_use_mm",
                        estimate=m["water_use_mm"],
                        diagnostics={"worlds": 30, "weather_years": 21},
                    ),
                    S.WitnessResult(
                        witness="own_past",
                        metric="cover_days",
                        estimate=T(m["cover_days"].value + rng.uniform(-6, 6), "days/year", "D", 9),
                        n=len(YEARS),
                        diagnostics={"credibility": 0.7, "ess": 210.0},
                    ),
                ],
                grade=grade,
                grade_reasons=[
                    "SYNTHETIC: physics and own past agree within 90 % intervals."
                    if grade == "B"
                    else "SYNTHETIC: only one witness is informative for RYI.",
                    "No neighbour witness yet, so the best possible grade is B.",
                ],
                regret=T(abs(dw) / 10, "mm/season", "D", 3, 0),
                rank=order.index(k) + 1,
                explanation=S.Explanation(
                    why=[
                        "This is your current rotation (last three seasons)."
                        if k == 0
                        else f"Lower water use priority: {dw:+.0f} mm/season vs Current (D)."
                    ],
                    evidence=[f"Grade {grade}: physics + own past; neighbours not yet available."],
                    benefits=[
                        f"Cover: {m['cover_days'].value:.0f} days/year (D).",
                        f"Bad-year water: {m['bad_year_water_mm'].value:.0f} mm/season (D).",
                    ],
                    gaps=[
                        "Forage value is an assumption (A), not from a cited source.",
                        "POWER weather is coarse context (scale flag).",
                    ],
                    risks=["Check local disease pressure and planting windows with an adviser."],
                ),
            )
        )
    options.sort(key=lambda o: o.rank)

    # --- ledger --------------------------------------------------------------------------------
    ledger = []
    for y in (2022, 2023, 2024):
        crop = crop_for(rotation, y)
        if crop not in TIMING:
            continue
        sos = TIMING[crop][0]
        pred = {
            "sos": T(sos, "day of harvest year", "D", 9, 0),
            "canopy_integral": T(rng.uniform(42, 56), "NDVI·day", "D", 8),
        }
        obs = {
            "sos": T(sos + rng.randint(-12, 12), "day of harvest year", "O", None, 0),
            "canopy_integral": T(rng.uniform(38, 60), "NDVI·day", "O"),
        }
        ledger.append(
            S.LedgerEntry(
                field_id=fid,
                as_of=date(2021, 12, 31),
                model_version="SYNTHETIC",
                mode="forecast",
                season_year=y,
                crop=crop,
                crop_observed_source="label",
                predicted=pred,
                observed=obs,
                scores={
                    "crps": round(rng.uniform(3, 8), 2),
                    "covered50": float(rng.random() < 0.5),
                    "covered90": float(rng.random() < 0.9),
                    "timing_err_days": float(obs["sos"].value - sos),
                },
            )
        )

    pack = S.FieldPack(
        schema_version=VERSION,
        field=field,
        story=story,
        credibility=T(rng.uniform(0.55, 0.85), "score 0–1", "D", 0.08, 2),
        options=options,
        advice=S.Advice(
            measure_next="SYNTHETIC: confirm irrigation yes/no (flips rank 1 most often).",
            flip_probability=T(rng.uniform(0.1, 0.35), "probability", "D", None, 2),
            counterfactual_flip=(
                "SYNTHETIC: if TAW were 20 % lower, Alternative 1 would rank first."
            ),
        ),
        ledger=ledger,
        data_as_of=AS_OF,
        generated_at=GENERATED,
    )

    # --- calendar ------------------------------------------------------------------------------
    bare = []
    for mth in range(1, 13):
        if mth == 1:  # one month left insufficient on purpose to show that UI state
            bare.append(
                S.BareMonth(
                    month=1, bare_share=None, clear_obs=4, years_with_data=2, insufficient=True
                )
            )
            continue
        shares = [smooth(date(y, mth, 15)) < 0.3 for y in YEARS]
        bare.append(
            S.BareMonth(
                month=mth,
                bare_share=T(sum(shares) / len(shares), "share of years", "O", None, 2),
                clear_obs=rng.randint(12, 40),
                years_with_data=len(YEARS),
                insufficient=False,
            )
        )

    def bare_sim(seq):
        hist = [(2000 + j, c) for j, c in enumerate(seq)]
        vals = []
        for mth in range(1, 13):
            s = [
                ndvi_at(hist, date(2001, mth, 15).timetuple().tm_yday, 2000 + j) < 0.3
                for j in (0, 1, 2)
            ]
            vals.append(round(sum(s) / 3, 2))
        return S.TaggedSeries(
            x=list(range(1, 13)), values=vals, unit="share of years", tag="D", source=SRC
        )

    crops = sorted({c for o in options for c in o.sequence if c != "fallow"})
    vuln = []
    for c in crops:
        sos, _, eos = TIMING[c]
        months = range(1, 13)

        def stage(mth, lo, hi):
            doy = 30 * mth - 15
            return lo <= doy <= hi or lo <= doy - 365 <= hi

        sh = {
            "heat": [
                round(rng.uniform(0.2, 0.6), 2)
                if stage(m, eos - 60, eos) and m in (6, 7, 8)
                else 0.0
                for m in months
            ],
            "frost": [
                round(rng.uniform(0.1, 0.4), 2) if m in (3, 4) and stage(m, sos, eos) else 0.0
                for m in months
            ],
            "water_stress": [
                round(rng.uniform(0.1, 0.7), 2) if stage(m, sos, eos) else 0.0 for m in months
            ],
            "extreme_rain_bare": [
                round(rng.uniform(0.0, 0.3), 2)
                if not stage(m, sos, eos) and m in (5, 6, 7, 8)
                else 0.0
                for m in months
            ],
        }
        vuln.append(
            S.CropVulnerability(
                crop=c,
                years=(2001, 2021),
                thresholds={
                    "heat": T(None, "°C Tmax", "A"),
                    "frost": T(0.0, "°C Tmin", "A"),
                    "water_stress": T(1.0, "Ks", "A"),
                    "extreme_rain_bare": T(None, "mm/day (local p99)", "A"),
                },
                threshold_notes={
                    h: "SYNTHETIC placeholder; real value must come from T3.6." for h in sh
                },
                shares={
                    h: S.TaggedSeries(
                        x=list(months), values=v, unit="share of years", tag="D", source=SRC
                    )
                    for h, v in sh.items()
                },
            )
        )
    calendar = S.FieldCalendar(
        schema_version=VERSION,
        field_id=fid,
        bare_observed=bare,
        bare_observed_years=(YEARS[0], YEARS[-1]),
        bare_by_option={o.option_id: bare_sim(o.sequence) for o in options},
        vulnerability=vuln,
        data_as_of=AS_OF,
    )

    # --- scenarios -----------------------------------------------------------------------------
    scen = []
    for dt in (0, 1, 2):
        for dp in (-20, -10, 0, 10):
            mets = {}
            for o in options:
                f_w = 1 + 0.03 * dt - 0.004 * dp
                f_y = 1 - 0.04 * dt + 0.005 * dp
                mm = dict(o.metrics)
                for key in ("water_use_mm", "bad_year_water_mm", "irrigation_mm"):
                    v = o.metrics[key].value
                    mm[key] = T(v * f_w, o.metrics[key].unit, "D", 30, 0)
                for key in ("ryi", "bad_year_ryi"):
                    v = o.metrics[key].value
                    mm[key] = T(min(1.0, v * f_y), o.metrics[key].unit, "D", 0.07, 2)
                mets[o.option_id] = mm
            by_w = sorted(mets, key=lambda oid: mets[oid]["water_use_mm"].value)
            scen.append(
                S.Scenario(
                    scenario_id=f"t{dt:+d}_p{dp:+d}",
                    dt_c=dt,
                    dp_pct=dp,
                    metrics=mets,
                    ranks={oid: by_w.index(oid) + 1 for oid in mets},
                )
            )
    scenarios = S.FieldScenarios(
        schema_version=VERSION,
        field_id=fid,
        baseline_id="t+0_p+0",
        note="Sensitivity tests on past weather, not climate projections.",
        scenarios=scen,
        data_as_of=AS_OF,
    )
    return pack, series, calendar, scenarios


def region_files(packs, calendars, rng: random.Random):
    w, s, e, n = BBOX
    years = list(range(2016, 2025))

    def grid(nx, ny, base, amp, unit, tag="D"):
        cells = []
        for ix in range(nx):
            for iy in range(ny):
                b = (
                    round(w + (e - w) * ix / nx, 4),
                    round(s + (n - s) * iy / ny, 4),
                    round(w + (e - w) * (ix + 1) / nx, 4),
                    round(s + (n - s) * (iy + 1) / ny, 4),
                )
                trend = rng.uniform(-amp, amp) / 4
                vals = [
                    round(base + trend * k + rng.gauss(0, amp / 3), 2) for k in range(len(years))
                ]
                cells.append(S.GridCell(bbox_lonlat=b, values=vals))
        return S.TaggedGrid(years=years, cells=cells, unit=unit, tag=tag, source=SRC)

    layers = []
    for lid, nx, base, amp, unit, res in (
        ("grace_tws", 2, -4.0, 6.0, "cm water equivalent anomaly", 50.0),
        ("smap_anomaly", 12, 0.0, 0.04, "m³/m³ anomaly", 9.0),
        ("heatwave_days", 2, 8.0, 5.0, "days/year", 50.0),
    ):
        g = grid(nx, nx, base, amp, unit)
        mean = [
            round(sum(c.values[k] for c in g.cells) / len(g.cells), 3) for k in range(len(years))
        ]
        slope = (mean[-1] - mean[0]) / (years[-1] - years[0])
        layers.append(
            S.RegionalLayer(
                layer_id=lid,
                resolution_km=res,
                resolution_source="SYNTHETIC placeholder; take from the product docs.",
                scale_flag=True,
                grid=g,
                region_mean=S.TaggedSeries(x=years, values=mean, unit=unit, tag="D", source=SRC),
                trend=T(slope, f"{unit} per year", "D", abs(slope) / 2 + 0.01, 3),
            )
        )
    colour = {"erosion_exposure": {}, "water_stress_share": {}, "frost_share": {}}
    for p, cal in zip(packs, calendars, strict=True):
        cur = next(o for o in p.options if o.option_id == "current")
        fid = p.field.field_id
        colour["erosion_exposure"][fid] = cur.metrics["erosion_exposure"]
        for key, hz in (("water_stress_share", "water_stress"), ("frost_share", "frost")):
            vals = [max(v.shares[hz].values) for v in cal.vulnerability if v.crop in cur.sequence]
            colour[key][fid] = T(max(vals) if vals else None, "share of years", "D", None, 2)
    region_layers = S.RegionLayers(
        schema_version=VERSION,
        region_id=REGION,
        layers=layers,
        field_colouring=colour,
        colouring_option="current",
        data_as_of=AS_OF,
    )
    index = S.RegionIndex(
        schema_version=VERSION,
        region_id=REGION,
        name="Kansas — DEMO DATA (synthetic)",
        tier=1,
        bbox_lonlat=BBOX,
        basemap=None,
        fields=[
            S.FieldSummary(
                field_id=p.field.field_id,
                geometry_wkt=p.field.geometry_wkt,
                area_ha=p.field.area_ha,
                current_sequence=next(o for o in p.options if o.option_id == "current").sequence,
                top_option_id=p.options[0].option_id,
                top_grade=p.options[0].grade,
            )
            for p in packs
        ],
        data_as_of=AS_OF,
    )
    rows = []
    for method in ("fieldwitness", "B0", "B1", "B2", "B3"):
        for metric in ("canopy_integral", "cover_days", "sos"):
            rows.append(
                S.HindcastRow(
                    method=method,
                    mode="forecast",
                    metric=metric,
                    n=rng.randint(240, 300),
                    scores={
                        "crps": round(rng.uniform(3, 9), 2),
                        "covered50": round(rng.uniform(0.35, 0.6), 2),
                        "covered90": round(rng.uniform(0.75, 0.95), 2),
                        "timing_err_days": round(rng.uniform(5, 18), 1),
                    },
                )
            )
    hindcast = S.RegionHindcast(
        schema_version=VERSION,
        region_id=REGION,
        cutoff=date(2021, 12, 31),
        scored_years=[2022, 2023, 2024],
        crop_observed_source="label",
        rows=rows,
        story_field_id=packs[0].field.field_id,
        data_as_of=AS_OF,
    )
    regions = S.RegionList(regions=[S.RegionEntry(region_id=REGION, name=index.name, tier=1)])
    return index, hindcast, region_layers, regions


def check_consistency(pack: S.FieldPack, series: S.FieldSeries) -> None:
    by_key = {(s.year, s.index): s for s in pack.story}
    for m in series.marks:
        s = by_key[(m.season_year, m.season_index)]
        if (m.sos, m.peak, m.eos) != (s.sos, s.peak, s.eos):
            raise ValueError(f"series marks differ from story for season {m.season_year}")


def main() -> int:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    out: dict[str, S.BaseModel] = {}
    packs, cals = [], []
    for i, spec in enumerate(FIELDS):
        pack, series, cal, scen = make_field(i, spec, rng)
        check_consistency(pack, series)
        fid = pack.field.field_id
        out |= {
            f"{fid}.SYNTHETIC.json": pack,
            f"{fid}.series.SYNTHETIC.json": series,
            f"{fid}.calendar.SYNTHETIC.json": cal,
            f"{fid}.scenarios.SYNTHETIC.json": scen,
        }
        packs.append(pack)
        cals.append(cal)
    index, hindcast, layers, regions = region_files(packs, cals, rng)
    out |= {
        "index.SYNTHETIC.json": index,
        "hindcast.SYNTHETIC.json": hindcast,
        "layers.SYNTHETIC.json": layers,
    }
    failed = False
    for name, model in out.items():
        bad = S.check_tagged(model)
        text = model.model_dump_json(indent=None)
        type(model).model_validate_json(text)  # round-trip through the schema
        size = len(text.encode())
        if bad:
            print(f"UNTAGGED in {name}: {bad[:5]}", file=sys.stderr)
            failed = True
        if size > MAX_PACK_BYTES:
            print(f"TOO BIG {name}: {size} bytes", file=sys.stderr)
            failed = True
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"{name:60s} {size / 1024:7.1f} KB")
    regions_path = OUT.parent / "regions.SYNTHETIC.json"
    regions_path.write_text(regions.model_dump_json(), encoding="utf-8")
    print(f"{regions_path.name:60s}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
