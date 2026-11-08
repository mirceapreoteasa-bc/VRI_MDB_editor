import unittest

from vri_editor import siteindex


class SiteIndexTests(unittest.TestCase):
    def test_matches_sitetools_value(self):
        # SiteToolsCmd (Sindex v1.54) gives 22.64 for Fdc at 50 years / 20 m
        self.assertAlmostEqual(siteindex.site_index("FDC", 50, 20), 22.64, places=2)

    def test_lodgepole_has_its_own_curve(self):
        pli = siteindex.site_index("PLI", 60, 18)
        self.assertIsNotNone(pli)
        self.assertNotEqual(siteindex.dll_index("PLI"), siteindex.dll_index("PY"))

    def test_out_of_range_and_unknown_species_return_none(self):
        self.assertIsNone(siteindex.site_index("FDC", 5, 18))      # age below grid
        self.assertIsNone(siteindex.site_index("FDC", 60, 45))     # height above grid
        self.assertIsNone(siteindex.site_index("X", 60, 18))       # no curve for X
        self.assertIsNone(siteindex.site_index("FDC", None, 18))

    def test_interpolation_is_between_neighbours(self):
        lo = siteindex.site_index("CW", 60, 20)
        hi = siteindex.site_index("CW", 62, 20)
        mid = siteindex.site_index("CW", 61, 20)
        self.assertLessEqual(min(lo, hi) - 0.01, mid)
        self.assertLessEqual(mid, max(lo, hi) + 0.01)


if __name__ == "__main__":
    unittest.main()
