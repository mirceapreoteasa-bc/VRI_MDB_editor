"""Shared validation pipeline used by the CLI and the desktop GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import rules  # noqa: F401  (registers rules)
from .codes import DEFAULT_CODES, DEFAULT_SPECIES_MAX, CodeBook, load_species_max
from .derive import DerivedUpdates, derive_updates
from .model import Dataset, load_dataset
from .report import write_csv, write_html
from .rules.engine import Findings, RuleContext, run_rules
from .species import species_type, species_types
from .writeback import apply_updates


@dataclass
class ValidationResult:
    dataset: Dataset
    findings: Findings
    report_paths: list[Path]


@dataclass
class RecalculationResult:
    updates: DerivedUpdates
    backup: Path | None
    updated: int


def recalculate_database(
    db_path: str | Path,
    *,
    codes_path: str | Path = DEFAULT_CODES,
    only_changed: bool = True,
) -> RecalculationResult:
    """Recalculate documented derived fields and write them to the MDB."""
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"database not found: {db_path}")
    codes = CodeBook(codes_path)
    types = species_types(codes)
    dataset = load_dataset(str(db_path))
    updates = derive_updates(
        dataset,
        lambda code: species_type(types, code),
        only_changed=only_changed,
    )
    backup, updated = apply_updates(db_path, updates)
    return RecalculationResult(updates=updates, backup=backup, updated=updated)


def validate_database(
    db_path: str | Path,
    *,
    out_dir: str | Path = "reports",
    formats: str = "both",
    title: str = "",
    codes_path: str | Path = DEFAULT_CODES,
    species_max_path: str | Path = DEFAULT_SPECIES_MAX,
) -> ValidationResult:
    """Validate one MDB and write the requested reports."""
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"database not found: {db_path}")

    codes = CodeBook(codes_path)
    species_max = load_species_max(species_max_path)
    dataset = load_dataset(str(db_path))
    ctx = RuleContext(
        dataset=dataset,
        codes=codes,
        species_types=species_types(codes),
        species_max=species_max,
    )
    findings = run_rules(ctx)

    out_dir = Path(out_dir)
    stem = db_path.stem
    paths: list[Path] = []
    if formats in ("both", "csv"):
        paths.append(write_csv(findings, out_dir / f"{stem}_validation.csv"))
    if formats in ("both", "html"):
        paths.append(write_html(
            dataset,
            findings,
            out_dir / f"{stem}_validation.html",
            title=title or f"VRI validation: {db_path.name}",
        ))
    return ValidationResult(dataset=dataset, findings=findings, report_paths=paths)
