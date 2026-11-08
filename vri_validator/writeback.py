"""Write documented derived fields back to a VRIMS MDB with a backup."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .derive import DerivedUpdates

JAR_DIR = Path(__file__).resolve().parent / "data" / "jars"
CLASSPATH = os.pathsep.join(str(JAR_DIR / name) for name in (
    "jackcess-4.0.8.jar",
    "commons-lang3-3.10.jar",
    "commons-logging-1.2.jar",
    "vri-writeback.jar",
))


def _tsv(updates: DerivedUpdates) -> str:
    lines: list[str] = []
    for update in updates.vcpe:
        values = [value if value else "\\N" for value in update.levels]
        lines.append("\t".join(["VCPE", str(update.fid), *values]))
    for update in updates.tcl:
        lines.append("\t".join(["TCL", str(update.layer_id), update.rank or "\\N"]))
    for update in updates.lcc:
        lines.append("\t".join(["LCC", str(update.lcc_id), str(update.order)]))
    return "\n".join(lines) + ("\n" if lines else "")


def backup_path(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = db_path.with_name(f"{db_path.stem}.vri-backup-{stamp}{db_path.suffix}")
    counter = 1
    while candidate.exists():
        candidate = db_path.with_name(
            f"{db_path.stem}.vri-backup-{stamp}-{counter}{db_path.suffix}")
        counter += 1
    return candidate


def apply_updates(db_path: str | Path, updates: DerivedUpdates, *,
                  keep_backup: bool = True) -> tuple[Path | None, int]:
    path = Path(db_path)
    if updates.total == 0:
        return None, 0
    java = shutil.which("java")
    if java is None:
        raise RuntimeError("Java runtime not found; install Java 8+ to write derived fields")
    missing = [name for name in (
        "jackcess-4.0.8.jar", "commons-lang3-3.10.jar",
        "commons-logging-1.2.jar", "vri-writeback.jar") if not (JAR_DIR / name).is_file()]
    if missing:
        raise RuntimeError("missing write-back helper: " + ", ".join(missing))

    backup = backup_path(path)
    shutil.copy2(path, backup)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".tsv",
                                         delete=False) as handle:
            handle.write(_tsv(updates))
            temp_name = handle.name
        completed = subprocess.run(
            [java, "-cp", CLASSPATH, "VriWriteback", str(path), temp_name],
            capture_output=True, text=True, timeout=600,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"write-back failed: {detail}")
        count = 0
        for line in completed.stdout.splitlines():
            if line.startswith("updated="):
                count = int(line.split("=", 1)[1])
        return backup, count
    except Exception:
        shutil.copy2(backup, path)
        if not keep_backup:
            backup.unlink(missing_ok=True)
        raise
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
