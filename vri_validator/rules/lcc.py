"""Land Cover Component (LCC) checks, including the derived TB/TC/TM rule."""

from __future__ import annotations

from ..derive import treed_class
from ..model import text, to_float, to_int
from .engine import RuleContext, rule

TREED = {"TB", "TC", "TM"}
NO_SMR = {"LA", "RI", "RE", "OC", "GL"}


@rule
def lcc_format(ctx: RuleContext) -> None:
    table = "LAND_COVER_COMPONENT_EST"
    for poly in ctx.dataset.polygons:
        orders = [to_int(r.get("LAND_COVER_ORDER")) for r in poly.lcc]
        present = sorted(o for o in orders if o is not None)
        if poly.lcc and (len(present) != len(orders) or present != list(range(1, len(orders) + 1))):
            ctx.add("E-LCC-Z-1320", poly,
                    f"LAND_COVER_ORDER must be consecutive 1..{len(orders)} (found {orders})",
                    table=table, field="LAND_COVER_ORDER", source="rules 6.1.1")
        for row in poly.lcc:
            ctx.number_check(poly, table, row, "LAND_COVER_ORDER", lo=1, hi=4,
                             integer=True, code="E-LCC-Z-1320",
                             source="rules 6.1.1")
            ctx.number_check(poly, table, row, "COVERAGE_PCT", lo=1, hi=100,
                             integer=True, code="E-LCC-Z-1330",
                             source="rules 6.1.2")
            ctx.code_check(poly, table, row, "LAND_COVER_CLASS_CODE",
                           code="E-LCC-Z-1350", source="rules 6.1.4")
            ctx.code_check(poly, table, row, "SOIL_MOISTURE_REGIME_CODE",
                           code="E-LCC-Z-1340", source="rules 6.1.3")
            ctx.code_check(poly, table, row, "LAND_COVER_LEVEL_CODE",
                           code="E-LCC-Z", source="rules 6.1")


@rule
def lcc_record_rules(ctx: RuleContext) -> None:
    table = "LAND_COVER_COMPONENT_EST"
    for poly in ctx.dataset.polygons:
        for row in poly.lcc:
            coverage = text(row.get("COVERAGE_PCT"))
            smr = text(row.get("SOIL_MOISTURE_REGIME_CODE"))
            klass = text(row.get("LAND_COVER_CLASS_CODE"))
            if coverage and klass and not smr and klass not in NO_SMR:
                ctx.add("E-LCC-R-1360", poly,
                        f"SOIL_MOISTURE_REGIME_CODE is required for LCC class {klass}",
                        table=table, field="SOIL_MOISTURE_REGIME_CODE", value=klass,
                        source="rules 6.1.5")
            if not coverage and (smr or klass):
                ctx.add("E-LCC-R-1360", poly,
                        "COVERAGE_PCT, LAND_COVER_CLASS_CODE and SOIL_MOISTURE_REGIME_CODE "
                        "must be all NULL or all populated",
                        table=table, source="rules 6.1.5")
            if coverage and not klass:
                ctx.add("E-LCC-R-1360", poly,
                        "LAND_COVER_CLASS_CODE is required when COVERAGE_PCT is set",
                        table=table, field="LAND_COVER_CLASS_CODE", source="rules 6.1.5")


@rule
def lcc_collection_rules(ctx: RuleContext) -> None:
    table = "LAND_COVER_COMPONENT_EST"
    for poly in ctx.dataset.polygons:
        lcc = poly.lcc
        if not lcc:
            if poly.standard == "V" and text((poly.vcpe or {}).get("BCLCS_LEVEL1_CODE")) != "U":
                ctx.add("E-LCC-P-1400", poly,
                        "at least one LCC record is required for a V polygon",
                        table=table, source="rules 6.1.6d")
            continue
        pcts = [to_float(r.get("COVERAGE_PCT")) for r in lcc]
        if all(p is not None for p in pcts):
            total = sum(p or 0 for p in pcts)
            if total > 100.0001:
                ctx.add("E-LCC-R-1380", poly,
                        f"LCC coverage totals {total:g}%, over 100%",
                        table=table, field="COVERAGE_PCT", value=f"{total:g}",
                        source="rules 6.1.6b")
            elif abs(total - 100) > 0.0001:
                ctx.add("W-LCC-R-1480", poly,
                        f"LCC coverage totals {total:g}%, not 100%",
                        table=table, field="COVERAGE_PCT", value=f"{total:g}",
                        source="rules 6.1.8")
            values = [p or 0 for p in pcts]
            if values != sorted(values, reverse=True):
                ctx.add("E-LCC-R-1370", poly,
                        f"LCC coverage is not in descending order ({values})",
                        table=table, field="COVERAGE_PCT", source="rules 6.1.6a")
        if len(lcc) > 4:
            ctx.add("E-LCC-R-1390", poly,
                    f"{len(lcc)} LCC records; at most 4 are allowed",
                    table=table, source="rules 6.1.6c")
        pairs = [(text(r.get("LAND_COVER_CLASS_CODE")), text(r.get("SOIL_MOISTURE_REGIME_CODE"))) for r in lcc]
        if len(set(pairs)) != len(pairs):
            ctx.add("E-LCC-P-1480", poly,
                    "duplicate LAND_COVER_CLASS_CODE + SOIL_MOISTURE_REGIME_CODE combination",
                    table=table, source="rules 6.1.7h")
        classes = [c for c, _ in pairs]
        if len(set(classes)) != len(classes):
            ctx.add("W-LCC-0390", poly,
                    "the same LAND_COVER_CLASS_CODE appears with different moisture regimes",
                    table=table, field="LAND_COVER_CLASS_CODE", source="Access 39")


@rule
def lcc_cross_checks(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        lcc = poly.lcc
        classes = [text(r.get("LAND_COVER_CLASS_CODE")) for r in lcc]
        if any(c in TREED for c in classes) and not any(layer.species for layer in poly.layers):
            ctx.add("E-LCC-P-1410", poly,
                    "treed LCC class present but the polygon has no TSE records",
                    table="LAND_COVER_COMPONENT_EST", field="LAND_COVER_CLASS_CODE",
                    source="rules 6.1.7a")
        if not text(v.get("SHRUB_CROWN_CLOSURE")):
            total = sum(to_float(r.get("COVERAGE_PCT")) or 0 for r in lcc
                        if text(r.get("LAND_COVER_CLASS_CODE")) in ("SL", "ST"))
            if total > 20.0001:
                ctx.add("E-LCC-P-1420", poly,
                        f"shrub LCC coverage is {total:g}% but SHRUB_CROWN_CLOSURE is empty",
                        table="LAND_COVER_COMPONENT_EST", source="rules 6.1.7b")
        if not text(v.get("HERB_COVER_PCT")):
            total = sum(to_float(r.get("COVERAGE_PCT")) or 0 for r in lcc
                        if text(r.get("LAND_COVER_CLASS_CODE")) in ("HE", "HF", "HG"))
            if total > 20.0001:
                ctx.add("E-LCC-P-1430", poly,
                        f"herb LCC coverage is {total:g}% but HERB_COVER_PCT is empty",
                        table="LAND_COVER_COMPONENT_EST", source="rules 6.1.7c")
        if not text(v.get("BRYOID_COVER_PCT")):
            total = sum(to_float(r.get("COVERAGE_PCT")) or 0 for r in lcc
                        if text(r.get("LAND_COVER_CLASS_CODE")) in ("BL", "BM", "BY"))
            if total > 20.0001:
                ctx.add("E-LCC-P-1440", poly,
                        f"bryoid LCC coverage is {total:g}% but BRYOID_COVER_PCT is empty",
                        table="LAND_COVER_COMPONENT_EST", source="rules 6.1.7d")
        # 6.1.7g: lake LCC needs a lake non-veg type
        if "LA" in classes:
            types = {text(r.get("NON_VEG_COVER_TYPE_CODE")) for r in poly.nvce}
            if "LA" not in types:
                ctx.add("E-LCC-P-1470", poly,
                        "LCC class LA requires a NON_VEG_COVER_TYPE_CODE = LA record",
                        table="LAND_COVER_COMPONENT_EST", field="LAND_COVER_CLASS_CODE",
                        source="rules 6.1.7g")

        # 6.1.7e/f: part 1 decides warning versus fatal part 2
        has_tse = any(layer.species for layer in poly.live_layers())
        if not has_tse:
            continue
        any_treed = any(c in TREED for c in classes)
        total_cc = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0
                       for layer in poly.live_layers())
        if total_cc < 20 and not any_treed:
            if total_cc >= 5:
                ctx.add("W-LCC-P-1460", poly,
                        f"live tree crown closure is {total_cc:g}% and no TB/TC/TM "
                        "land cover component exists; possible missing treed LCC",
                        table="LAND_COVER_COMPONENT_EST", field="LAND_COVER_CLASS_CODE",
                        value=f"{total_cc:g}", source="rules 6.1.7e/f")
            continue
        derived = derive_treed_class(poly, ctx)
        if derived is None:
            continue
        expected, conifer_share, deciduous_share, unknown_share = derived
        if expected in classes:
            continue
        detail = (f"derived {expected} (conifer {conifer_share:.0%}, "
                  f"deciduous {deciduous_share:.0%})")
        if unknown_share > 0:
            detail += f", {unknown_share:.0%} unknown species"
        ctx.add("E-LCC-P-1450", poly,
                f"{detail} but LCC classes are {classes}",
                table="LAND_COVER_COMPONENT_EST", field="LAND_COVER_CLASS_CODE",
                value=",".join(classes), source="rules 6.1.7e/f")


def derive_treed_class(poly, ctx: RuleContext):
    """Return (expected TB/TC/TM, conifer share, deciduous share, unknown share)."""
    return treed_class(poly, ctx.species_class)
