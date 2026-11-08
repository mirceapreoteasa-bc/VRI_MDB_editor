import unittest

from vri_editor import basal


class BasalEstimateTests(unittest.TestCase):
    def test_density_and_height_raise_basal_area(self):
        low = basal.estimate("FDC", 80, 20, 600)
        high = basal.estimate("FDC", 80, 20, 1600)
        self.assertGreater(high, low)
        tall = basal.estimate("FDC", 80, 26, 1000)
        short = basal.estimate("FDC", 80, 14, 1000)
        self.assertGreater(tall, short)

    def test_plausible_range_for_a_mature_stand(self):
        value = basal.estimate("FDC", 100, 25, 1000)
        self.assertIsNotNone(value)
        self.assertTrue(10 <= value <= 80, value)

    def test_missing_or_bad_inputs_return_none(self):
        self.assertIsNone(basal.estimate("FDC", None, 20, 1000))
        self.assertIsNone(basal.estimate("FDC", 80, 0, 1000))
        self.assertIsNone(basal.estimate("FDC", 80, 20, "abc"))

    def test_crown_closure_is_optional(self):
        without = basal.estimate("HW", 60, 18, 1200)
        with_cc = basal.estimate("HW", 60, 18, 1200, crown_closure=50)
        self.assertIsNotNone(without)
        self.assertIsNotNone(with_cc)

    def test_output_is_clamped(self):
        self.assertLessEqual(basal.estimate("FDC", 400, 60, 7500), basal.MAX_BA)
        self.assertGreaterEqual(basal.estimate("FDC", 1, 1, 5), basal.MIN_BA)


if __name__ == "__main__":
    unittest.main()
