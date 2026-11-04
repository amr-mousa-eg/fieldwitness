"""T2.1 gap-fill + Savitzky-Golay smoothing of one field's NDVI series.

Savitzky-Golay filter: Savitzky & Golay (1964), Anal. Chem. 36(8):1627 - local least-squares
polynomial fit; the smoothed value is the fitted polynomial at the window centre. Implemented here
with numpy (no scipy dependency). Edge handling: window shrinks is NOT used; the first/last
half-window values are fitted with the polynomial of the first/last full window (standard
"interp" mode). Parameters come from config/story.yaml (team choices, tag A).
"""

from pathlib import Path

import numpy as np
import yaml

CONFIG = Path("config/story.yaml")


def load_story(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def savgol(y: np.ndarray, window: int, order: int) -> np.ndarray:
    """Savitzky-Golay smoothing of a complete (no NaN) 1-D array; output length = input length."""
    y = np.asarray(y, dtype=float)
    if window % 2 != 1 or window <= order:
        raise ValueError("window must be odd and > order")
    n = len(y)
    if n < window:
        return y.copy()
    h = window // 2
    x = np.arange(-h, h + 1, dtype=float)
    vander = np.vander(x, order + 1, increasing=True)
    pinv = np.linalg.pinv(vander)  # (order+1, window); row 0 = centre-value coefficients
    out = np.convolve(y, pinv[0][::-1], mode="same")
    # edges: evaluate the polynomial fitted on the first / last full window
    first = vander @ (pinv @ y[:window])
    last = vander @ (pinv @ y[-window:])
    out[:h] = first[:h]
    out[-h:] = last[-h:]
    return out


def gap_fill(
    days: np.ndarray, values: np.ndarray, grid_days: int, max_gap_days: int
) -> tuple[np.ndarray, np.ndarray]:
    """Linear interpolation onto a regular grid (days = integer day numbers, sorted, finite values).

    Grid points inside a gap longer than max_gap_days, or outside the observed range, are NaN.
    """
    days = np.asarray(days, dtype=float)
    values = np.asarray(values, dtype=float)
    grid = np.arange(days[0], days[-1] + 1, grid_days, dtype=float)
    filled = np.interp(grid, days, values)
    idx = np.searchsorted(days, grid, side="right")
    left = days[np.clip(idx - 1, 0, len(days) - 1)]
    right = days[np.clip(idx, 0, len(days) - 1)]
    filled[(right - left) > max_gap_days] = np.nan
    return grid, filled


def smooth_series(
    days: np.ndarray, values: np.ndarray, cfg: dict | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Gap-fill then Savitzky-Golay per contiguous (non-NaN) run; clip to [-1, 1].

    Returns (grid_days, smoothed) with len(smoothed) == len(grid_days). Runs shorter than the
    window are returned unsmoothed (just gap-filled). Needs >= 2 observations, else empty.
    """
    cfg = cfg or load_story()["smoothing"]
    days = np.asarray(days, dtype=float)
    values = np.asarray(values, dtype=float)
    ok = np.isfinite(values)
    days, values = days[ok], values[ok]
    if len(days) < 2:
        return days.copy(), np.clip(values, -1.0, 1.0)
    grid, filled = gap_fill(days, values, cfg["grid_days"], cfg["max_gap_days"])
    out = filled.copy()
    good = np.isfinite(filled)
    # contiguous runs of finite values
    edges = np.flatnonzero(np.diff(np.concatenate(([0], good.view(np.int8), [0]))))
    for s, e in zip(edges[::2], edges[1::2], strict=True):
        out[s:e] = savgol(filled[s:e], cfg["savgol_window"], cfg["savgol_order"])
    return grid, np.clip(out, -1.0, 1.0)
