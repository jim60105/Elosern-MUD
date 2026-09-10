"""Regression tests for direct monster-tier construction."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.rules.traits import (
    _resolve_band_position,
    build_initial_traits_for_monster_tier,
)

from ._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_MONSTER_TIERS as _KIT_TIERS

# The kit's two synthetic threat tiers, ordered: every assertion below reads
# the live registry rows, so a shipped-data rework cannot break this file.
_T_FAINT = _KIT_TIERS["t_faint"]
_T_RIVEN = _KIT_TIERS["t_riven"]
assert _T_RIVEN.hp_band[0] > _T_FAINT.hp_band[0]


class MonsterScaleTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "monster_tiers")

    @covers_requirement("entity-trait-scales::monster-trait-baselines-read-monstertier-static-band-and-hp-band-directly-never-a-derived-multiplier")
    def test_floor_values_are_direct_registry_reads(self):
        faint = build_initial_traits_for_monster_tier(_T_FAINT.key)
        riven = build_initial_traits_for_monster_tier(_T_RIVEN.key)
        tier = _T_RIVEN
        self.assertEqual(riven["atk_phys"], tier.static_band.atk_phys[0])
        self.assertEqual(riven["hp"], tier.hp_band[0])
        self.assertGreater(riven["atk_phys"], faint["atk_phys"])
        self.assertGreater(riven["hp"], faint["hp"])
        for key in ("mp", "sp", "magic_power"):
            self.assertEqual(riven[key], 0)

    def test_positions_and_invalid_inputs(self):
        band = _T_RIVEN.hp_band
        floor = build_initial_traits_for_monster_tier(_T_RIVEN.key, "floor")["hp"]
        middle = build_initial_traits_for_monster_tier(_T_RIVEN.key, "mid")["hp"]
        ceiling = build_initial_traits_for_monster_tier(_T_RIVEN.key, "ceiling")["hp"]
        self.assertLess(floor, middle)
        self.assertLess(middle, ceiling)
        self.assertEqual(middle, _resolve_band_position(band, "mid"))
        with self.assertRaises(ValueError):
            build_initial_traits_for_monster_tier(_T_RIVEN.key, "unknown")
        with self.assertRaises(ValueError):
            _resolve_band_position((1, None), "ceiling")
        with self.assertRaises(KeyError):
            build_initial_traits_for_monster_tier("t_missing_tier")


class MonsterPopulationTests(EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "monster_tiers")
        super().setUp()

    def test_invalid_assigned_tier_is_rejected_when_population_is_requested(self):
        monster = create_object(Monster, key="invalid")
        monster.threat_tier = "t_missing_tier"
        with self.assertRaises(KeyError):
            monster.apply_monster_tier()
        self.assertEqual(monster.traits.all(), [])
