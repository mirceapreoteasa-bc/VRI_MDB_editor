"""Line + point import: each polygon must get exactly one point; no polygon lost or merged.

Regression for lines that end on the middle of another line (T-junction) or stop a few
centimetres short of it. Before the fix, polygonize merged neighbours and dropped areas.
"""
import tempfile
import unittest
from pathlib import Path

from osgeo import ogr

from vri_editor import spatial

ogr.UseExceptions()


def _write_lines(path, lines):
    ds = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(str(path))
    layer = ds.CreateLayer("lines", geom_type=ogr.wkbLineString)
    for coords in lines:
        feat = ogr.Feature(layer.GetLayerDefn())
        geom = ogr.Geometry(ogr.wkbLineString)
        for x, y in coords:
            geom.AddPoint_2D(x, y)
        feat.SetGeometry(geom)
        layer.CreateFeature(feat)
    ds = None


def _write_points(path, points):
    ds = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(str(path))
    layer = ds.CreateLayer("points", geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("POLYGON_ID", ogr.OFTInteger))
    for pid, (x, y) in points:
        feat = ogr.Feature(layer.GetLayerDefn())
        feat.SetField("POLYGON_ID", pid)
        feat.SetGeometry(ogr.CreateGeometryFromWkt(f"POINT({x} {y})"))
        layer.CreateFeature(feat)
    ds = None


class LinePointImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _run(self, lines, points):
        lp, pp = self.tmp / "l.shp", self.tmp / "p.shp"
        _write_lines(lp, lines)
        _write_points(pp, points)
        polys, _, unmatched = spatial._polygonize_lines(lp, pp, "POLYGON_ID")
        return polys, unmatched

    def test_t_junction_and_gap_give_one_polygon_per_point(self):
        # two squares sharing an edge; the shared edge is drawn as two lines that
        # meet the other line at a T (no shared vertex), and the outer top edge has a
        # 0.2 m gap at the corner
        lines = [
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],       # left square outline
            [(10, 0), (20, 0), (20, 10), (10, 10)],              # right square, three sides
            [(10, 5), (0, 5)],                                   # shared edge as a T-junction stub
            [(9.8, 10.0), (20.0, 10.0)],                         # top edge, gap of 0.2 m to x=10
        ]
        points = [(1, (5, 2.5)), (2, (5, 7.5)), (3, (15, 5))]
        polys, unmatched = self._run(lines, points)
        ids = sorted(pid for pid, _ in polys)
        self.assertEqual(unmatched, [])
        self.assertEqual(ids, [1, 2, 3], "every point must give its own polygon")

    def test_sliver_is_not_a_polygon(self):
        # a near-duplicate line produces a zero-area sliver; it must not be imported
        lines = [
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
            [(0, 0), (10, 0)],
        ]
        polys, unmatched = self._run(lines, [(7, (5, 5))])
        self.assertEqual([pid for pid, _ in polys], [7])
        self.assertEqual(unmatched, [])


if __name__ == "__main__":
    unittest.main()
