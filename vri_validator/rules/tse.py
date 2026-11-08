"""Tree Species Estimated (TSE) checks."""

from __future__ import annotations

from ..model import text, to_float, to_int
from .engine import RuleContext, rule

def _is_d_layer(layer) -> bool:
    return layer.level.upper() == "D"


@rule
def species_format(ctx: RuleContext) -> None:
    table = "TREE_SPECIES_ESTIMATED"
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            orders = [to_int(sp.get("SPECIES_ORDER")) for sp in layer.species]
            present = sorted(o for o in orders if o is not None)
            if orders and (len(present) != len(orders) or present != list(range(1, len(orders) + 1))):
                ctx.add("E-TSP-Z-0910", poly,
                        f"SPECIES_ORDER must be consecutive 1..{len(orders)} (found {orders})",
                        table=table, field="SPECIES_ORDER", layer=layer,
                        source="rules 4.1.1")
            for sp in layer.species:
                order = to_int(sp.get("SPECIES_ORDER"))
                if order is not None and not (1 <= order <= 6):
                    ctx.add("E-TSP-Z-0910", poly,
                            f"SPECIES_ORDER {order} is outside 1..6",
                            table=table, field="SPECIES_ORDER", layer=layer,
                            species=sp, source="rules 4.1.1")
                ctx.code_check(poly, table, sp, "TREE_SPECIES_CODE",
                               code="E-TSP-Z-0990", source="rules 4.1.2")
                ctx.number_check(poly, table, sp, "SPECIES_PCT", lo=1, hi=100,
                                 integer=True, code="E-TSP-Z-1000",
                                 source="rules 4.1.3")
                ctx.number_check(poly, table, sp, "AGE", lo=1, hi=999,
                                 code="E-TSP-Z-1010", source="rules 4.1.4a")
                ctx.number_check(poly, table, sp, "HEIGHT", lo=0.01, hi=99.99,
                                 code="E-TSP-Z-1080", source="rules 4.1.5a")
                ctx.code_check(poly, table, sp, "DATA_SOURCE_AGE_CODE",
                               code="E-TSP-Z-1140", source="rules 4.1.6a")
                ctx.code_check(poly, table, sp, "DATA_SOURCE_HEIGHT_CODE",
                               code="E-TSP-Z-1160", source="rules 4.1.7a")


@rule
def species_required_and_pairs(ctx: RuleContext) -> None:
    table = "TREE_SPECIES_ESTIMATED"
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            dead = _is_d_layer(layer)
            for sp in layer.species:
                order = to_int(sp.get("SPECIES_ORDER")) or 0
                # 4.1.8a: order / code / pct are mandatory
                for field_name in ("SPECIES_ORDER", "TREE_SPECIES_CODE", "SPECIES_PCT"):
                    if not text(sp.get(field_name)):
                        ctx.add("E-TSP-R-1180", poly,
                                f"{field_name} is required for a species record",
                                table=table, field=field_name, layer=layer,
                                species=sp, source="rules 4.1.8a")
                age = text(sp.get("AGE"))
                height = text(sp.get("HEIGHT"))
                if bool(age) != bool(height):
                    ctx.add("E-TSP-R-1190", poly,
                            "AGE and HEIGHT must both be NULL or both be populated",
                            table=table, layer=layer, species=sp,
                            source="rules 4.1.8b")

                if poly.standard == "V" and dead and order == 1:
                    if not age:
                        ctx.add("E-TSP-P-1040", poly,
                                "AGE is required for the leading species of a V D-layer",
                                table=table, field="AGE", layer=layer,
                                species=sp, source="rules 4.1.4d")
                    if not height:
                        ctx.add("E-TSP-P-1110", poly,
                                "HEIGHT is required for the leading species of a V D-layer",
                                table=table, field="HEIGHT", layer=layer,
                                species=sp, source="rules 4.1.5d")
                    for field_name in ("AGE", "HEIGHT", "BASAL_AREA",
                                       "VRI_LIVE_STEMS_PER_HA"):
                        target = layer.row if field_name in (
                            "BASAL_AREA", "VRI_LIVE_STEMS_PER_HA") else sp
                        if not text(target.get(field_name)):
                            ctx.add("E-TSP-R-1240", poly,
                                    f"{field_name} is required for the leading species of a D-layer",
                                    table=table if target is sp else "TREE_COVER_LAYER_ESTIMATED",
                                    field=field_name, layer=layer,
                                    species=sp if target is sp else None,
                                    source="rules 4.1.9e")
                elif poly.standard == "V" and not dead and order in (1, 2):
                    if not age:
                        ctx.add("E-TSP-P-1020", poly,
                                f"AGE is required for species order {order}",
                                table=table, field="AGE", layer=layer,
                                species=sp, source="rules 4.1.4b")
                    if not height:
                        ctx.add("E-TSP-P-1090", poly,
                                f"HEIGHT is required for species order {order}",
                                table=table, field="HEIGHT", layer=layer,
                                species=sp, source="rules 4.1.5b")
                elif poly.standard == "I" and order == 1:
                    if not age:
                        ctx.add("E-TSP-P-1020", poly,
                                "AGE is required for species order 1",
                                table=table, field="AGE", layer=layer,
                                species=sp, source="rules 4.1.4c")
                    if not height:
                        ctx.add("E-TSP-P-1100", poly,
                                "HEIGHT is required for species order 1",
                                table=table, field="HEIGHT", layer=layer,
                                species=sp, source="rules 4.1.5c")
                if order not in (1, 2):
                    if age:
                        ctx.add("E-TSP-R-1050", poly,
                                f"AGE must be NULL for species order {order}",
                                table=table, field="AGE", layer=layer,
                                species=sp, source="rules 4.1.4e")
                    if height:
                        ctx.add("E-TSP-R-1120", poly,
                                f"HEIGHT must be NULL for species order {order}",
                                table=table, field="HEIGHT", layer=layer,
                                species=sp, source="rules 4.1.5e")
                if order == 1:
                    if not text(sp.get("DATA_SOURCE_AGE_CODE")):
                        ctx.add("E-TSP-P-1150", poly,
                                "DATA_SOURCE_AGE_CODE is required for species order 1",
                                table=table, field="DATA_SOURCE_AGE_CODE",
                                layer=layer, species=sp, source="rules 4.1.6b")
                    if not text(sp.get("DATA_SOURCE_HEIGHT_CODE")):
                        ctx.add("E-TSP-P-1170", poly,
                                "DATA_SOURCE_HEIGHT_CODE is required for species order 1",
                                table=table, field="DATA_SOURCE_HEIGHT_CODE",
                                layer=layer, species=sp, source="rules 4.1.7b")


@rule
def species_collection(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            if not layer.species:
                continue
            pcts = [to_float(sp.get("SPECIES_PCT")) for sp in layer.species]
            if all(p is not None for p in pcts):
                total = sum(p or 0 for p in pcts)
                if abs(total - 100) > 0.01:
                    ctx.add("E-TSP-R-1200", poly,
                            f"species percentages total {total:g}%, expected 100%",
                            table="TREE_SPECIES_ESTIMATED", field="SPECIES_PCT",
                            layer=layer, source="rules 4.1.9a")
                values = [p or 0 for p in pcts]
                if values != sorted(values, reverse=True):
                    ctx.add("E-TSP-R-1210", poly,
                            f"species percentages are not in descending order ({values})",
                            table="TREE_SPECIES_ESTIMATED", field="SPECIES_PCT",
                            layer=layer, source="rules 4.1.9b")
            # duplicate handled in tcl.py; collected here too for the code number
            seen: set[str] = set()
            for sp in layer.species:
                code = text(sp.get("TREE_SPECIES_CODE"))
                if code and code in seen:
                    ctx.add("E-TCL-R-0580", poly,
                            f"duplicate species code '{code}' in the same layer",
                            table="TREE_SPECIES_ESTIMATED", field="TREE_SPECIES_CODE",
                            value=code, layer=layer, species=sp,
                            source="rules 3.1.16")
                seen.add(code)


@rule
def species_age_height(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        smr = text(v.get("SOIL_NUTRIENT_REGIME_CODE"))
        for layer in poly.layers:
            ba = to_float(layer.row.get("BASAL_AREA"))
            for sp in layer.species:
                age = to_float(sp.get("AGE"))
                height = to_float(sp.get("HEIGHT"))
                if age is not None and height is not None and height > 0:
                    ratio = age / height
                    if ratio <= 0.6:
                        ctx.add("E-TSP-R-1060", poly,
                                f"invalid age/height combination (age {age:g}, height {height:g})",
                                table="TREE_SPECIES_ESTIMATED", layer=layer,
                                species=sp, source="rules 4.1.4f")
                    elif ratio >= 30.0:
                        ctx.add("S-TSP-R-0960", poly,
                                f"critical: check age/height combination (age {age:g}, height {height:g})",
                                table="TREE_SPECIES_ESTIMATED", layer=layer,
                                species=sp, source="rules 4.1.10e")
                if age is not None and age > 500:
                    ctx.add("W-TSP-R-1070", poly,
                            f"AGE {age:g} > 500; verify for possible inconsistency",
                            table="TREE_SPECIES_ESTIMATED", field="AGE",
                            layer=layer, species=sp, source="rules 4.1.4g")
                if height is not None and height > 80:
                    ctx.add("W-TSP-R-1130", poly,
                            f"HEIGHT {height:g} m is unusually high",
                            table="TREE_SPECIES_ESTIMATED", field="HEIGHT",
                            layer=layer, species=sp, source="rules 4.1.5f")
                if height is not None and ba is not None and height < 15 and ba > 50:
                    ctx.add("W-TSP-P-0920", poly,
                            f"unlikely height/basal area combination (height {height:g}, BA {ba:g})",
                            table="TREE_SPECIES_ESTIMATED", layer=layer,
                            species=sp, source="rules 4.1.10a")
                if age is not None and height is not None:
                    if age > 300 and height < 20 and smr in ("D", "E"):
                        ctx.add("W-TSP-P-0930", poly,
                                f"unlikely age/height/soil combination (age {age:g}, height {height:g}, SMR {smr})",
                                table="TREE_SPECIES_ESTIMATED", layer=layer,
                                species=sp, source="rules 4.1.10b")
                    if age < 60 and height > 40 and smr in ("A", "B"):
                        ctx.add("W-TSP-P-0940", poly,
                                f"unlikely age/height/soil combination (age {age:g}, height {height:g}, SMR {smr})",
                                table="TREE_SPECIES_ESTIMATED", layer=layer,
                                species=sp, source="rules 4.1.10c")
                    if age > 20 and height < 0.1:
                        ctx.add("W-TSP-P-0950", poly,
                                f"leading species height is questionable with age (age {age:g}, height {height:g})",
                                table="TREE_SPECIES_ESTIMATED", layer=layer,
                                species=sp, source="rules 4.1.10d")
                # species maximum age/height table from the Access queries
                code = text(sp.get("TREE_SPECIES_CODE"))
                maximum = ctx.species_max.get(code)
                if maximum:
                    max_age = maximum.get("age")
                    max_height = maximum.get("height")
                    if age is not None and max_age and age > max_age:
                        ctx.add("W-TSP-0210", poly,
                                f"AGE {age:g} exceeds the known maximum {max_age:g} for species {code}",
                                table="TREE_SPECIES_ESTIMATED", field="AGE",
                                layer=layer, species=sp, source="Access 21")
                    if height is not None and max_height and height > max_height:
                        ctx.add("W-TSP-0210", poly,
                                f"HEIGHT {height:g} exceeds the known maximum {max_height:g} for species {code}",
                                table="TREE_SPECIES_ESTIMATED", field="HEIGHT",
                                layer=layer, species=sp, source="Access 21")

@rule
def layer_age_height_consistency(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        live = sorted(poly.live_layers(), key=lambda l: l.order or 0)
        if len(live) < 2:
            continue
        first, second = live[0], live[1]
        sp1 = first.species[0] if first.species else None
        sp2 = second.species[0] if second.species else None
        age1 = to_float(sp1.get("AGE")) if sp1 else None
        age2 = to_float(sp2.get("AGE")) if sp2 else None
        hgt1 = to_float(sp1.get("HEIGHT")) if sp1 else None
        hgt2 = to_float(sp2.get("HEIGHT")) if sp2 else None
        if age1 is not None and age2 is not None and age1 > 120 and age2 > 120:
            ctx.add("E-TSP-R-1220", poly,
                    f"both layer 1 and layer 2 leading species ages exceed 120 ({age1:g}, {age2:g})",
                    table="TREE_SPECIES_ESTIMATED", field="AGE",
                    layer=first, species=sp1, source="rules 4.1.9c")
        if hgt1 is not None and hgt2 is not None and hgt1 <= hgt2:
            ctx.add("E-TSP-R-1230", poly,
                    f"layer 1 leading height {hgt1:g} is not greater than layer 2 leading height {hgt2:g}",
                    table="TREE_SPECIES_ESTIMATED", field="HEIGHT",
                    layer=first, species=sp1, source="rules 4.1.9d")
