"""Skill, enemy, and tie-break selection tests."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.monster_behaviour import (
    _choose_skill,
    _choose_target,
    _living_enemies,
    _owned_damage_skills,
)
from world.skills.registry import SKILL_REGISTRY

from .combat_fixtures import FakeEntity, FakeGauge


class MonsterBehaviourSelectionTests(unittest.TestCase):
    def test_owned_damage_skills_preserve_owned_order(self):
        entity = FakeEntity(
            "actor",
            owned=["fire_mastery", "flight", "shadow_slash", "fire_ball"],
        )
        entity.traits.sp = FakeGauge(18, 18)
        entity.traits.mp = FakeGauge(20, 20)
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            ["shadow_slash", "fire_ball"],
        )
        entity.traits.mp.value = 0
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            ["shadow_slash"],
        )
        entity.skills._owned = ["flight"]
        self.assertEqual(_owned_damage_skills(entity), [])

    def test_living_enemies_excludes_dead_and_fled(self):
        actor = FakeEntity("actor")
        alive = FakeEntity("alive")
        dead = FakeEntity("dead", hp=0, max_hp=100)
        fled = FakeEntity("fled")
        field = Battlefield(
            {
                "monsters": frozenset({"actor"}),
                "party": frozenset({"alive", "dead", "fled"}),
            },
            {entity.key: entity for entity in (actor, alive, dead, fled)},
            fled={"fled"},
        )
        self.assertEqual(_living_enemies(field, actor), [alive])
        field.fled.add("alive")
        self.assertEqual(_living_enemies(field, actor), [])

    @covers_requirement("monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed")
    def test_target_strategies_and_seeded_tie_break(self):
        actor = FakeEntity("actor")
        weak = FakeEntity("weak", hp=20, max_hp=100, atk_phys=2)
        strong = FakeEntity("strong", hp=80, atk_phys=30)
        enemies = [weak, strong]
        self.assertIs(_choose_target(actor, enemies, "lowest_hp"), weak)
        self.assertIs(
            _choose_target(actor, enemies, "highest_effective_power"),
            strong,
        )
        first = FakeEntity("first")
        second = FakeEntity("second")
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=1,
        ) as roller:
            self.assertIs(
                _choose_target(actor, [first, second], "lowest_hp"),
                second,
            )
        roller.assert_called_once_with()

    def test_skill_strategies_and_expected_damage(self):
        entity = FakeEntity(
            "actor",
            atk_phys=30,
            magic_power=50,
        )
        target = FakeEntity("target", defense=12)
        physical = SKILL_REGISTRY["shadow_slash"]
        magic = SKILL_REGISTRY["fire_ball"]
        self.assertIs(
            _choose_skill(
                entity,
                [physical, magic],
                "first_owned",
                target,
            ),
            physical,
        )
        self.assertIs(
            _choose_skill(
                entity,
                [physical, magic],
                "highest_expected_damage",
                target,
            ),
            magic,
        )
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=0,
        ) as roller:
            entity.skills.values["magic_power"] = 30
            self.assertIs(
                _choose_skill(
                    entity,
                    [physical, magic],
                    "highest_expected_damage",
                    None,
                ),
                physical,
            )
        roller.assert_called_once_with()

    @covers_requirement(
        "combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math"
    )
    def test_physical_candidate_ranks_with_its_atk_phys_bonus(self):
        entity = FakeEntity("actor", atk_phys=30, magic_power=30)
        entity.skills._owned = ["retainer_martial_training"]
        target = FakeEntity("target", defense=12)
        physical = SKILL_REGISTRY["shadow_slash"]
        magic = SKILL_REGISTRY["fire_ball"]
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=0,
        ) as roller:
            self.assertIs(
                _choose_skill(
                    entity,
                    [physical, magic],
                    "highest_expected_damage",
                    target,
                ),
                physical,
            )
        roller.assert_not_called()
