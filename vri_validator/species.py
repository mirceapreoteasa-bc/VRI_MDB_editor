"""Conifer / deciduous classification built from codes.xml species names."""

from __future__ import annotations

from .codes import CodeBook

CONIFER_WORDS = (
    "fir", "cedar", "douglas-fir", "hemlock", "juniper", "larch", "tamarack",
    "pine", "spruce", "yew", "cypress", "sequoia", "redwood", "conifer",
    "port orford-cedar", "incense-cedar",
)
DECIDUOUS_WORDS = (
    "aspen", "poplar", "cottonwood", "alder", "birch", "dogwood", "cascara",
    "maple", "oak", "cherry", "willow", "apple", "pear", "ash", "elm",
    "hickory", "mountain-ash", "crab apple", "hardwood", "broadleaf",
    "arbutus",
)
# Codes whose names are ambiguous or missing from the description keywords.
OVERRIDES = {
    "X": "unknown", "Z": "unknown",
    "XC": "conifer", "ZC": "conifer",
    "XH": "deciduous", "ZH": "deciduous",
    "R": "deciduous", "RA": "deciduous",       # arbutus
    "U": "deciduous", "UA": "deciduous", "UP": "deciduous",
    "ME": "deciduous",                          # box elder
    "SXL": "conifer", "SXS": "conifer",         # Sitka hybrids
}


def classify(desc: str) -> str:
    d = (desc or "").lower()
    conifer = any(w in d for w in CONIFER_WORDS)
    deciduous = any(w in d for w in DECIDUOUS_WORDS)
    if conifer and not deciduous:
        return "conifer"
    if deciduous and not conifer:
        return "deciduous"
    if conifer and deciduous:
        # e.g. "Douglas maple" contains neither; "mountain-ash" is deciduous.
        # Prefer the more specific deciduous words.
        if any(w in d for w in ("maple", "ash", "apple", "cherry", "willow", "birch",
                                "alder", "aspen", "poplar", "cottonwood", "oak")):
            return "deciduous"
        return "conifer"
    return "unknown"


def species_types(codes: CodeBook) -> dict[str, str]:
    types: dict[str, str] = {}
    for code, desc in codes.codes("TREE_SPECIES_CODE").items():
        types[code] = OVERRIDES.get(code, classify(desc))
    return types


def species_type(types: dict[str, str], code: str) -> str:
    return types.get((code or "").strip(), "unknown")
