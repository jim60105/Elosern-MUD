"""Regression tests for subrace adjustment order."""

import unittest

from world.rules.traits import build_initial_traits


class SubraceOrderTests(unittest.TestCase):
    def test_static_modifiers_and_vital_overrides(self):
        catkin = build_initial_traits("beastfolk", "catkin")
        wolfkin = build_initial_traits("beastfolk", "wolfkin")
        foxkin = build_initial_traits("beastfolk", "foxkin")
        self.assertGreater(catkin["agility"], wolfkin["agility"])
        self.assertLess(catkin["defense"], wolfkin["defense"])
        self.assertEqual(foxkin["mp"], 50)
        self.assertNotEqual(foxkin["mp"], 30)

    def test_zero_modifier_subrace_matches_race_floor(self):
        self.assertEqual(
            build_initial_traits("elf", "fionnen"),
            build_initial_traits("elf"),
        )

    def test_cross_race_subrace_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "belongs to race"):
            build_initial_traits("human", "fionnen")

