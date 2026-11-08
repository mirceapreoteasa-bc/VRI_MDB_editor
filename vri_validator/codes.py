"""Code tables from the VRIMS codes.xml file."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_CODES = Path(__file__).resolve().parent / "data" / "codes.xml"
DEFAULT_SPECIES_MAX = Path(__file__).resolve().parent / "data" / "species_max.json"

# (table, column) -> code table name in codes.xml
FIELD_CODES: dict[tuple[str, str], str] = {
    ("FOREST_COVER_OBJECT", "INVENTORY_STANDARD_CODE"): "INVENTORY_STANDARD_CODE",
    ("FOREST_COVER_OBJECT", "DISTURBANCE_TYPE_CODE"): "DISTURBANCE_TYPE_CODE",
    ("FOREST_COVER_OBJECT", "DISTURBANCE_CODE"): "DISTURBANCE_CODE",
    ("FOREST_COVER_OBJECT", "DATA_CAPTURE_METHOD_CODE"): "DATA_CAPTURE_METHOD_CODE",
    ("FOREST_COVER_OBJECT", "FREE_TO_GROW_IND"): "FREE_TO_GROW_IND",
    ("VEGETATION_COVER_POLYGON_EST", "NON_PRODUCTIVE_CODE"): "NON_PRODUCTIVE_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "NON_PRODUCTIVE_DESCRIPTOR_CODE"): "NON_PRODUCTIVE_DESCRIPTOR_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "SURFACE_EXPRESSION_CODE"): "SURFACE_EXPRESSION_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "MODIFYING_PROCESS_CODE"): "MODIFYING_PROCESS_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "SITE_POSITION_MESO_CODE"): "SITE_POSITION_MESO_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "ALPINE_DESIGNATION_CODE"): "ALPINE_DESIGNATION_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "SOIL_NUTRIENT_REGIME_CODE"): "SOIL_NUTRIENT_REGIME_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "DATA_SOURCE_ECOSYS_CLASS_CODE"): "DATA_SOURCE_ECOSYS_CLASS_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BCLCS_LEVEL1_CODE"): "BCLCS_LEVEL1_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BCLCS_LEVEL2_CODE"): "BCLCS_LEVEL2_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BCLCS_LEVEL3_CODE"): "BCLCS_LEVEL3_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BCLCS_LEVEL4_CODE"): "BCLCS_LEVEL4_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BCLCS_LEVEL5_CODE"): "BCLCS_LEVEL5_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "COVER_PATTERN_CODE"): "COVER_PATTERN_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "HERB_COVER_TYPE_CODE"): "HERB_COVER_TYPE_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "HERB_COVER_PATTERN_CODE"): "COVER_PATTERN_CODE",
    ("VEGETATION_COVER_POLYGON_EST", "BEC_ZONE_CODE"): "BEC_ZONE_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "LAYER_LEVEL_CODE"): "LAYER_LEVEL_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "NON_FOREST_DESCRIPTOR_CODE"): "NON_FOREST_DESCRIPTOR_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "DATA_SOURCE_INTERPRETED_CODE"): "DATA_SOURCE_INTERPRETED_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "TREE_SPECIES_CODE"): "TREE_SPECIES_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "DATA_SOURCE_BASAL_AREA_CODE"): "DATA_SOURCE_BASAL_AREA_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "DATA_SRC_VRI_LIVE_STEM_HA_CODE"): "DATA_SRC_VRI_LIVE_STEM_HA_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "COVER_PATTERN_CODE"): "COVER_PATTERN_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "VERTICAL_COMPLEXITY_CODE"): "VERTICAL_COMPLEXITY_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "ESTIMATED_SINDEX_SOURCE_CODE"): "ESTIMATED_SINDEX_SOURCE_CODE",
    ("TREE_COVER_LAYER_ESTIMATED", "FOREST_COVER_RANK_CODE"): "FOREST_COVER_RANK_CODE",
    ("TREE_SPECIES_ESTIMATED", "TREE_SPECIES_CODE"): "TREE_SPECIES_CODE",
    ("TREE_SPECIES_ESTIMATED", "DATA_SOURCE_AGE_CODE"): "DATA_SOURCE_AGE_CODE",
    ("TREE_SPECIES_ESTIMATED", "DATA_SOURCE_HEIGHT_CODE"): "DATA_SOURCE_HEIGHT_CODE",
    ("LAND_COVER_COMPONENT_EST", "LAND_COVER_CLASS_CODE"): "LAND_COVER_CLASS_CODE",
    ("LAND_COVER_COMPONENT_EST", "SOIL_MOISTURE_REGIME_CODE"): "SOIL_MOISTURE_REGIME_CODE",
    ("LAND_COVER_COMPONENT_EST", "LAND_COVER_LEVEL_CODE"): "LAND_COVER_LEVEL_CODE",
    ("NON_VEGETATIVE_COVER_EST", "NON_VEG_COVER_TYPE_CODE"): "NON_VEG_COVER_TYPE_CODE",
    ("NON_VEGETATIVE_COVER_EST", "COVER_PATTERN_CODE"): "COVER_PATTERN_CODE",
    ("NON_VEGETATIVE_COVER_EST", "LAYER_LEVEL_CODE"): "LAYER_LEVEL_CODE",
}


# Values listed in the V2.0.0 rule document but absent from some codes.xml builds.
EXTRA_CODES: dict[str, dict[str, str]] = {
    "ESTIMATED_SINDEX_SOURCE_CODE": {
        "M": "Site index source M (legacy code list)",
        "O": "Site index source O (legacy code list)",
    },
}


class CodeBook:
    def __init__(self, path: str | Path = DEFAULT_CODES):
        self.path = Path(path)
        self.tables: dict[str, dict[str, str]] = {}
        root = ET.parse(self.path).getroot()
        for table in root.findall("table"):
            name = table.get("name") or ""
            self.tables[name] = {
                (code.get("key") or "").strip(): (code.get("desc") or "").strip()
                for code in table.findall("code")
            }
        for name, extra in EXTRA_CODES.items():
            self.tables.setdefault(name, {}).update(extra)

    def table_for(self, table: str, column: str) -> str | None:
        return FIELD_CODES.get((table, column))

    def valid(self, table: str, column: str, value: str) -> bool:
        code_table = self.table_for(table, column)
        if code_table is None:
            return True
        return value in self.tables.get(code_table, {})

    def desc(self, table: str, column: str, value: str) -> str:
        code_table = self.table_for(table, column)
        if code_table is None:
            return ""
        return self.tables.get(code_table, {}).get(value, "")

    def codes(self, code_table: str) -> dict[str, str]:
        return self.tables.get(code_table, {})


def load_species_max(path: str | Path = DEFAULT_SPECIES_MAX) -> dict[str, dict[str, float | None]]:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
