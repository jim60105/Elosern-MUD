"""Skill, enemy, and tie-break selection tests."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules import combat_modifiers
from world.rules.combat import Battlefield
from world.rules.monster_behaviour import (
    _choose_skill,
    _choose_target,
    _living_enemies,
    _owned_damage_skills,
)
from world.rules.rulebook.schema import Rule
from world.skills.registry import SkillKind

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    open_synthetic_scope,
    synth_damage_skill,
)
from .combat_fixtures import FakeEntity, FakeGauge

# File-local synthetic rows (data independence): a passive, a non-damage
# active, a zero-cost physical strike, and an MP-costing magic spell. Their
# relative costs/stats are authored here, so every expectation below names
# its own numbers.
_T_PASSIVE = synth_damage_skill(
    "t_guard_shell", "合成護殼", effects=["passive_buff:t_guard_shell"], kind=SkillKind.PASSIVE
)
_T_FLIGHT = synth_damage_skill("t_synth_flight", "合成飛行", effects=["movement:flight"])
_T_CLAW = synth_damage_skill("t_split_claw", "裂爪擊")
_T_SPELL = synth_damage_skill(
    "t_rain_spray",
    "瀧灑法術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 12},
)
# One flat atk_phys bonus rule keyed to the synthetic passive, mirroring the
# rule-table shape any shipped ownership bonus uses (see test_stat_breakdown).
_T_BONUS_PASSIVE = synth_damage_skill(
    "t_training_drill", "合成鍛鍊", effects=["passive_buff:t_training_drill"], kind=SkillKind.PASSIVE
)
_T_BONUS_RULE = Rule(
    "t_training_drill_atk_phys_bonus",
    {"skill_owned": _T_BONUS_PASSIVE.key},
    {"atk_phys": 5},
)
_SCOPE_EXTRA = {
    "skills": {
        row.key: row
        for row in (_T_PASSIVE, _T_FLIGHT, _T_CLAW, _T_SPELL, _T_BONUS_PASSIVE)
    }
}


class MonsterBehaviourSelectionTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    def test_owned_damage_skills_preserve_owned_order(self):
        entity = FakeEntity(
            "actor",
            owned=[_T_PASSIVE.key, _T_FLIGHT.key, _T_CLAW.key, _T_SPELL.key],
        )
        entity.traits.sp = FakeGauge(18, 18)
        entity.traits.mp = FakeGauge(20, 20)
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            [_T_CLAW.key, _T_SPELL.key],
        )
        entity.traits.mp.value = 0
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            [_T_CLAW.key],
        )
        entity.skills._owned = [_T_FLIGHT.key]
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
        physical = _T_CLAW
        magic = _T_SPELL
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
        entity.skills._owned = [_T_BONUS_PASSIVE.key]
        target = FakeEntity("target", defense=12)
        physical = _T_CLAW
        magic = _T_SPELL
        with (
            patch.object(
                combat_modifiers, "_RULES", list(combat_modifiers._RULES) + [_T_BONUS_RULE]
            ),
            patch(
                "world.rules.monster_behaviour.dice.roll_d100",
                return_value=0,
            ) as roller,
        ):
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
