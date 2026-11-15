"""Build `option_deltas.json` companion packs for S7 Map Option Comparison vs Current.

Usage:
    uv run python scripts/build_option_deltas.py [packs/demo]
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from fieldwitness.packs.extras import build_option_deltas_for_region
from fieldwitness.schemas import check_tagged


def main(packs_root: Path = Path("packs/demo")) -> None:
    app_public = packs_root.parent.parent / "app" / "public" / "packs"
    for region_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
        if not (region_dir / "index.json").exists():
            continue
        model = build_option_deltas_for_region(region_dir)
        errs = check_tagged(model)
        if errs:
            raise ValueError(f"Untagged floats in {region_dir.name}: {errs[:5]}")
        out_path = region_dir / "option_deltas.json"
        payload = model.model_dump_json()
        out_path.write_text(payload, encoding="utf-8")
        if (app_public / region_dir.name).exists():
            shutil.copyfile(out_path, app_public / region_dir.name / "option_deltas.json")
        print(
            f"{region_dir.name}: wrote {out_path} ({len(model.fields)}/{model.n_fields} fields, "
            f"{len(payload.encode('utf-8'))} bytes)"
        )
        for metric, s in model.summary.items():
            print(
                f"  - {metric}: mean={s.mean.value} {s.mean.unit} "
                f"(improved={s.improved_count}/{s.valid_count})"
            )


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("packs/demo")
    main(root)
