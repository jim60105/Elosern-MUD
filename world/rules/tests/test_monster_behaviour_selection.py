"""Skill, enemy, and tie-break selection tests."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
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
from world.rules.combat_identity import stable_actor_id

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
            "actor", combat_identity='actor',
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

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
    )
    def test_ineligible_skill_filtered_from_damage_candidates(self):
        from world.skills.registry import SkillEligibility
        ineligible_skill = replace(
            synth_damage_skill("t_ineligible_dmg", "不合身分傷害"),
            eligibility=SkillEligibility(allowed_actor_kinds=("player",))
        )
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {ineligible_skill.key: ineligible_skill}):
            entity = FakeEntity("monster_actor", combat_identity='monster_actor', owned=[ineligible_skill.key, _T_CLAW.key])
            entity.traits.sp = FakeGauge(18, 18)
            entity.traits.mp = FakeGauge(20, 20)
            self.assertEqual([s.key for s in _owned_damage_skills(entity)], [_T_CLAW.key])

    def test_living_enemies_excludes_dead_and_fled(self):
        actor = FakeEntity("actor", combat_identity='actor')
        alive = FakeEntity("alive", combat_identity='alive')
        dead = FakeEntity("dead", combat_identity='dead', hp=0, max_hp=100)
        fled = FakeEntity("fled", combat_identity='fled')
        field = Battlefield(
            {
                'monsters': frozenset({"fixture:actor"}),
                'party': frozenset({"fixture:alive", "fixture:dead", "fixture:fled"}),
            },
            {stable_actor_id(entity): entity for entity in (actor, alive, dead, fled)},
            fled={stable_actor_id(fled)},
        )
        self.assertEqual(_living_enemies(field, actor), [alive])
        field.fled.add(stable_actor_id(alive))
        self.assertEqual(_living_enemies(field, actor), [])

    @covers_requirement("monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed")
    def test_target_strategies_and_seeded_tie_break(self):
        actor = FakeEntity("actor", combat_identity='actor')
        weak = FakeEntity("weak", combat_identity='weak', hp=20, max_hp=100, atk_phys=2)
        strong = FakeEntity("strong", combat_identity='strong', hp=80, atk_phys=30)
        enemies = [weak, strong]
        self.assertIs(_choose_target(actor, enemies, "lowest_hp"), weak)
        self.assertIs(
            _choose_target(actor, enemies, "highest_effective_power"),
            strong,
        )
        first = FakeEntity("first", combat_identity='first')
        second = FakeEntity("second", combat_identity='second')
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=1,
        ) as roller:
            self.assertIs(
                _choose_target(actor, [first, second], "lowest_hp"),
                second,
            )
        roller.assert_called_once_with()

    @covers_requirement(
        "monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll",
    )
    def test_skill_strategies_and_expected_damage(self):
        entity = FakeEntity(
            "actor", combat_identity='actor',
            atk_phys=30,
            magic_power=50,
        )
        target = FakeEntity("target", combat_identity='target', defense=12)
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
        entity = FakeEntity("actor", combat_identity='actor', atk_phys=30, magic_power=30)
        entity.skills._owned = [_T_BONUS_PASSIVE.key]
        target = FakeEntity("target", combat_identity='target', defense=12)
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
