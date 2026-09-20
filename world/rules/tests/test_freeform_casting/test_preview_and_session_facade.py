"""Slice of ``test_freeform_casting``: cast preview surfacing and the
in-session command facade.
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
    _mastery_key,
    _monster,
    _open_scope,
    _owned,
    _player,
)


class FreeformPreviewTests(EvenniaTestCase):
    """Preview and the combat facade accept and revalidate scale."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="preview target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        grant_lineage(
            self.actor,
            [_T_CAST.key],
            [_mastery_key()],
            rungs={_T_CAST.key: len(FREEFORM_SCALE_VALUES) * 2},
        )
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"preview target"}),
            },
            {"freeform caster": self.actor, "preview target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_reports_scaled_resource_availability(self):
        top_cost = scaled_mp_cost(int(_T_CAST.cost["mp"]), 4.0)
        self.actor.traits.mp.current = top_cost
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertTrue(preview.enabled)
        self.actor.traits.mp.current = top_cost - 1
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "mp")

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_applies_the_freeform_gate(self):
        self.actor.db.skills = _owned(_T_CAST)
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        preview = revalidate_submission(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)


class FreeformSessionFacadeTests(EvenniaTest, BattlefieldIsolation):
    """The facade resolves a scaled combat cast and rejects tampered scales."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player("freeform session")
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 6}
        )
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.monster = _monster("session wolf")
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        self.actor.move_to(self.room1)
        self.monster.move_to(self.room1)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_resolves_a_scaled_combat_cast(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.actor, _T_CAST.key, [self.monster], scale=2.0
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_CAST.cost["mp"]), 2.0),
        )
        self.assertLess(self.monster.traits.hp.value, 200)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_rejects_a_tampered_scale_before_initiative(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        record_before = self.actor.db.active_combat
        result = submit_player_action(
            self.actor, _T_CAST.key, [self.monster], scale=3.0
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertEqual(self.actor.traits.mp.value, mp_before)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertEqual(self.actor.db.active_combat, record_before)
