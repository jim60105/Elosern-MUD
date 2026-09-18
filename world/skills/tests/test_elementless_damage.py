"""Behavioral tests for the elementless damage token (elementless-damage-effect).

Every scenario resolves a real cast through the shipped pipeline or
constructs a real ``SkillDef``; none asserts a bare dataclass field in
isolation. No shipped key, label, cost, or coefficient is named anywhere in
this module — every skill under test is synthetic.
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.combat import Battlefield, BattlefieldActionContext, _stored_hp
from world.rules.progression import SKILL_PRACTICE_XP_PER_USE
from world.rules.tests.combat_fixtures import grant_lineage
from world.rules.traits import restore_gauges_to_full
from world.skills.effects import DamageEffect, parse_effect
from world.tests.synthetic_data import make_skill, synthetic_registries

# An elementless physical strike: the reserved ``damage:none:physical`` token.
_T_ELEMENTLESS_STRIKE = make_skill(
    "t_elementless_strike",
    effects=("damage:none:physical",),
)

# An element-bearing physical twin of identical shape and coefficient.
_T_ELEMENT_TWIN = make_skill(
    "t_element_twin_strike",
    element="fire",
    effects=("damage:fire:physical",),
)

_EXTRA_SKILLS = {
    _T_ELEMENTLESS_STRIKE.key: _T_ELEMENTLESS_STRIKE,
    _T_ELEMENT_TWIN.key: _T_ELEMENT_TWIN,
}
_SCOPE = synthetic_registries("skills", extra={"skills": _EXTRA_SKILLS})


class ParseEffectReservedNoneTokenTests(unittest.TestCase):
    """``parse_effect`` recognizes ``none`` as the reserved elementless token."""

    @covers_requirement("skill-effect-model::a-damage-effect-can-declare-the-absence-of-an-element")
    def test_reserved_token_parses_to_an_absent_element(self):
        self.assertEqual(
            parse_effect("damage:none:physical"),
            DamageEffect(element=None, school="physical"),
        )
        self.assertEqual(
            parse_effect("damage:none:magic"),
            DamageEffect(element=None, school="magic"),
        )

    def test_a_registry_element_form_still_parses_unchanged(self):
        self.assertEqual(
            parse_effect("damage:fire:physical"),
            DamageEffect(element="fire", school="physical"),
        )


class SkillDefElementConsistencyTests(unittest.TestCase):
    """The one-directional consistency check in ``SkillDef.__post_init__``."""

    @covers_requirement("skill-effect-model::an-elementless-damage-effect-and-a-declared-skill-element-are-mutually-exclusive")
    def test_element_bearing_skill_with_elementless_effect_raises(self):
        with self.assertRaises(ValueError) as ctx:
            make_skill(
                "t_contradictory_skill",
                element="fire",
                effects=("damage:none:physical",),
            )
        self.assertIn("fire", str(ctx.exception))
        self.assertIn("t_contradictory_skill", str(ctx.exception))

    def test_elementless_skill_with_only_elementless_effects_constructs(self):
        skill = make_skill(
            "t_consistent_elementless",
            effects=("damage:none:physical",),
        )
        self.assertIsNone(skill.element)

    def test_element_bearing_skill_with_matching_element_effect_constructs(self):
        skill = make_skill(
            "t_consistent_element",
            element="fire",
            effects=("damage:fire:physical",),
        )
        self.assertEqual(skill.element.key, "fire")

    @covers_requirement("skill-effect-model::an-elementless-damage-effect-and-a-declared-skill-element-are-mutually-exclusive")
    def test_elementless_skill_with_element_bearing_effect_still_constructs(self):
        # The pre-existing reverse shape (design.md D3): predates this change
        # across shipped and synthetic fixtures, and stays legal.
        skill = make_skill(
            "t_legal_reverse_shape",
            effects=("damage:fire:physical",),
        )
        self.assertIsNone(skill.element)

    def test_skill_with_no_damage_effect_is_unaffected(self):
        skill = make_skill("t_no_damage_effect_at_all", effects=())
        self.assertIsNone(skill.element)


@_SCOPE
class ElementlessDamageSettlementParityTests(EvenniaTestCase):
    """An elementless strike settles identically to an element-bearing twin."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="ed_actor")
        self.target = create_object(PlayerCharacter, key="ed_target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.traits.atk_phys.base = 40
        self.target.traits.defense.base = 20
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)
        grant_lineage(
            self.actor,
            [_T_ELEMENTLESS_STRIKE.key, _T_ELEMENT_TWIN.key],
        )

    def _resolve_cast(self, skill_key: str, roll: int = 60):
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)
        battlefield = Battlefield(
            {"party": frozenset({"ed_actor"}), "foes": frozenset({"ed_target"})},
            {"ed_actor": self.actor, "ed_target": self.target},
        )
        request = ActionRequest(
            self.actor,
            skill_key,
            [self.target],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100", return_value=roll):
            return ActionResolver.resolve(request)

    @covers_requirement("damage-effect-handlers::damage-element-school-is-the-defined-convention-for-this-prefix")
    def test_elementless_strike_settles_identically_to_element_bearing_twin(self):
        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_ELEMENTLESS_STRIKE.key)
        self.assertEqual(result.outcome, "success")
        elementless_damage = before_hp - _stored_hp(self.target)

        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_ELEMENT_TWIN.key)
        self.assertEqual(result.outcome, "success")
        element_bearing_damage = before_hp - _stored_hp(self.target)

        self.assertEqual(elementless_damage, element_bearing_damage)

    @covers_requirement("damage-effect-handlers::damage-element-school-is-the-defined-convention-for-this-prefix")
    def test_neither_side_s_affinity_changes_the_elementless_result(self):
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_ELEMENTLESS_STRIKE.key)
        self.assertEqual(result.outcome, "success")
        neutral_damage = before_hp - _stored_hp(self.target)

        self.actor.db.affinity_elements = ["fire"]
        self.target.db.affinity_elements = ["fire"]
        restore_gauges_to_full(self.target)
        before_hp = _stored_hp(self.target)
        result = self._resolve_cast(_T_ELEMENTLESS_STRIKE.key)
        self.assertEqual(result.outcome, "success")
        affinity_damage = before_hp - _stored_hp(self.target)

        self.assertEqual(neutral_damage, affinity_damage)


@_SCOPE
class ElementlessPracticeAccrualParityTests(EvenniaTestCase):
    """Elemental affinity never scales practice XP for an elementless skill."""

    def setUp(self):
        super().setUp()
        self.favored = create_object(PlayerCharacter, key="ep_favored")
        self.neutral = create_object(PlayerCharacter, key="ep_neutral")
        for entity in (self.favored, self.neutral):
            entity.race = "human"
            entity.apply_race_baseline()
            entity.db.skills = {"active": [_T_ELEMENTLESS_STRIKE.key], "passive": []}
            restore_gauges_to_full(entity)
        self.favored.db.affinity_elements = ["fire"]
        self.neutral.db.affinity_elements = []
        self.target = create_object(PlayerCharacter, key="ep_target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        restore_gauges_to_full(self.target)

    def _resolve_cast(self, actor):
        restore_gauges_to_full(actor)
        restore_gauges_to_full(self.target)
        battlefield = Battlefield(
            {"party": frozenset({actor.key}), "foes": frozenset({"ep_target"})},
            {actor.key: actor, "ep_target": self.target},
        )
        request = ActionRequest(
            actor,
            _T_ELEMENTLESS_STRIKE.key,
            [self.target],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    @covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")
    def test_affinity_bearing_and_neutral_actors_accrue_the_same_practice(self):
        result = self._resolve_cast(self.favored)
        self.assertEqual(result.outcome, "success")
        favored_xp = self.favored.db.skill_proficiency[_T_ELEMENTLESS_STRIKE.key]

        result = self._resolve_cast(self.neutral)
        self.assertEqual(result.outcome, "success")
        neutral_xp = self.neutral.db.skill_proficiency[_T_ELEMENTLESS_STRIKE.key]

        self.assertEqual(favored_xp, neutral_xp)
        self.assertEqual(favored_xp, SKILL_PRACTICE_XP_PER_USE)
