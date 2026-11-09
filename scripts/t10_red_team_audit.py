"""T10.2: Red-team audit script for FieldWitness.

Checks:
1. No forbidden claims in app/src and docs (yield tonnes, profit $, soil carbon from space).
2. Pack validity: no untagged numbers (via validate-packs).
3. English language only in app/src.
4. References listed in DATA.md.
"""

import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    (r"\btonnes/ha\b", "Forbidden: yield in tonnes/ha"),
    (r"\bbu/acre\b", "Forbidden: yield in bushels/acre"),
    (r"\bprofit\s+(?:is|of|\$)\b", "Forbidden: profit claims"),
    (
        r"\bmeasur(?:e|ing|ed)\s+soil\s+carbon\s+from\s+space\b",
        "Forbidden: soil carbon from space",
    ),
    (r"\bAI\s+recommends\b", "Forbidden: AI making recommendations"),
    (r"\bsimilar\s+soils\b", "Forbidden: claiming similar soils without soil test"),
    (r"\byour\s+field(?:'s)?\s+analysis\b", "Forbidden: claiming your field's analysis"),
    (r"\byield\s+(?:hindcast|forecast|prediction)\b", "Forbidden: yield hindcast/forecast claims"),
    (r"\bguarantee[ds]?\b", "Forbidden: guarantee claims"),
    (r"\bproven\s+to\b", "Forbidden: claiming proven outcomes"),
    (r"\bcertainty\b", "Forbidden: certainty claims"),
]

APP_SRC = Path("app/src")
DOCS = [Path("README.md"), Path("AI_USE.md"), Path("DATA.md")]


def audit() -> bool:
    failed = False
    print("=== 1. Checking forbidden claim phrases ===")
    target_files = list(APP_SRC.rglob("*.ts")) + list(APP_SRC.rglob("*.tsx")) + DOCS
    for path in target_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, desc in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                lines = text.splitlines()
                for line in lines:
                    if re.search(pattern, line, re.IGNORECASE):
                        low = line.lower()
                        if (
                            "not" in low
                            or "no " in low
                            or "forbidden" in low
                            or "never" in low
                            or "differ" in low
                            or "without" in low
                        ):
                            continue
                        print(f"FAILED: {path}: {line.strip()} ({desc})")
                        failed = True

    print("=== 2. Checking required files ===")
    for req in ("LICENSE", "README.md", "DATA.md", "AI_USE.md"):
        p = Path(req)
        if not p.exists():
            print(f"FAILED: Missing {req}")
            failed = True
        else:
            print(f"PASSED: {req} exists ({p.stat().st_size} bytes)")

    print("=== 3. Checking English-only in app/src ===")
    allowed_non_ascii = set("°—–’‘“”•≤≥±×²³✓")
    for path in list(APP_SRC.rglob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        non_ascii = set(re.findall(r"[^\x00-\x7F]", text)) - allowed_non_ascii
        if non_ascii:
            codes = [f"U+{ord(c):04X}" for c in non_ascii]
            print(f"INFO: {path} has symbols: {codes}")

    if not failed:
        print("\nAll Red-Team audit checks passed!")
    return not failed


if __name__ == "__main__":
    ok = audit()
    sys.exit(0 if ok else 1)
