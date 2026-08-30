"""Regression tests for direct monster-tier construction."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.rules.traits import (
    _resolve_band_position,
    build_initial_traits_for_monster_tier,
)


class MonsterScaleTests(unittest.TestCase):
    @covers_requirement("entity-trait-scales::monster-trait-baselines-read-monstertier-static-band-and-hp-band-directly-never-a-derived-multiplier")
    def test_floor_values_are_direct_registry_reads(self):
        low = build_initial_traits_for_monster_tier("low")
        calamity = build_initial_traits_for_monster_tier("calamity")
        tier = MONSTER_TIER_REGISTRY["calamity"]
        self.assertEqual(calamity["atk_phys"], tier.static_band.atk_phys[0])
        self.assertEqual(calamity["hp"], tier.hp_band[0])
        self.assertGreater(calamity["atk_phys"], low["atk_phys"])
        self.assertGreater(calamity["hp"], low["hp"])
        for key in ("mp", "sp", "magic_power"):
            self.assertEqual(calamity[key], 0)

    def test_positions_and_invalid_inputs(self):
        band = MONSTER_TIER_REGISTRY["mid"].hp_band
        floor = build_initial_traits_for_monster_tier("mid", "floor")["hp"]
        middle = build_initial_traits_for_monster_tier("mid", "mid")["hp"]
        ceiling = build_initial_traits_for_monster_tier("mid", "ceiling")["hp"]
        self.assertLess(floor, middle)
        self.assertLess(middle, ceiling)
        self.assertEqual(middle, _resolve_band_position(band, "mid"))
        with self.assertRaises(ValueError):
            build_initial_traits_for_monster_tier("mid", "unknown")
        with self.assertRaises(ValueError):
            _resolve_band_position((1, None), "ceiling")
        with self.assertRaises(KeyError):
            build_initial_traits_for_monster_tier("missing")


class MonsterPopulationTests(EvenniaTest):
    def test_invalid_assigned_tier_is_rejected_when_population_is_requested(self):
        monster = create_object(Monster, key="invalid")
        monster.threat_tier = "missing"
        with self.assertRaises(KeyError):
            monster.apply_monster_tier()
        self.assertEqual(monster.traits.all(), [])
