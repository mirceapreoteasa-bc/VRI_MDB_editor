"""Tree Cover Layer (TCL) checks."""

from __future__ import annotations

from ..model import Layer, text, to_float, to_int
from .engine import RuleContext, rule


def _first_species(layer: Layer) -> dict[str, str] | None:
    return layer.species[0] if layer.species else None


@rule
def layer_order(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if not poly.layers:
            continue
        orders = [layer.order for layer in poly.layers]
        present = sorted(o for o in orders if o is not None)
        if len(present) != len(orders) or present != list(range(1, len(orders) + 1)):
            ctx.add("E-TCL-R-0660", poly,
                    f"LAYER_ORDER must be consecutive 1..{len(orders)} (found {orders})",
                    table="TREE_COVER_LAYER_ESTIMATED", field="LAYER_ORDER",
                    source="rules 3.1.1b")
        for layer in poly.layers:
            ctx.number_check(poly, "TREE_COVER_LAYER_ESTIMATED", layer.row,
                             "LAYER_ORDER", lo=1, hi=9, integer=True,
                             code="E-TCL-Z-0650", source="rules 3.1.1a",
                             label="LAYER_ORDER")
        dead = [layer for layer in poly.layers if layer.is_dead]
        if len(dead) > 1:
            ctx.add("E-TCL-R-0700", poly,
                    f"{len(dead)} D-layers; only one is allowed",
                    table="TREE_COVER_LAYER_ESTIMATED", field="LAYER_LEVEL_CODE",
                    source="rules 3.1.1f")
        if dead:
            last = max(poly.layers, key=lambda l: l.order or 0)
            if not last.is_dead:
                for layer in dead:
                    ctx.add("E-TCL-R-0690", poly,
                            "D-layer must be the last LAYER_ORDER",
                            table="TREE_COVER_LAYER_ESTIMATED",
                            field="LAYER_LEVEL_CODE", layer=layer,
                            source="rules 3.1.1e")
        if len(poly.layers) == 1 and poly.layers[0].order == -1:
            ctx.add("E-TCL-R-0670", poly,
                    "a single TCL must not have LAYER_ORDER = -1",
                    table="TREE_COVER_LAYER_ESTIMATED", field="LAYER_ORDER",
                    layer=poly.layers[0], source="rules 3.1.1c")
        for layer in poly.layers:
            if layer.order == -1 and text(layer.row.get("FOREST_COVER_RANK_CODE")):
                ctx.add("E-TCL-R-0730", poly,
                        "FOREST_COVER_RANK_CODE must be NULL when LAYER_ORDER is -1",
                        table="TREE_COVER_LAYER_ESTIMATED",
                        field="FOREST_COVER_RANK_CODE", layer=layer,
                        source="rules 3.1.2c")


@rule
def layer_codes_and_ranges(ctx: RuleContext) -> None:
    table = "TREE_COVER_LAYER_ESTIMATED"
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            ctx.code_check(poly, table, layer.row, "LAYER_LEVEL_CODE",
                           code="E-TCL-Z", source="rules 3.1.2")
            ctx.code_check(poly, table, layer.row, "NON_FOREST_DESCRIPTOR_CODE",
                           code="E-TCL-Z", source="rules 3.1.2")
            ctx.code_check(poly, table, layer.row, "DATA_SOURCE_INTERPRETED_CODE",
                           code="E-TCL-Z-0740", source="rules 3.1.3a")
            ctx.code_check(poly, table, layer.row, "TREE_SPECIES_CODE",
                           code="E-TCL-Z-0760", source="rules 3.1.4a")
            ctx.code_check(poly, table, layer.row, "ESTIMATED_SINDEX_SOURCE_CODE",
                           code="E-TCL-Z-0800", source="rules 3.1.6a")
            ctx.code_check(poly, table, layer.row, "DATA_SOURCE_BASAL_AREA_CODE",
                           code="E-TCL-Z-0890", source="rules 3.1.9a")
            ctx.code_check(poly, table, layer.row, "DATA_SRC_VRI_LIVE_STEM_HA_CODE",
                           code="E-TCL-Z-0500", source="rules 3.1.11a")
            ctx.code_check(poly, table, layer.row, "COVER_PATTERN_CODE",
                           code="E-TCL-Z-0520", source="rules 3.1.12a")
            ctx.code_check(poly, table, layer.row, "VERTICAL_COMPLEXITY_CODE",
                           code="E-TCL-Z-0540", source="rules 3.1.13a")
            ctx.code_check(poly, table, layer.row, "FOREST_COVER_RANK_CODE",
                           code="E-TCL-Z-0710", source="rules 3.1.2a")

            ctx.number_check(poly, table, layer.row, "CROWN_CLOSURE_PCT", lo=1, hi=100,
                             integer=True, code="E-TCL-Z-0830",
                             source="rules 3.1.7a")
            ctx.number_check(poly, table, layer.row, "BASAL_AREA", lo=0, hi=200,
                             code="E-TCL-Z-0870", source="rules 3.1.8a")
            ctx.number_check(poly, table, layer.row, "VRI_LIVE_STEMS_PER_HA", lo=0,
                             hi=50000, code="E-TCL-Z-0480", source="rules 3.1.10a")
            ctx.number_check(poly, table, layer.row, "ESTIMATED_SITE_INDEX", lo=2,
                             hi=99, integer=True, code="E-TCL-Z-0780",
                             source="rules 3.1.5a")
            ctx.number_check(poly, table, layer.row, "COVER_PATTERN_CODE", lo=1, hi=9,
                             integer=True, code="E-TCL-Z-0520",
                             source="rules 3.1.12a")
            ctx.number_check(poly, table, layer.row, "VERTICAL_COMPLEXITY_CODE", lo=1,
                             hi=5, integer=True, code="E-TCL-Z-0540",
                             source="rules 3.1.13a")

            # 3.1.2b: at most one layer may carry rank 1
        rank_one = [layer for layer in poly.layers
                    if text(layer.row.get("FOREST_COVER_RANK_CODE")) == "1"]
        if len(rank_one) > 1:
            for layer in rank_one:
                ctx.add("E-TCL-R-0720", poly,
                        "more than one TCL has FOREST_COVER_RANK_CODE = 1",
                        table=table, field="FOREST_COVER_RANK_CODE",
                        layer=layer, source="rules 3.1.2b")


@rule
def layer_conditional_requirements(ctx: RuleContext) -> None:
    table = "TREE_COVER_LAYER_ESTIMATED"
    for poly in ctx.dataset.polygons:
        first_dead = False
        for layer in poly.layers:
            order = layer.order or 0
            first = _first_species(layer)
            age = to_float(first.get("AGE")) if first else None
            live_tree = not layer.is_dead and bool(layer.species)
            if poly.standard in ("V", "I") and order != 0:
                if not text(layer.row.get("DATA_SOURCE_INTERPRETED_CODE")):
                    ctx.add("E-TCL-P-0750", poly,
                            "DATA_SOURCE_INTERPRETED_CODE is required for V/I layers",
                            table=table, field="DATA_SOURCE_INTERPRETED_CODE",
                            layer=layer, source="rules 3.1.3b")
            if age is not None and age < 30:
                for field_name, code in (
                    ("TREE_SPECIES_CODE", "E-TCL-P-0770"),
                    ("ESTIMATED_SITE_INDEX", "E-TCL-P-0790"),
                    ("ESTIMATED_SINDEX_SOURCE_CODE", "E-TCL-P-0810"),
                ):
                    if not text(layer.row.get(field_name)):
                        ctx.add(code, poly,
                                f"{field_name} is required when the leading species age is < 30",
                                table=table, field=field_name, layer=layer,
                                source="rules 3.1.4b/3.1.5b/3.1.6b")
            if poly.standard in ("V", "I") and text(layer.row.get("ESTIMATED_SINDEX_SOURCE_CODE")) == "M":
                ctx.add("E-TCL-P-0820", poly,
                        "ESTIMATED_SINDEX_SOURCE_CODE must not be M for V/I polygons",
                        table=table, field="ESTIMATED_SINDEX_SOURCE_CODE",
                        value="M", layer=layer, source="rules 3.1.6c")
            if poly.standard in ("V", "I") and live_tree:
                for field_name, code in (
                    ("CROWN_CLOSURE_PCT", "E-TCL-P-0860"),
                    ("COVER_PATTERN_CODE", "E-TCL-P-0530"),
                ):
                    if not text(layer.row.get(field_name)):
                        ctx.add(code, poly,
                                f"{field_name} is required for a V/I live tree layer",
                                table=table, field=field_name, layer=layer,
                                source="rules 3.1.7d/3.1.12b")
                if not text(layer.row.get("VERTICAL_COMPLEXITY_CODE")):
                    ctx.add("E-TCL-P-0550", poly,
                            "VERTICAL_COMPLEXITY_CODE is required for a V/I live tree layer",
                            table=table, field="VERTICAL_COMPLEXITY_CODE",
                            layer=layer, source="rules 3.1.13b")
            if poly.standard == "V" and live_tree:
                for field_name, code in (
                    ("BASAL_AREA", "E-TCL-P-0880"),
                    ("VRI_LIVE_STEMS_PER_HA", "E-TCL-P-0490"),
                ):
                    if not text(layer.row.get(field_name)):
                        ctx.add(code, poly,
                                f"{field_name} is required for a V live tree layer",
                                table=table, field=field_name, layer=layer,
                                source="rules 3.1.8b/3.1.10b")
            if text(layer.row.get("BASAL_AREA")) and not text(layer.row.get("DATA_SOURCE_BASAL_AREA_CODE")):
                ctx.add("E-TCL-R-0900", poly,
                        "DATA_SOURCE_BASAL_AREA_CODE is required when BASAL_AREA is set",
                        table=table, field="DATA_SOURCE_BASAL_AREA_CODE", layer=layer,
                        source="rules 3.1.9b")
            if text(layer.row.get("VRI_LIVE_STEMS_PER_HA")) and not text(layer.row.get("DATA_SRC_VRI_LIVE_STEM_HA_CODE")):
                ctx.add("E-TCL-R-0510", poly,
                        "DATA_SRC_VRI_LIVE_STEM_HA_CODE is required when VRI_LIVE_STEMS_PER_HA is set",
                        table=table, field="DATA_SRC_VRI_LIVE_STEM_HA_CODE", layer=layer,
                        source="rules 3.1.11b")

            # 3.1.14: all-or-none of species / site index / source
            trio = [text(layer.row.get(f)) for f in
                    ("TREE_SPECIES_CODE", "ESTIMATED_SITE_INDEX", "ESTIMATED_SINDEX_SOURCE_CODE")]
            if any(trio) and not all(trio):
                ctx.add("E-TCL-R-0560", poly,
                        "TREE_SPECIES_CODE, ESTIMATED_SITE_INDEX and "
                        "ESTIMATED_SINDEX_SOURCE_CODE must be all NULL or all populated",
                        table=table, layer=layer, source="rules 3.1.14")

            # 3.1.15: leading species must have age > 0 and height
            if layer.species:
                lead = max(layer.species, key=lambda s: to_float(s.get("SPECIES_PCT")) or 0)
                if not (to_float(lead.get("AGE")) or 0) > 0 or not text(lead.get("HEIGHT")):
                    ctx.add("E-TCL-R-0570", poly,
                            "the highest-percentage species must have AGE > 0 and a HEIGHT",
                            table="TREE_SPECIES_ESTIMATED", layer=layer,
                            species=lead, source="rules 3.1.15")

            # 3.1.16: duplicate species within a layer
            seen: dict[str, dict[str, str]] = {}
            for sp in layer.species:
                code = text(sp.get("TREE_SPECIES_CODE"))
                if not code:
                    continue
                if code in seen:
                    ctx.add("E-TCL-R-0580", poly,
                            f"duplicate species code '{code}' in the same layer",
                            table="TREE_SPECIES_ESTIMATED", field="TREE_SPECIES_CODE",
                            value=code, layer=layer, species=sp, source="rules 3.1.16")
                else:
                    seen[code] = sp


@rule
def layer_warnings(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        smr = text(v.get("SOIL_NUTRIENT_REGIME_CODE"))
        alpine = text(v.get("ALPINE_DESIGNATION_CODE"))
        for layer in poly.layers:
            si = to_float(layer.row.get("ESTIMATED_SITE_INDEX"))
            if si is not None and si > 26 and smr in ("A", "B"):
                ctx.add("W-TCL-P-0590", poly,
                        f"unlikely site index {si:g} with soil nutrient regime {smr}",
                        table="TREE_COVER_LAYER_ESTIMATED", field="ESTIMATED_SITE_INDEX",
                        layer=layer, source="rules 3.1.17a")
            if si is not None and si < 12 and smr in ("D", "E"):
                ctx.add("W-TCL-P-0600", poly,
                        f"unlikely site index {si:g} with soil nutrient regime {smr}",
                        table="TREE_COVER_LAYER_ESTIMATED", field="ESTIMATED_SITE_INDEX",
                        layer=layer, source="rules 3.1.17b")
            if si is not None and si < 20 and alpine == "A" and smr == "A":
                ctx.add("W-TCL-P-0610", poly,
                        "unlikely site index / alpine designation combination (SI < 20, Alpine A, SMR A)",
                        table="TREE_COVER_LAYER_ESTIMATED", field="ESTIMATED_SITE_INDEX",
                        layer=layer, source="rules 3.1.17c")
            if si is not None and si < 5 and alpine == "N":
                ctx.add("W-TCL-P-0620", poly,
                        "unlikely site index / alpine designation combination (SI < 5, Alpine N)",
                        table="TREE_COVER_LAYER_ESTIMATED", field="ESTIMATED_SITE_INDEX",
                        layer=layer, source="rules 3.1.17d")
            if layer.level.upper() == "S":
                ctx.add("W-TCL-R-0630", poly, "S-layers have been deprecated",
                        table="TREE_COVER_LAYER_ESTIMATED", field="LAYER_LEVEL_CODE",
                        layer=layer, source="rules 3.1.17e")
        dead = [l for l in poly.layers if l.is_dead]
        if len(poly.layers) == 1 and dead and not text(dead[0].row.get("ESTIMATED_SITE_INDEX")):
            ctx.add("W-TCL-R-0640", poly,
                    "a single D-layer should have an ESTIMATED_SITE_INDEX",
                    table="TREE_COVER_LAYER_ESTIMATED", field="ESTIMATED_SITE_INDEX",
                    layer=dead[0], source="rules 3.1.17f")

@rule
def layer_crown_closure_totals(ctx: RuleContext) -> None:
    table = "TREE_COVER_LAYER_ESTIMATED"
    for poly in ctx.dataset.polygons:
        if not poly.layers:
            continue
        live_total = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0
                         for layer in poly.live_layers())
        dead_total = sum(to_float(layer.row.get("CROWN_CLOSURE_PCT")) or 0
                         for layer in poly.layers if layer.is_dead)
        if live_total > 100.0001:
            ctx.add("E-TCL-R-0850", poly,
                    f"non-dead layer crown closure totals {live_total:g}%, over 100%",
                    table=table, field="CROWN_CLOSURE_PCT",
                    value=f"{live_total:g}", source="rules 3.1.7b/c")
        if dead_total and live_total + dead_total > 200.0001:
            ctx.add("E-TCL-R-0850", poly,
                    f"all-layer crown closure totals {live_total + dead_total:g}%, over 200%",
                    table=table, field="CROWN_CLOSURE_PCT",
                    value=f"{live_total + dead_total:g}", source="rules 3.1.7c")
