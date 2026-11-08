"""Dataset / Forest Cover Object level checks."""

from __future__ import annotations

from ..model import date_of, text, to_float, to_int
from .engine import RuleContext, rule


@rule
def fco_identifier(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if poly.fid == 0:
            ctx.add("E-GEN-001", poly,
                    "FOREST_COVER_OBJECT_ID = 0 is not permitted",
                    table="FOREST_COVER_OBJECT", field="FOREST_COVER_OBJECT_ID",
                    value=poly.fid, source="rules 1.3 / Access 15")

    for row in ctx.dataset.orphans.get("FOREST_COVER_OBJECT_DUPLICATE", []):
        ctx.add("E-GEN-002", None,
                f"duplicate FOREST_COVER_OBJECT_ID {row.get('FOREST_COVER_OBJECT_ID')}",
                table="FOREST_COVER_OBJECT",
                field="FOREST_COVER_OBJECT_ID",
                value=row.get("FOREST_COVER_OBJECT_ID"),
                source="Access 16")


@rule
def referential_integrity(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if poly.vcpe is None:
            ctx.add("E-GEN-003", poly,
                    "polygon has no VEGETATION_COVER_POLYGON_EST record",
                    table="VEGETATION_COVER_POLYGON_EST",
                    field="FOREST_COVER_OBJECT_ID", value=poly.fid,
                    source="rules 1.2 / Access 33")

    labels = {
        "VEGETATION_COVER_POLYGON_EST": "VCPE",
        "TREE_COVER_LAYER_ESTIMATED": "TCL",
        "TREE_SPECIES_ESTIMATED": "TSE",
        "LAND_COVER_COMPONENT_EST": "LCC",
        "NON_VEGETATIVE_COVER_EST": "NVCE",
    }
    for table, rows in ctx.dataset.orphans.items():
        if table == "FOREST_COVER_OBJECT_DUPLICATE":
            continue
        for row in rows:
            ctx.add("E-GEN-004", None,
                    f"{labels.get(table, table)} record has no matching "
                    "FOREST_COVER_OBJECT / parent record",
                    table=table,
                    field="FOREST_COVER_OBJECT_ID",
                    value=row.get("FOREST_COVER_OBJECT_ID"),
                    source="rules 1.2 / Access 33")


@rule
def duplicate_polygon_numbers(ctx: RuleContext) -> None:
    seen: dict[str, list] = {}
    for poly in ctx.dataset.polygons:
        number = poly.number
        if number:
            seen.setdefault(number, []).append(poly)
    for number, polys in seen.items():
        if len(polys) > 1:
            for poly in polys:
                ctx.add("I-ACC-0017", poly,
                        f"duplicate POLYGON_NUMBER '{number}' ({len(polys)} polygons)",
                        table="FOREST_COVER_OBJECT", field="POLYGON_NUMBER",
                        value=number, source="Access 17")


@rule
def required_fco_fields(ctx: RuleContext) -> None:
    required = (
        "INVENTORY_STANDARD_CODE", "INTERPRETER", "PROJECT_NAME",
        "REFERENCE_YEAR", "INTERPRETATION_DATE",
    )
    for poly in ctx.dataset.polygons:
        row = poly.fco
        missing = [field_name for field_name in required if not text(row.get(field_name))]
        if missing:
            ctx.add("E-FCO-P-0005", poly,
                    "minimum data set is incomplete: " + ", ".join(missing),
                    table="FOREST_COVER_OBJECT",
                    source="rules 1.3 / minimum data set")
        area = to_float(row.get("POLYGON_AREA"))
        spatial_area = to_float(row.get("GEOMETRY_Area"))
        if not (area or 0) > 0 and not (spatial_area or 0) > 0:
            ctx.add("E-VCP-Z-0020", poly, "POLYGON_AREA must be greater than zero",
                    table="FOREST_COVER_OBJECT", field="POLYGON_AREA",
                    value=row.get("POLYGON_AREA"), source="rules 2.1.1")
        if not (spatial_area or 0) > 0:
            ctx.add("E-VCP-Z-0010", poly,
                    "polygon has no spatial geometry (GEOMETRY_Area is empty/0)",
                    table="FOREST_COVER_OBJECT", field="GEOMETRY_Area",
                    value=row.get("GEOMETRY_Area"), source="rules 2.1.0 / Access 33")


@rule
def fco_code_values(ctx: RuleContext) -> None:
    fields = (
        "DISTURBANCE_TYPE_CODE", "DISTURBANCE_CODE",
        "DATA_CAPTURE_METHOD_CODE", "FREE_TO_GROW_IND",
    )
    for poly in ctx.dataset.polygons:
        standard = text(poly.fco.get("INVENTORY_STANDARD_CODE"))
        if standard and standard not in {"F", "I", "V"}:
            ctx.add("E-VCP-Z-0210", poly,
                    f"INVENTORY_STANDARD_CODE '{standard}' is not one of F, I, V",
                    table="FOREST_COVER_OBJECT", field="INVENTORY_STANDARD_CODE",
                    value=standard, source="rules 2.1.26")
        for field_name in fields:
            ctx.code_check(poly, "FOREST_COVER_OBJECT", poly.fco, field_name,
                           code="E-GEN-009", source="rules 7.1")


@rule
def reference_year(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        raw = text(poly.fco.get("REFERENCE_YEAR"))
        if not raw:
            continue
        year = to_int(raw)
        if year is None:
            ctx.add("E-VCP-Z-0230", poly, f"REFERENCE_YEAR '{raw}' is not a year",
                    table="FOREST_COVER_OBJECT", field="REFERENCE_YEAR",
                    value=raw, source="rules 2.1.28")
        elif not (1901 <= year <= ctx.current_year):
            ctx.add("E-VCP-Z-0230", poly,
                    f"REFERENCE_YEAR {year} is outside 1901..{ctx.current_year}",
                    table="FOREST_COVER_OBJECT", field="REFERENCE_YEAR",
                    value=raw, source="rules 2.1.28")


@rule
def dates(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        interp = date_of(poly.fco.get("INTERPRETATION_DATE"))
        expiry = date_of(poly.fco.get("EXPIRY_DATE"))
        if text(poly.fco.get("INTERPRETATION_DATE")) and interp is None:
            ctx.add("E-VCP-Z-0110", poly, "INTERPRETATION_DATE cannot be parsed",
                    table="FOREST_COVER_OBJECT", field="INTERPRETATION_DATE",
                    value=poly.fco.get("INTERPRETATION_DATE"),
                    source="rules 2.1.17a")
        if interp and expiry and expiry < interp:
            ctx.add("W-GEN-012", poly, "EXPIRY_DATE is before INTERPRETATION_DATE",
                    table="FOREST_COVER_OBJECT", field="EXPIRY_DATE",
                    value=poly.fco.get("EXPIRY_DATE"), source="rules 2.1.27")


@rule
def name_hygiene(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        for field_name in ("PROJECT_NAME", "INTERPRETER"):
            value = text(poly.fco.get(field_name))
            if not value:
                continue
            if value != value.strip() or "  " in value:
                ctx.add("W-GEN-013", poly,
                        f"{field_name} has leading/trailing or repeated spaces",
                        table="FOREST_COVER_OBJECT", field=field_name,
                        value=value, source="Access 01 / 02")
