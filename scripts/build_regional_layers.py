"""E1.1: Build/update NASA regional layers (GRACE TWS + POWER heatwave_days) for UA & KS.

Usage: uv run python -u scripts/build_regional_layers.py

Reads region bounding boxes from config/regions.yaml, preserves existing field_colouring
and any pre-built layers (such as Kansas JPL TELLUS GRACE and SMAP L4 anomaly), and
appends/updates UT-CSR RL06.3 GRACE TWS (when NetCDF assets exist in data/context/grace/)
plus NASA POWER heatwave_days (T2M_MAX >= 35.0 degC on verified MERRA-2 0.5 x 0.625 deg cells).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from fieldwitness.packs import extras as X
from fieldwitness.packs.validate import validate_dir
from fieldwitness.schemas import RegionLayers

CSR_NC = Path("data/context/grace/CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc")
CSR_MASK = Path("data/context/grace/CSR_GRACE_GRACE-FO_RL06_Mascons_v02_LandMask.nc")
PACKS_ROOT = Path("packs/demo")
CUTOFF = date(2024, 12, 31)


def _write_compact(path: Path, model: RegionLayers) -> None:
    path.write_text(
        json.dumps(model.model_dump(mode="json"), separators=(",", ":")),
        encoding="utf-8",
    )


def update_region(region_id: str, reg_cfg: dict, vuln_cfg: dict, include_csr: bool) -> None:
    path = PACKS_ROOT / region_id / "layers.json"
    existing = RegionLayers.model_validate_json(path.read_bytes())
    bbox = tuple(float(x) for x in reg_cfg["bbox_lonlat"])
    heat_thr = float(vuln_cfg["heat_tmax_c"]["maize"]["value"])

    by_id = {layer.layer_id: layer for layer in existing.layers}
    if include_csr and CSR_NC.exists() and CSR_MASK.exists():
        by_id["grace_tws"] = X.grace_csr_layer(str(CSR_NC), str(CSR_MASK), bbox, cutoff_date=CUTOFF)
    by_id["heatwave_days"] = X.heatwave_layer(bbox, threshold_c=heat_thr, cutoff_date=CUTOFF)

    order = [lid for lid in ("grace_tws", "smap_anomaly", "heatwave_days") if lid in by_id]
    updated = RegionLayers(
        schema_version=existing.schema_version,
        region_id=existing.region_id,
        layers=[by_id[lid] for lid in order],
        field_colouring=existing.field_colouring,
        data_as_of=max(existing.data_as_of, CUTOFF),
    )
    _write_compact(path, updated)
    for lid in order:
        lay = by_id[lid]
        yrs = lay.region_mean.x
        print(
            f"  [{region_id}] {lid}: {len(lay.grid.cells)} cells, years {yrs[0]}..{yrs[-1]} "
            f"(latest={lay.region_mean.values[-1]}, trend={lay.trend.value} {lay.trend.unit})",
            flush=True,
        )


def main() -> None:
    reg_all = yaml.safe_load(Path("config/regions.yaml").read_text(encoding="utf-8"))["regions"]
    vuln_cfg = X.load_vuln_cfg()

    print("Updating regional layers in packs/demo ...", flush=True)
    update_region("ua_central_t36uvu", reg_all["ua_central_t36uvu"], vuln_cfg, include_csr=True)
    update_region("ks_t14slh", reg_all["ks_t14slh"], vuln_cfg, include_csr=False)

    probs = validate_dir(PACKS_ROOT)
    if probs:
        raise SystemExit(f"Validation failed: {probs[:5]}")
    print("Validation passed for packs/demo.", flush=True)


if __name__ == "__main__":
    main()
