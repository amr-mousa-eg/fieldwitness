"""Botanical family per crop: GBIF Backbone species-match, cross-checked with USDA PLANTS.

Usage:  uv run python -u scripts/check_families.py

Scientific names come from FAO-66 crop chapters (PDF page cited) where they exist; rapeseed and the
oat cover-crop proxy have no FAO-66 chapter, so their names were specified by the user (2026-11-04).
APIs verified with one call each on 2026-11-04 (docs/api_notes.md). Prints a JSON summary.
"""

import datetime as dt
import json
import re

import requests

GBIF = "https://api.gbif.org/v1/species"
USDA = "https://plantsservices.sc.egov.usda.gov/api"

# crop key -> (scientific name, name source)
FAO66 = "FAO-66 (Steduto et al. 2012), PDF p. {}"
NAMES = {
    "maize": ("Zea mays", FAO66.format(129)),
    "sorghum": ("Sorghum bicolor", FAO66.format(159)),
    "winter_wheat": ("Triticum aestivum", FAO66.format(107)),
    "spring_wheat": ("Triticum aestivum", FAO66.format(107)),
    "winter_barley": ("Hordeum vulgare", FAO66.format(149)),
    "spring_barley": ("Hordeum vulgare", FAO66.format(149)),
    "sunflower": ("Helianthus annuus", FAO66.format(179)),
    "soybean": ("Glycine max", FAO66.format(139)),
    "rapeseed": ("Brassica napus", "specified by the user (2026-11-04); no FAO-66 chapter"),
    "cover_crop": (
        "Avena sativa",
        "specified by the user (2026-11-04) for the oat proxy; no FAO-66 chapter",
    ),
}


def gbif_match(name: str) -> dict:
    r = requests.get(f"{GBIF}/match", params={"name": name, "kingdom": "Plantae"}, timeout=60)
    r.raise_for_status()
    return r.json()


def usda_search(text: str) -> list[dict]:
    r = requests.get(f"{USDA}/PlantSearch", params={"searchText": text}, timeout=60)
    r.raise_for_status()
    return r.json()


def usda_family(symbol: str) -> str | None:
    r = requests.get(f"{USDA}/PlantProfile", params={"symbol": symbol}, timeout=60)
    r.raise_for_status()
    for a in r.json().get("Ancestors") or []:
        if (a.get("Rank") or "").lower() == "family":
            return re.sub(r"<[^>]+>", "", a.get("ScientificName") or "")
    return None


def usda_species(name: str) -> dict | None:
    for hit in usda_search(name):
        p = hit.get("Plant") or {}
        sci = re.sub(r"<[^>]+>", "", p.get("ScientificName") or "")
        if p.get("Rank") == "Species" and sci.startswith(name):
            return {
                "symbol": p["Symbol"],
                "scientific_name": sci,
                "common_name": p.get("CommonName"),
            }
    return None


def main() -> None:
    out = {}
    for crop, (name, src) in NAMES.items():
        if name is None:
            out[crop] = {"error": "no agreed scientific name"}
            continue
        g = gbif_match(name)
        u = usda_species(name)
        fam_u = usda_family(u["symbol"]) if u else None
        out[crop] = {
            "scientific_name": name,
            "name_source": src,
            "gbif_usage_key": g.get("usageKey"),
            "gbif_scientific_name": g.get("scientificName"),
            "gbif_status": g.get("status"),
            "gbif_match_type": g.get("matchType"),
            "gbif_confidence": g.get("confidence"),
            "gbif_family": g.get("family"),
            "usda_symbol": u["symbol"] if u else None,
            "usda_family": fam_u,
            "families_agree": fam_u is not None and fam_u.split()[0] == g.get("family"),
        }
    out["_accessed"] = dt.date.today().isoformat()
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
