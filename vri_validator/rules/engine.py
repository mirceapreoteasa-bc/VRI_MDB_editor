"""Rule engine primitives and shared checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

from ..codes import CodeBook
from ..model import Dataset, Layer, Polygon, text, to_float, to_int
from ..species import species_type

SEVERITY_NAMES = {"E": "error", "W": "warning", "S": "warning", "I": "info"}


@dataclass
class Finding:
    code: str
    message: str
    table: str = ""
    field: str = ""
    value: str = ""
    polygon_id: int | None = None
    polygon_number: str = ""
    objectid: int | None = None
    layer_order: int | None = None
    species_order: int | None = None
    record_id: int | None = None
    source: str = ""

    @property
    def severity(self) -> str:
        return SEVERITY_NAMES.get(self.code[:1].upper(), "info")

    def key(self) -> tuple:
        return (
            self.code, self.polygon_id, self.table, self.field,
            self.layer_order, self.species_order, self.record_id, self.message,
        )


class Findings:
    def __init__(self) -> None:
        self.items: list[Finding] = []
        self._seen: set[tuple] = set()

    def add(self, finding: Finding) -> None:
        key = finding.key()
        if key not in self._seen:
            self._seen.add(key)
            self.items.append(finding)

    def counts(self) -> dict[str, int]:
        out = {"error": 0, "warning": 0, "info": 0}
        for f in self.items:
            out[f.severity] += 1
        return out

    def __len__(self) -> int:
        return len(self.items)


@dataclass
class RuleContext:
    dataset: Dataset
    codes: CodeBook
    species_types: dict[str, str]
    species_max: dict[str, dict[str, float | None]]
    current_year: int = field(default_factory=lambda: datetime.now().year)
    findings: Findings = field(default_factory=Findings)

    # -- finding helpers -------------------------------------------------
    def add(self, code: str, poly: Polygon | None, message: str, *,
            table: str = "", field: str = "", value: Any = "",
            layer: Layer | None = None, species: dict[str, str] | None = None,
            record_id: int | None = None, source: str = "") -> None:
        if layer is not None:
            layer_order = layer.order
            if record_id is None:
                record_id = to_int(layer.row.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        else:
            layer_order = None
        species_order = to_int(species.get("SPECIES_ORDER")) if species else None
        if species is not None and record_id is None:
            record_id = to_int(species.get("TREE_SPECIES_ESTIMATED_ID"))
        self.findings.add(Finding(
            code=code,
            message=message,
            table=table,
            field=field,
            value="" if value is None else str(value),
            polygon_id=poly.fid if poly else None,
            polygon_number=poly.number if poly else "",
            objectid=poly.objectid if poly else None,
            layer_order=layer_order,
            species_order=species_order,
            record_id=record_id,
            source=source,
        ))

    # -- generic checks --------------------------------------------------
    def code_check(self, poly: Polygon, table: str, row: dict[str, str], field_name: str,
                   *, required: bool = False, code: str = "E-COD-001",
                   label: str | None = None, source: str = "") -> None:
        raw = text(row.get(field_name))
        label = label or field_name
        if not raw:
            if required:
                self.add(code, poly, f"{label} is required", table=table,
                         field=field_name, source=source)
            return
        if not self.codes.valid(table, field_name, raw):
            self.add(code, poly,
                     f"{label} '{raw}' is not a valid code ({self.codes.table_for(table, field_name)})",
                     table=table, field=field_name, value=raw, source=source)

    def number_check(self, poly: Polygon, table: str, row: dict[str, str], field_name: str,
                     *, lo: float | None = None, hi: float | None = None,
                     required: bool = False, integer: bool = False,
                     code: str = "E-NUM-001", label: str | None = None,
                     source: str = "") -> None:
        raw = text(row.get(field_name))
        label = label or field_name
        if not raw:
            if required:
                self.add(code, poly, f"{label} is required", table=table,
                         field=field_name, source=source)
            return
        value = to_float(raw)
        if value is None:
            self.add(code, poly, f"{label} '{raw}' is not numeric", table=table,
                     field=field_name, value=raw, source=source)
            return
        if integer and abs(value - round(value)) > 1e-9:
            self.add(code, poly, f"{label} must be a whole number (got {raw})",
                     table=table, field=field_name, value=raw, source=source)
        if lo is not None and value < lo:
            self.add(code, poly, f"{label} {raw} is below {lo:g}", table=table,
                     field=field_name, value=raw, source=source)
        if hi is not None and value > hi:
            self.add(code, poly, f"{label} {raw} is above {hi:g}", table=table,
                     field=field_name, value=raw, source=source)

    # -- domain helpers --------------------------------------------------
    def species_class(self, code: str) -> str:
        return species_type(self.species_types, code)


RULES: list[Callable[[RuleContext], None]] = []


def rule(fn: Callable[[RuleContext], None]) -> Callable[[RuleContext], None]:
    RULES.append(fn)
    return fn


def run_rules(ctx: RuleContext) -> Findings:
    for fn in RULES:
        fn(ctx)
    return ctx.findings
