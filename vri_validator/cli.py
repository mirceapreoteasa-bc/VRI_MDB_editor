"""Command-line entry point for the VRI validator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .codes import DEFAULT_CODES, DEFAULT_SPECIES_MAX
from .report import counts_by_code
from .service import recalculate_database, validate_database


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vri-validate",
        description="Validate a BC VRI/VRIMS personal geodatabase (.mdb); optional derived-field recalculation.",
    )
    p.add_argument("path", help="path to the VRIMS .mdb file")
    p.add_argument("-o", "--out", default="reports",
                   help="output directory (default: ./reports)")
    p.add_argument("--format", choices=("both", "csv", "html"), default="both",
                   help="report format (default: both)")
    p.add_argument("--title", default="", help="optional report title")
    p.add_argument("--codes", default=str(DEFAULT_CODES),
                   help="path to codes.xml (default: bundled vri_validator/data/codes.xml)")
    p.add_argument("--species-max", default=str(DEFAULT_SPECIES_MAX),
                   help="path to species_max.json (default: bundled vri_validator/data/species_max.json)")
    p.add_argument("--fail-on", choices=("error", "warning", "never"), default="error",
                   help="exit non-zero when findings at this severity exist (default: error)")
    p.add_argument("--recalculate", action="store_true",
                   help="recalculate BCLCS, layer rank and LCC order, writing a backup first")
    p.add_argument("--quiet", action="store_true", help="only print the report paths")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = Path(args.path).expanduser()
    if not db_path.is_file():
        print(f"error: database not found: {db_path}", file=sys.stderr)
        return 2

    if args.recalculate:
        try:
            recalc = recalculate_database(db_path, codes_path=args.codes)
        except Exception as exc:
            print(f"error: recalculation failed: {exc}", file=sys.stderr)
            return 2
        if recalc.updated:
            if not args.quiet:
                print(f"Recalculated {recalc.updated:,} derived values")
                print(f"Backup: {recalc.backup}")
        elif not args.quiet:
            print("Derived fields already current; no backup written")

    try:
        result = validate_database(
            db_path,
            out_dir=Path(args.out).expanduser(),
            formats=args.format,
            title=args.title,
            codes_path=args.codes,
            species_max_path=args.species_max,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    dataset = result.dataset
    findings = result.findings
    counts = findings.counts()
    paths = result.report_paths

    if not args.quiet:
        print(f"Database: {db_path}")
        print(f"Polygons: {len(dataset.polygons):,}")
        print("Rows: " + ", ".join(f"{k}={v:,}" for k, v in dataset.row_counts.items()))
        print(f"Findings: {counts['error']:,} errors, {counts['warning']:,} warnings, "
              f"{counts['info']:,} info")
        top = counts_by_code(findings)[:12]
        if top:
            print("Top rules:")
            for code, severity, n in top:
                print(f"  {code:<18} {severity:<8} {n:,}")
        for path in paths:
            print(f"Report: {path}")

    if args.fail_on == "warning" and (counts["error"] or counts["warning"]):
        return 1
    if args.fail_on == "error" and counts["error"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
