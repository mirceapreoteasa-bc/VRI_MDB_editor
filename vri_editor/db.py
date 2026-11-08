"""Minimal MDB access for the VRI editor skeleton.

Reads with mdbtools, writes with a small Jackcess helper.  All writes go to a
temporary copy and replace the original only after the helper succeeds.
"""

from __future__ import annotations

import base64
import csv
import io
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
TEMPLATE_PATH = DATA_DIR / "template.mdb"
JAVA_SRC = PACKAGE_DIR / "java" / "VriEdit.java"
CLASSES_DIR = DATA_DIR / "classes"
JARS = tuple(DATA_DIR / name for name in (
    "jackcess-4.0.8.jar",
    "commons-lang3-3.10.jar",
    "commons-logging-1.2.jar",
))


class EditorError(RuntimeError):
    pass


def _java() -> str:
    java = shutil.which("java")
    if java is None:
        raise EditorError("Java runtime not found (install Java 8+)")
    return java


def _classpath() -> str:
    return os.pathsep.join([*(str(p) for p in JARS), str(CLASSES_DIR)])


def _ensure_helper() -> None:
    CLASSES_DIR.mkdir(parents=True, exist_ok=True)
    if (CLASSES_DIR / "VriEdit.class").is_file() and (CLASSES_DIR / "VriDump.class").is_file():
        return
    java = _java()
    sources = [str(JAVA_SRC), str(JAVA_SRC.with_name("VriDump.java"))]
    completed = subprocess.run(
        [java, "-m", "jdk.compiler/com.sun.tools.javac.Main",
         "-cp", _classpath(), "-d", str(CLASSES_DIR), *sources],
        capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise EditorError("cannot compile MDB helper:\n" + (completed.stderr or completed.stdout))


def _b64(value: Any) -> str:
    if value is None:
        return "~"
    if isinstance(value, (bytes, bytearray)):
        return base64.b64encode(bytes(value)).decode("ascii")
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


def _edit_line(action: str, table: str, key_name: str, key_value: Any,
               values: dict[str, Any]) -> str:
    fields = [f"{name}={_b64(value)}" for name, value in values.items() if value is not None]
    return "\t".join([action, table, key_name, str(key_value), *fields])


def _delete_line(table: str, key_name: str, key_value: Any) -> str:
    return "\t".join(["D", table, key_name, str(key_value)])


def _apply(path: Path, edits: list[str]) -> int:
    if not edits:
        return 0
    _ensure_helper()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".tsv", delete=False) as handle:
        handle.write("\n".join(edits) + "\n")
        temp = Path(handle.name)
    try:
        completed = subprocess.run(
            [_java(), "-cp", _classpath(), "VriEdit", str(path), str(temp)],
            capture_output=True, text=True, timeout=120,
        )
        if completed.returncode != 0:
            raise EditorError((completed.stderr or completed.stdout).strip() or "write failed")
        for line in completed.stdout.splitlines():
            if line.startswith("updated="):
                return int(line.split("=", 1)[1])
        return 0
    finally:
        temp.unlink(missing_ok=True)


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.stem}.vri-backup-{stamp}{path.suffix}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}.vri-backup-{stamp}-{counter}{path.suffix}")
        counter += 1
    return candidate


def read_rows(path: Path | str, table: str) -> list[dict[str, str]]:
    """All live rows of a table as strings, read with Jackcess (the writer's library).

    mdb-export (mdbtools) also returns stale copies of rows that Jackcess has moved
    during an update, so it is not used for reading.
    """
    path = Path(path)
    _ensure_helper()
    completed = subprocess.run(
        [_java(), "-cp", _classpath(), "VriDump", str(path), table],
        capture_output=True, text=True, timeout=300,
    )
    if completed.returncode != 0:
        raise EditorError((completed.stderr or completed.stdout).strip() or f"cannot read {table}")
    lines = completed.stdout.splitlines()
    if not lines:
        return []
    decode = lambda cell: base64.b64decode(cell).decode("utf-8") if cell else ""
    names = [decode(c) for c in lines[0].split("\t")] if lines[0] else []
    rows = []
    for line in lines[1:]:
        cells = line.split("\t") if line else [""] * len(names)
        rows.append({name: decode(cells[i]) if i < len(cells) else "" for i, name in enumerate(names)})
    return rows


def new_project(target: Path | str, *, project: str, interpreter: str,
                map_name: str, overwrite: bool = False) -> Path:
    target = Path(target).expanduser()
    if target.exists() and not overwrite:
        raise EditorError(f"file already exists: {target}")
    if not TEMPLATE_PATH.is_file():
        raise EditorError(f"template missing: {TEMPLATE_PATH}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE_PATH, target)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    edits = [
        _edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", 1, {
            "PROJECT_NAME": project,
            "INTERPRETER": interpreter,
            "INTERPRETATION_DATE": now,
            "CREATED_DATE": now,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": interpreter,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": interpreter,
        }),
        _edit_line("U", "VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID", 1, {
            "INPUT_DATE": now,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": interpreter,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": interpreter,
        }),
        _edit_line("U", "Polygon_Label", "FOREST_COVER_OBJECT_ID", 1, {
            "BCGS": map_name,
            "GEO_CENTROID_XYZ": "",
            "POLYGON_AREA_LENGTH": "",
            "MAX_LAYERS_LEVELS": "",
        }),
    ]
    try:
        _apply(target, edits)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def save(path: Path | str, edits: list[str]) -> tuple[Path | None, int]:
    """Apply edits to a temp copy, then replace the original after a backup."""
    path = Path(path)
    if not edits:
        return None, 0
    backup = backup_path(path)
    shutil.copy2(path, backup)
    temp = path.with_name(path.name + ".vri-edit.tmp")
    tables = sorted({e.split("\t")[1] for e in edits if "\t" in e})
    # expected row change per table: +1 per insert, -1 per delete, 0 per update
    expected_delta = {t: 0 for t in tables}
    for e in edits:
        parts = e.split("\t")
        if len(parts) > 1 and parts[1] in expected_delta:
            if parts[0] == "I":
                expected_delta[parts[1]] += 1
            elif parts[0] == "D":
                expected_delta[parts[1]] -= 1
    before = {t: len(read_rows(path, t)) for t in tables}
    try:
        shutil.copy2(path, temp)
        updated = _apply(temp, edits)
        after = {t: len(read_rows(temp, t)) for t in tables}
        bad = [t for t in tables if after[t] != before[t] + expected_delta[t]]
        if bad:
            # an update must never add or lose rows: restore the original and refuse
            raise EditorError(
                "write check failed: unexpected row count in " + ", ".join(bad)
                + " (" + ", ".join(f"{t} {before[t]}->{after[t]}" for t in bad)
                + "). The original map was not changed.")
        os.replace(temp, path)
        return backup, updated
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def update_polygon(path: Path | str, fid: int, fco: dict[str, Any],
                   vcpe: dict[str, Any]) -> tuple[Path | None, int]:
    edits = [
        _edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", fid, fco),
        _edit_line("U", "VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID", fid, vcpe),
    ]
    return save(path, edits)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _max_int(rows: list[dict[str, str]], field: str) -> int:
    values = []
    for row in rows:
        try:
            values.append(int(float(row.get(field, ""))))
        except (TypeError, ValueError):
            pass
    return max(values, default=0)


def poly_number_conflict(rows: dict[int, dict[str, Any]] | list[dict[str, str]],
                         fid: int, number: str) -> int | None:
    """Return the id of another polygon already using ``number``, or None.

    ``rows`` is either the editor's {fid: {"fco": {...}}} mapping or a list of
    FOREST_COVER_OBJECT rows. The polygon being saved (``fid``) is ignored.
    """
    wanted = (number or "").strip()
    if not wanted:
        return None
    if isinstance(rows, dict):
        items = [(key, record.get("fco", {})) for key, record in rows.items()]
    else:
        items = [(_int(row.get("FOREST_COVER_OBJECT_ID")), row) for row in rows]
    for other_fid, fco in items:
        if other_fid == fid:
            continue
        if (fco.get("POLYGON_NUMBER", "") or "").strip() == wanted:
            return other_fid
    return None


def next_polygon_number(rows: list[dict[str, str]]) -> str:
    values = []
    for row in rows:
        try:
            values.append(int(float(row.get("POLYGON_NUMBER", ""))))
        except (TypeError, ValueError):
            pass
    return str(max(values, default=0) + 1)


def next_negative_id(rows: list[dict[str, str]], field: str) -> int:
    values = []
    for row in rows:
        try:
            value = int(float(row.get(field, "")))
        except (TypeError, ValueError):
            continue
        if value < 0:
            values.append(value)
    return min(values, default=0) - 1


def add_polygon(path: Path | str, polygon_number: str | None = None) -> int:
    path = Path(path)
    fco = read_rows(path, "FOREST_COVER_OBJECT")
    vcpe = read_rows(path, "VEGETATION_COVER_POLYGON_EST")
    labels = read_rows(path, "Polygon_Label")
    fid = _max_int(fco, "FOREST_COVER_OBJECT_ID") + 1
    number = polygon_number.strip() if polygon_number and polygon_number.strip() else next_polygon_number(fco)
    first = fco[0] if fco else {}
    user = first.get("INTERPRETER", "")
    project = first.get("PROJECT_NAME", "")
    map_name = labels[0].get("BCGS", "") if labels else ""
    objectid = _max_int(fco, "OBJECTID") + 1
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    edits = [
        _edit_line("I", "FOREST_COVER_OBJECT", "", "", {
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": objectid,
            "POLYGON_NUMBER": number,
            "INVENTORY_STANDARD_CODE": first.get("INVENTORY_STANDARD_CODE", "V"),
            "INTERPRETER": user,
            "PROJECT_NAME": project,
            "TSA_NUMBER": first.get("TSA_NUMBER", ""),
            "TFL_NUMBER": first.get("TFL_NUMBER", ""),
            "REFERENCE_YEAR": first.get("REFERENCE_YEAR", ""),
            "DATA_CAPTURE_METHOD_CODE": first.get("DATA_CAPTURE_METHOD_CODE", ""),
            "FREE_TO_GROW_IND": first.get("FREE_TO_GROW_IND", ""),
            "INTERPRETATION_DATE": now,
            "CREATED_DATE": now,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": user,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": user,
        }),
        _edit_line("I", "VEGETATION_COVER_POLYGON_EST", "", "", {
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": _max_int(vcpe, "OBJECTID") + 1,
            "INPUT_DATE": now,
            "ENTRY_TIMESTAMP": now,
            "ENTRY_USERID": user,
            "UPDATE_TIMESTAMP": now,
            "UPDATE_USERID": user,
        }),
        _edit_line("I", "Polygon_Label", "", "", {
            "FOREST_COVER_OBJECT_ID": fid,
            "OBJECTID": _max_int(labels, "OBJECTID") + 1,
            "BCGS": map_name,
            "MENSURATIONAL_DATA": "|||||0",
            "INVSTD_TSA_TFL": "V||",
        }),
    ]
    save(path, edits)
    return fid




def delete_polygon(path: Path | str, fid: int) -> tuple[Path | None, int]:
    """Delete a polygon and its child rows, including the geometry index row."""
    path = Path(path)
    fco = read_rows(path, "FOREST_COVER_OBJECT")
    target = next((row for row in fco if _int(row.get("FOREST_COVER_OBJECT_ID")) == fid), None)
    if target is None:
        raise EditorError(f"polygon {fid} not found")
    objectid = _int(target.get("OBJECTID"))
    vcpe = read_rows(path, "VEGETATION_COVER_POLYGON_EST")
    labels = read_rows(path, "Polygon_Label")
    tcl = read_rows(path, "TREE_COVER_LAYER_ESTIMATED")
    tse = read_rows(path, "TREE_SPECIES_ESTIMATED")
    lcc = read_rows(path, "LAND_COVER_COMPONENT_EST")
    nvce = read_rows(path, "NON_VEGETATIVE_COVER_EST")
    layer_ids = {
        _int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")) for row in tcl
        if _int(row.get("FOREST_COVER_OBJECT_ID")) == fid
    }
    edits = [_delete_line("FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", fid)]
    for table, key, rows in (
        ("VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID", vcpe),
        ("Polygon_Label", "FOREST_COVER_OBJECT_ID", labels),
        ("LAND_COVER_COMPONENT_EST", "LAND_COVER_COMPONENT_EST_ID", lcc),
        ("NON_VEGETATIVE_COVER_EST", "NON_VEGETATIVE_COVER_EST_ID", nvce),
    ):
        field = "FOREST_COVER_OBJECT_ID" if key == "FOREST_COVER_OBJECT_ID" else None
        for row in rows:
            if _int(row.get(field or "FOREST_COVER_OBJECT_ID")) == fid:
                edits.append(_delete_line(table, key, _int(row.get(key))))
    for layer_id in sorted(layer_ids):
        edits.append(_delete_line(
            "TREE_COVER_LAYER_ESTIMATED", "TREE_COVER_LAYER_ESTIMATED_ID", layer_id))
    for row in tse:
        if _int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")) in layer_ids:
            edits.append(_delete_line(
                "TREE_SPECIES_ESTIMATED", "TREE_SPECIES_ESTIMATED_ID",
                _int(row.get("TREE_SPECIES_ESTIMATED_ID"))))
    try:
        index_rows = read_rows(path, "FOREST_COVER_OBJECT_GEOMETRY_Index")
    except EditorError:
        index_rows = []
    for row in index_rows:
        if _int(row.get("IndexedObjectId")) == objectid:
            edits.append(_delete_line(
                "FOREST_COVER_OBJECT_GEOMETRY_Index", "IndexedObjectId", objectid))
    return save(path, list(dict.fromkeys(edits)))


def insert_row(path: Path | str, table: str, values: dict[str, Any]) -> tuple[Path | None, int]:
    return save(path, [_edit_line("I", table, "", "", values)])


def delete_row(path: Path | str, table: str, key_name: str, key_value: Any) -> tuple[Path | None, int]:
    return save(path, [_delete_line(table, key_name, key_value)])


def child_id(path: Path | str, table: str, field: str) -> int:
    return next_negative_id(read_rows(path, table), field)


def edit_line(action: str, table: str, key_name: str, key_value: Any,
              values: dict[str, Any]) -> str:
    return _edit_line(action, table, key_name, key_value, values)


def delete_line(table: str, key_name: str, key_value: Any) -> str:
    return _delete_line(table, key_name, key_value)


def next_objectid(path: Path | str, table: str) -> int:
    return _max_int(read_rows(path, table), "OBJECTID") + 1
