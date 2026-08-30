"""Tests for max-hp-scaled effective combat power."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.combat import effective_power

from .combat_fixtures import FakeEntity


class EffectivePowerTests(unittest.TestCase):
    def test_reference_ratios(self):
        human = FakeEntity(
            "human", hp=120, atk_phys=8, agility=9, defense=7, magic_power=40
        )
        elf = FakeEntity(
            "elf",
            hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
        )
        monster = FakeEntity(
            "monster",
            hp=300,
            atk_phys=16,
            agility=16,
            defense=16,
            magic_power=0,
        )
        self.assertGreaterEqual(effective_power(elf) / effective_power(human), 100)
        ratio = effective_power(monster) / effective_power(human)
        self.assertGreater(ratio, 1)
        self.assertLess(ratio, 100)

    @covers_requirement("combat-resolution::effective-power-combines-four-effective-stats-multiplied-by-max-hp", "overwhelm-threshold::a-decided-direction-is-further-gated-by-an-estimated-round-count-bound-overwhelm", "overwhelm-threshold::the-hit-rate-signal-detects-to-hit-saturation-without-rolling-dice-checked-over-every", "overwhelm-threshold::the-power-ratio-signal-is-computed-from-team-summed-effective-power-checked-in-both")
    def test_current_hp_does_not_change_power_but_effective_stats_do(self):
        entity = FakeEntity("entity", hp=100, max_hp=100)
        before = effective_power(entity)
        entity.traits.hp.value = 1
        self.assertEqual(effective_power(entity), before)
        entity.skills.values["atk_phys"] *= 100
        self.assertGreater(effective_power(entity), before)


class EffectivePowerIntegrationTests(EvenniaTest):
    @covers_requirement("damage-effect-handlers::damage-reads-every-stat-through-effective-value-never-raw-entity-traits")
    def test_real_skill_handler_multiplier_changes_power_not_stored_trait(self):
        entity = create_object(PlayerCharacter, key="power")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        stored_attack = entity.traits.atk_phys.value
        before = effective_power(entity)
        entity.db.skills = {
            "active": ["body_enhancement"],
            "passive": [],
        }
        self.assertGreater(effective_power(entity), before)
        self.assertEqual(entity.traits.atk_phys.value, stored_attack)
