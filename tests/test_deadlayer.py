import unittest

from vri_editor import deadlayer

LIVE = [{"LAYER_LEVEL_CODE": "1", "VRI_LIVE_STEMS_PER_HA": "400"}]
WITH_D = LIVE + [{"LAYER_LEVEL_CODE": "D", "VRI_LIVE_STEMS_PER_HA": "120"}]


class DeadLayerRuleTests(unittest.TestCase):
    def test_default_rule_is_100_stems(self):
        self.assertEqual(deadlayer.DEFAULT_RULE, "stems100")
        self.assertIsNotNone(deadlayer.dead_layer_message({"VRI_DEAD_STEMS_PER_HA": "100"}, LIVE))
        self.assertIsNone(deadlayer.dead_layer_message({"VRI_DEAD_STEMS_PER_HA": "99"}, LIVE))

    def test_no_message_when_a_d_layer_exists(self):
        self.assertIsNone(deadlayer.dead_layer_message({"VRI_DEAD_STEMS_PER_HA": "300"}, WITH_D))

    def test_30_percent_rule_uses_live_density(self):
        # 120 dead stems is 30% of 400 live stems: flagged under pct30, not under the 100-stem rule
        vcpe = {"VRI_DEAD_STEMS_PER_HA": "120"}
        self.assertIsNotNone(deadlayer.dead_layer_message(vcpe, LIVE, "pct30"))
        self.assertIsNotNone(deadlayer.dead_layer_message(vcpe, LIVE, "stems100"))
        # 60 dead stems: under 100 stems, under 30% of 400 (120) -> no flag in either mode
        low = {"VRI_DEAD_STEMS_PER_HA": "60"}
        self.assertIsNone(deadlayer.dead_layer_message(low, LIVE, "stems100"))
        self.assertIsNone(deadlayer.dead_layer_message(low, LIVE, "pct30"))

    def test_zero_or_missing_snags_never_flag(self):
        self.assertIsNone(deadlayer.dead_layer_message({}, LIVE))
        self.assertIsNone(deadlayer.dead_layer_message({"VRI_DEAD_STEMS_PER_HA": "0"}, LIVE))


if __name__ == "__main__":
    unittest.main()
