"""Spatial geometry import for VRI MDBs."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from osgeo import ogr, osr

from . import db


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _normalize_id(value: Any) -> int:
    return _int(value)


def _read_shape_polygons(path: Path, id_field: str) -> tuple[list[tuple[int, Any]], Any, list[str]]:
    dataset = ogr.Open(str(path))
    if dataset is None:
        raise db.EditorError(f"cannot open shapefile: {path}")
    layer = dataset.GetLayer(0)
    if layer is None:
        raise db.EditorError(f"no layer in shapefile: {path}")
    srs = layer.GetSpatialRef()
    fields = [layer.GetLayerDefn().GetFieldDefn(i).GetName()
              for i in range(layer.GetLayerDefn().GetFieldCount())]
    if id_field not in fields:
        if "POLYGON_ID" in fields:
            id_field = "POLYGON_ID"
        elif fields:
            id_field = fields[0]
        else:
            raise db.EditorError("shapefile has no attribute fields for polygon IDs")
    polygons: list[tuple[int, Any]] = []
    unmatched: list[str] = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        geometry = geometry.Clone()
        raw_id = feature.GetField(id_field)
        try:
            polygon_id = int(float(str(raw_id).strip()))
        except (TypeError, ValueError):
            unmatched.append(f"feature has non-numeric {id_field}={raw_id!r}")
            continue
        if geometry.GetGeometryType() not in (ogr.wkbPolygon, ogr.wkbPolygon25D,
                                             ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
            unmatched.append(f"polygon {polygon_id}: geometry is not a polygon")
            continue
        polygons.append((polygon_id, geometry))
    dataset = None
    return polygons, srs, unmatched


SNAP_TOLERANCE = 0.5      # metres; vertices closer than this are the same node
MIN_POLYGON_AREA = 1.0    # m2; smaller polygonize results are slivers


def _segments(geometry: Any) -> list[tuple[float, float, float, float, int]]:
    """All straight segments of a (multi)line, with the index of the line they belong to."""
    segs = []
    parts = [geometry] if geometry.GetGeometryCount() == 0 else [
        geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())]
    return [seg for part in parts for seg in _part_segments(part)]


def _part_segments(line: Any) -> list[tuple[float, float, float, float]]:
    out = []
    for i in range(line.GetPointCount() - 1):
        out.append((line.GetX(i), line.GetY(i), line.GetX(i + 1), line.GetY(i + 1)))
    return out


def _closest_on_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    cx, cy = ax + t * dx, ay + t * dy
    return cx, cy, math.hypot(px - cx, py - cy)


def _snap_endpoints(lines: list[Any], tolerance: float) -> list[Any]:
    """Move each line end onto the nearest other line within ``tolerance`` (the QGIS snap step).

    Ends that already touch another line are moved onto it exactly, which makes
    the network noding below reliable.
    """
    cell = max(tolerance * 4, 1.0)
    grid: dict[tuple[int, int], list[tuple[int, float, float, float, float]]] = {}
    for li, line in enumerate(lines):
        for ax, ay, bx, by in _part_segments_all(line):
            x0, x1 = min(ax, bx) - tolerance, max(ax, bx) + tolerance
            y0, y1 = min(ay, by) - tolerance, max(ay, by) + tolerance
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    grid.setdefault((gx, gy), []).append((li, ax, ay, bx, by))
    out = []
    for li, line in enumerate(lines):
        new = line.Clone()
        n = new.GetPointCount()
        for vi in {0, n - 1}:
            px, py = new.GetX(vi), new.GetY(vi)
            best = None
            gx, gy = int(math.floor(px / cell)), int(math.floor(py / cell))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for oj, ax, ay, bx, by in grid.get((gx + dx, gy + dy), []):
                        if oj == li:
                            continue
                        cx, cy, d = _closest_on_segment(px, py, ax, ay, bx, by)
                        if d <= tolerance and (best is None or d < best[2]):
                            best = (cx, cy, d)
            if best is not None:
                new.SetPoint_2D(vi, best[0], best[1])
        out.append(new)
    return out


def _part_segments_all(geometry: Any) -> list[tuple[float, float, float, float]]:
    if geometry.GetGeometryCount() == 0:
        return _part_segments(geometry)
    out = []
    for i in range(geometry.GetGeometryCount()):
        out.extend(_part_segments(geometry.GetGeometryRef(i)))
    return out


def _polygonize_lines(line_path: Path, point_path: Path, point_id_field: str
                      ) -> tuple[list[tuple[int, Any]], Any, list[str]]:
    line_dataset = ogr.Open(str(line_path))
    if line_dataset is None:
        raise db.EditorError(f"cannot open line shapefile: {line_path}")
    line_layer = line_dataset.GetLayer(0)
    if line_layer is None:
        raise db.EditorError(f"no layer in line shapefile: {line_path}")
    srs = line_layer.GetSpatialRef()
    lines = []
    for feature in line_layer:
        geometry = feature.GetGeometryRef()
        if geometry is not None:
            lines.append(geometry.Clone())
    line_dataset = None
    # Lines that almost meet leave open gaps and lines can end on the middle of another,
    # so polygonize merges neighbours and drops areas. Snap the line ends, node the
    # network, then polygonize (the same sequence as the QGIS snap and polygonize tools).
    lines = _snap_endpoints(lines, SNAP_TOLERANCE)
    # node the network: where one line ends on another, the two must share a vertex
    network = ogr.Geometry(ogr.wkbMultiLineString)
    for geometry in lines:
        network.AddGeometry(geometry)
    noded = network.Union(network)
    polygons_geometry = noded.Polygonize()
    if polygons_geometry is None or polygons_geometry.GetGeometryCount() == 0:
        raise db.EditorError("could not build polygons from the supplied lines")
    # zero-area slivers are polygonize artefacts, not polygons
    kept = ogr.Geometry(ogr.wkbGeometryCollection)
    for i in range(polygons_geometry.GetGeometryCount()):
        part = polygons_geometry.GetGeometryRef(i).Clone()
        if part.GetArea() > MIN_POLYGON_AREA:
            kept.AddGeometry(part)
    polygons_geometry = kept

    point_dataset = ogr.Open(str(point_path))
    if point_dataset is None:
        raise db.EditorError(f"cannot open point shapefile: {point_path}")
    point_layer = point_dataset.GetLayer(0)
    if point_layer is None:
        raise db.EditorError(f"no layer in point shapefile: {point_path}")
    if point_id_field not in [point_layer.GetLayerDefn().GetFieldDefn(i).GetName()
                              for i in range(point_layer.GetLayerDefn().GetFieldCount())]:
        if "POLYGON_ID" in [point_layer.GetLayerDefn().GetFieldDefn(i).GetName()
                            for i in range(point_layer.GetLayerDefn().GetFieldCount())]:
            point_id_field = "POLYGON_ID"
        else:
            raise db.EditorError("point shapefile has no polygon ID field")
    points: list[tuple[int, Any]] = []
    for feature in point_layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        try:
            polygon_id = int(float(str(feature.GetField(point_id_field)).strip()))
        except (TypeError, ValueError):
            continue
        points.append((polygon_id, geometry.Clone()))
    point_dataset = None

    result: list[tuple[int, Any]] = []
    unmatched: list[str] = []
    for i in range(polygons_geometry.GetGeometryCount()):
        polygon = polygons_geometry.GetGeometryRef(i).Clone()
        contained = [polygon_id for polygon_id, point in points
                     if polygon.Contains(point)]
        if len(contained) == 1:
            result.append((contained[0], polygon))
            continue
        if not contained:
            # Fall back to the nearest point, but only when it is unambiguous.
            distances = sorted((point.DistanceToClosestPointInGeom(polygon)
                                if hasattr(point, "DistanceToClosestPointInGeom") else polygon.Distance(point),
                                polygon_id, point)
                               for polygon_id, point in points)
            if distances and distances[0][0] <= 5.0 and (
                    len(distances) == 1 or distances[0][0] < distances[1][0] - 1e-9):
                result.append((distances[0][1], polygon))
                continue
        unmatched.append(f"polygon {i + 1}: contains {len(contained)} point(s)")
    return result, srs, unmatched


def _transform(geometry: Any, source_srs: Any, target_srs: Any) -> None:
    if source_srs is not None and target_srs is not None and not source_srs.IsSame(target_srs):
        transform = osr.CreateCoordinateTransformation(source_srs, target_srs)
        if transform is None:
            raise db.EditorError("cannot transform geometry to the MDB coordinate system")
        geometry.Transform(transform)


def _flatten(geometry: Any) -> Any:
    geometry = geometry.Clone()
    geometry.FlattenTo2D()
    return geometry


def _shape_bytes(geometry: Any) -> bytes:
    geometry = _flatten(geometry)
    if geometry.GetGeometryType() in (ogr.wkbPolygon, ogr.wkbPolygon25D):
        multi = ogr.ForceToMultiPolygon(geometry.Clone())
    elif geometry.GetGeometryType() in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
        multi = geometry.Clone()
    else:
        raise db.EditorError("geometry is not a polygon")
    rings: list[list[tuple[float, float]]] = []
    for i in range(multi.GetGeometryCount()):
        polygon = multi.GetGeometryRef(i)
        if polygon.GetGeometryCount() < 1:
            continue
        exterior = polygon.GetGeometryRef(0)
        if exterior is None or exterior.GetPointCount() < 3:
            continue
        ring = [(float(exterior.GetX(j)), float(exterior.GetY(j)))
                 for j in range(exterior.GetPointCount())]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        rings.append(ring)
        for k in range(1, polygon.GetGeometryCount()):
            interior = polygon.GetGeometryRef(k)
            if interior is None or interior.GetPointCount() < 3:
                continue
            ring = [(float(interior.GetX(j)), float(interior.GetY(j)))
                     for j in range(interior.GetPointCount())]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)
    if not rings:
        raise db.EditorError("polygon has no rings")
    xs = [point[0] for ring in rings for point in ring]
    ys = [point[1] for ring in rings for point in ring]
    num_parts = len(rings)
    num_points = sum(len(ring) for ring in rings)
    parts: list[int] = []
    offset = 0
    for ring in rings:
        parts.append(offset)
        offset += len(ring)
    import struct
    data = struct.pack("<i", 5)
    data += struct.pack("<4d", min(xs), min(ys), max(xs), max(ys))
    data += struct.pack("<ii", num_parts, num_points)
    data += struct.pack(f"<{num_parts}i", *parts)
    for ring in rings:
        for x, y in ring:
            data += struct.pack("<2d", x, y)
    return data


def _perimeter(geometry: Any) -> float:
    boundary = geometry.Boundary()
    if boundary is None:
        return 0.0
    return float(boundary.Length())


def import_geometry(mdb_path: Path | str, source_path: Path | str, *,
                    point_path: Path | str | None = None,
                    id_field: str = "POLYGON_ID",
                    point_id_field: str = "POLYGON_ID",
                    create_missing: bool = False,
                    user: str = "") -> tuple[Any, int, str]:
    mdb_path = Path(mdb_path)
    source_path = Path(source_path)
    point_path = Path(point_path) if point_path else None

    existing_rows = db.read_rows(mdb_path, "FOREST_COVER_OBJECT")
    existing = {_int(row.get("FOREST_COVER_OBJECT_ID")): row for row in existing_rows}
    vcpe_rows = db.read_rows(mdb_path, "VEGETATION_COVER_POLYGON_EST")
    label_rows = db.read_rows(mdb_path, "Polygon_Label")
    index_rows = db.read_rows(mdb_path, "FOREST_COVER_OBJECT_GEOMETRY_Index")
    existing_index = {_int(row.get("IndexedObjectId")): row for row in index_rows}

    if point_path is not None:
        imported, source_srs, unmatched = _polygonize_lines(
            source_path, point_path, point_id_field)
    else:
        imported, source_srs, unmatched = _read_shape_polygons(source_path, id_field)

    target_srs = None
    try:
        dataset = ogr.Open(str(mdb_path))
        if dataset is not None:
            layer = dataset.GetLayer("FOREST_COVER_OBJECT")
            if layer is not None:
                target_srs = layer.GetSpatialRef()
            dataset = None
    except Exception:
        target_srs = None

    geom_columns = db.read_rows(mdb_path, "GDB_GeomColumns")
    geom_column = geom_columns[0] if geom_columns else {}
    grid_size = float(geom_column.get("IdxGridSize") or 1000.0)
    origin_x = float(geom_column.get("IdxOriginX") or 0.0)
    origin_y = float(geom_column.get("IdxOriginY") or 0.0)
    current_extent = (float(geom_column.get("ExtentLeft") or 0.0),
                      float(geom_column.get("ExtentBottom") or 0.0),
                      float(geom_column.get("ExtentRight") or 0.0),
                      float(geom_column.get("ExtentTop") or 0.0)) if geom_column else (0.0, 0.0, 0.0, 0.0)

    next_fco_objectid = db._max_int(existing_rows, "OBJECTID") + 1
    next_vcpe_objectid = db._max_int(vcpe_rows, "OBJECTID") + 1
    next_label_objectid = db._max_int(label_rows, "OBJECTID") + 1

    labels_by_fid = {_int(row.get("FOREST_COVER_OBJECT_ID")): row for row in label_rows}
    map_name = ""
    if label_rows:
        map_name = str(label_rows[0].get("BCGS") or "").strip()
    if not map_name and existing_rows:
        map_name = str(existing_rows[0].get("PROJECT_NAME") or "").strip()

    imported_by_id: dict[int, Any] = {}
    for polygon_id, geometry in imported:
        fid = _normalize_id(polygon_id)
        imported_by_id[fid] = geometry

    matched_ids: list[int] = []
    created_ids: list[int] = []
    skipped_ids: list[int] = []
    edits: list[str] = []
    min_x = current_extent[0] if geom_column else None
    min_y = current_extent[1] if geom_column else None
    max_x = current_extent[2] if geom_column else None
    max_y = current_extent[3] if geom_column else None

    for fid, raw_geometry in imported_by_id.items():
        geometry = _flatten(raw_geometry)
        _transform(geometry, source_srs, target_srs)
        if geometry is None or geometry.GetGeometryCount() == 0 and geometry.GetGeometryType() not in (ogr.wkbPolygon, ogr.wkbPolygon25D):
            skipped_ids.append(fid)
            continue
        if geometry.GetGeometryType() not in (ogr.wkbPolygon, ogr.wkbPolygon25D,
                                             ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
            skipped_ids.append(fid)
            continue
        try:
            shape = _shape_bytes(geometry)
        except Exception:
            skipped_ids.append(fid)
            continue
        area = float(geometry.GetArea())
        perimeter = _perimeter(geometry)
        envelope = geometry.GetEnvelope()  # (minx, maxx, miny, maxy)
        if min_x is None:
            min_x, max_x = envelope[0], envelope[1]
            min_y, max_y = envelope[2], envelope[3]
        else:
            min_x = min(min_x, envelope[0])
            max_x = max(max_x, envelope[1])
            min_y = min(min_y, envelope[2])
            max_y = max(max_y, envelope[3])

        if fid in existing:
            matched_ids.append(fid)
            edits.append(db.edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", fid, {
                "GEOMETRY": shape,
                "GEOMETRY_Length": perimeter,
                "GEOMETRY_Area": area,
                "POLYGON_AREA": area,
            }))
            if fid in labels_by_fid:
                edits.append(db.edit_line("U", "Polygon_Label", "FOREST_COVER_OBJECT_ID", fid, {
                    "POLYGON_AREA_LENGTH": f"{area:.1f},{perimeter:.1f}",
                }))
        elif create_missing:
            created_ids.append(fid)
            fco_objectid = next_fco_objectid
            vcpe_objectid = next_vcpe_objectid
            label_objectid = next_label_objectid
            next_fco_objectid += 1
            next_vcpe_objectid += 1
            next_label_objectid += 1
            edits.append(db.edit_line("I", "FOREST_COVER_OBJECT", "", "", {
                "FOREST_COVER_OBJECT_ID": fid,
                "OBJECTID": fco_objectid,
                "POLYGON_NUMBER": str(fid),
                "INVENTORY_STANDARD_CODE": "V",
                "INTERPRETER": user,
                "PROJECT_NAME": existing_rows[0].get("PROJECT_NAME", "") if existing_rows else "",
                "GEOMETRY": shape,
                "GEOMETRY_Length": perimeter,
                "GEOMETRY_Area": area,
                "POLYGON_AREA": area,
                "ENTRY_USERID": user,
                "UPDATE_USERID": user,
            }))
            edits.append(db.edit_line("I", "VEGETATION_COVER_POLYGON_EST", "", "", {
                "FOREST_COVER_OBJECT_ID": fid,
                "OBJECTID": vcpe_objectid,
                "ENTRY_USERID": user,
                "UPDATE_USERID": user,
            }))
            edits.append(db.edit_line("I", "Polygon_Label", "", "", {
                "FOREST_COVER_OBJECT_ID": fid,
                "OBJECTID": label_objectid,
                "BCGS": map_name,
                "POLYGON_AREA_LENGTH": f"{area:.1f},{perimeter:.1f}",
                "MENSURATIONAL_DATA": "|||||0",
                "INVSTD_TSA_TFL": "V||",
            }))
        else:
            skipped_ids.append(fid)
            continue

        min_gx = math.floor((envelope[0] - origin_x) / grid_size)
        min_gy = math.floor((envelope[2] - origin_y) / grid_size)
        max_gx = math.floor((envelope[1] - origin_x) / grid_size)
        max_gy = math.floor((envelope[3] - origin_y) / grid_size)
        if fid in existing_index:
            edits.append(db.edit_line("U", "FOREST_COVER_OBJECT_GEOMETRY_Index", "IndexedObjectId", fid, {
                "MinGX": min_gx,
                "MinGY": min_gy,
                "MaxGX": max_gx,
                "MaxGY": max_gy,
            }))
        else:
            edits.append(db.edit_line("I", "FOREST_COVER_OBJECT_GEOMETRY_Index", "", "", {
                "IndexedObjectId": fid,
                "MinGX": min_gx,
                "MinGY": min_gy,
                "MaxGX": max_gx,
                "MaxGY": max_gy,
            }))

    if geom_column and (min_x is not None):
        edits.append(db.edit_line("U", "GDB_GeomColumns", "TableName", "FOREST_COVER_OBJECT", {
            "ExtentLeft": min(current_extent[0], min_x),
            "ExtentBottom": min(current_extent[1], min_y),
            "ExtentRight": max(current_extent[2], max_x),
            "ExtentTop": max(current_extent[3], max_y),
        }))

    backup, updated = db.save(mdb_path, edits)
    summary = (f"imported {len(matched_ids) + len(created_ids)} polygon(s): "
               f"{len(matched_ids)} updated, {len(created_ids)} created, "
               f"{len(skipped_ids)} skipped")
    if unmatched:
        summary += "; " + "; ".join(unmatched[:5])
        if len(unmatched) > 5:
            summary += f"; and {len(unmatched) - 5} more build warnings"
    if skipped_ids:
        summary += f"; skipped IDs: {', '.join(str(v) for v in skipped_ids[:10])}"
        if len(skipped_ids) > 10:
            summary += f" ... ({len(skipped_ids)} total)"
    return backup, updated, summary


def _label_eco(vcpe: dict[str, Any], layer: dict[str, Any] | None,
               lcc_rows: list[dict[str, Any]]) -> str:
    parts = [
        (vcpe.get("SURFACE_EXPRESSION_CODE") or "").strip(),
        (vcpe.get("MODIFYING_PROCESS_CODE") or "").strip(),
        (vcpe.get("SITE_POSITION_MESO_CODE") or "").strip(),
        (vcpe.get("ALPINE_DESIGNATION_CODE") or "").strip(),
        (vcpe.get("SOIL_NUTRIENT_REGIME_CODE") or "").strip(),
    ]
    soil_moist = ""
    if lcc_rows:
        soil_moist = (lcc_rows[0].get("SOIL_MOISTURE_REGIME_CODE") or "").strip()
    basal = ""
    stems = ""
    if layer:
        basal = (layer.get("BASAL_AREA") or "").strip()
        stems = (layer.get("VRI_LIVE_STEMS_PER_HA") or "").strip()
    return ("".join(parts) + "_" + soil_moist + "_ba=" + basal
            + "_stems=" + stems)


def _label_spec(species_rows: list[dict[str, Any]]) -> str:
    pairs = []
    for row in species_rows[:6]:
        code = (row.get("TREE_SPECIES_CODE") or "").strip()
        pct = (row.get("SPECIES_PCT") or "").strip()
        pairs.append(code + pct)
    return "__".join(pairs)


def _label_dim(species_rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in species_rows[:2]:
        code = (row.get("TREE_SPECIES_CODE") or "").strip()
        age = (row.get("AGE") or "").strip()
        height = (row.get("HEIGHT") or "").strip()
        parts.append(f"{code}_age={age}_height={height}")
    return "__".join(parts)


def export_polygons(mdb_path: Path | str, output_path: Path | str) -> tuple[str, int]:
    """Export VRI polygons to a shapefile with the three label columns.

    Geometry is read from the MDB (FOREST_COVER_OBJECT OGR layer) and the
    attribute columns are joined from the VRIMS tables. The three label columns
    follow the user's field-calculator formulas.
    """
    from osgeo import ogr, osr
    from vri_editor import db

    mdb = Path(mdb_path)
    out = Path(output_path)
    if out.suffix.lower() != ".shp":
        out = out.with_suffix(".shp")
    if out.exists():
        for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            candidate = out.with_suffix(suffix)
            if candidate.exists():
                candidate.unlink()

    ds = ogr.Open(str(mdb))
    if ds is None:
        raise db.EditorError(f"cannot open MDB: {mdb}")
    src_layer = ds.GetLayer("FOREST_COVER_OBJECT")
    if src_layer is None:
        raise db.EditorError("FOREST_COVER_OBJECT layer not found in MDB")
    srs = src_layer.GetSpatialRef()

    # preload VRIMS tables
    fco_rows = {int(r["FOREST_COVER_OBJECT_ID"]): r
                for r in db.read_rows(mdb, "FOREST_COVER_OBJECT")
                if r.get("FOREST_COVER_OBJECT_ID")}
    vcpe_rows = {}
    for r in db.read_rows(mdb, "VEGETATION_COVER_POLYGON_EST"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            vcpe_rows[int(fid)] = r
    tcl_by_fid: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "TREE_COVER_LAYER_ESTIMATED"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            tcl_by_fid.setdefault(int(fid), []).append(r)
    tse_by_layer: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "TREE_SPECIES_ESTIMATED"):
        lid = r.get("TREE_COVER_LAYER_ESTIMATED_ID")
        if lid:
            tse_by_layer.setdefault(int(lid), []).append(r)
    lcc_by_fid: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "LAND_COVER_COMPONENT_EST"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            lcc_by_fid.setdefault(int(fid), []).append(r)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    out_ds = driver.CreateDataSource(str(out))
    out_layer = out_ds.CreateLayer("polygons", srs, ogr.wkbPolygon)
    def add_field(name: str, ftype: int, width: int = 254):
        field = ogr.FieldDefn(name, ftype)
        if ftype == ogr.OFTString:
            field.SetWidth(width)
        out_layer.CreateField(field)

    add_field("POLY_NUM", ogr.OFTString, 12)
    add_field("OPENING_ID", ogr.OFTString, 12)
    add_field("INV_STD", ogr.OFTString, 4)
    add_field("LAB_1_ECO", ogr.OFTString, 254)
    add_field("LAB_2_SPEC", ogr.OFTString, 254)
    add_field("LAB_3_DIM", ogr.OFTString, 254)

    count = 0
    src_layer.ResetReading()
    for feature in src_layer:
        try:
            fid = int(feature.GetField("FOREST_COVER_OBJECT_ID"))
        except (TypeError, ValueError):
            continue
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        geometry = geometry.Clone()
        out_feature = ogr.Feature(out_layer.GetLayerDefn())
        out_feature.SetGeometry(geometry)
        fco = fco_rows.get(fid, {})
        vcpe = vcpe_rows.get(fid, {})
        layers = sorted(tcl_by_fid.get(fid, []),
                        key=lambda r: int(r.get("LAYER_ORDER") or 99))
        layer = layers[0] if layers else None
        species_rows: list[dict[str, str]] = []
        if layer:
            lid = int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID") or 0)
            species_rows = sorted(tse_by_layer.get(lid, []),
                                 key=lambda r: int(r.get("SPECIES_ORDER") or 99))
        lcc_rows = lcc_by_fid.get(fid, [])
        out_feature.SetField("POLY_NUM", str(fco.get("POLYGON_NUMBER") or ""))
        out_feature.SetField("OPENING_ID", str(fco.get("OPENING_ID") or ""))
        out_feature.SetField("INV_STD", str(fco.get("INVENTORY_STANDARD_CODE") or ""))
        out_feature.SetField("LAB_1_ECO", _label_eco(vcpe, layer, lcc_rows))
        out_feature.SetField("LAB_2_SPEC", _label_spec(species_rows))
        out_feature.SetField("LAB_3_DIM", _label_dim(species_rows))
        out_layer.CreateFeature(out_feature)
        out_feature = None
        count += 1

    out_ds = None
    ds = None
    return str(out), count


def export_to_gpkg(mdb_path: Path | str, output_path: Path | str) -> tuple[str, int]:
    """Export the whole VRIMS MDB structure to a GeoPackage (.gpkg).

    The FOREST_COVER_OBJECT layer keeps its geometry; every other VRIMS table
    is written as a non-spatial attribute table, preserving the relational
    structure of the MDB.
    """
    from osgeo import ogr
    from vri_editor import db
    from vri_validator.model import TABLES

    mdb = Path(mdb_path)
    out = Path(output_path)
    if out.suffix.lower() != ".gpkg":
        out = out.with_suffix(".gpkg")
    if out.exists():
        out.unlink()

    ds = ogr.Open(str(mdb))
    if ds is None:
        raise db.EditorError(f"cannot open MDB: {mdb}")

    driver = ogr.GetDriverByName("GPKG")
    out_ds = driver.CreateDataSource(str(out))

    # spatial layer: FOREST_COVER_OBJECT (with geometry)
    src_layer = ds.GetLayer("FOREST_COVER_OBJECT")
    srs = src_layer.GetSpatialRef() if src_layer is not None else None
    spatial_count = 0
    if src_layer is not None:
        out_layer = out_ds.CopyLayer(src_layer, "FOREST_COVER_OBJECT",
                                    options=["OVERWRITE=YES"])
        spatial_count = out_layer.GetFeatureCount() if out_layer else 0

    total_tables = 1 if src_layer is not None else 0
    for table_name in TABLES:
        if table_name == "FOREST_COVER_OBJECT":
            continue
        rows = db.read_rows(mdb, table_name)
        if not rows:
            continue
        # infer fields from the first row's keys
        field_names = list(rows[0].keys())
        layer = out_ds.CreateLayer(table_name, geom_type=ogr.wkbNone)
        for name in field_names:
            field = ogr.FieldDefn(name, ogr.OFTString)
            field.SetWidth(255)
            layer.CreateField(field)
        for row in rows:
            feat = ogr.Feature(layer.GetLayerDefn())
            for name in field_names:
                value = row.get(name)
                if value is not None:
                    feat.SetField(name, str(value))
            layer.CreateFeature(feat)
            feat = None
        total_tables += 1

    out_ds = None
    ds = None
    return str(out), total_tables


def export_points(mdb_path: Path | str, output_path: Path | str) -> tuple[str, int]:
    """Export VRI polygon centroids as a point shapefile with the label columns."""
    from osgeo import ogr
    from vri_editor import db

    mdb = Path(mdb_path)
    out = Path(output_path)
    if out.suffix.lower() != ".shp":
        out = out.with_suffix(".shp")
    if out.exists():
        for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            candidate = out.with_suffix(suffix)
            if candidate.exists():
                candidate.unlink()

    ds = ogr.Open(str(mdb))
    if ds is None:
        raise db.EditorError(f"cannot open MDB: {mdb}")
    src_layer = ds.GetLayer("FOREST_COVER_OBJECT")
    if src_layer is None:
        raise db.EditorError("FOREST_COVER_OBJECT layer not found in MDB")
    srs = src_layer.GetSpatialRef()

    fco_rows = {int(r["FOREST_COVER_OBJECT_ID"]): r
                for r in db.read_rows(mdb, "FOREST_COVER_OBJECT")
                if r.get("FOREST_COVER_OBJECT_ID")}
    vcpe_rows = {}
    for r in db.read_rows(mdb, "VEGETATION_COVER_POLYGON_EST"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            vcpe_rows[int(fid)] = r
    tcl_by_fid: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "TREE_COVER_LAYER_ESTIMATED"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            tcl_by_fid.setdefault(int(fid), []).append(r)
    tse_by_layer: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "TREE_SPECIES_ESTIMATED"):
        lid = r.get("TREE_COVER_LAYER_ESTIMATED_ID")
        if lid:
            tse_by_layer.setdefault(int(lid), []).append(r)
    lcc_by_fid: dict[int, list[dict[str, str]]] = {}
    for r in db.read_rows(mdb, "LAND_COVER_COMPONENT_EST"):
        fid = r.get("FOREST_COVER_OBJECT_ID")
        if fid:
            lcc_by_fid.setdefault(int(fid), []).append(r)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    out_ds = driver.CreateDataSource(str(out))
    out_layer = out_ds.CreateLayer("points", srs, ogr.wkbPoint)
    def add_field(name: str, width: int = 254):
        field = ogr.FieldDefn(name, ogr.OFTString)
        field.SetWidth(width)
        out_layer.CreateField(field)

    add_field("POLY_NUM", 12)
    add_field("OPENING_ID", 12)
    add_field("INV_STD", 4)
    add_field("LAB_1_ECO", 254)
    add_field("LAB_2_SPEC", 254)
    add_field("LAB_3_DIM", 254)

    count = 0
    src_layer.ResetReading()
    for feature in src_layer:
        try:
            fid = int(feature.GetField("FOREST_COVER_OBJECT_ID"))
        except (TypeError, ValueError):
            continue
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        centroid = geometry.Centroid()
        if centroid is None:
            continue
        fco = fco_rows.get(fid, {})
        vcpe = vcpe_rows.get(fid, {})
        layers = sorted(tcl_by_fid.get(fid, []),
                        key=lambda r: int(r.get("LAYER_ORDER") or 99))
        layer = layers[0] if layers else None
        species_rows: list[dict[str, str]] = []
        if layer:
            lid = int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID") or 0)
            species_rows = sorted(tse_by_layer.get(lid, []),
                                 key=lambda r: int(r.get("SPECIES_ORDER") or 99))
        lcc_rows = lcc_by_fid.get(fid, [])
        out_feature = ogr.Feature(out_layer.GetLayerDefn())
        out_feature.SetGeometry(centroid)
        out_feature.SetField("POLY_NUM", str(fco.get("POLYGON_NUMBER") or ""))
        out_feature.SetField("OPENING_ID", str(fco.get("OPENING_ID") or ""))
        out_feature.SetField("INV_STD", str(fco.get("INVENTORY_STANDARD_CODE") or ""))
        out_feature.SetField("LAB_1_ECO", _label_eco(vcpe, layer, lcc_rows))
        out_feature.SetField("LAB_2_SPEC", _label_spec(species_rows))
        out_feature.SetField("LAB_3_DIM", _label_dim(species_rows))
        out_layer.CreateFeature(out_feature)
        out_feature = None
        count += 1

    out_ds = None
    ds = None
    return str(out), count
