"""Non-Vegetative Cover Estimated (NVCE) checks."""

from __future__ import annotations

from ..model import text, to_float, to_int
from .engine import RuleContext, rule


@rule
def nvce_format(ctx: RuleContext) -> None:
    table = "NON_VEGETATIVE_COVER_EST"
    for poly in ctx.dataset.polygons:
        orders = [to_int(r.get("NON_VEG_ORDER")) for r in poly.nvce]
        present = sorted(o for o in orders if o is not None)
        # Accepted VRI files sometimes start non-veg numbering at 2 or 3, so only
        # require uniqueness and no gaps after the first value (not necessarily 1).
        expected = list(range(present[0], present[0] + len(orders))) if present else []
        if poly.nvce and (len(present) != len(orders) or present != expected):
            ctx.add("E-NVC-ORDER", poly,
                    f"NON_VEG_ORDER must be unique and consecutive (found {orders})",
                    table=table, field="NON_VEG_ORDER", value=orders,
                    source="rules 5.1.6c")
        for row in poly.nvce:
            ctx.number_check(poly, table, row, "NON_VEG_ORDER", lo=1, hi=9,
                             integer=True, code="E-NVC-Z-1250",
                             source="rules 5.1.6c")
            ctx.number_check(poly, table, row, "NON_VEG_COVER_PCT", lo=1, hi=100,
                             integer=True, code="E-NVC-Z-1260",
                             source="rules 5.1.2")
            ctx.code_check(poly, table, row, "COVER_PATTERN_CODE",
                           code="E-NVC-Z-1270", source="rules 5.1.3")
            ctx.code_check(poly, table, row, "NON_VEG_COVER_TYPE_CODE",
                           code="E-NVC-Z-1280", source="rules 5.1.4")
            ctx.code_check(poly, table, row, "LAYER_LEVEL_CODE",
                           code="E-NVC-Z", source="rules 5.1")
            for field_name in ("NON_VEG_ORDER", "NON_VEG_COVER_PCT",
                               "COVER_PATTERN_CODE", "NON_VEG_COVER_TYPE_CODE"):
                if not text(row.get(field_name)):
                    ctx.add("E-NVC-R-1290", poly,
                            f"{field_name} is required for a non-veg record",
                            table=table, field=field_name, source="rules 5.1.5a")


@rule
def nvce_collection(ctx: RuleContext) -> None:
    table = "NON_VEGETATIVE_COVER_EST"
    for poly in ctx.dataset.polygons:
        rows = poly.nvce
        if not rows:
            continue
        pcts = [to_float(r.get("NON_VEG_COVER_PCT")) for r in rows]
        if all(p is not None for p in pcts):
            values = [p or 0 for p in pcts]
            if values != sorted(values, reverse=True):
                ctx.add("E-NVC-R-1300", poly,
                        f"NON_VEG_COVER_PCT is not in descending order ({values})",
                        table=table, field="NON_VEG_COVER_PCT", value=values,
                        source="rules 5.1.5b")
        pairs = [(text(r.get("NON_VEG_COVER_TYPE_CODE")), text(r.get("COVER_PATTERN_CODE")))
                 for r in rows]
        if len(set(pairs)) != len(pairs):
            ctx.add("E-NVC-DUP", poly,
                    "duplicate NON_VEG_COVER_TYPE_CODE + COVER_PATTERN_CODE combination",
                    table=table, source="rules 5.1.6b")
        classes = {text(r.get("LAND_COVER_CLASS_CODE")) for r in poly.lcc}
        unmatched = []
        for row in rows:
            if (to_float(row.get("NON_VEG_COVER_PCT")) or 0) >= 20:
                typ = text(row.get("NON_VEG_COVER_TYPE_CODE"))
                if typ and typ not in classes:
                    unmatched.append(typ)
        if unmatched:
            ctx.add("W-NVC-P-1310", poly,
                    "significant non-veg cover has no matching LCC record: "
                    + ", ".join(sorted(set(unmatched))),
                    table=table, field="NON_VEG_COVER_TYPE_CODE",
                    value=", ".join(sorted(set(unmatched))),
                    source="rules 5.1.6")
