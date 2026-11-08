"""Dead-layer rule: when are snags large enough to require a D-layer description?

Two interchangeable rules (Tools > Dead-layer rule):
  "stems100": dead stems per hectare (VRI_DEAD_STEMS_PER_HA) >= 100   (default)
  "pct30":    dead stems >= 30 % of the live layer density (VRI_LIVE_STEMS_PER_HA)

When the rule is met and the polygon has no dead (D) layer, a description is needed.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

RULES = {
    "stems100": "Snags >= 100 stems/ha",
    "pct30": "Snags >= 30% of live density",
}
DEFAULT_RULE = "stems100"
CODE = "E-ACC-0035"


def _float(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def dead_layer_message(vcpe: dict[str, Any], layers: Iterable[dict[str, Any]],
                       rule: str = DEFAULT_RULE) -> Optional[str]:
    """Return the message when a D-layer description is needed, otherwise None."""
    snags = _float((vcpe or {}).get("VRI_DEAD_STEMS_PER_HA"))
    if snags is None or snags <= 0:
        return None
    layers = list(layers)
    if any(str(layer.get("LAYER_LEVEL_CODE", "")).strip().upper() == "D" for layer in layers):
        return None
    if rule == "pct30":
        live = [_float(layer.get("VRI_LIVE_STEMS_PER_HA")) for layer in layers
                if str(layer.get("LAYER_LEVEL_CODE", "")).strip().upper() != "D"]
        live = [value for value in live if value and value > 0]
        if not live:
            return None
        density = live[0]
        if snags < 0.30 * density:
            return None
        return (f"dead stems {snags:g}/ha are {100 * snags / density:.0f}% of live density "
                f"{density:g}/ha but there is no D-layer description")
    if snags < 100:
        return None
    return f"VRI_DEAD_STEMS_PER_HA is {snags:g} but there is no D-layer description"
