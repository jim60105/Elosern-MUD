"""Slice of ``test_freeform_casting``: the resolver eligibility gate and
the ActionRequest scale-field contract.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.elements import Element
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import preview_skill, revalidate_submission
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)
from world.rules.combat_session import engage, submit_player_action
from world.rules.player_messages import rejection_message
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_LADDER,
    FREEFORM_SCALE_VALUES,
    _load_freeform_cast_scales,
    freeform_mastery_entitled,
    freeform_scale_entries_for,
    freeform_scales_for,
    scale_for_label,
    scale_label_for,
    scaled_magnitude,
    scaled_mp_cost,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS
from .._combat_session_helpers import (
    _monster_tier_key,
    _race_key,
    _behaviour_archetype_key,
    open_synthetic_scope,
)
from ..combat_fixtures import BattlefieldIsolation, grant_lineage


from ._support import (
    _T_CAST,
    _T_FOCUS_MP,
    _T_GLOW,
    _T_MIXED,
    _T_SP_SPELL,
    _T_VEIL,
    _mastery_key,
    _mastery_row,
    _open_scope,
    _owned,
    _player,
)


class FreeformResolverGateTests(EvenniaTestCase):
    """The resolver gates scaled casts at the ownership step."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="freeform target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform target"}),
            },
            {"freeform caster": self.actor, "freeform target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    def _request(self, skill_key, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            [self.target],
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_holder_can_scale_an_eligible_spell(self):
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 6}
        )
        result = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(result.outcome, "success")
        self.assertNotEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_without_mastery_is_rejected(self):
        self.actor.db.skills = _owned(_T_CAST)
        result = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_entitles_scaling_of_that_element_only(self):
        grant_lineage(
            self.actor,
            [_T_CAST.key, _T_GLOW.key],
            [_mastery_key()],
            rungs={_T_CAST.key: 6},
        )
        glow = ActionResolver.preflight(self._request(_T_GLOW.key, 2.0))
        self.assertEqual(glow.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        wind = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(wind.outcome, "success")

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_an_ineligible_spell_is_rejected_even_with_mastery(self):
        self.actor.db.skills = _owned(_T_MIXED, _mastery_row())
        result = ActionResolver.preflight(self._request(_T_MIXED.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_elemental_mp_skill_never_crashes_the_gate(self):
        self.actor.db.skills = _owned(_T_FOCUS_MP)
        result = ActionResolver.preflight(self._request(_T_FOCUS_MP.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_sp_only_elemental_skill_is_not_scalable(self):
        self.actor.db.skills = _owned(_T_SP_SPELL, _mastery_row())
        self.actor.traits.sp.current = 500
        result = ActionResolver.preflight(self._request(_T_SP_SPELL.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        sp_before = self.actor.traits.sp.value
        ActionResolver.resolve(self._request(_T_SP_SPELL.key, 2.0))
        self.assertEqual(self.actor.traits.sp.value, sp_before)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_member_scale_is_rejected(self):
        self.actor.db.skills = _owned(_T_CAST, _mastery_row())
        result = ActionResolver.preflight(self._request(_T_CAST.key, 3.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scale_one_is_always_permitted(self):
        grant_lineage(
            self.actor,
            [_T_FOCUS_MP.key, _T_MIXED.key, _T_VEIL.key],
            [_mastery_key()],
        )
        for key in (_T_FOCUS_MP.key, _T_MIXED.key, _T_VEIL.key):
            with self.subTest(skill=key):
                result = ActionResolver.preflight(self._request(key, 1.0))
                self.assertNotEqual(
                    result.reason,
                    RejectReason.SCALED_CAST_FORBIDDEN,
                )


class ActionRequestScaleContractTests(EvenniaTestCase):
    """ActionRequest carries an optional scale modifier and a new rejection category."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="scale contract target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 1}
        )
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"scale contract target"}),
            },
            {"freeform caster": self.actor, "scale contract target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_existing_requests_default_to_scale_one(self):
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
        )
        self.assertEqual(request.scale, 1.0)
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        self.assertEqual(
            spend.data["amount"], scaled_mp_cost(int(_T_CAST.cost["mp"]), 1.0)
        )

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_scale_reaches_the_resource_steps_and_the_handlers(self):
        self.target.traits.defense.base = 0
        self.target.traits.hp.base = 200
        self.target.traits.hp.current = 200
        self.actor.traits.magic_power.base = 6
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
            scale=0.5,
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        # Step 2 and step 6 compare and deduct the same scaled amount.
        self.assertEqual(
            spend.data["amount"], scaled_mp_cost(int(_T_CAST.cost["mp"]), 0.5)
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        # magic_power 6 → unscaled critical 12 → half scale 6.
        self.assertEqual(damage_entry.data["amount"], 6)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_the_rejection_category_is_available(self):
        self.actor.db.skills = _owned(_T_CAST)
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
            scale=2.0,
        )
        result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertIsNone(result.event_log)
        self.assertIsNone(result.time_cost_seconds)
