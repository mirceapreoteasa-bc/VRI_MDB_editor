"""Disturbance and opening-related checks."""

from __future__ import annotations

from ..model import text, to_int, year_of
from .engine import RuleContext, rule


@rule
def disturbance_values(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        row = poly.fco
        start = year_of(row.get("DISTURBANCE_START_YEAR")) or to_int(row.get("DISTURBANCE_START_YEAR"))
        end = year_of(row.get("DISTURBANCE_END_YEAR")) or to_int(row.get("DISTURBANCE_END_YEAR"))
        typ = text(row.get("DISTURBANCE_TYPE_CODE"))
        if start is not None and not (1900 <= start <= ctx.current_year):
            ctx.add("W-DSE-R-1510", poly,
                    f"DISTURBANCE_START_YEAR {start} is outside 1900..{ctx.current_year}",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_START_YEAR",
                    value=row.get("DISTURBANCE_START_YEAR"), source="rules 7.1.3a")
        if end is not None and not (1900 <= end <= ctx.current_year):
            ctx.add("W-DSE-R-1530", poly,
                    f"DISTURBANCE_END_YEAR {end} is outside 1900..{ctx.current_year}",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_END_YEAR",
                    value=row.get("DISTURBANCE_END_YEAR"), source="rules 7.1.4a")
        if start is not None and end is not None and end < start:
            ctx.add("W-DSE-R-1520", poly,
                    f"DISTURBANCE_END_YEAR {end} is before DISTURBANCE_START_YEAR {start}",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_END_YEAR",
                    value=row.get("DISTURBANCE_END_YEAR"), source="rules 7.1.3b")
        if typ and not text(row.get("DATA_CAPTURE_METHOD_CODE")):
            ctx.add("W-DSE-R-1490", poly,
                    f"DATA_CAPTURE_METHOD_CODE is required when DISTURBANCE_TYPE_CODE is set ('{typ}')",
                    table="FOREST_COVER_OBJECT", field="DATA_CAPTURE_METHOD_CODE",
                    value=row.get("DATA_CAPTURE_METHOD_CODE"), source="rules 7.1.1")
        if typ and not text(row.get("DISTURBANCE_START_YEAR")):
            ctx.add("W-DSE-R-1500", poly,
                    f"DISTURBANCE_START_YEAR is required when DISTURBANCE_TYPE_CODE is set ('{typ}')",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_START_YEAR",
                    value=row.get("DISTURBANCE_START_YEAR"), source="rules 7.1.2")
        if not text(row.get("DISTURBANCE_START_YEAR")) and text(row.get("DISTURBANCE_END_YEAR")):
            ctx.add("W-DSE-R-1540", poly,
                    "DISTURBANCE_START_YEAR is null but DISTURBANCE_END_YEAR is populated",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_END_YEAR",
                    value=row.get("DISTURBANCE_END_YEAR"), source="rules 7.1.4b")


@rule
def opening_rules(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        row = poly.fco
        opening_id = text(row.get("OPENING_ID"))
        opening_number = text(row.get("OPENING_NUMBER"))
        if opening_number and not opening_id:
            ctx.add("W-OPN-0310", poly,
                    "OPENING_NUMBER is set but OPENING_ID is empty",
                    table="FOREST_COVER_OBJECT", field="OPENING_ID",
                    value=opening_number, source="Access 31")
        if opening_id:
            if not poly.layers:
                ctx.add("W-OPN-0080", poly,
                        "polygon has an OPENING_ID but no tree layer records",
                        table="FOREST_COVER_OBJECT", field="OPENING_ID",
                        value=opening_id, source="Access 08 / 49")
            bclcs5 = text((poly.vcpe or {}).get("BCLCS_LEVEL5_CODE"))
            non_forest = {"LA", "GL", "TZ", "RN", "UR", "GP", "AP", "MI",
                          "RE", "RI", "OC", "MN", "TA", "BR", "RO", "PN",
                          "SI", "LS"}
            if bclcs5 in non_forest:
                ctx.add("W-OPN-0070", poly,
                        f"non-forested polygon (BCLCS L5={bclcs5}) has an OPENING_ID",
                        table="FOREST_COVER_OBJECT", field="OPENING_ID",
                        value=opening_id, source="Access 07")
        else:
            if poly.standard == "I":
                ctx.add("E-OPN-0550", poly,
                        "I-standard polygon has no OPENING_ID",
                        table="FOREST_COVER_OBJECT", field="OPENING_ID",
                        source="Access 55")
