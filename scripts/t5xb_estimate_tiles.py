"""T5.xb: estimate HLS download size for surrounding Kansas tiles.

CLAUDE.md Rule 11: Stop if download estimate > 1 GB.
Outputs results/neighbours/tiles_estimate.json and tiles_estimate.md.
"""

import json
from pathlib import Path

BASE_TILE = "14SLH"
SURROUNDING_TILES = [
    "14SLJ",  # N
    "14SLG",  # S
    "14SKH",  # W
    "14SMH",  # E
    "14SKJ",  # NW
    "14SMJ",  # NE
    "14SKG",  # SW
    "14SMG",  # SE
]

APPEEARS_DIR = Path("data/appeears/ks_t14slh")
OUT_JSON = Path("results/neighbours/tiles_estimate.json")
OUT_MD = Path("results/neighbours/tiles_estimate.md")


def estimate() -> dict:
    files = list(APPEEARS_DIR.rglob("*.*"))
    base_bytes = sum(f.stat().st_size for f in files if f.is_file())
    base_mb = base_bytes / (1024 * 1024)
    base_gb = base_bytes / (1024 * 1024 * 1024)
    n_fields = 200
    mb_per_field = base_mb / n_fields

    estimates = {
        "base_tile": BASE_TILE,
        "base_tile_fields": n_fields,
        "base_tile_files": len(files),
        "base_tile_mb": round(base_mb, 1),
        "base_tile_gb": round(base_gb, 2),
        "mb_per_field": round(mb_per_field, 2),
        "cap_gb": 1.0,
        "surrounding_tile_count": len(SURROUNDING_TILES),
        "surrounding_tiles": SURROUNDING_TILES,
        "one_additional_tile_gb": round(base_gb, 2),
        "four_cardinal_tiles_gb": round(4 * base_gb, 2),
        "full_ring_eight_tiles_gb": round(8 * base_gb, 2),
        "exceeds_cap_single_tile": base_gb > 1.0,
        "exceeds_cap_full_ring": (8 * base_gb) > 1.0,
        "action": "STOP",
        "reason": (
            f"Even a single additional tile (~{base_gb:.2f} GB) exceeds the 1.0 GB download cap "
            f"(CLAUDE.md rule 11). Full 8-tile ring would require ~{8 * base_gb:.1f} GB."
        ),
    }
    return estimates


def write_md(data: dict, out_path: Path) -> None:
    tiles_str = ", ".join(data["surrounding_tiles"])
    lines = [
        "# T5.xb Surrounding Tiles HLS Download Estimation",
        "",
        "Source: `scripts/t5xb_estimate_tiles.py` -> `results/neighbours/tiles_estimate.json`.",
        "Rule: CLAUDE.md Rule 11 (1 GB download cap per run). Stop if > 1 GB.",
        "",
        "## Baseline (T14SLH)",
        "",
        f"- Pilot fields: {data['base_tile_fields']}",
        (
            f"- On-disk HLS data: {data['base_tile_files']} files, "
            f"{data['base_tile_mb']} MB ({data['base_tile_gb']} GB)"
        ),
        f"- Average per field: {data['mb_per_field']} MB/field (2016-2024, 30 m HLS-VI + Fmask)",
        "",
        "## Surrounding Tiles Candidate Grid",
        "",
        f"- Target MGRS tiles (8 surrounding 100 km squares): {tiles_str}",
        f"- 1 additional tile (200 fields): **{data['one_additional_tile_gb']} GB** (> 1.0 GB cap)",
        f"- 4 cardinal tiles (800 fields): **{data['four_cardinal_tiles_gb']} GB** (>> 1.0 GB cap)",
        f"- 8 full ring tiles (1,600 fields): **{data['full_ring_eight_tiles_gb']} GB**",
        "",
        "## Conclusion & Recommendation",
        "",
        f"**Status: {data['action']}**.",
        data["reason"],
        "",
        "Without user authorization for a multi-gigabyte download exception (similar to the",
        "2026-11-04 T1.5 exception), tile expansion cannot proceed under the 1 GB cap.",
        "Consequently, T5.xc (re-grading) is skipped because no contrast passed diagnostics.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    data = estimate()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_md(data, OUT_MD)
    print(f"Estimation complete: Action = {data['action']} ({data['reason']})")
