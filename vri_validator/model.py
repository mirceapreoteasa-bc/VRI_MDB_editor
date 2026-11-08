"""In-memory polygon model, joined by FOREST_COVER_OBJECT_ID."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .mdb import MdbReader

TABLES = (
    "FOREST_COVER_OBJECT",
    "VEGETATION_COVER_POLYGON_EST",
    "TREE_COVER_LAYER_ESTIMATED",
    "TREE_SPECIES_ESTIMATED",
    "LAND_COVER_COMPONENT_EST",
    "NON_VEGETATIVE_COVER_EST",
)


def to_int(value: Any) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _logical_count(reader: MdbReader, name: str, rows: list[dict[str, str]]) -> int:
    count = reader.count(name)
    return len(rows) if count is None else count


def _dedupe_last(rows: list[dict[str, str]], key: Any) -> list[dict[str, str]]:
    """Keep the last row for each key.

    An Access update can leave the old row image on disk.  mdbtools 1.0.0's
    ``mdb-export`` emits that image and the replacement, while ``mdb-count``
    and Access hide the deleted image.  The replacement is appended after the
    original, so keeping the last occurrence matches Jet's logical view.
    """
    indexed: dict[Any, dict[str, str]] = {}
    unkeyed: list[dict[str, str]] = []
    for row in rows:
        value = key(row)
        if value is None:
            unkeyed.append(row)
        else:
            indexed[value] = row
    return list(indexed.values()) + unkeyed


def _pivot_year(dt: datetime) -> datetime:
    if dt.year > datetime.now().year + 1:
        try:
            return dt.replace(year=dt.year - 100)
        except ValueError:
            pass
    return dt


def year_of(value: Any) -> int | None:
    s = text(value)
    if not s:
        return None
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return _pivot_year(datetime.strptime(s, fmt)).year
        except ValueError:
            pass
    if s.isdigit() and len(s) == 4:
        return int(s)
    return None


def date_of(value: Any) -> datetime | None:
    s = text(value)
    if not s:
        return None
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return _pivot_year(datetime.strptime(s, fmt))
        except ValueError:
            pass
    return None


@dataclass
class Layer:
    row: dict[str, str]
    species: list[dict[str, str]] = field(default_factory=list)

    @property
    def order(self) -> int | None:
        return to_int(self.row.get("LAYER_ORDER"))

    @property
    def level(self) -> str:
        return text(self.row.get("LAYER_LEVEL_CODE"))

    @property
    def is_dead(self) -> bool:
        return self.level.upper() == "D"


@dataclass
class Polygon:
    fid: int | None
    fco: dict[str, str]
    vcpe: dict[str, str] | None = None
    layers: list[Layer] = field(default_factory=list)
    lcc: list[dict[str, str]] = field(default_factory=list)
    nvce: list[dict[str, str]] = field(default_factory=list)

    @property
    def number(self) -> str:
        return text(self.fco.get("POLYGON_NUMBER"))

    @property
    def objectid(self) -> int | None:
        return to_int(self.fco.get("OBJECTID"))

    @property
    def standard(self) -> str:
        return text(self.fco.get("INVENTORY_STANDARD_CODE"))

    @property
    def area(self) -> float | None:
        return to_float(self.fco.get("POLYGON_AREA"))

    def live_layers(self) -> list[Layer]:
        return [layer for layer in self.layers if not layer.is_dead]

    def tse(self) -> list[tuple[Layer, dict[str, str]]]:
        return [(layer, sp) for layer in self.layers for sp in layer.species]

    def label(self) -> str:
        return self.number or str(self.fid if self.fid is not None else "?")


@dataclass
class Dataset:
    path: str
    polygons: list[Polygon]
    orphans: dict[str, list[dict[str, str]]]
    row_counts: dict[str, int]


def load_dataset(path: str) -> Dataset:
    reader = MdbReader(path)
    available = set(reader.tables())
    missing = [t for t in TABLES if t not in available]
    if missing:
        raise RuntimeError(
            f"not a VRIMS personal geodatabase (missing tables: {', '.join(missing)})"
        )

    fco_rows = reader.table("FOREST_COVER_OBJECT")
    vcpe_rows = _dedupe_last(
        reader.table("VEGETATION_COVER_POLYGON_EST"),
        lambda row: to_int(row.get("FOREST_COVER_OBJECT_ID")),
    )
    tcl_rows = _dedupe_last(
        reader.table("TREE_COVER_LAYER_ESTIMATED"),
        lambda row: to_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")),
    )
    tse_rows = reader.table("TREE_SPECIES_ESTIMATED")
    lcc_rows = reader.table("LAND_COVER_COMPONENT_EST")
    nvce_rows = reader.table("NON_VEGETATIVE_COVER_EST")

    polygons: dict[int, Polygon] = {}
    duplicate_fco: list[dict[str, str]] = []
    for row in fco_rows:
        fid = to_int(row.get("FOREST_COVER_OBJECT_ID"))
        if fid is None:
            continue
        if fid in polygons:
            duplicate_fco.append(row)
            continue
        polygons[fid] = Polygon(fid=fid, fco=row)

    orphans: dict[str, list[dict[str, str]]] = {
        "VEGETATION_COVER_POLYGON_EST": [],
        "TREE_COVER_LAYER_ESTIMATED": [],
        "TREE_SPECIES_ESTIMATED": [],
        "LAND_COVER_COMPONENT_EST": [],
        "NON_VEGETATIVE_COVER_EST": [],
    }

    vcpe_by_fid: dict[int, dict[str, str]] = {}
    for row in vcpe_rows:
        fid = to_int(row.get("FOREST_COVER_OBJECT_ID"))
        if fid not in polygons:
            orphans["VEGETATION_COVER_POLYGON_EST"].append(row)
            continue
        if fid in vcpe_by_fid:
            # keep the first, report duplicates as an orphan-like problem later
            orphans["VEGETATION_COVER_POLYGON_EST"].append(row)
            continue
        vcpe_by_fid[fid] = row
    for fid, poly in polygons.items():
        poly.vcpe = vcpe_by_fid.get(fid)

    layers_by_id: dict[int, Layer] = {}
    for row in tcl_rows:
        fid = to_int(row.get("FOREST_COVER_OBJECT_ID"))
        if fid not in polygons:
            orphans["TREE_COVER_LAYER_ESTIMATED"].append(row)
            continue
        layer = Layer(row=row)
        polygons[fid].layers.append(layer)
        lid = to_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        if lid is not None:
            layers_by_id[lid] = layer

    for row in tse_rows:
        lid = to_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        layer = layers_by_id.get(lid)
        if layer is None:
            orphans["TREE_SPECIES_ESTIMATED"].append(row)
            continue
        layer.species.append(row)

    for row in lcc_rows:
        fid = to_int(row.get("FOREST_COVER_OBJECT_ID"))
        if fid not in polygons:
            orphans["LAND_COVER_COMPONENT_EST"].append(row)
            continue
        polygons[fid].lcc.append(row)

    for row in nvce_rows:
        fid = to_int(row.get("FOREST_COVER_OBJECT_ID"))
        if fid not in polygons:
            orphans["NON_VEGETATIVE_COVER_EST"].append(row)
            continue
        polygons[fid].nvce.append(row)

    for poly in polygons.values():
        poly.layers.sort(key=lambda l: (l.order is None, l.order or 0))
        for layer in poly.layers:
            layer.species.sort(key=lambda s: to_int(s.get("SPECIES_ORDER")) or 0)
        poly.lcc.sort(key=lambda r: to_int(r.get("LAND_COVER_ORDER")) or 0)
        poly.nvce.sort(key=lambda r: to_int(r.get("NON_VEG_ORDER")) or 0)

    if duplicate_fco:
        orphans["FOREST_COVER_OBJECT_DUPLICATE"] = duplicate_fco

    return Dataset(
        path=str(path),
        polygons=sorted(polygons.values(), key=lambda p: (p.number, p.fid or 0)),
        orphans=orphans,
        row_counts={
            "FOREST_COVER_OBJECT": _logical_count(reader, "FOREST_COVER_OBJECT", fco_rows),
            "VEGETATION_COVER_POLYGON_EST": _logical_count(reader, "VEGETATION_COVER_POLYGON_EST", vcpe_rows),
            "TREE_COVER_LAYER_ESTIMATED": _logical_count(reader, "TREE_COVER_LAYER_ESTIMATED", tcl_rows),
            "TREE_SPECIES_ESTIMATED": _logical_count(reader, "TREE_SPECIES_ESTIMATED", tse_rows),
            "LAND_COVER_COMPONENT_EST": _logical_count(reader, "LAND_COVER_COMPONENT_EST", lcc_rows),
            "NON_VEGETATIVE_COVER_EST": _logical_count(reader, "NON_VEGETATIVE_COVER_EST", nvce_rows),
        },
    )
