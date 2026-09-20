"""Slice of ``test_freeform_casting``: end-to-end scaled cast resolution
on the battlefield.
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
    _T_PHOENIX,
    _T_STORM,
    _T_TIDE,
    _T_TYRANT,
    _mastery_key,
    _monster,
    _open_scope,
    _player,
)


class FreeformScaledResolutionTests(EvenniaTestCase, BattlefieldIsolation):
    """A scaled cast deducts scaled MP and applies scaled magnitudes."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.monster = _monster("freeform wolf")
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform wolf"}),
            },
            {"freeform caster": self.actor, "freeform wolf": self.monster},
        )
        self.context = BattlefieldActionContext(self.field)
        grant_lineage(
            self.actor,
            [_T_CAST.key, _T_STORM.key, _T_PHOENIX.key],
            [_mastery_key()],
            rungs={
                _T_CAST.key: 6,
                _T_STORM.key: 6,
                _T_PHOENIX.key: 6,
            },
        )

    def _request(self, skill_key, targets, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            targets,
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_half_scale_cast_deducts_half_mp_and_deals_half_damage(self):
        # magic_power 6 gives an unscaled critical of round(6 * 2.0) = 12
        # against zero defense; half scale stages 6.
        self.actor.traits.magic_power.base = 6
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 0.5)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_CAST.cost["mp"]), 0.5),
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 6)
        self.assertEqual(self.monster.traits.hp.value, hp_before - 6)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_double_scale_cast_deducts_double_mp(self):
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_STORM.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_STORM.cost["mp"]), 2.0),
        )

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_unaffordable_scaled_cost_rejects_without_any_effect(self):
        grant_lineage(
            self.actor,
            [_T_TYRANT.key],
            [_mastery_key()],
            rungs={_T_TYRANT.key: 10},
        )
        self.actor.traits.mp.base = 200
        self.actor.traits.mp.current = 200
        hp_before = self.monster.traits.hp.value
        # The fixture budget sits strictly under the ×4 rung of the heavy row.
        self.assertLess(200, scaled_mp_cost(int(_T_TYRANT.cost["mp"]), 4.0))
        result = ActionResolver.resolve(
            self._request(_T_TYRANT.key, [self.monster], 4.0)
        )
        self.assertEqual(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(self.actor.traits.mp.value, 200)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertIsNone(result.event_log)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_damage_obeys_the_floor(self):
        # magic_power 2 → base critical 4 → quarter scale 1 (the floor), never 0.
        self.actor.traits.magic_power.base = 2
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 0.25)
            )
        self.assertEqual(result.outcome, "success")
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 1)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_lethal_hit_emits_exactly_one_defeat(self):
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 5
        self.monster.traits.hp.current = 5
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        defeated = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertEqual(len(defeated), 1)
        self.assertLessEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_healing_respects_the_maximum_and_knockout_rules(self):
        grant_lineage(
            self.actor, [_T_TIDE.key], [_mastery_key()],
            rungs={_T_TIDE.key: 6},
        )
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 150
        # magic_power 30 → base heal 30 → double scale 60, capped by the gap 50.
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_TIDE.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "heal"
        )
        self.assertEqual(heal_entry.data["amount"], 50)
        self.assertEqual(self.monster.traits.hp.value, 200)
        # A zero-HP entity is never revived: targeting drops the dead
        # candidate, so the scaled heal applies no restoration.
        self.monster.traits.hp.current = 0
        self.actor.traits.mp.current = 1000
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_TIDE.key, [self.monster], 2.0)
            )
        self.assertEqual(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)
        self.assertEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_damage_self_heal_spell_scales_damage_self_heal_and_mp_together(self):
        self.actor.traits.hp.base = 100
        self.actor.traits.hp.current = 40
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_PHOENIX.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_PHOENIX.cost["mp"]), 2.0),
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        # magic_power 30 → base critical 60 → double scale 120.
        self.assertEqual(damage_entry.data["amount"], 120)
        self.assertEqual(self.monster.traits.hp.value, 80)
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "self_heal"
        )
        # base heal 30 → double scale 60, capped by the gap to maximum.
        self.assertEqual(heal_entry.data["amount"], 60)
        self.assertEqual(self.actor.traits.hp.value, 100)
