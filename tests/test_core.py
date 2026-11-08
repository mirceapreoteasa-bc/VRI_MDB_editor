import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vri_validator.codes import DEFAULT_CODES, DEFAULT_SPECIES_MAX, CodeBook, load_species_max
from vri_validator.derive import (
    bclcs_levels,
    derive_updates,
    lcc_order_updates,
    rank_updates,
    treed_class,
)
from vri_validator.model import TABLES, Dataset, Layer, Polygon, load_dataset, year_of
from vri_validator.report import write_csv, write_html
from vri_validator.rules.access_queries import bclcs_and_lcc_warnings
from vri_validator.rules.engine import Finding, Findings, RuleContext
from vri_validator.rules.lcc import lcc_cross_checks
from vri_validator.species import species_type, species_types

class CodeBookTests(unittest.TestCase):
    def setUp(self):
        self.codes = CodeBook(DEFAULT_CODES)

    def test_codes_load(self):
        self.assertGreaterEqual(len(self.codes.tables), 50)
        self.assertTrue(self.codes.valid("FOREST_COVER_OBJECT", "INVENTORY_STANDARD_CODE", "V"))
        self.assertFalse(self.codes.valid("FOREST_COVER_OBJECT", "INVENTORY_STANDARD_CODE", "Q"))

    def test_species_classification(self):
        types = species_types(self.codes)
        self.assertEqual(species_type(types, "FDC"), "conifer")
        self.assertEqual(species_type(types, "EP"), "deciduous")
        self.assertEqual(species_type(types, "ZZZ"), "unknown")

    def test_species_max(self):
        data = load_species_max(DEFAULT_SPECIES_MAX)
        self.assertGreater(len(data), 100)


class DateTests(unittest.TestCase):
    def test_two_digit_years_pivot_to_past(self):
        self.assertEqual(year_of("01/01/68 00:00:00"), 1968)
        self.assertEqual(year_of("05/29/61 23:00:00"), 1961)
        self.assertEqual(year_of("2010"), 2010)


class LowCrownClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes = CodeBook(DEFAULT_CODES)
        cls.species_max = load_species_max(DEFAULT_SPECIES_MAX)

    def _rule_codes(self, crown_closure):
        vcpe = {
            "SHRUB_CROWN_CLOSURE": "100",
            "HERB_COVER_PCT": "0",
            "BRYOID_COVER_PCT": "0",
        }
        layer = Layer(
            row={
                "CROWN_CLOSURE_PCT": str(crown_closure),
                "BASAL_AREA": "1",
                "LAYER_LEVEL_CODE": "1",
                "LAYER_ORDER": "1",
            },
            species=[{
                "TREE_SPECIES_CODE": "FDC",
                "SPECIES_PCT": "100",
                "SPECIES_ORDER": "1",
            }],
        )
        polygon = Polygon(
            fid=1,
            fco={
                "INVENTORY_STANDARD_CODE": "V",
                "POLYGON_NUMBER": "1",
            },
            vcpe=vcpe,
            layers=[layer],
            lcc=[{"LAND_COVER_CLASS_CODE": "SL", "COVERAGE_PCT": "100"}],
        )
        dataset = Dataset(
            path="/tmp/fake.mdb",
            polygons=[polygon],
            orphans={},
            row_counts={},
        )
        ctx = RuleContext(
            dataset=dataset,
            codes=self.codes,
            species_types=species_types(self.codes),
            species_max=self.species_max,
        )
        lcc_cross_checks(ctx)
        return {finding.code for finding in ctx.findings.items}

    def test_low_crown_closure_is_suppressed(self):
        self.assertNotIn("W-LCC-P-1460", self._rule_codes(2))

    def test_five_percent_still_warns(self):
        self.assertIn("W-LCC-P-1460", self._rule_codes(5))


class DeriveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.types = species_types(CodeBook(DEFAULT_CODES))

    def _classify(self, code):
        return self.types.get(code, "unknown")

    def _polygon(self, *, layers=None, vcpe=None, lcc=None, nvce=None,
                 standard="V", number="1"):
        return Polygon(
            fid=1,
            fco={"INVENTORY_STANDARD_CODE": standard, "POLYGON_NUMBER": number},
            vcpe=vcpe or {},
            layers=layers or [],
            lcc=lcc or [],
            nvce=nvce or [],
        )

    def _layer(self, layer_id, closure, species, order=1):
        return Layer(
            row={
                "TREE_COVER_LAYER_ESTIMATED_ID": str(layer_id),
                "CROWN_CLOSURE_PCT": str(closure),
                "BASAL_AREA": "20",
                "LAYER_LEVEL_CODE": "1",
                "LAYER_ORDER": str(order),
            },
            species=[{
                "TREE_SPECIES_CODE": code,
                "SPECIES_PCT": str(pct),
                "SPECIES_ORDER": str(index),
            } for index, (code, pct) in enumerate(species, 1)],
        )

    def test_coniferous_treed(self):
        poly = self._polygon(
            layers=[self._layer(1, 35, [("FDC", 100)])],
            vcpe={"SHRUB_CROWN_CLOSURE": "0", "HERB_COVER_PCT": "0",
                  "BRYOID_COVER_PCT": "0", "ALPINE_DESIGNATION_CODE": "N"},
            lcc=[{"LAND_COVER_CLASS_CODE": "TC", "COVERAGE_PCT": "100"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("V", "T", "U", "TC", "OP"))

    def test_mixed_treed(self):
        poly = self._polygon(
            layers=[self._layer(1, 35, [("FDC", 70), ("DR", 30)])],
            vcpe={"SHRUB_CROWN_CLOSURE": "0", "HERB_COVER_PCT": "0",
                  "BRYOID_COVER_PCT": "0", "ALPINE_DESIGNATION_CODE": "N"},
            lcc=[{"LAND_COVER_CLASS_CODE": "TM", "COVERAGE_PCT": "100"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("V", "T", "U", "TM", "OP"))

    def test_tall_shrub(self):
        poly = self._polygon(
            vcpe={"SHRUB_CROWN_CLOSURE": "30", "SHRUB_HEIGHT": "3",
                  "HERB_COVER_PCT": "0", "BRYOID_COVER_PCT": "0",
                  "ALPINE_DESIGNATION_CODE": "N"},
            lcc=[{"LAND_COVER_CLASS_CODE": "ST", "COVERAGE_PCT": "100"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("V", "N", "U", "ST", "OP"))

    def test_water(self):
        poly = self._polygon(
            vcpe={"ALPINE_DESIGNATION_CODE": "N"},
            nvce=[{"NON_VEG_COVER_TYPE_CODE": "LA", "NON_VEG_COVER_PCT": "60"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("N", "W", "W", "", "LA"))

    def test_land_rock(self):
        poly = self._polygon(
            vcpe={"ALPINE_DESIGNATION_CODE": "N"},
            nvce=[{"NON_VEG_COVER_TYPE_CODE": "BR", "NON_VEG_COVER_PCT": "60"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("N", "L", "U", "RO", "BR"))

    def test_alpine(self):
        poly = self._polygon(
            vcpe={"ALPINE_DESIGNATION_CODE": "A"},
            nvce=[{"NON_VEG_COVER_TYPE_CODE": "BR", "NON_VEG_COVER_PCT": "60"}],
        )
        self.assertEqual(bclcs_levels(poly, self._classify),
                         ("N", "L", "A", "RO", "BR"))

    def test_rank_uses_first_layer_above_ten(self):
        poly = self._polygon(layers=[
            self._layer(10, 5, [("FDC", 100)], order=1),
            self._layer(20, 40, [("FDC", 100)], order=2),
        ])
        self.assertEqual([(u.layer_id, u.rank) for u in rank_updates(poly)],
                         [(10, None), (20, "1")])

    def test_rank_falls_back_to_largest_closure(self):
        poly = self._polygon(layers=[
            self._layer(10, 5, [("FDC", 100)], order=1),
            self._layer(20, 8, [("FDC", 100)], order=2),
        ])
        self.assertEqual([(u.layer_id, u.rank) for u in rank_updates(poly)],
                         [(10, None), (20, "1")])

    def test_lcc_order_sorts_by_coverage(self):
        poly = self._polygon(lcc=[
            {"LAND_COVER_COMPONENT_EST_ID": "1", "LAND_COVER_ORDER": "1",
             "COVERAGE_PCT": "20"},
            {"LAND_COVER_COMPONENT_EST_ID": "2", "LAND_COVER_ORDER": "2",
             "COVERAGE_PCT": "50"},
        ])
        self.assertEqual([(u.lcc_id, u.order) for u in lcc_order_updates(poly)],
                         [(2, 1), (1, 2)])

    def test_fip_bclcs_and_rank_unchanged(self):
        poly = self._polygon(
            standard="F",
            layers=[self._layer(1, 35, [("FDC", 100)])],
            vcpe={"BCLCS_LEVEL1_CODE": "V", "BCLCS_LEVEL2_CODE": "N",
                  "BCLCS_LEVEL3_CODE": "U", "BCLCS_LEVEL4_CODE": "SL",
                  "BCLCS_LEVEL5_CODE": "SP"},
        )
        dataset = Dataset(path="/tmp/fake.mdb", polygons=[poly],
                          orphans={}, row_counts={})
        updates = derive_updates(dataset, self._classify)
        self.assertEqual(updates.vcpe, [])
        self.assertEqual(updates.tcl, [])


class ModelTests(unittest.TestCase):
    def test_deleted_duplicate_tcl_row_keeps_last(self):
        fco = {
            "FOREST_COVER_OBJECT_ID": "1",
            "POLYGON_NUMBER": "1",
            "OBJECTID": "10",
            "INVENTORY_STANDARD_CODE": "V",
        }
        tcl = [
            {
                "TREE_COVER_LAYER_ESTIMATED_ID": "9",
                "FOREST_COVER_OBJECT_ID": "1",
                "LAYER_ORDER": "1",
                "LAYER_LEVEL_CODE": "1",
                "CROWN_CLOSURE_PCT": "40",
                "FOREST_COVER_RANK_CODE": "",
            },
            {
                "TREE_COVER_LAYER_ESTIMATED_ID": "9",
                "FOREST_COVER_OBJECT_ID": "1",
                "LAYER_ORDER": "1",
                "LAYER_LEVEL_CODE": "1",
                "CROWN_CLOSURE_PCT": "40",
                "FOREST_COVER_RANK_CODE": "1",
            },
        ]
        rows = {
            "FOREST_COVER_OBJECT": [fco],
            "TREE_COVER_LAYER_ESTIMATED": tcl,
            "TREE_SPECIES_ESTIMATED": [{
                "TREE_COVER_LAYER_ESTIMATED_ID": "9",
                "TREE_SPECIES_CODE": "FDC",
                "SPECIES_PCT": "100",
                "SPECIES_ORDER": "1",
            }],
        }

        class FakeReader:
            def __init__(self, _path):
                pass

            def tables(self):
                return list(TABLES)

            def table(self, name):
                return rows.get(name, [])

            def count(self, name):
                return len(rows.get(name, [])) - (1 if name == "TREE_COVER_LAYER_ESTIMATED" else 0)

        with patch("vri_validator.model.MdbReader", FakeReader):
            dataset = load_dataset("/tmp/fake.mdb")

        poly = dataset.polygons[0]
        self.assertEqual(len(poly.layers), 1)
        self.assertEqual(poly.layers[0].row["FOREST_COVER_RANK_CODE"], "1")
        self.assertEqual(len(poly.layers[0].species), 1)
        self.assertEqual(dataset.row_counts["TREE_COVER_LAYER_ESTIMATED"], 1)


class TreeClassTests(unittest.TestCase):
    """TC/TM/TB must follow the basal area split over the alive layers."""

    @classmethod
    def setUpClass(cls):
        cls.codes = CodeBook(DEFAULT_CODES)
        cls.types = species_types(cls.codes)

    def _poly(self, layers, lcc="TC", standard="V"):
        built = []
        for index, (level, basal, species) in enumerate(layers, 1):
            layer = Layer(
                row={
                    "TREE_COVER_LAYER_ESTIMATED_ID": str(index),
                    "FOREST_COVER_OBJECT_ID": "1",
                    "LAYER_ORDER": str(index),
                    "LAYER_LEVEL_CODE": level,
                    "BASAL_AREA": str(basal),
                    "CROWN_CLOSURE_PCT": "50",
                },
                species=[
                    {"TREE_SPECIES_CODE": code, "SPECIES_PCT": str(pct),
                     "SPECIES_ORDER": str(order)}
                    for order, (code, pct) in enumerate(species, 1)
                ],
            )
            built.append(layer)
        return Polygon(
            fid=1,
            fco={"POLYGON_NUMBER": "1", "INVENTORY_STANDARD_CODE": standard},
            vcpe={},
            layers=built,
            lcc=[{"LAND_COVER_CLASS_CODE": lcc, "COVERAGE_PCT": "100",
                  "LAND_COVER_COMPONENT_EST_ID": "-1",
                  "FOREST_COVER_OBJECT_ID": "1"}],
        )

    def test_conifer_dominant_gives_tc(self):
        poly = self._poly([("1", 100, [("FDC", 100)])])
        expected, conifer, deciduous, _unknown = treed_class(poly, self.types.get)
        self.assertEqual(expected, "TC")
        self.assertAlmostEqual(conifer, 1.0)
        self.assertAlmostEqual(deciduous, 0.0)

    def test_basal_area_is_summed_over_alive_layers(self):
        poly = self._poly([
            ("1", 10, [("FDC", 100)]),
            ("2", 90, [("DR", 100)]),
        ])
        expected, conifer, deciduous, _unknown = treed_class(poly, self.types.get)
        self.assertEqual(expected, "TB")
        self.assertAlmostEqual(conifer, 0.1)
        self.assertAlmostEqual(deciduous, 0.9)

    def test_dead_layers_are_excluded(self):
        poly = self._poly([
            ("1", 100, [("FDC", 100)]),
            ("D", 500, [("DR", 100)]),
        ])
        expected, conifer, deciduous, _unknown = treed_class(poly, self.types.get)
        self.assertEqual(expected, "TC")
        self.assertAlmostEqual(deciduous, 0.0)

    def test_mismatched_tree_class_is_reported(self):
        poly = self._poly([("1", 100, [("FDC", 100)])], lcc="TB")
        context = RuleContext(
            dataset=Dataset(path="/tmp/fake.mdb", polygons=[poly], orphans={},
                            row_counts={}),
            codes=self.codes,
            species_types=self.types,
            species_max=load_species_max(DEFAULT_SPECIES_MAX),
        )
        lcc_cross_checks(context)
        codes = [finding.code for finding in context.findings.items]
        self.assertIn("E-LCC-P-1450", codes)


class AccessQueryTests(unittest.TestCase):
    def test_empty_u_polygon_does_not_double_report(self):
        empty = Polygon(
            fid=1,
            fco={"POLYGON_NUMBER": "1", "INVENTORY_STANDARD_CODE": "V"},
            vcpe={"BCLCS_LEVEL1_CODE": "U"},
        )
        incomplete = Polygon(
            fid=2,
            fco={
                "POLYGON_NUMBER": "2",
                "INVENTORY_STANDARD_CODE": "V",
                "PROJECT_NAME": "PROJECT",
                "REFERENCE_YEAR": "2026",
            },
            vcpe={"BCLCS_LEVEL1_CODE": "U"},
        )
        dataset = Dataset(
            path="/tmp/fake.mdb",
            polygons=[empty, incomplete],
            orphans={},
            row_counts={},
        )
        ctx = RuleContext(
            dataset=dataset,
            codes=CodeBook(DEFAULT_CODES),
            species_types={},
            species_max={},
        )
        bclcs_and_lcc_warnings(ctx)
        self.assertEqual(
            [f.polygon_number for f in ctx.findings.items if f.code == "W-ACC-0026"],
            ["2"],
        )


class ReportTests(unittest.TestCase):
    def test_csv_and_html(self):
        dataset = Dataset(
            path="/tmp/fake.mdb",
            polygons=[],
            orphans={"TREE_SPECIES_ESTIMATED": []},
            row_counts={"FOREST_COVER_OBJECT": 0},
        )
        findings = Findings()
        findings.add(Finding(code="E-TEST-001", message="a <bad> thing",
                             polygon_id=1, polygon_number="1", table="T",
                             field="F", value="x"))
        findings.add(Finding(code="E-TEST-001", message="a <bad> thing",
                             polygon_id=1, polygon_number="1", table="T",
                             field="F", value="x"))
        self.assertEqual(len(findings), 1)
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = write_csv(findings, Path(tmp) / "out.csv")
            html_path = write_html(dataset, findings, Path(tmp) / "out.html")
            self.assertIn("E-TEST-001", csv_path.read_text())
            text = html_path.read_text()
            self.assertIn("a &lt;bad&gt; thing", text)
            self.assertIn("E-TEST-001", text)


if __name__ == "__main__":
    unittest.main()
