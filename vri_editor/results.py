"""Import polygon/opening data from a RESULTS MDB into a VRIMS polygon."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from . import db

VRIB_FCO_FIELDS = (
    "OPENING_ID", "OPENING_NUMBER", "INVENTORY_STANDARD_CODE", "REFERENCE_YEAR",
    "DISTURBANCE_START_YEAR", "DISTURBANCE_END_YEAR", "DISTURBANCE_TYPE_CODE",
    "DISTURBANCE_CODE", "DATA_CAPTURE_METHOD_CODE", "FREE_TO_GROW_IND",
    "TSA_NUMBER", "TFL_NUMBER",
)
VRIB_VCPE_FIELDS = (
    "NON_PRODUCTIVE_CODE", "NON_PRODUCTIVE_DESCRIPTOR_CODE",
    "SURFACE_EXPRESSION_CODE", "MODIFYING_PROCESS_CODE", "SITE_POSITION_MESO_CODE",
    "ALPINE_DESIGNATION_CODE", "SOIL_NUTRIENT_REGIME_CODE",
    "DATA_SOURCE_ECOSYS_CLASS_CODE", "BCLCS_LEVEL1_CODE", "BCLCS_LEVEL2_CODE",
    "BCLCS_LEVEL3_CODE", "BCLCS_LEVEL4_CODE", "BCLCS_LEVEL5_CODE",
    "SHRUB_HEIGHT", "SHRUB_CROWN_CLOSURE", "COVER_PATTERN_CODE",
    "HERB_COVER_TYPE_CODE", "HERB_COVER_PCT", "HERB_COVER_PATTERN_CODE",
    "BRYOID_COVER_PCT", "BEC_ZONE_CODE", "VRI_DEAD_STEMS_PER_HA", "REFERENCE_YEAR",
)
VRIB_TCL_FIELDS = (
    "LAYER_ORDER", "LAYER_LEVEL_CODE", "NON_FOREST_DESCRIPTOR_CODE",
    "DATA_SOURCE_INTERPRETED_CODE", "TREE_SPECIES_CODE", "ESTIMATED_SITE_INDEX",
    "CROWN_CLOSURE_PCT", "BASAL_AREA", "DATA_SOURCE_BASAL_AREA_CODE",
    "VRI_LIVE_STEMS_PER_HA", "DATA_SRC_VRI_LIVE_STEM_HA_CODE",
    "COVER_PATTERN_CODE", "VERTICAL_COMPLEXITY_CODE",
    "ESTIMATED_SINDEX_SOURCE_CODE", "FOREST_COVER_RANK_CODE",
)
VRIB_TSE_FIELDS = (
    "SPECIES_ORDER", "TREE_SPECIES_CODE", "SPECIES_PCT", "AGE",
    "DATA_SOURCE_AGE_CODE", "HEIGHT", "DATA_SOURCE_HEIGHT_CODE",
)
VRIB_LCC_FIELDS = (
    "LAND_COVER_ORDER", "LAND_COVER_LEVEL_CODE", "COVERAGE_PCT",
    "SOIL_MOISTURE_REGIME_CODE", "LAND_COVER_CLASS_CODE",
)
VRIB_NVCE_FIELDS = (
    "NON_VEG_ORDER", "LAYER_LEVEL_CODE", "NON_VEG_COVER_PCT",
    "COVER_PATTERN_CODE", "NON_VEG_COVER_TYPE_CODE",
)


def _rows(path: Path | str, table: str) -> list[dict[str, str]]:
    try:
        return db.read_rows(path, table)
    except db.EditorError:
        return []


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _int_text(value: Any) -> str:
    value = _text(value)
    if not value:
        return ""
    try:
        return str(int(float(value)))
    except ValueError:
        return value


def _code2(value: Any) -> str:
    value = _text(value)
    if not value:
        return ""
    try:
        return f"{int(float(value)):02d}"
    except ValueError:
        return value


def _pick(row: dict[str, str], *names: str) -> str:
    lower = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return _text(value)
    return ""


def _join(species: dict[str, str], leading: dict[str, str]) -> dict[str, str]:
    merged = dict(species)
    if leading:
        merged.update({key: value for key, value in leading.items()
                       if value not in (None, "")})
    return merged


def list_polygons(path: Path | str) -> list[dict[str, str]]:
    """Return one row per RESULTS polygon from either supported MDB layout."""
    polygons = _rows(path, "POLYGON")
    if polygons:
        result = []
        for row in polygons:
            result.append({
                "map_id": _pick(row, "MAP_ID"),
                "opening_id": _pick(row, "opening_id", "OPENING_ID"),
                "opening_number": "",
                "polygon_id": _pick(row, "POLYGON_ID"),
                "area": _pick(row, "POLYGON_AREA"),
                "layers": _pick(row, "LAYER_CNT"),
                "bclcs": "".join(_pick(row, f"BCLCS_LEVEL_{n}") for n in range(1, 6)),
                "interpreter": _pick(row, "INTERPRETER"),
                "project": _pick(row, "PROJECT"),
                "format": "results",
            })
        result.sort(key=lambda row: (
            0 if row["opening_id"] else 1, row["map_id"],
            _sort_int(row["opening_id"]), _sort_int(row["polygon_id"])))
        return result
    fco = _rows(path, "FOREST_COVER_OBJECT")
    if fco:
        return _list_vrib(path, fco)
    raise db.EditorError(
        "No POLYGON or FOREST_COVER_OBJECT table found. "
        "This does not look like a RESULTS or VRI-B database.")


def _list_vrib(path: Path | str, fco: list[dict[str, str]]) -> list[dict[str, str]]:
    vcpe = {_pick(row, "FOREST_COVER_OBJECT_ID"): row
            for row in _rows(path, "VEGETATION_COVER_POLYGON_EST")}
    tcl_count: dict[str, int] = {}
    for row in _rows(path, "TREE_COVER_LAYER_ESTIMATED"):
        fid = _pick(row, "FOREST_COVER_OBJECT_ID")
        tcl_count[fid] = tcl_count.get(fid, 0) + 1
    map_id = Path(path).stem.split("_", 1)[0]
    result = []
    for row in fco:
        fid = _pick(row, "FOREST_COVER_OBJECT_ID")
        ecology = vcpe.get(fid, {})
        opening_id = _pick(row, "OPENING_ID")
        if _sort_int(opening_id) <= 0:
            opening_id = ""
        result.append({
            "map_id": map_id,
            "opening_id": opening_id,
            "opening_number": _pick(row, "OPENING_NUMBER"),
            "polygon_id": fid,
            "area": _pick(row, "POLYGON_AREA") or _pick(row, "GEOMETRY_Area"),
            "layers": str(tcl_count.get(fid, 0)),
            "bclcs": "".join(_pick(ecology, f"BCLCS_LEVEL{n}_CODE") for n in range(1, 6)),
            "interpreter": _pick(row, "INTERPRETER"),
            "project": _pick(row, "PROJECT_NAME"),
            "format": "vrib",
        })
    result.sort(key=lambda row: (
        0 if row["opening_id"] else 1, _sort_int(row["opening_id"]),
        _sort_int(row["polygon_id"])))
    return result


def _sort_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _polygon_key(row: dict[str, str], map_id: str, polygon_id: str) -> bool:
    return (_pick(row, "MAP_ID") == map_id
            and _pick(row, "POLYGON_ID") == polygon_id)


def details(path: Path | str, map_id: str, polygon_id: str) -> dict[str, Any]:
    if _rows(path, "FOREST_COVER_OBJECT"):
        return _details_vrib(path, polygon_id)
    return _details_standard(path, map_id, polygon_id)


def _details_standard(path: Path | str, map_id: str, polygon_id: str) -> dict[str, Any]:
    """Load one standard RESULTS polygon and map it for the editor."""
    map_id = _text(map_id)
    polygon_id = _text(polygon_id)
    polygon = next((row for row in _rows(path, "POLYGON")
                    if _polygon_key(row, map_id, polygon_id)), None)
    if polygon is None:
        raise db.EditorError(f"RESULTS polygon {map_id}/{polygon_id} not found")
    resultant = next((row for row in _rows(path, "RESULTANT")
                      if _polygon_key(row, map_id, polygon_id)), {})
    all_layers = [row for row in _rows(path, "LAYER")
                  if _polygon_key(row, map_id, polygon_id)]
    all_species = [row for row in _rows(path, "SPECIES")
                   if _polygon_key(row, map_id, polygon_id)]
    leading = [row for row in _rows(path, "LEADING_SPECIES")
               if _polygon_key(row, map_id, polygon_id)]
    land = next((row for row in _rows(path, "LAND_COVER_COMPONENTS")
                 if _polygon_key(row, map_id, polygon_id)), {})
    non_veg = [row for row in _rows(path, "NON_VEG")
               if _polygon_key(row, map_id, polygon_id)]
    non_tree = next((row for row in _rows(path, "NON_TREE")
                     if _polygon_key(row, map_id, polygon_id)), {})
    history = next((row for row in _rows(path, "HISTORY")
                    if _polygon_key(row, map_id, polygon_id)), {})

    all_layers.sort(key=lambda row: _sort_int(_pick(row, "LAYER_ID")))
    leading_by_species = {
        _pick(row, "SPECIES_ID"): row for row in leading if _pick(row, "SPECIES_ID")}
    layers: list[dict[str, Any]] = []
    for order, layer in enumerate(all_layers, 1):
        layer_id = _pick(layer, "LAYER_ID")
        species = [row for row in all_species if _pick(row, "LAYER_ID") == layer_id]
        species.sort(key=lambda row: _sort_int(_pick(row, "SPECIES_ID")))
        species_rows = []
        for row in species:
            species_id = _pick(row, "SPECIES_ID")
            tree = _join(row, leading_by_species.get(species_id, {}))
            species_rows.append({
                "SPECIES_ORDER": _int_text(species_id) or str(len(species_rows) + 1),
                "TREE_SPECIES_CODE": _pick(row, "SPECIES_CD"),
                "SPECIES_PCT": _pick(row, "SPECIES_PERCENT"),
                "AGE": _pick(tree, "AGE"),
                "DATA_SOURCE_AGE_CODE": _int_text(_pick(tree, "DATA_SOURCE_AGE")),
                "HEIGHT": _pick(tree, "HEIGHT"),
                "DATA_SOURCE_HEIGHT_CODE": _int_text(_pick(tree, "DATA_SOURCE_HEIGHT")),
            })
        first_species = species_rows[0]["TREE_SPECIES_CODE"] if species_rows else ""
        layers.append({
            "LAYER_ORDER": order,
            "LAYER_LEVEL_CODE": layer_id,
            "NON_FOREST_DESCRIPTOR_CODE": _pick(layer, "NON_FOREST_DESCRIPTOR"),
            "DATA_SOURCE_INTERPRETED_CODE": _int_text(
                _pick(layer, "INTERPRETED_DATA_SOURCE_CODE")),
            "TREE_SPECIES_CODE": first_species,
            "ESTIMATED_SITE_INDEX": _pick(layer, "ESTIMATED_SITE_INDEX"),
            "CROWN_CLOSURE_PCT": _pick(layer, "CROWN_CLOSURE"),
            "BASAL_AREA": _pick(layer, "BASAL_AREA"),
            "DATA_SOURCE_BASAL_AREA_CODE": _int_text(
                _pick(layer, "DATA_SOURCE_BASAL_AREA")),
            "VRI_LIVE_STEMS_PER_HA": _pick(layer, "VRI_LIVE_STEMS_PER_HA"),
            "DATA_SRC_VRI_LIVE_STEM_HA_CODE": _int_text(
                _pick(layer, "DATA_SOURCE_VRI_LIVE_STEMS_PER_H")),
            "COVER_PATTERN_CODE": _int_text(_pick(layer, "TREE_COVER_PATTERN")),
            "VERTICAL_COMPLEXITY_CODE": _int_text(_pick(layer, "VERTICAL_COMPLEXITY")),
            "ESTIMATED_SINDEX_SOURCE_CODE": _pick(layer, "SUPPLIED_SITE_INDEX_SOURCE"),
            "FOREST_COVER_RANK_CODE": _pick(layer, "FOR_COVER_RANK_CD"),
            "species": species_rows,
        })

    lcc: list[dict[str, str]] = []
    for n in (1, 2, 3):
        component = _pick(land, f"COMP{n}")
        if not component:
            continue
        lcc.append({
            "LAND_COVER_ORDER": str(n),
            "LAND_COVER_LEVEL_CODE": str(n),
            "COVERAGE_PCT": _pick(land, f"PERCENT{n}"),
            "SOIL_MOISTURE_REGIME_CODE": _int_text(_pick(land, f"SOIL_MOIST{n}")),
            "LAND_COVER_CLASS_CODE": component,
        })
    nvce = []
    non_veg.sort(key=lambda row: _sort_int(_pick(row, "NON_VEG_ID")))
    for order, row in enumerate(non_veg, 1):
        nvce.append({
            "NON_VEG_ORDER": str(order),
            "LAYER_LEVEL_CODE": str(order),
            "NON_VEG_COVER_PCT": _pick(row, "NON_VEG_COVER_PERCENT"),
            "COVER_PATTERN_CODE": _int_text(_pick(row, "NON_VEG_COVER_PATTERN")),
            "NON_VEG_COVER_TYPE_CODE": _pick(row, "NON_VEG_COVER_TYPE"),
        })

    disturbance = _pick(resultant, "DISTURBANCE_CD")
    opening_id = _pick(polygon, "opening_id", "OPENING_ID")
    if _sort_int(opening_id) <= 0:
        opening_id = ""
    opening_number = _pick(history, "OPENING_NUMBER")
    if _sort_int(opening_number) <= 0:
        opening_number = ""
    fco = {
        "OPENING_ID": opening_id,
        "OPENING_NUMBER": opening_number,
        "INVENTORY_STANDARD_CODE": _pick(polygon, "INVENTORY_STANDARD"),
        "POLYGON_AREA": _pick(polygon, "POLYGON_AREA"),
        "TSA_NUMBER": _pick(resultant, "TSA_NUMBER"),
        "DISTURBANCE_TYPE_CODE": disturbance,
    }
    vcpe = {
        "NON_PRODUCTIVE_CODE": _code2(_pick(polygon, "NON_PRODUCTIVE_CD")),
        "NON_PRODUCTIVE_DESCRIPTOR_CODE": _pick(polygon, "NON_PRODUCTIVE_DESCRIPTOR"),
        "SURFACE_EXPRESSION_CODE": _pick(polygon, "SURFACE_EXPRESSION"),
        "MODIFYING_PROCESS_CODE": _pick(polygon, "MODIFYING_PROCESS"),
        "SITE_POSITION_MESO_CODE": _pick(polygon, "SITE_POSITION_MESO"),
        "ALPINE_DESIGNATION_CODE": _pick(polygon, "ALPINE_DESIGNATION"),
        "SOIL_NUTRIENT_REGIME_CODE": _pick(polygon, "SOIL_NUTRIENT_REGIME"),
        "DATA_SOURCE_ECOSYS_CLASS_CODE": _int_text(_pick(polygon, "DATA_SOURCE_ECOLOGY")),
        "BCLCS_LEVEL1_CODE": _pick(polygon, "BCLCS_LEVEL_1"),
        "BCLCS_LEVEL2_CODE": _pick(polygon, "BCLCS_LEVEL_2"),
        "BCLCS_LEVEL3_CODE": _pick(polygon, "BCLCS_LEVEL_3"),
        "BCLCS_LEVEL4_CODE": _pick(polygon, "BCLCS_LEVEL_4"),
        "BCLCS_LEVEL5_CODE": _pick(polygon, "BCLCS_LEVEL_5"),
        "BEC_ZONE_CODE": _pick(resultant, "BGC_ZONE"),
        "SHRUB_HEIGHT": _pick(non_tree, "SHRUB_HEIGHT"),
        "SHRUB_CROWN_CLOSURE": _pick(non_tree, "SHRUB_CROWN_CLOSURE"),
        "HERB_COVER_TYPE_CODE": _pick(non_tree, "HERB_COVER_TYPE"),
        "HERB_COVER_PCT": _pick(non_tree, "HERB_COVER_PERCENT"),
        "BRYOID_COVER_PCT": _pick(non_tree, "BRYOID_COVER_PERCENT"),
    }
    return {
        "polygon": polygon,
        "fco": fco,
        "vcpe": vcpe,
        "layers": layers,
        "lcc": lcc,
        "nvce": nvce,
        "opening_status": _pick(polygon, "OPENING_STATUS_CODE"),
    }


def _details_vrib(path: Path | str, polygon_id: str) -> dict[str, Any]:
    fid = _text(polygon_id)
    fco_rows = _rows(path, "FOREST_COVER_OBJECT")
    source = next((row for row in fco_rows
                   if _pick(row, "FOREST_COVER_OBJECT_ID") == fid), None)
    if source is None:
        raise db.EditorError(f"VRI-B polygon {fid} not found")
    vcpe_rows = _rows(path, "VEGETATION_COVER_POLYGON_EST")
    ecology = next((row for row in vcpe_rows
                    if _pick(row, "FOREST_COVER_OBJECT_ID") == fid), {})
    tcl_rows = [row for row in _rows(path, "TREE_COVER_LAYER_ESTIMATED")
                if _pick(row, "FOREST_COVER_OBJECT_ID") == fid]
    layer_ids = {_pick(row, "TREE_COVER_LAYER_ESTIMATED_ID") for row in tcl_rows}
    tse_rows = [row for row in _rows(path, "TREE_SPECIES_ESTIMATED")
                if _pick(row, "TREE_COVER_LAYER_ESTIMATED_ID") in layer_ids]
    lcc_rows = [row for row in _rows(path, "LAND_COVER_COMPONENT_EST")
                if _pick(row, "FOREST_COVER_OBJECT_ID") == fid]
    nvce_rows = [row for row in _rows(path, "NON_VEGETATIVE_COVER_EST")
                 if _pick(row, "FOREST_COVER_OBJECT_ID") == fid]

    opening_id = _pick(source, "OPENING_ID")
    if _sort_int(opening_id) <= 0:
        opening_id = ""
    fco = {field: _text(source.get(field)) for field in VRIB_FCO_FIELDS}
    fco["OPENING_ID"] = opening_id
    fco["OPENING_NUMBER"] = _pick(source, "OPENING_NUMBER")
    vcpe = {field: _text(ecology.get(field)) for field in VRIB_VCPE_FIELDS}

    tcl_rows.sort(key=lambda row: (
        _sort_int(_pick(row, "LAYER_ORDER")),
        _sort_int(_pick(row, "TREE_COVER_LAYER_ESTIMATED_ID"))))
    species_by_layer: dict[str, list[dict[str, str]]] = {}
    for row in tse_rows:
        species_by_layer.setdefault(_pick(row, "TREE_COVER_LAYER_ESTIMATED_ID"), []).append(row)
    layers = []
    for layer in tcl_rows:
        layer_id = _pick(layer, "TREE_COVER_LAYER_ESTIMATED_ID")
        species = species_by_layer.get(layer_id, [])
        species.sort(key=lambda row: _sort_int(_pick(row, "SPECIES_ORDER")))
        layers.append({
            **{field: _text(layer.get(field)) for field in VRIB_TCL_FIELDS},
            "species": [
                {field: _text(row.get(field)) for field in VRIB_TSE_FIELDS}
                for row in species
            ],
        })
    lcc_rows.sort(key=lambda row: _sort_int(_pick(row, "LAND_COVER_ORDER")))
    nvce_rows.sort(key=lambda row: _sort_int(_pick(row, "NON_VEG_ORDER")))
    return {
        "polygon": source,
        "fco": fco,
        "vcpe": vcpe,
        "layers": layers,
        "lcc": [{field: _text(row.get(field)) for field in VRIB_LCC_FIELDS}
                for row in lcc_rows],
        "nvce": [{field: _text(row.get(field)) for field in VRIB_NVCE_FIELDS}
                 for row in nvce_rows],
    }


def tie_unique(vri_path: Path | str, res_path: Path | str, *,
               replace_children: bool = True, user: str = "") -> tuple[list[str], list[str], int]:
    """Apply only openings that identify exactly one VRI and one RESULTS polygon."""
    vri_rows = db.read_rows(vri_path, "FOREST_COVER_OBJECT")
    vri_by_opening: dict[str, list[int]] = {}
    for row in vri_rows:
        opening = _pick(row, "OPENING_ID")
        if opening in ("", "0", "-99"):
            continue
        vri_by_opening.setdefault(opening, []).append(
            _sort_int(_pick(row, "FOREST_COVER_OBJECT_ID")))
    res_rows = list_polygons(res_path)
    res_by_opening: dict[str, list[dict[str, str]]] = {}
    for row in res_rows:
        if row["opening_id"] and row["opening_id"] not in ("0", "-99"):
            res_by_opening.setdefault(row["opening_id"], []).append(row)
    applied: list[str] = []
    skipped: list[str] = []
    updated_total = 0
    for opening in sorted(set(vri_by_opening) & set(res_by_opening)):
        fids = vri_by_opening[opening]
        sources = res_by_opening[opening]
        if len(fids) != 1 or len(sources) != 1:
            skipped.append(f"{opening} (VRI {len(fids)}, RESULTS {len(sources)})")
            continue
        source = sources[0]
        try:
            _backup, updated, summary = apply_to_polygon(
                vri_path, fids[0], res_path, source["map_id"], source["polygon_id"],
                replace_children=replace_children, user=user)
        except Exception as exc:
            skipped.append(f"{opening} (error: {exc})")
            continue
        updated_total += updated
        applied.append(f"{opening} -> polygon {fids[0]} ({summary})")
    return applied, skipped, updated_total


def tie_by_geometry(vri_path: Path | str, res_path: Path | str, *,
                     replace_children: bool = True, user: str = "",
                     allow_duplicates: bool = False) -> tuple[list[str], list[str], int]:
    """Tie VRI and RESULTS polygons by opening ID, using geometry overlap for ties."""
    try:
        from osgeo import ogr, osr
    except Exception as exc:
        raise db.EditorError(f"GDAL/OGR is required for geometry tie: {exc}") from exc
    globals()["ogr"]=ogr
    globals()["osr"]=osr

    vri_path = Path(vri_path)
    res_path = Path(res_path)
    vri_features, vri_srs = _geometry_features(vri_path)
    res_features, res_srs = _geometry_features(res_path)
    if vri_srs is not None and res_srs is not None and not vri_srs.IsSame(res_srs):
        try:
            from osgeo import osr
        except Exception as exc:
            raise db.EditorError(f"GDAL/OGR is required for geometry tie: {exc}") from exc
        transform = osr.CreateCoordinateTransformation(res_srs, vri_srs)
        if transform is None:
            raise db.EditorError("VRI and RESULTS use different coordinate systems")
        for _oid, _opening, geometry in res_features:
            geometry.Transform(transform)

    vri_by_opening: dict[str, list[int]] = {}
    vri_geom: dict[int, Any] = {}
    for oid, opening, geometry in vri_features:
        opening_text = str(opening).strip()
        if opening_text in ("", "0", "-99") or geometry is None:
            continue
        vri_by_opening.setdefault(opening_text, []).append(oid)
        vri_geom[oid] = geometry
    res_by_opening: dict[str, list[int]] = {}
    res_geom: dict[int, Any] = {}
    for oid, opening, geometry in res_features:
        opening_text = str(opening).strip()
        if opening_text in ("", "0", "-99") or geometry is None:
            continue
        res_by_opening.setdefault(opening_text, []).append(oid)
        res_geom[oid] = geometry

    res_rows = list_polygons(res_path)
    res_lookup = {str(row["polygon_id"]): row for row in res_rows}

    applied: list[str] = []
    skipped: list[str] = []
    updated_total = 0
    for opening in sorted(set(vri_by_opening) & set(res_by_opening)):
        vri_ids = vri_by_opening[opening]
        res_ids = res_by_opening[opening]
        pairs: list[tuple[int, int]] = []
        if allow_duplicates:
            for vfid in vri_ids:
                best: tuple[float, int] | None = None
                for rid in res_ids:
                    intersection = vri_geom[vfid].Intersection(res_geom[rid])
                    area = float(intersection.GetArea()) if intersection is not None else 0.0
                    if best is None or area > best[0]:
                        best = (area, rid)
                if best is not None and best[0] > 0:
                    pairs.append((vfid, best[1]))
        elif len(vri_ids) == 1 and len(res_ids) == 1:
            pairs.append((vri_ids[0], res_ids[0]))
        else:
            candidates: list[tuple[float, int, int]] = []
            for vfid in vri_ids:
                for rid in res_ids:
                    intersection = vri_geom[vfid].Intersection(res_geom[rid])
                    area = float(intersection.GetArea()) if intersection is not None else 0.0
                    if area > 0:
                        candidates.append((area, vfid, rid))
            candidates.sort(reverse=True)
            used_v: set[int] = set()
            used_r: set[int] = set()
            for _area, vfid, rid in candidates:
                if vfid in used_v or rid in used_r:
                    continue
                pairs.append((vfid, rid))
                used_v.add(vfid)
                used_r.add(rid)
        if not pairs:
            skipped.append(f"{opening} (no geometry overlap)")
            continue
        for vfid, rid in pairs:
            source = res_lookup.get(str(rid))
            if source is None:
                skipped.append(f"{opening} (RESULTS polygon {rid} not found)")
                continue
            try:
                _backup, updated, summary = apply_to_polygon(
                    vri_path, vfid, res_path, source["map_id"], source["polygon_id"],
                    replace_children=replace_children, user=user)
            except Exception as exc:
                skipped.append(f"{opening} (polygon {vfid}: {exc})")
                continue
            updated_total += updated
            applied.append(f"{opening} -> VRI polygon {vfid} ({summary})")
        unmatched_v = len(vri_ids) - len(pairs)
        unmatched_r = len(res_ids) - len(pairs)
        if unmatched_v > 0 or unmatched_r > 0:
            skipped.append(
                f"{opening} (matched {len(pairs)} of "
                f"{len(vri_ids)} VRI / {len(res_ids)} RESULTS)")
    return applied, skipped, updated_total


def _geometry_features(path: Path) -> tuple[list[tuple[int, str, Any]], Any]:
    try:
        from osgeo import ogr
    except Exception as exc:
        raise db.EditorError(f"GDAL/OGR is required for geometry tie: {exc}") from exc
    ds = ogr.Open(str(path))
    if ds is None:
        raise db.EditorError(f"cannot open geometry in {path}")
    layer = ds.GetLayer("FOREST_COVER_OBJECT")
    if layer is None:
        raise db.EditorError(f"FOREST_COVER_OBJECT layer not found in {path}")
    srs = layer.GetSpatialRef()
    features: list[tuple[int, str, Any]] = []
    for feature in layer:
        try:
            oid = int(feature.GetField("FOREST_COVER_OBJECT_ID"))
        except (TypeError, ValueError):
            continue
        opening = feature.GetField("OPENING_ID")
        opening_text = "" if opening is None else str(opening).strip()
        geometry = feature.GetGeometryRef()
        features.append((oid, opening_text, geometry.Clone() if geometry is not None else None))
    ds = None
    return features, srs


def import_log_dates(vri_path: Path | str, res_path: Path | str, *,
                     overwrite: bool = False, user: str = "") -> tuple[list[str], list[str], int]:
    """Import disturbance start/end dates from RESULTS into VRI polygons.

    Matching is by opening ID plus geometry overlap (same as tie_by_geometry).
    Only DISTURBANCE_START_YEAR and DISTURBANCE_END_YEAR are written, and only
    when the VRI field is empty unless ``overwrite`` is True.
    """
    from datetime import datetime
    vri_path = Path(vri_path)
    res_path = Path(res_path)
    vri_features, vri_srs = _geometry_features(vri_path)
    res_features, res_srs = _geometry_features(res_path)
    if vri_srs is not None and res_srs is not None and not vri_srs.IsSame(res_srs):
        from osgeo import osr
        transform = osr.CreateCoordinateTransformation(res_srs, vri_srs)
        if transform is None:
            raise db.EditorError("VRI and RESULTS use different coordinate systems")
        for _oid, _opening, geometry in res_features:
            geometry.Transform(transform)

    vri_by_opening: dict[str, list[int]] = {}
    vri_geom: dict[int, Any] = {}
    for oid, opening, geometry in vri_features:
        opening_text = str(opening).strip()
        if opening_text in ("", "0", "-99") or geometry is None:
            continue
        vri_by_opening.setdefault(opening_text, []).append(oid)
        vri_geom[oid] = geometry
    res_by_opening: dict[str, list[int]] = {}
    res_geom: dict[int, Any] = {}
    for oid, opening, geometry in res_features:
        opening_text = str(opening).strip()
        if opening_text in ("", "0", "-99") or geometry is None:
            continue
        res_by_opening.setdefault(opening_text, []).append(oid)
        res_geom[oid] = geometry

    res_rows = list_polygons(res_path)
    res_lookup = {str(row["polygon_id"]): row for row in res_rows}

    applied: list[str] = []
    skipped: list[str] = []
    updated_total = 0
    edits: list[str] = []
    for opening in sorted(set(vri_by_opening) & set(res_by_opening)):
        vri_ids = vri_by_opening[opening]
        res_ids = res_by_opening[opening]
        pairs: list[tuple[int, int]] = []
        if len(vri_ids) == 1 and len(res_ids) == 1:
            pairs.append((vri_ids[0], res_ids[0]))
        else:
            candidates: list[tuple[float, int, int]] = []
            for vfid in vri_ids:
                for rid in res_ids:
                    intersection = vri_geom[vfid].Intersection(res_geom[rid])
                    area = float(intersection.GetArea()) if intersection is not None else 0.0
                    if area > 0:
                        candidates.append((area, vfid, rid))
            candidates.sort(reverse=True)
            used_v: set[int] = set()
            used_r: set[int] = set()
            for _area, vfid, rid in candidates:
                if vfid in used_v or rid in used_r:
                    continue
                pairs.append((vfid, rid))
                used_v.add(vfid)
                used_r.add(rid)
        for vfid, rid in pairs:
            source = res_lookup.get(str(rid))
            if source is None:
                skipped.append(f"{opening} (RESULTS polygon {rid} not found)")
                continue
            # read disturbance dates from RESULTS FCO
            res_fco_rows = [r for r in db.read_rows(res_path, "FOREST_COVER_OBJECT")
                            if str(r.get("FOREST_COVER_OBJECT_ID")) == str(rid)]
            if not res_fco_rows:
                skipped.append(f"{opening} (no FCO row in RESULTS)")
                continue
            res_fco = res_fco_rows[0]
            start = (res_fco.get("DISTURBANCE_START_YEAR") or "").strip()
            end = (res_fco.get("DISTURBANCE_END_YEAR") or "").strip()
            if not start and not end:
                skipped.append(f"{opening} (no disturbance dates in RESULTS)")
                continue
            vri_fco_rows = [r for r in db.read_rows(vri_path, "FOREST_COVER_OBJECT")
                            if str(r.get("FOREST_COVER_OBJECT_ID")) == str(vfid)]
            if not vri_fco_rows:
                skipped.append(f"{opening} (VRI polygon {vfid} not found)")
                continue
            vri_fco = vri_fco_rows[0]
            values: dict[str, Any] = {}
            if start and (overwrite or not (vri_fco.get("DISTURBANCE_START_YEAR") or "").strip()):
                values["DISTURBANCE_START_YEAR"] = start
            if end and (overwrite or not (vri_fco.get("DISTURBANCE_END_YEAR") or "").strip()):
                values["DISTURBANCE_END_YEAR"] = end
            if not values:
                skipped.append(f"{opening} (VRI already has dates)")
                continue
            edits.append(db.edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID",
                                     vfid, values))
            updated_total += 1
            applied.append(f"{opening} -> VRI polygon {vfid}")
    if edits:
        db.save(vri_path, edits)
    return applied, skipped, updated_total


def status_by_opening(res_path: Path | str) -> dict[str, str]:
    """Map opening ID to the opening status carried by the RESULTS source."""
    result: dict[str, str] = {}
    for row in _rows(res_path, "FOREST_COVER_OBJECT"):
        opening = _pick(row, "OPENING_ID")
        status = _pick(row, "OPENING_STATUS_CODE")
        if opening and status:
            result[opening] = status
    return result


def apply_to_polygon(vri_path: Path | str, fid: int, res_path: Path | str,
                     map_id: str, polygon_id: str, *,
                     replace_children: bool = True,
                     user: str = "") -> tuple[Path | None, int, str]:
    """Copy one RESULTS polygon into a VRI polygon and return a summary."""
    vri_path = Path(vri_path)
    data = details(res_path, map_id, polygon_id)
    fco_rows = db.read_rows(vri_path, "FOREST_COVER_OBJECT")
    tcl_rows = db.read_rows(vri_path, "TREE_COVER_LAYER_ESTIMATED")
    tse_rows = db.read_rows(vri_path, "TREE_SPECIES_ESTIMATED")
    lcc_rows = db.read_rows(vri_path, "LAND_COVER_COMPONENT_EST")
    nvce_rows = db.read_rows(vri_path, "NON_VEGETATIVE_COVER_EST")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    fco = {key: value for key, value in data["fco"].items()
           if value not in (None, "")}
    fco.update({"UPDATE_TIMESTAMP": now, "UPDATE_USERID": user})
    vcpe = {key: value for key, value in data["vcpe"].items()
            if value not in (None, "")}
    vcpe.update({"UPDATE_TIMESTAMP": now, "UPDATE_USERID": user})
    edits = [
        db.edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", fid, fco),
        db.edit_line("U", "VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID", fid, vcpe),
    ]
    old_layers = [row for row in tcl_rows
                  if _sort_int(_pick(row, "FOREST_COVER_OBJECT_ID")) == fid]
    old_layer_ids = {_sort_int(_pick(row, "TREE_COVER_LAYER_ESTIMATED_ID"))
                     for row in old_layers}
    if replace_children:
        if data["layers"]:
            for row in tse_rows:
                if _sort_int(_pick(row, "TREE_COVER_LAYER_ESTIMATED_ID")) in old_layer_ids:
                    edits.append(db.delete_line(
                        "TREE_SPECIES_ESTIMATED", "TREE_SPECIES_ESTIMATED_ID",
                        _sort_int(_pick(row, "TREE_SPECIES_ESTIMATED_ID"))))
            for layer_id in sorted(old_layer_ids):
                edits.append(db.delete_line(
                    "TREE_COVER_LAYER_ESTIMATED", "TREE_COVER_LAYER_ESTIMATED_ID", layer_id))
        if data["lcc"]:
            for row in lcc_rows:
                if _sort_int(_pick(row, "FOREST_COVER_OBJECT_ID")) == fid:
                    edits.append(db.delete_line(
                        "LAND_COVER_COMPONENT_EST", "LAND_COVER_COMPONENT_EST_ID",
                        _sort_int(_pick(row, "LAND_COVER_COMPONENT_EST_ID"))))
        if data["nvce"]:
            for row in nvce_rows:
                if _sort_int(_pick(row, "FOREST_COVER_OBJECT_ID")) == fid:
                    edits.append(db.delete_line(
                        "NON_VEGETATIVE_COVER_EST", "NON_VEGETATIVE_COVER_EST_ID",
                        _sort_int(_pick(row, "NON_VEGETATIVE_COVER_EST_ID"))))

    next_tcl_id = db.next_negative_id(tcl_rows, "TREE_COVER_LAYER_ESTIMATED_ID")
    next_tse_id = db.next_negative_id(tse_rows, "TREE_SPECIES_ESTIMATED_ID")
    next_lcc_id = db.next_negative_id(lcc_rows, "LAND_COVER_COMPONENT_EST_ID")
    next_nvce_id = db.next_negative_id(nvce_rows, "NON_VEGETATIVE_COVER_EST_ID")
    next_tcl_obj = db._max_int(tcl_rows, "OBJECTID") + 1
    next_tse_obj = db._max_int(tse_rows, "OBJECTID") + 1
    next_lcc_obj = db._max_int(lcc_rows, "OBJECTID") + 1
    next_nvce_obj = db._max_int(nvce_rows, "OBJECTID") + 1

    for layer in data["layers"]:
        layer_id = next_tcl_id
        next_tcl_id -= 1
        values = {key: value for key, value in layer.items()
                  if key != "species" and value not in (None, "")}
        values.update({
            "TREE_COVER_LAYER_ESTIMATED_ID": layer_id,
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": next_tcl_obj,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": user,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": user,
        })
        next_tcl_obj += 1
        edits.append(db.edit_line(
            "I", "TREE_COVER_LAYER_ESTIMATED", "", "", values))
        for species in layer["species"]:
            values = {key: value for key, value in species.items()
                      if value not in (None, "")}
            values.update({
                "TREE_SPECIES_ESTIMATED_ID": next_tse_id,
                "TREE_COVER_LAYER_ESTIMATED_ID": layer_id,
                "OBJECTID": next_tse_obj,
                "ENTRY_TIMESTAMP": now,
                "ENTRY_USERID": user,
                "UPDATE_TIMESTAMP": now,
                "UPDATE_USERID": user,
            })
            next_tse_id -= 1
            next_tse_obj += 1
            edits.append(db.edit_line(
                "I", "TREE_SPECIES_ESTIMATED", "", "", values))
    for row in data["lcc"]:
        values = dict(row)
        values.update({
            "LAND_COVER_COMPONENT_EST_ID": next_lcc_id,
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": next_lcc_obj,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": user,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": user,
        })
        next_lcc_id -= 1
        next_lcc_obj += 1
        edits.append(db.edit_line(
            "I", "LAND_COVER_COMPONENT_EST", "", "", values))
    for row in data["nvce"]:
        values = dict(row)
        values.update({
            "NON_VEGETATIVE_COVER_EST_ID": next_nvce_id,
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": next_nvce_obj,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": user,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": user,
        })
        next_nvce_id -= 1
        next_nvce_obj += 1
        edits.append(db.edit_line(
            "I", "NON_VEGETATIVE_COVER_EST", "", "", values))
    backup, updated = db.save(vri_path, edits)
    summary = (f"{map_id}/{polygon_id}: {len(data['layers'])} layer(s), "
               f"{sum(len(layer['species']) for layer in data['layers'])} species, "
               f"{len(data['lcc'])} land-cover, {len(data['nvce'])} non-veg")
    return backup, updated, summary
