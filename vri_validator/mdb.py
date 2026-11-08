"""Access (.mdb) table export through the mdbtools CLI.

The validator never writes to the geodatabase.  Bytes are read with
``mdb-export``; geometry columns can be stripped (``-b strip``) because
validation only needs the attribute tables.
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
from pathlib import Path


class MdbError(RuntimeError):
    pass


class MdbReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise MdbError(f"database not found: {self.path}")
        if shutil.which("mdb-export") is None:
            raise MdbError("mdb-export is missing (install the mdbtools package)")

    def tables(self) -> list[str]:
        try:
            out = subprocess.run(
                ["mdb-tables", "-1", str(self.path)],
                capture_output=True, text=True, check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise MdbError(f"cannot read {self.path}: {exc.stderr.strip()}") from exc
        return [line.strip() for line in out.stdout.splitlines() if line.strip()]

    def table(self, name: str, binary: bool = False) -> list[dict[str, str]]:
        cmd = ["mdb-export"]
        if not binary:
            cmd += ["-b", "strip"]
        cmd += [str(self.path), name]
        try:
            out = subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as exc:
            msg = exc.stderr.decode("latin1", "replace").strip()
            raise MdbError(f"cannot export {name}: {msg}") from exc
        text = out.stdout.decode("latin1", "replace")
        return list(csv.DictReader(io.StringIO(text)))

    def count(self, name: str) -> int | None:
        """Logical row count, excluding rows Access has marked deleted.

        ``mdb-export`` in mdbtools 1.0.0 still emits deleted row images.  A
        Jackcess update that appends a replacement row therefore appears as a
        duplicate on export even though Access/Jet only sees the new row.
        ``mdb-count`` applies the deletion flags correctly.
        """
        try:
            out = subprocess.run(
                ["mdb-count", str(self.path), name],
                capture_output=True, text=True, check=True,
            )
            return int(out.stdout.strip().splitlines()[-1])
        except (OSError, ValueError, IndexError, subprocess.CalledProcessError):
            return None

    def has_table(self, name: str) -> bool:
        return name.lower() in {t.lower() for t in self.tables()}
