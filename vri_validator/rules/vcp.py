"""Vegetation Cover Polygon (VCPE) and FCO general attributes."""

from __future__ import annotations

from datetime import datetime

from ..model import date_of, text, to_float, to_int
from .engine import RuleContext, rule

BCLCS1 = {"N", "U", "V"}
BCLCS2 = {"L", "N", "T", "W"}
BCLCS3 = {"A", "U", "W"}
BCLCS4 = {"BI", "BM", "BY", "EL", "HE", "HF", "HG", "RO", "SI", "SL", "ST", "TB", "TC", "TM"}
BCLCS5 = {
    "BE", "BI", "BR", "BU", "CB", "CL", "DE", "ES", "GL", "GP", "LA", "LB", "LL",
    "LS", "MI", "MN", "MU", "MZ", "OC", "OP", "OT", "PN", "RE", "RI", "RM", "RN",
    "RS", "RZ", "SP", "TA", "TZ", "UR",
}
WATER_ROCK = {"LA", "RI", "RE", "OC"}
NO_NUTRIENT = {"LA", "RI", "RE", "OC", "GL", "RZ", "UR", "AP"}
SURFACE_EXPRESSION = {"C", "D", "F", "H", "M", "N", "P", "R", "T", "U"}
MODIFYING_PROCESS = {"A", "B", "F", "N", "U", "V"}
SITE_POSITION = {"C", "D", "F", "L", "M", "T", "U"}
ALPINE = {"A", "N"}
NUTRIENT = {"A", "B", "C", "D", "E", "F"}
HERB_TYPES = {"HE", "HF", "HG"}
STANDARDS = {"F", "I", "V"}


@rule
def vcpe_present_and_codes(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        table = "VEGETATION_COVER_POLYGON_EST"
        code_fields = {
            "NON_PRODUCTIVE_CODE": "E-VCP-Z",
            "NON_PRODUCTIVE_DESCRIPTOR_CODE": "E-VCP-Z-0270",
            "SURFACE_EXPRESSION_CODE": "E-VCP-Z-0360",
            "MODIFYING_PROCESS_CODE": "E-VCP-Z-0380",
            "SITE_POSITION_MESO_CODE": "E-VCP-Z-0400",
            "ALPINE_DESIGNATION_CODE": "E-VCP-Z-0420",
            "SOIL_NUTRIENT_REGIME_CODE": "E-VCP-Z-0440",
            "DATA_SOURCE_ECOSYS_CLASS_CODE": "E-VCP-Z-0460",
            "COVER_PATTERN_CODE": "E-VCP-Z-0160",
            "HERB_COVER_TYPE_CODE": "E-VCP-Z-0170",
            "HERB_COVER_PATTERN_CODE": "E-VCP-Z-0190",
            "BEC_ZONE_CODE": "E-VCP-Z",
        }
        for field_name, code in code_fields.items():
            ctx.code_check(poly, table, v, field_name, code=code,
                           source="rules 2.1.2-2.1.25")
        for field_name, allowed, code in (
            ("BCLCS_LEVEL1_CODE", BCLCS1, "E-VCP-Z-0050"),
            ("BCLCS_LEVEL2_CODE", BCLCS2, "E-VCP-Z-0060"),
            ("BCLCS_LEVEL3_CODE", BCLCS3, "E-VCP-Z-0070"),
            ("BCLCS_LEVEL4_CODE", BCLCS4, "E-VCP-Z-0080"),
            ("BCLCS_LEVEL5_CODE", BCLCS5, "E-VCP-Z-0090"),
        ):
            value = text(v.get(field_name))
            if value and value not in allowed:
                ctx.add(code, poly,
                        f"{field_name} '{value}' is not one of the allowed values",
                        table=table, field=field_name, value=value,
                        source="rules 2.1.11-2.1.15")

        ctx.number_check(poly, table, v, "SHRUB_HEIGHT", lo=0.01, hi=10.0,
                         code="E-VCP-Z-0140", source="rules 2.1.19")
        ctx.number_check(poly, table, v, "SHRUB_CROWN_CLOSURE", lo=1, hi=100,
                         integer=True, code="E-VCP-Z-0150", source="rules 2.1.20")
        ctx.number_check(poly, table, v, "COVER_PATTERN_CODE", lo=1, hi=9,
                         integer=True, code="E-VCP-Z-0160", source="rules 2.1.21")
        ctx.number_check(poly, table, v, "HERB_COVER_PCT", lo=1, hi=100,
                         integer=True, code="E-VCP-Z-0180", source="rules 2.1.23")
        ctx.number_check(poly, table, v, "HERB_COVER_PATTERN_CODE", lo=1, hi=9,
                         integer=True, code="E-VCP-Z-0190", source="rules 2.1.24")
        ctx.number_check(poly, table, v, "BRYOID_COVER_PCT", lo=0, hi=100,
                         integer=True, code="E-VCP-Z-0200", source="rules 2.1.25")
        ctx.number_check(poly, table, v, "VRI_DEAD_STEMS_PER_HA", lo=0, hi=9999,
                         integer=True, code="E-VCP-Z-0030", source="rules 2.1.10")


@rule
def vcpe_required_conditional(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        if poly.standard == "V" and text(v.get("BCLCS_LEVEL1_CODE")) != "U" and poly.layers:
            if not text(v.get("VRI_DEAD_STEMS_PER_HA")):
                ctx.add("E-VCP-P-0040", poly,
                        "VRI_DEAD_STEMS_PER_HA is required for V polygons with tree layers",
                        table="VEGETATION_COVER_POLYGON_EST",
                        field="VRI_DEAD_STEMS_PER_HA", source="rules 2.1.10b")
        if text(v.get("HERB_COVER_PCT")) and not text(v.get("HERB_COVER_TYPE_CODE")):
            ctx.add("E-VCP-Z-0171", poly,
                    "HERB_COVER_TYPE_CODE is required when HERB_COVER_PCT is set",
                    table="VEGETATION_COVER_POLYGON_EST",
                    field="HERB_COVER_TYPE_CODE", source="rules 2.1.22")
        if text(v.get("HERB_COVER_PCT")) and not text(v.get("HERB_COVER_PATTERN_CODE")):
            ctx.add("E-VCP-Z-0191", poly,
                    "HERB_COVER_PATTERN_CODE is required when HERB_COVER_PCT is set",
                    table="VEGETATION_COVER_POLYGON_EST",
                    field="HERB_COVER_PATTERN_CODE", source="rules 2.1.24")


@rule
def interpreter_project_rules(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        for field_name, limit, code in (
            ("INTERPRETER", 30, "E-VCP-Z-0100"),
            ("PROJECT_NAME", 100, "E-VCP-Z-0130"),
        ):
            value = text(poly.fco.get(field_name))
            if value and len(value) > limit:
                ctx.add(code, poly, f"{field_name} exceeds {limit} characters",
                        table="FOREST_COVER_OBJECT", field=field_name,
                        value=value, source="rules 2.1.16 / 2.1.18")
            if value and value != value.upper():
                ctx.add("E-VCP-Z-0105", poly,
                        f"{field_name} must be upper case",
                        table="FOREST_COVER_OBJECT", field=field_name,
                        value=value, source="rules 2.1.16.1 / 2.1.18.1")


@rule
def interpretation_date(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        raw = text(poly.fco.get("INTERPRETATION_DATE"))
        dt = date_of(raw)
        ref = to_int(poly.fco.get("REFERENCE_YEAR"))
        if raw and dt is None:
            ctx.add("E-VCP-Z-0110", poly,
                    "INTERPRETATION_DATE is not a valid date",
                    table="FOREST_COVER_OBJECT", field="INTERPRETATION_DATE",
                    value=raw, source="rules 2.1.17a")
            continue
        if dt is None:
            continue
        if ref is not None and dt.year < ref:
            ctx.add("E-VCP-R-0120", poly,
                    f"INTERPRETATION_DATE {dt.date()} is before REFERENCE_YEAR {ref}",
                    table="FOREST_COVER_OBJECT", field="INTERPRETATION_DATE",
                    value=poly.fco.get("INTERPRETATION_DATE"), source="rules 2.1.17b")
        if dt.date() > date_of("12/31/%d 00:00:00" % ctx.current_year).date():
            ctx.add("E-VCP-R-0120", poly,
                    f"INTERPRETATION_DATE {dt.date()} is in the future",
                    table="FOREST_COVER_OBJECT", field="INTERPRETATION_DATE",
                    value=poly.fco.get("INTERPRETATION_DATE"), source="rules 2.1.17b")
        if text(poly.fco.get("EXPIRY_DATE")):
            ctx.add("E-FCO-R-0220", poly,
                    "EXPIRY_DATE must be NULL",
                    table="FOREST_COVER_OBJECT", field="EXPIRY_DATE",
                    value=poly.fco.get("EXPIRY_DATE"), source="rules 2.1.27")


@rule
def record_level_blocks(ctx: RuleContext) -> None:
    eco_fields = (
        "ALPINE_DESIGNATION_CODE", "MODIFYING_PROCESS_CODE",
        "SITE_POSITION_MESO_CODE", "SURFACE_EXPRESSION_CODE",
        "SOIL_NUTRIENT_REGIME_CODE", "DATA_SOURCE_ECOSYS_CLASS_CODE",
    )
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        vals = [text(v.get(f)) for f in eco_fields]
        if any(vals) and not all(vals):
            ctx.add("E-VCP-R-0240", poly,
                    "ecology codes must be either all NULL or all populated: "
                    + ", ".join(f for f, val in zip(eco_fields, vals) if not val),
                    table="VEGETATION_COVER_POLYGON_EST", source="rules 2.1.29a")

        for fields, code, label in (
            (("SHRUB_HEIGHT", "SHRUB_CROWN_CLOSURE", "COVER_PATTERN_CODE"),
             "E-VCP-R-0250", "shrub"),
            (("HERB_COVER_TYPE_CODE", "HERB_COVER_PCT", "HERB_COVER_PATTERN_CODE"),
             "E-VCP-R-0260", "herb"),
        ):
            vals = [text(v.get(f)) for f in fields]
            if any(vals) and not all(vals):
                ctx.add(code, poly,
                        f"{label} fields must be either all NULL or all populated: "
                        + ", ".join(f for f, val in zip(fields, vals) if not val),
                        table="VEGETATION_COVER_POLYGON_EST", source="rules 2.1.29")


@rule
def total_cover(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        tcl_cc = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0 for layer in poly.layers)
        nvce = sum(to_float(row.get("NON_VEG_COVER_PCT")) or 0 for row in poly.nvce)
        total = (
            tcl_cc
            + (to_float(v.get("SHRUB_CROWN_CLOSURE")) or 0)
            + (to_float(v.get("HERB_COVER_PCT")) or 0)
            + (to_float(v.get("BRYOID_COVER_PCT")) or 0)
            + nvce
        )
        if total > 100.0001:
            ctx.add("W-VCP-P-0300", poly,
                    f"total cover (TCL crown closure + shrub + herb + bryoid + non-veg) is {total:.1f}%, over 100%",
                    table="VEGETATION_COVER_POLYGON_EST", field="CROWN_CLOSURE_PCT",
                    value=f"{total:.1f}", source="rules 2.1.30a")

@rule
def understory_consistency(ctx: RuleContext) -> None:
    checks = (
        ("SHRUB_CROWN_CLOSURE", {"ST", "SL"}, "W-VCP-P-0320",
         "shrub cover is greater than 20% but no ST/SL land cover component is present"),
        ("HERB_COVER_PCT", {"HE", "HF", "HG"}, "W-VCP-P-0330",
         "herb cover is greater than 20% but no HE/HF/HG land cover component is present"),
        ("BRYOID_COVER_PCT", {"BL", "BM", "BY"}, "W-VCP-P-0340",
         "bryoid cover is greater than 20% but no BL/BM/BY land cover component is present"),
    )
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        classes = {text(row.get("LAND_COVER_CLASS_CODE")) for row in poly.lcc}
        for field_name, wanted, code, message in checks:
            value = to_float(v.get(field_name))
            if value is not None and value > 20 and not (classes & wanted) and len(poly.lcc) < 3:
                ctx.add(code, poly, message,
                        table="VEGETATION_COVER_POLYGON_EST", field=field_name,
                        value=v.get(field_name), source="rules 2.1.30c-e")

@rule
def vcpe_input_date(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        raw = text(v.get("INPUT_DATE"))
        if not raw:
            continue
        dt = date_of(raw)
        if dt is None:
            ctx.add("E-VCP-Z-0290", poly,
                    "INPUT_DATE is not a valid date",
                    table="VEGETATION_COVER_POLYGON_EST", field="INPUT_DATE",
                    value=raw, source="rules 2.1.3")
        elif dt.date() >= datetime.now().date():
            ctx.add("E-VCP-Z-0290", poly,
                    f"INPUT_DATE {dt.date()} is not before the current date",
                    table="VEGETATION_COVER_POLYGON_EST", field="INPUT_DATE",
                    value=raw, source="rules 2.1.3")


@rule
def vcpe_conditional_fields(ctx: RuleContext) -> None:
    table = "VEGETATION_COVER_POLYGON_EST"
    for poly in ctx.dataset.polygons:
        v = poly.vcpe
        if v is None:
            continue
        standard = poly.standard
        l1 = text(v.get("BCLCS_LEVEL1_CODE"))
        l5 = text(v.get("BCLCS_LEVEL5_CODE"))
        if standard in ("V", "I") and text(v.get("NON_PRODUCTIVE_DESCRIPTOR_CODE")):
            ctx.add("E-VCP-P-0280", poly,
                    "NON_PRODUCTIVE_DESCRIPTOR_CODE must be NULL for V/I polygons",
                    table=table, field="NON_PRODUCTIVE_DESCRIPTOR_CODE",
                    value=v.get("NON_PRODUCTIVE_DESCRIPTOR_CODE"),
                    source="rules 2.1.2b")
        if standard != "V" or l1 == "U":
            continue
        if l5 not in WATER_ROCK:
            for field_name, code, label in (
                ("SURFACE_EXPRESSION_CODE", "E-VCP-P-0370", "SURFACE_EXPRESSION_CODE"),
                ("MODIFYING_PROCESS_CODE", "E-VCP-P-0390", "MODIFYING_PROCESS_CODE"),
                ("SITE_POSITION_MESO_CODE", "E-VCP-P-0410", "SITE_POSITION_MESO_CODE"),
                ("DATA_SOURCE_ECOSYS_CLASS_CODE", "E-VCP-P-0470", "DATA_SOURCE_ECOSYS_CLASS_CODE"),
            ):
                if not text(v.get(field_name)):
                    ctx.add(code, poly,
                            f"{label} is required for a V polygon with BCLCS level 1 V",
                            table=table, field=field_name,
                            source="rules 2.1.4b/2.1.5b/2.1.6b/2.1.9b")
        if not text(v.get("ALPINE_DESIGNATION_CODE")):
            ctx.add("E-VCP-P-0430", poly,
                    "ALPINE_DESIGNATION_CODE is required for a V polygon with BCLCS level 1 V",
                    table=table, field="ALPINE_DESIGNATION_CODE",
                    source="rules 2.1.7b")
        nutrient = text(v.get("SOIL_NUTRIENT_REGIME_CODE"))
        if l5 not in NO_NUTRIENT:
            if not nutrient:
                ctx.add("E-VCP-P-0450", poly,
                        "SOIL_NUTRIENT_REGIME_CODE is required for this V polygon",
                        table=table, field="SOIL_NUTRIENT_REGIME_CODE",
                        source="rules 2.1.8b")
        elif nutrient != "A":
            ctx.add("E-VCP-P-0450", poly,
                    f"SOIL_NUTRIENT_REGIME_CODE must be 'A' for BCLCS level 5 {l5}",
                    table=table, field="SOIL_NUTRIENT_REGIME_CODE",
                    value=nutrient, source="rules 2.1.8b")


@rule
def alpine_crown_closure(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        if text(v.get("ALPINE_DESIGNATION_CODE")) != "A":
            continue
        total = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0
                    for layer in poly.layers)
        if total > 10.0001:
            ctx.add("E-VCP-P-0310", poly,
                    f"alpine polygon has total crown closure {total:g}%; expected <= 10%",
                    table="TREE_COVER_LAYER_ESTIMATED", field="CROWN_CLOSURE_PCT",
                    value=f"{total:g}", source="rules 2.1.30b")


@rule
def understory_bclcs_consistency(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        if poly.standard != "V" or text(v.get("BCLCS_LEVEL1_CODE")) != "V":
            continue
        total_cc = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0
                       for layer in poly.layers)
        if total_cc >= 10:
            continue
        shrub = to_float(v.get("SHRUB_CROWN_CLOSURE")) or 0
        herb = to_float(v.get("HERB_COVER_PCT")) or 0
        bryoid = to_float(v.get("BRYOID_COVER_PCT")) or 0
        average = (shrub + herb + bryoid) / 3
        l2 = text(v.get("BCLCS_LEVEL2_CODE"))
        l4 = text(v.get("BCLCS_LEVEL4_CODE"))
        if shrub > 20:
            expected = {"ST", "SL"}
        elif herb > 20:
            expected = {"HE", "HF", "HG"}
        elif shrub > average:
            expected = {"ST", "SL"}
        elif herb > average:
            expected = {"HE", "HF", "HG"}
        elif bryoid > average:
            expected = {"BY", "BM", "BL"}
        elif shrub == herb == bryoid and shrub > 0:
            expected = {"ST", "SL"}
        elif total_cc >= 5 and l2 == "T":
            expected = {"TC", "TB", "TM"}
        elif shrub > 0:
            expected = {"ST", "SL"}
        elif herb > 0:
            expected = {"HE", "HF", "HG"}
        elif bryoid > 0:
            expected = {"BY", "BM", "BL"}
        else:
            continue
        if l4 not in expected:
            ctx.add("E-VCP-P-0350", poly,
                    f"BCLCS_LEVEL4_CODE '{l4}' does not match the dominant understory "
                    f"(shrub {shrub:g}%, herb {herb:g}%, bryoid {bryoid:g}%)",
                    table="VEGETATION_COVER_POLYGON_EST", field="BCLCS_LEVEL4_CODE",
                    value=l4, source="rules 2.1.30f")
