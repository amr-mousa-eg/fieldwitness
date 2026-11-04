"""T2.2 seasons and phenology from one field's NDVI series (PLAN.md T2.2).

Method (team choices in config/story.yaml, tag A): smooth (T2.1); each smoothed peak with enough
height and prominence is one season. SOS / EOS are amplitude-threshold crossings (a fraction of
peak minus the left / right trough), the usual threshold method; fractions are config, not from a
paper (UNVERIFIED). Seasons whose rise or fall is not fully inside the data are dropped.
Harvest year = calendar year of EOS; a 2nd season ending the same year gets index 1.
Day numbers: 1 Jan of the harvest year = 1, 31 Dec before = 0, negative = earlier.
Winter dormancy (user decision 2026-11-04, from agronomy, not tuned): two peaks whose trough lies
in Dec-Feb and stays at or above the cover threshold (not bare soil) are one season; the higher
peak is kept. Crop-like season: seasonal amplitude (peak minus the lower base) must reach
seasons.min_crop_amplitude (tag A, set on the dev set only); weaker green-ups (weeds, volunteers)
are not seasons.
Variant: SOS in an earlier calendar year than EOS -> winter green-up, else spring (tag D).
Cover / bare days: smoothed days inside [SOS, EOS] with NDVI >= / < cover threshold.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from fieldwitness.schemas import Tagged
from fieldwitness.story.smooth import load_story, smooth_series

EPOCH = pd.Timestamp("1970-01-01")
SRC = "HLS L30/S30 NDVI, smoothed (Savitzky-Golay), clear pixels"
UNIT_DAY = "day of harvest year"


@dataclass
class SeasonMetrics:
    year: int
    index: int
    variant: str  # "winter" | "spring" (tag D)
    sos: Tagged
    peak: Tagged
    eos: Tagged
    peak_ndvi: Tagged
    canopy_integral: Tagged
    cover_days: Tagged
    bare_days: Tagged
    clear_obs: int


def _tag(v: float, unit: str, tag: str) -> Tagged:
    return Tagged(value=float(v), unit=unit, tag=tag, source=SRC)


def _date(day: float) -> pd.Timestamp:
    return EPOCH + pd.Timedelta(days=float(day))


def _doy(day: float, year: int) -> float:
    """Day of harvest year: 1 Jan of `year` = 1; earlier days are <= 0."""
    return float((_date(day).normalize() - pd.Timestamp(year=year, month=1, day=1)).days + 1)


def _peaks(sm: np.ndarray, step: int, sc: dict) -> list[int]:
    half = max(1, int(sc["min_peak_separation_days"] // step // 2))
    out = []
    for i in range(len(sm)):
        if not np.isfinite(sm[i]) or sm[i] < sc["peak_min_ndvi"]:
            continue
        w = sm[max(0, i - half) : i + half + 1]
        if sm[i] >= np.nanmax(w) and (sm[max(0, i - half) : i] < sm[i]).all():
            out.append(i)
    return out


def _merge_dormant(
    pk: list[int], sm: np.ndarray, grid: np.ndarray, cover: float, cfg: dict
) -> list[int]:
    """Merge neighbouring peaks separated by a Dec-Feb dip that stays above bare soil."""
    months = set(cfg.get("dormancy", {}).get("months", []))
    if not months or not pk:
        return pk
    out = [pk[0]]
    for j in pk[1:]:
        seg = sm[out[-1] : j + 1]
        if np.isfinite(seg).all():
            k = out[-1] + int(np.argmin(seg))
            if seg.min() >= cover and _date(grid[k]).month in months:
                if sm[j] > sm[out[-1]]:
                    out[-1] = j
                continue
        out.append(j)
    return out


def detect_seasons(
    dates: pd.Series, ndvi: pd.Series, cfg: dict | None = None
) -> list[SeasonMetrics]:
    """One field. dates: observation dates; ndvi: clear field medians. Seasons ordered by EOS."""
    cfg = cfg or load_story()
    sc, cover = cfg["seasons"], cfg["cover"]["ndvi_threshold"]
    d = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    v = np.asarray(ndvi, dtype=float)
    ok = np.isfinite(v)
    days = (d[ok] - EPOCH).dt.days.to_numpy(float)
    if len(days) < 4:
        return []
    grid, sm = smooth_series(days, v[ok], cfg["smoothing"])
    step = int(cfg["smoothing"]["grid_days"])
    pk = _merge_dormant(_peaks(sm, step, sc), sm, grid, cover, cfg)
    res: list[SeasonMetrics] = []
    for n, i in enumerate(pk):
        lo = pk[n - 1] if n else 0
        hi = pk[n + 1] if n + 1 < len(pk) else len(sm) - 1
        # keep troughs inside the contiguous (non-gap) stretch around the peak
        nan_l = np.where(np.isnan(sm[lo:i]))[0]
        nan_r = np.where(np.isnan(sm[i : hi + 1]))[0]
        lo = lo + int(nan_l.max()) + 1 if len(nan_l) else lo
        hi = i + int(nan_r.min()) - 1 if len(nan_r) else hi
        left, right = sm[lo : i + 1], sm[i : hi + 1]
        if len(left) < 2 or len(right) < 2:
            continue
        bl, br, pv = float(left.min()), float(right.min()), float(sm[i])
        if pv - max(bl, br) < sc["min_prominence"]:
            continue
        if pv - min(bl, br) < sc.get("min_crop_amplitude", 0.0):
            continue  # weak green-up: weeds / volunteers, not a crop season
        thr = bl + sc["sos_frac"] * (pv - bl)
        tl = int(np.argmin(left))  # SOS = first crossing AFTER the left trough
        a = np.where(left[tl:] >= thr)[0] + tl
        if lo == 0 and left[0] >= thr:
            continue  # data starts above the SOS level -> rise not observed
        b = np.where(right <= br + sc["eos_frac"] * (pv - br))[0]
        if not len(a) or not len(b) or (lo == 0 and a[0] == 0):
            continue  # rise or fall not inside the data -> incomplete season
        si, ei = lo + int(a[0]), i + int(b[0])
        sos_d, eos_d = grid[si], grid[ei]
        year = _date(eos_d).year
        win = sm[si : ei + 1]
        fin = win[np.isfinite(win)]
        integral = float(np.trapezoid(fin, dx=step)) if len(fin) > 1 else 0.0
        res.append(
            SeasonMetrics(
                year=year,
                index=0,
                variant="winter" if _date(sos_d).year < year else "spring",
                sos=_tag(_doy(sos_d, year), UNIT_DAY, "D"),
                peak=_tag(_doy(grid[i], year), UNIT_DAY, "O"),
                eos=_tag(_doy(eos_d, year), UNIT_DAY, "D"),
                peak_ndvi=_tag(pv, "NDVI", "O"),
                canopy_integral=_tag(integral, "NDVI day", "O"),
                cover_days=_tag((fin >= cover).sum() * step, "day", "D"),
                bare_days=_tag((fin < cover).sum() * step, "day", "D"),
                clear_obs=int(((days >= sos_d) & (days <= eos_d)).sum()),
            )
        )
    seen: dict[int, int] = {}
    for s in res:
        s.index = seen.get(s.year, 0)
        seen[s.year] = s.index + 1
    return res
