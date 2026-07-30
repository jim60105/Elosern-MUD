"""Tests for the Evennia-backed d100 wrapper."""

import random
import unittest

from world.rules.dice import roll_d100


class DiceTests(unittest.TestCase):
    def test_rolls_stay_in_range(self):
        self.assertTrue(all(1 <= roll_d100() <= 100 for _ in range(500)))

    def test_fixed_seed_reproduces_the_sequence(self):
        random.seed(913)
        first = [roll_d100() for _ in range(20)]
        random.seed(913)
        self.assertEqual(first, [roll_d100() for _ in range(20)])
