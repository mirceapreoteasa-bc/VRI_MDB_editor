"""Documented VRIMS derived fields: BCLCS, layer rank, and LCC order."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .model import Dataset, Layer, Polygon, text, to_float, to_int

TREED = {"TB", "TC", "TM"}
SHRUB = {"ST", "SL"}
HERB = {"HE", "HF", "HG"}
BRYOID = {"BY", "BM", "BL"}
WATER_NV = {"LA", "RI", "RE", "OC"}

BCLCS_ATTRIBUTES = (
    "SURFACE_EXPRESSION_CODE",
    "MODIFYING_PROCESS_CODE",
    "SITE_POSITION_MESO_CODE",
    "ALPINE_DESIGNATION_CODE",
    "SOIL_NUTRIENT_REGIME_CODE",
    "DATA_SOURCE_ECOSYS_CLASS_CODE",
    "SHRUB_HEIGHT",
    "SHRUB_CROWN_CLOSURE",
    "SHRUB_COVER_PATTERN_CODE",
    "HERB_COVER_TYPE_CODE",
    "HERB_COVER_PCT",
    "HERB_COVER_PATTERN_CODE",
    "BRYOID_COVER_PCT",
)


@dataclass(frozen=True)
class VcpeUpdate:
    fid: int
    levels: tuple[str, str, str, str, str]


@dataclass(frozen=True)
class RankUpdate:
    layer_id: int
    rank: str | None


@dataclass(frozen=True)
class LccOrderUpdate:
    lcc_id: int
    order: int


@dataclass
class DerivedUpdates:
    vcpe: list[VcpeUpdate] = field(default_factory=list)
    tcl: list[RankUpdate] = field(default_factory=list)
    lcc: list[LccOrderUpdate] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.vcpe) + len(self.tcl) + len(self.lcc)


def tree_closure(poly: Polygon) -> float:
    return sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0 for layer in poly.layers)


def understory_total(vcpe: dict[str, str]) -> float:
    return sum(to_float(vcpe.get(name)) or 0 for name in
               ("SHRUB_CROWN_CLOSURE", "HERB_COVER_PCT", "BRYOID_COVER_PCT"))


def mostly_water(poly: Polygon) -> bool:
    vcpe = poly.vcpe or {}
    if text(vcpe.get("NON_PRODUCTIVE_DESCRIPTOR_CODE")) in {"L", "RIV", "NA"}:
        return True
    for row in poly.nvce:
        if (text(row.get("NON_VEG_COVER_TYPE_CODE")) in WATER_NV
                and (to_float(row.get("NON_VEG_COVER_PCT")) or 0) >= 50):
            return True
    return False


def swampy(poly: Polygon) -> bool:
    if not poly.lcc:
        return False
    return (to_float(poly.lcc[0].get("SOIL_MOISTURE_REGIME_CODE")) or 0) > 6


def dominant_nv(poly: Polygon) -> str:
    if not poly.nvce:
        return ""
    row = max(poly.nvce, key=lambda item: to_float(item.get("NON_VEG_COVER_PCT")) or 0)
    return text(row.get("NON_VEG_COVER_TYPE_CODE"))


def treed_class(poly: Polygon, species_class: Callable[[str], str]):
    use_ba = poly.standard == "V"
    conifer = deciduous = unknown = total = 0.0
    for layer in poly.live_layers():
        base = to_float(layer.row.get("BASAL_AREA")) if use_ba else to_float(
            layer.row.get("CROWN_CLOSURE_PCT"))
        if base is None or not layer.species:
            continue
        for species in layer.species:
            pct = to_float(species.get("SPECIES_PCT")) or 0
            weight = pct / 100.0 * base
            kind = species_class(text(species.get("TREE_SPECIES_CODE")))
            if kind == "conifer":
                conifer += weight
            elif kind == "deciduous":
                deciduous += weight
            else:
                unknown += weight
            total += weight
    known = conifer + deciduous
    if total <= 0 or known <= 0:
        return None
    conifer_share = conifer / total
    deciduous_share = deciduous / total
    unknown_share = unknown / total
    if conifer_share >= 0.75:
        expected = "TC"
    elif deciduous_share >= 0.75:
        expected = "TB"
    else:
        expected = "TM"
    return expected, conifer_share, deciduous_share, unknown_share


def _lcc_classes(poly: Polygon) -> set[str]:
    return {text(row.get("LAND_COVER_CLASS_CODE")) for row in poly.lcc}


def _treed_level4(poly: Polygon, species_class: Callable[[str], str]) -> str:
    derived = treed_class(poly, species_class)
    if derived is not None:
        return derived[0]
    classes = _lcc_classes(poly)
    for code in ("TC", "TB", "TM"):
        if code in classes:
            return code
    return "TM"


def _non_treed_level4(poly: Polygon, vcpe: dict[str, str],
                      species_class: Callable[[str], str]) -> tuple[str, str]:
    shrub = to_float(vcpe.get("SHRUB_CROWN_CLOSURE")) or 0
    height = to_float(vcpe.get("SHRUB_HEIGHT")) or 0
    herb = to_float(vcpe.get("HERB_COVER_PCT")) or 0
    bryoid = to_float(vcpe.get("BRYOID_COVER_PCT")) or 0
    average = (shrub + herb + bryoid) / 3
    herb_code = text(vcpe.get("HERB_COVER_TYPE_CODE")) or "HE"
    classes = _lcc_classes(poly)

    if shrub > 20 and height > 2:
        return "ST", "N"
    if shrub > 20:
        return "SL", "N"
    if herb > 20:
        return herb_code, "N"
    if shrub > average and height > 2:
        return "ST", "N"
    if shrub > average:
        return "SL", "N"
    if herb > average:
        return herb_code, "N"
    if bryoid > average:
        for code in ("BM", "BL"):
            if code in classes:
                return code, "N"
        return "BY", "N"
    if shrub == herb == bryoid and shrub > 0:
        return ("ST" if height > 2 else "SL"), "N"
    if tree_closure(poly) >= 5:
        return _treed_level4(poly, species_class), "T"
    if shrub > 0:
        return ("ST" if height > 2 else "SL"), "N"
    if herb > 0:
        return herb_code, "N"
    if bryoid > 0:
        for code in ("BM", "BL"):
            if code in classes:
                return code, "N"
        return "BY", "N"
    return "", "N"


def _level5(level4: str, poly: Polygon, vcpe: dict[str, str]) -> str:
    if level4 in TREED:
        cover = tree_closure(poly)
        return "DE" if cover >= 61 else "OP" if cover >= 26 else "SP"
    if level4 in SHRUB:
        cover = to_float(vcpe.get("SHRUB_CROWN_CLOSURE")) or 0
        return "DE" if cover >= 61 else "OP" if cover >= 26 else "SP"
    if level4 in HERB:
        cover = to_float(vcpe.get("HERB_COVER_PCT")) or 0
        return "DE" if cover >= 61 else "OP" if cover >= 26 else "SP"
    if level4 in BRYOID:
        cover = to_float(vcpe.get("BRYOID_COVER_PCT")) or 0
        return "CL" if cover >= 51 else "OP"
    return dominant_nv(poly)


def bclcs_levels(poly: Polygon, species_class: Callable[[str], str]
                 ) -> tuple[str, str, str, str, str]:
    vcpe = poly.vcpe or {}
    has_records = bool(poly.nvce or poly.lcc or poly.layers)
    has_attributes = any(text(vcpe.get(name)) for name in BCLCS_ATTRIBUTES)
    if not has_records and not has_attributes:
        return "U", "", "", "", ""

    tree = tree_closure(poly)
    understory = understory_total(vcpe)
    if tree >= 10 or understory >= 5:
        level1 = "V"
        level2 = "T" if tree >= 10 else "N"
    else:
        level1 = "N"
        level2 = "W" if mostly_water(poly) else "L"

    if text(vcpe.get("ALPINE_DESIGNATION_CODE")) == "A" and level2 in {"W", "N", "L"}:
        level3 = "A"
    elif mostly_water(poly) or swampy(poly):
        level3 = "W"
    else:
        level3 = "U"

    level4 = ""
    if level2 == "T":
        level4 = _treed_level4(poly, species_class)
    elif level2 == "N":
        level4, level2 = _non_treed_level4(poly, vcpe, species_class)
    elif level2 == "L":
        non_veg = dominant_nv(poly)
        if non_veg in {"GL", "PN"}:
            level4 = "SI"
        elif non_veg in {"BR", "MZ", "LB", "TA", "BI"}:
            level4 = "RO"
        else:
            level4 = "EL"

    if level2 == "W":
        level4 = ""

    level5 = _level5(level4, poly, vcpe) if level4 or level2 == "W" else ""
    return level1, level2, level3, level4, level5


def rank_updates(poly: Polygon) -> list[RankUpdate]:
    if poly.standard not in {"V", "I"}:
        return []
    candidates = [layer for layer in poly.live_layers() if layer.order != -1]
    winner: Layer | None = None
    for layer in sorted(candidates, key=lambda item: to_int(
            item.row.get("TREE_COVER_LAYER_ESTIMATED_ID")) or 0):
        if (to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0) > 10:
            winner = layer
            break
    if winner is None and candidates:
        winner = max(candidates, key=lambda item: to_float(
            item.row.get("CROWN_CLOSURE_PCT")) or 0)
    updates: list[RankUpdate] = []
    for layer in poly.layers:
        layer_id = to_int(layer.row.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        if layer_id is None:
            continue
        rank = "1" if layer is winner else None
        updates.append(RankUpdate(layer_id, rank))
    return updates


def lcc_order_updates(poly: Polygon) -> list[LccOrderUpdate]:
    rows = list(poly.lcc)
    if not rows:
        return []
    rows.sort(key=lambda row: (
        -(to_float(row.get("COVERAGE_PCT")) or 0),
        to_int(row.get("LAND_COVER_ORDER")) or 0,
    ))
    updates: list[LccOrderUpdate] = []
    for order, row in enumerate(rows, 1):
        row_id = to_int(row.get("LAND_COVER_COMPONENT_EST_ID"))
        if row_id is not None:
            updates.append(LccOrderUpdate(row_id, order))
    return updates


def derive_updates(dataset: Dataset, species_class: Callable[[str], str],
                   *, only_changed: bool = True) -> DerivedUpdates:
    updates = DerivedUpdates()
    for poly in dataset.polygons:
        if poly.vcpe is not None and poly.standard in {"V", "I"}:
            levels = bclcs_levels(poly, species_class)
            stored = tuple(text(poly.vcpe.get(f"BCLCS_LEVEL{index}_CODE"))
                           for index in range(1, 6))
            if not only_changed or levels != stored:
                updates.vcpe.append(VcpeUpdate(poly.fid or 0, levels))
        elif poly.standard in {"V", "I"}:
            updates.skipped.append(poly.label())

        for update in rank_updates(poly):
            stored = text(poly_layers(poly, update.layer_id).get("FOREST_COVER_RANK_CODE"))
            wanted = update.rank or ""
            if not only_changed or stored != wanted:
                updates.tcl.append(update)

        for update in lcc_order_updates(poly):
            stored = text(poly_lcc(poly, update.lcc_id).get("LAND_COVER_ORDER"))
            if not only_changed or stored != str(update.order):
                updates.lcc.append(update)
    return updates


def poly_layers(poly: Polygon, layer_id: int) -> dict[str, str]:
    for layer in poly.layers:
        if to_int(layer.row.get("TREE_COVER_LAYER_ESTIMATED_ID")) == layer_id:
            return layer.row
    return {}


def poly_lcc(poly: Polygon, lcc_id: int) -> dict[str, str]:
    for row in poly.lcc:
        if to_int(row.get("LAND_COVER_COMPONENT_EST_ID")) == lcc_id:
            return row
    return {}
