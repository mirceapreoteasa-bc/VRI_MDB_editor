"""Additional checks derived from the Access query library (QUERIESforMDBpgdb)."""

from __future__ import annotations

from ..model import text, to_float, to_int
from .engine import RuleContext, rule

WATER = {"LA", "RI", "RE", "OC", "GL"}


@rule
def density_and_crown_closure(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            cc = to_float(layer.row.get("CROWN_CLOSURE_PCT"))
            stems = to_float(layer.row.get("VRI_LIVE_STEMS_PER_HA"))
            if cc is not None and cc > 0 and not layer.species:
                ctx.add("E-ACC-0041", poly,
                        "crown closure is set but the layer has no species records",
                        table="TREE_COVER_LAYER_ESTIMATED", field="CROWN_CLOSURE_PCT",
                        layer=layer, source="Access 41")
            if cc is not None and cc > 0 and stems is not None and stems == 0:
                ctx.add("W-ACC-0012", poly,
                        "live stems per hectare = 0 while crown closure > 0",
                        table="TREE_COVER_LAYER_ESTIMATED",
                        field="VRI_LIVE_STEMS_PER_HA", layer=layer,
                        source="Access 12")
            ba = to_float(layer.row.get("BASAL_AREA"))
            lead = layer.species[0] if layer.species else None
            age = to_float(lead.get("AGE")) if lead else None
            height = to_float(lead.get("HEIGHT")) if lead else None
            if (ba is not None and ba < 5 and cc is not None and cc >= 40
                    and age is not None and age >= 20 and height is not None and height > 10):
                ctx.add("W-ACC-0022", poly,
                        f"unlikely basal area {ba:g} with crown closure {cc:g}, age {age:g}, height {height:g}",
                        table="TREE_COVER_LAYER_ESTIMATED", field="BASAL_AREA",
                        layer=layer, source="Access 22")
            if height is not None and height < 2 and text(lead.get("DATA_SOURCE_HEIGHT_CODE")) == "22":
                ctx.add("W-ACC-0011", poly,
                        f"height {height:g} m with DATA_SOURCE_HEIGHT_CODE 22",
                        table="TREE_SPECIES_ESTIMATED", field="HEIGHT",
                        layer=layer, species=lead, source="Access 11")


@rule
def free_to_grow(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if poly.standard == "I" and text(poly.fco.get("FREE_TO_GROW_IND")).upper() == "Y":
            ctx.add("E-ACC-0040", poly,
                    "I-standard polygon has FREE_TO_GROW_IND = Y",
                    table="FOREST_COVER_OBJECT", field="FREE_TO_GROW_IND",
                    value=poly.fco.get("FREE_TO_GROW_IND"), source="Access 40")


@rule
def non_veg_layer_level(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        levels = [text(r.get("LAYER_LEVEL_CODE")) for r in poly.nvce]
        for row, level in zip(poly.nvce, levels):
            if not level:
                ctx.add("E-ACC-0023", poly,
                        "non-veg record has no LAYER_LEVEL_CODE",
                        table="NON_VEGETATIVE_COVER_EST", field="LAYER_LEVEL_CODE",
                        source="Access 23")
        populated = [l for l in levels if l]
        if len(set(populated)) != len(populated):
            ctx.add("E-ACC-0024", poly,
                    f"duplicate LAYER_LEVEL_CODE in non-veg records ({populated})",
                    table="NON_VEGETATIVE_COVER_EST", field="LAYER_LEVEL_CODE",
                    source="Access 24")
        for row in poly.nvce:
            if text(row.get("NON_VEG_COVER_TYPE_CODE")) == "OT":
                ctx.add("W-ACC-0025", poly,
                        "non-veg cover type is OT (other)",
                        table="NON_VEGETATIVE_COVER_EST",
                        field="NON_VEG_COVER_TYPE_CODE", source="Access 25")


@rule
def bclcs_and_lcc_warnings(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        v = poly.vcpe or {}
        if text(v.get("BCLCS_LEVEL1_CODE")) == "U":
            empty = not (poly.layers or poly.lcc or poly.nvce)
            missing_minimum = not (text(poly.fco.get("PROJECT_NAME"))
                                   and text(poly.fco.get("REFERENCE_YEAR")))
            if not (empty and missing_minimum):
                ctx.add("W-ACC-0026", poly,
                        "BCLCS level 1 = U (unknown) is unusual in VRI",
                        table="VEGETATION_COVER_POLYGON_EST", field="BCLCS_LEVEL1_CODE",
                        value="U", source="Access 26")
        l5 = text(v.get("BCLCS_LEVEL5_CODE"))
        if l5 in ("LA", "RI", "RE", "OC"):
            expected = {"SITE_POSITION_MESO_CODE": "D",
                        "SURFACE_EXPRESSION_CODE": "D",
                        "MODIFYING_PROCESS_CODE": "N"}
            for field_name, want in expected.items():
                got = text(v.get(field_name))
                if got != want:
                    ctx.add("E-ACC-0005", poly,
                            f"water polygon should have {field_name} = {want} (found '{got}')",
                            table="VEGETATION_COVER_POLYGON_EST", field=field_name,
                            value=got, source="Access 05")
        for row in poly.lcc:
            klass = text(row.get("LAND_COVER_CLASS_CODE"))
            smr = text(row.get("SOIL_MOISTURE_REGIME_CODE"))
            if klass in WATER and smr:
                ctx.add("W-ACC-0006", poly,
                        f"LCC class {klass} should have a NULL moisture regime",
                        table="LAND_COVER_COMPONENT_EST",
                        field="SOIL_MOISTURE_REGIME_CODE", value=smr,
                        source="Access 06")
            if klass == "RZ" and smr and (to_int(smr) or 0) > 2:
                ctx.add("W-ACC-0027", poly,
                        f"road LCC has moisture regime {smr} (>2)",
                        table="LAND_COVER_COMPONENT_EST",
                        field="SOIL_MOISTURE_REGIME_CODE", value=smr,
                        source="Access 27")


@rule
def layer_structure_warnings(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if poly.layers and poly.layers[0].is_dead:
            ctx.add("W-ACC-0032", poly,
                    "layer 1 is a D-layer; a live layer 1 is normally required",
                    table="TREE_COVER_LAYER_ESTIMATED", field="LAYER_LEVEL_CODE",
                    layer=poly.layers[0], source="Access 32")
        for layer in poly.live_layers():
            lead = layer.species[0] if layer.species else None
            age = to_float(lead.get("AGE")) if lead else None
            vc = text(layer.row.get("VERTICAL_COMPLEXITY_CODE"))
            if age is not None and age < 30 and vc and vc != "1":
                ctx.add("W-ACC-0013", poly,
                        f"non-uniform vertical complexity ({vc}) for age {age:g} < 30",
                        table="TREE_COVER_LAYER_ESTIMATED",
                        field="VERTICAL_COMPLEXITY_CODE", value=vc,
                        layer=layer, source="Access 13")


@rule
def dead_layer_density(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        dead_stems = to_float((poly.vcpe or {}).get("VRI_DEAD_STEMS_PER_HA"))
        for layer in poly.layers:
            if not layer.is_dead:
                continue
            live_stems = to_float(layer.row.get("VRI_LIVE_STEMS_PER_HA"))
            if (live_stems is not None and dead_stems is not None
                    and abs(live_stems - dead_stems) > 1e-9):
                ctx.add("E-ACC-0010", poly,
                        f"D-layer live stems per ha ({live_stems:g}) does not match "
                        f"VRI_DEAD_STEMS_PER_HA ({dead_stems:g})",
                        table="TREE_COVER_LAYER_ESTIMATED",
                        field="VRI_LIVE_STEMS_PER_HA", layer=layer,
                        source="Access 10")


@rule
def no_opening_data_sources(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        if text(poly.fco.get("OPENING_ID")):
            continue
        for layer in poly.layers:
            checks = (
                ("DATA_SOURCE_INTERPRETED_CODE", layer.row, layer, None),
                ("DATA_SRC_VRI_LIVE_STEM_HA_CODE", layer.row, layer, None),
                ("DATA_SOURCE_BASAL_AREA_CODE", layer.row, layer, None),
            )
            for field_name, row, target_layer, target_species in checks:
                value = text(row.get(field_name))
                if value in ("7", "11"):
                    ctx.add("W-OPN-0090", poly,
                            f"no OPENING_ID but a layer has {field_name} {value}",
                            table="TREE_COVER_LAYER_ESTIMATED",
                            field=field_name, value=value, layer=target_layer,
                            source="Access 09")
            for sp in layer.species:
                for field_name in ("DATA_SOURCE_AGE_CODE", "DATA_SOURCE_HEIGHT_CODE"):
                    value = text(sp.get(field_name))
                    if value in ("7", "11"):
                        ctx.add("W-OPN-0090", poly,
                                f"no OPENING_ID but a species has {field_name} {value}",
                                table="TREE_SPECIES_ESTIMATED",
                                field=field_name, value=value, layer=layer,
                                species=sp, source="Access 09")


@rule
def misc_access_warnings(ctx: RuleContext) -> None:
    odd_disturbance = {"C", "F", "I", "P", "S", "W"}
    non_preferred = {"F", "FD", "B", "H", "L", "P", "PL", "S", "A", "E"}
    for poly in ctx.dataset.polygons:
        row = poly.fco
        v = poly.vcpe or {}
        typ = text(row.get("DISTURBANCE_TYPE_CODE"))
        if typ in odd_disturbance:
            ctx.add("W-ACC-0028", poly,
                    f"disturbance type {typ} is unusual (verify the disturbance code)",
                    table="FOREST_COVER_OBJECT", field="DISTURBANCE_TYPE_CODE",
                    value=typ, source="Access 28")
        if not text(row.get("OPENING_ID")) and typ == "L":
            ctx.add("W-ACC-0043", poly,
                    "logged polygon has no OPENING_ID (OK only on private land)",
                    table="FOREST_COVER_OBJECT", field="OPENING_ID",
                    source="Access 43")
        if text(row.get("REFERENCE_YEAR")) and text(v.get("REFERENCE_YEAR")):
            if text(row.get("REFERENCE_YEAR")) != text(v.get("REFERENCE_YEAR")):
                ctx.add("W-ACC-0038", poly,
                        "FOREST_COVER_OBJECT and VEGETATION_COVER_POLYGON_EST "
                        "REFERENCE_YEAR values differ",
                        table="VEGETATION_COVER_POLYGON_EST", field="REFERENCE_YEAR",
                        value=v.get("REFERENCE_YEAR"), source="Access 38")
        dead_stems = to_float(v.get("VRI_DEAD_STEMS_PER_HA"))
        if dead_stems is not None and dead_stems >= 100 and not any(
                layer.is_dead for layer in poly.layers):
            ctx.add("E-ACC-0035", poly,
                    f"VRI_DEAD_STEMS_PER_HA is {dead_stems:g} but there is no D-layer",
                    table="VEGETATION_COVER_POLYGON_EST",
                    field="VRI_DEAD_STEMS_PER_HA", value=v.get("VRI_DEAD_STEMS_PER_HA"),
                    source="Access 35")
        for layer in poly.layers:
            if not text(layer.row.get("DATA_SOURCE_INTERPRETED_CODE")):
                if not (poly.standard in ("V", "I") and (layer.order or 0) != 0):
                    ctx.add("W-ACC-0034", poly,
                            "DATA_SOURCE_INTERPRETED_CODE is NULL",
                            table="TREE_COVER_LAYER_ESTIMATED",
                            field="DATA_SOURCE_INTERPRETED_CODE", layer=layer,
                            source="Access 34")
            lead = layer.species[0] if layer.species else None
            if lead is None:
                continue
            code = text(lead.get("TREE_SPECIES_CODE"))
            if code in non_preferred:
                ctx.add("I-ACC-0019", poly,
                        f"species code '{code}' is non-preferred/incomplete",
                        table="TREE_SPECIES_ESTIMATED", field="TREE_SPECIES_CODE",
                        value=code, layer=layer, species=lead, source="Access 19")
            if text(row.get("OPENING_ID")):
                si = to_float(layer.row.get("ESTIMATED_SITE_INDEX"))
                age = to_float(lead.get("AGE"))
                order = to_int(lead.get("SPECIES_ORDER"))
                if (si is not None and si < 10 and age is not None and age < 25
                        and order == 1):
                    ctx.add("W-ACC-0050", poly,
                            f"unlikely site index {si:g} with leading age {age:g}",
                            table="TREE_COVER_LAYER_ESTIMATED",
                            field="ESTIMATED_SITE_INDEX", layer=layer,
                            species=lead, source="Access 50")


@rule
def shrub_height_landcover(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        height = to_float((poly.vcpe or {}).get("SHRUB_HEIGHT"))
        if height is None:
            continue
        classes = {text(row.get("LAND_COVER_CLASS_CODE")) for row in poly.lcc}
        if height > 1.9 and "ST" not in classes and "SL" in classes:
            ctx.add("W-ACC-0044", poly,
                    f"shrub height {height:g} m is tall but only SL land cover is present",
                    table="VEGETATION_COVER_POLYGON_EST", field="SHRUB_HEIGHT",
                    value=height, source="Access 44")
        if height < 2 and "ST" in classes and "SL" not in classes:
            ctx.add("W-ACC-0044", poly,
                    f"shrub height {height:g} m is low but only ST land cover is present",
                    table="VEGETATION_COVER_POLYGON_EST", field="SHRUB_HEIGHT",
                    value=height, source="Access 44")


@rule
def likely_photo_year(ctx: RuleContext) -> None:
    counts: dict[int, int] = {}
    for poly in ctx.dataset.polygons:
        year = to_int(poly.fco.get("REFERENCE_YEAR"))
        if year is not None:
            counts[year] = counts.get(year, 0) + 1
    if not counts:
        return
    likely = max(counts, key=lambda y: (counts[y], y))
    for poly in ctx.dataset.polygons:
        year = to_int(poly.fco.get("REFERENCE_YEAR"))
        if year is None or year <= likely:
            continue
        for layer in poly.layers:
            if (text(layer.row.get("DATA_SOURCE_INTERPRETED_CODE")) == "0"
                    and text(layer.row.get("DATA_SOURCE_BASAL_AREA_CODE")) == "0"
                    and text(layer.row.get("DATA_SRC_VRI_LIVE_STEM_HA_CODE")) == "0"):
                ctx.add("W-ACC-0004", poly,
                        f"REFERENCE_YEAR {year} is later than the likely photo year {likely} "
                        "but all layer data sources are 0",
                        table="TREE_COVER_LAYER_ESTIMATED",
                        field="DATA_SOURCE_INTERPRETED_CODE", value="0",
                        layer=layer, source="Access 04")


@rule
def possible_missed_layers(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        for layer in poly.layers:
            if len(layer.species) < 2:
                continue
            first, second = layer.species[0], layer.species[1]
            age1 = to_float(first.get("AGE"))
            age2 = to_float(second.get("AGE"))
            hgt1 = to_float(first.get("HEIGHT"))
            hgt2 = to_float(second.get("HEIGHT"))
            if None in (age1, age2, hgt1, hgt2):
                continue
            if abs(age1 - age2) >= 40 and abs(hgt1 - hgt2) >= 10:
                ctx.add("W-ACC-0046", poly,
                        f"species 1 and 2 in layer {layer.order} differ strongly "
                        f"(age {age1:g}/{age2:g}, height {hgt1:g}/{hgt2:g}); "
                        "a layer may be missing",
                        table="TREE_SPECIES_ESTIMATED", field="AGE",
                        layer=layer, species=first, source="Access 46")


@rule
def possible_extra_layers(ctx: RuleContext) -> None:
    for poly in ctx.dataset.polygons:
        live = sorted(poly.live_layers(), key=lambda l: l.order or 0)
        if len(live) < 2:
            continue
        first, second = live[0], live[1]
        sp1 = first.species[0] if first.species else None
        sp2 = second.species[0] if second.species else None
        if sp1 is None or sp2 is None:
            continue
        if (text(sp1.get("DATA_SOURCE_AGE_CODE")) in ("7", "11")
                or text(sp1.get("DATA_SOURCE_HEIGHT_CODE")) in ("7", "11")
                or text(sp2.get("DATA_SOURCE_AGE_CODE")) in ("7", "11")
                or text(sp2.get("DATA_SOURCE_HEIGHT_CODE")) in ("7", "11")):
            continue
        age1 = to_float(sp1.get("AGE"))
        age2 = to_float(sp2.get("AGE"))
        hgt1 = to_float(sp1.get("HEIGHT"))
        hgt2 = to_float(sp2.get("HEIGHT"))
        if None in (age1, age2, hgt1, hgt2):
            continue
        if abs(age1 - age2) < 40 and (hgt1 - hgt2) < 10:
            ctx.add("W-ACC-0047", poly,
                    f"layer 1 and layer 2 leading species are similar "
                    f"(age {age1:g}/{age2:g}, height {hgt1:g}/{hgt2:g}); "
                    "one layer may be extra",
                    table="TREE_SPECIES_ESTIMATED", field="AGE",
                    layer=first, species=sp1, source="Access 47")
