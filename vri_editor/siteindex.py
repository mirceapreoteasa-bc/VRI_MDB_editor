"""Site index from leading species, age and height (Fix Site Index).

The table data/si_table_v154.csv.gz was generated from the official Ministry
Sindex DLL v1.54 (sindex64.dll) through SiteToolsCmd (LIDAR mode): for each DLL
species, breast-height age 10-200 (step 2) and height 2-40 m (step 0.5) give a
site index. Values between grid nodes are bilinearly interpolated.

Species codes are the VRIMS codes (data/bc_species_dll_index.json maps them to
the DLL species index).
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

_DATA = Path(__file__).resolve().parent.parent / "data"
AGE_MIN, AGE_STEP, AGE_MAX = 10, 2, 200
HT_MIN, HT_STEP, HT_MAX = 2.0, 0.5, 40.0

_grids: Optional[Dict[int, Dict[Tuple[int, float], float]]] = None
_species_index: Optional[Dict[str, int]] = None


def _load() -> None:
    global _grids, _species_index
    if _grids is not None:
        return
    _species_index = {k.upper(): int(v) for k, v in json.loads(
        (_DATA / "bc_species_dll_index.json").read_text(encoding="utf-8")).items()}
    grids: Dict[int, Dict[Tuple[int, float], float]] = {}
    with gzip.open(_DATA / "si_table_v154.csv.gz", "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            grids.setdefault(int(row["dll_species_code"]), {})[
                (int(row["age_bh"]), float(row["height_m"]))] = float(row["site_index_m"])
    _grids = grids


def dll_index(species: str) -> Optional[int]:
    """DLL species index for a VRIMS species code, or None if no curve."""
    _load()
    return _species_index.get((species or "").strip().upper())


def site_index(species: str, age: float, height: float) -> Optional[float]:
    """Site index (m, base age 50) for a species, breast-height age and height."""
    idx = dll_index(species)
    if idx is None:
        return None
    try:
        age = float(age)
        height = float(height)
    except (TypeError, ValueError):
        return None
    if not (AGE_MIN <= age <= AGE_MAX) or not (HT_MIN <= height <= HT_MAX):
        return None
    _load()
    grid = _grids.get(idx)
    if not grid:
        return None
    a0 = AGE_MIN + int((age - AGE_MIN) // AGE_STEP) * AGE_STEP
    a1 = min(a0 + AGE_STEP, AGE_MAX)
    h0 = HT_MIN + int((height - HT_MIN) // HT_STEP) * HT_STEP
    h1 = min(h0 + HT_STEP, HT_MAX)
    ta = 0.0 if a1 == a0 else (age - a0) / (a1 - a0)
    th = 0.0 if h1 == h0 else (height - h0) / (h1 - h0)
    corners = [(grid.get((a0, round(h0, 2))), (1 - ta) * (1 - th)),
               (grid.get((a1, round(h0, 2))), ta * (1 - th)),
               (grid.get((a0, round(h1, 2))), (1 - ta) * th),
               (grid.get((a1, round(h1, 2))), ta * th)]
    if any(v is None for v, _ in corners):
        return None
    return round(sum(v * w for v, w in corners), 2)
