"""Tests for the Evennia-backed d100 wrapper."""

from tools.spec_traceability import covers_requirement

import random
import unittest

from world.rules.dice import roll_d100


class DiceTests(unittest.TestCase):
    @covers_requirement("dice-roller::d100-roller-wraps-evennia-contrib-rpg-dice-directly")
    def test_rolls_stay_in_range(self):
        self.assertTrue(all(1 <= roll_d100() <= 100 for _ in range(500)))

    @covers_requirement("dice-roller::rolls-are-reproducible-under-a-fixed-seed")
    def test_fixed_seed_reproduces_the_sequence(self):
        random.seed(913)
        first = [roll_d100() for _ in range(20)]
        random.seed(913)
        self.assertEqual(first, [roll_d100() for _ in range(20)])
