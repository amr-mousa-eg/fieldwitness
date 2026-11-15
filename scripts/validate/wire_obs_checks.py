"""Attach leak-free Landsat LST [O] & ERA5 extreme-rain [E] obs_checks to shipped calendars.

Updates `packs/demo/{ks_t14slh,ua_central_t36uvu}/*.calendar.json` in place using cached
observations clipped to each calendar's `data_as_of`, validates provenance tags (`check_tagged`),
and checks the 300 KB shipped pack file limit.

Usage: uv run python scripts/validate/wire_obs_checks.py
"""

from __future__ import annotations

import json
from pathlib import Path

from fieldwitness.packs import extras as X
from fieldwitness.schemas import FieldCalendar, check_tagged

REGIONS = ("ks_t14slh", "ua_central_t36uvu")
MAX_PACK_BYTES = 300_000


def wire_region(region_id: str, packs_root: Path = Path("packs/demo")) -> dict[str, int]:
    reg_dir = packs_root / region_id
    cal_files = sorted(reg_dir.glob("*.calendar.json"))
    if not cal_files:
        return {"calendars": 0, "with_lst": 0, "with_era5": 0, "tagged_errors": 0}

    sample_cal = FieldCalendar.model_validate_json(cal_files[0].read_text(encoding="utf-8"))
    lst_all, era5_all = X.load_obs_checks_inputs(region_id, cutoff_date=sample_cal.data_as_of)

    with_lst = 0
    with_era5 = 0
    errors = 0
    for path in cal_files:
        cal = FieldCalendar.model_validate_json(path.read_text(encoding="utf-8"))
        # Re-clip if an individual field has an earlier data_as_of
        lst_sub = lst_all
        era_sub = era5_all
        if cal.data_as_of != sample_cal.data_as_of:
            lst_sub, era_sub = X.load_obs_checks_inputs(region_id, cutoff_date=cal.data_as_of)
        lst_f = (
            lst_sub[lst_sub["field_id"].astype(str) == cal.field_id]
            if lst_sub is not None
            else None
        )
        checks = X.obs_checks_series(field_lst=lst_f, era5_df=era_sub)
        updated = cal.model_copy(update={"obs_checks": checks})
        bad = check_tagged(updated)
        if bad:
            errors += len(bad)
            raise RuntimeError(f"{path.name}: untagged fields: {bad[:5]}")
        txt = json.dumps(updated.model_dump(mode="json", exclude_none=False), separators=(",", ":"))
        raw = txt.encode("utf-8")
        if len(raw) > MAX_PACK_BYTES:
            raise RuntimeError(f"{path.name}: {len(raw)} bytes > {MAX_PACK_BYTES}")
        path.write_text(txt, encoding="utf-8")
        if checks:
            if "lst_heat" in checks:
                with_lst += 1
            if "extreme_rain_era5" in checks:
                with_era5 += 1
    return {
        "calendars": len(cal_files),
        "with_lst": with_lst,
        "with_era5": with_era5,
        "tagged_errors": errors,
    }


def main() -> int:
    for reg in REGIONS:
        stats = wire_region(reg)
        print(f"{reg}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
