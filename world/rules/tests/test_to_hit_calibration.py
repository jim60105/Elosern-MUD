"""Exact calibration checks for the linear to-hit formula."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules.combat import _to_hit

from .combat_fixtures import FakeEntity


class ToHitCalibrationTests(unittest.TestCase):
    @staticmethod
    def hit_rate(attacker_agility: int, defender_agility: int) -> float:
        attacker = FakeEntity("attacker", agility=attacker_agility)
        defender = FakeEntity("defender", agility=defender_agility)
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            hits = sum(_to_hit(attacker, defender, roll)[0] for roll in range(1, 101))
        return hits / 100

    @covers_requirement("overwhelm-threshold::a-decided-direction-is-computed-by-combining-the-ratio-and-hit-rate-signals-by")
    def test_parity_is_exactly_fifty_percent(self):
        self.assertEqual(self.hit_rate(9, 9), 0.5)

    def test_reference_matchups(self):
        self.assertEqual(self.hit_rate(6, 3), 0.53)
        self.assertEqual(self.hit_rate(6, 8), 0.48)
        self.assertEqual(self.hit_rate(9, 12), 0.47)
        self.assertEqual(self.hit_rate(9, 20), 0.39)
        self.assertEqual(self.hit_rate(18, 35), 0.33)
        self.assertEqual(self.hit_rate(92, 9), 1.0)
        self.assertEqual(self.hit_rate(9, 92), 0.0)
        self.assertEqual(self.hit_rate(92, 70), 0.72)

    @covers_requirement("combat-resolution::to-hit-uses-a-recalibrated-defender-constant-of-51-not-the-design-doc-s-original-60")
    def test_fifty_point_gap_saturates_and_natural_100_does_not_override(self):
        self.assertEqual(self.hit_rate(60, 10), 1.0)
        self.assertEqual(self.hit_rate(10, 60), 0.0)
        attacker = FakeEntity("attacker", agility=10)
        defender = FakeEntity("defender", agility=60)
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertFalse(_to_hit(attacker, defender, 100)[0])
