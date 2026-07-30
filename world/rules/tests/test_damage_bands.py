"""Damage band and floor tests."""

import unittest
from unittest.mock import patch

from world.rules.combat import COMBAT_YAML, _handle_damage, _roll_multiplier

from .combat_fixtures import FakeEntity


class DamageBandTests(unittest.TestCase):
    def test_bare_solid_and_critical_bands(self):
        damage = COMBAT_YAML["damage"]
        self.assertEqual(_roll_multiplier(50, 1), damage["base_multiplier"])
        self.assertEqual(
            _roll_multiplier(50, damage["solid_hit_margin"]),
            damage["solid_hit_multiplier"],
        )
        self.assertEqual(
            _roll_multiplier(100, 0), damage["crit_multiplier"]
        )

    def test_floor_shape_does_not_apply_to_a_miss(self):
        actor = FakeEntity("actor", atk_phys=1, agility=10)
        target = FakeEntity("target", hp=100, defense=99, agility=10)
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            with patch("world.rules.combat.roll_d100", return_value=51):
                hit = _handle_damage(
                    actor, [target], "damage:dark:physical", {}
                )[0]
            with patch("world.rules.combat.roll_d100", return_value=1):
                miss = _handle_damage(
                    actor, [target], "damage:dark:physical", {}
                )[0]
        self.assertTrue(hit.description.endswith("|1|1"))
        self.assertTrue(miss.description.endswith("|0|0"))
        miss.apply()
        self.assertEqual(target.traits.hp.value, 100)
