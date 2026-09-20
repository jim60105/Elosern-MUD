"""Slice of ``test_freeform_casting``: the freeform-cast text-command
surface.
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
    _T_OOC_CAST,
    _T_OOC_HEAL,
    _T_VEIL,
    _mastery_key,
    _open_scope,
)


class FreeformTextCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """The text cast command accepts a scale token."""

    def setUp(self):
        _open_scope(self)
        super().setUp()

    def _setup_caster(self, *, mastery: bool) -> None:
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        grant_lineage(
            self.char1,
            [_T_OOC_HEAL.key, _T_VEIL.key],
            [_mastery_key()] if mastery else [],
            rungs={_T_OOC_HEAL.key: len(FREEFORM_SCALE_VALUES) * 2}
            if mastery
            else None,
        )
        self.char1.traits.mp.base = 500
        self.char1.traits.mp.current = 500
        self.char1.move_to(self.room1)

    def _setup_target(self) -> None:
        target = create_object(PlayerCharacter, key="glow target")
        target.race = _race_key()
        target.apply_race_baseline()
        target.move_to(self.room1)

    def _clock(self):
        clock = WorldClock()
        return patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch(
            "world.rules.cast_settlement.get_world_clock", return_value=clock
        ), clock

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scaled_out_of_combat_cast_deducts_scaled_mp_and_advances_time(self):
        from commands.action import CmdCast

        # The synthetic row itself declares out-of-combat usability (no
        # shipped-registry mutation needed); the heal shape keeps the room
        # cast clear of the sanctioned damaging-action gate
        # (out-of-combat-damage-gate) while the scale-token mechanics under
        # test (cost scaling, clock advance) stay shape-independent.
        self._setup_caster(mastery=True)
        self._setup_target()
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1/2=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        half_end = self.char1.traits.mp.value
        # The ordinary command-time charge applies per cast.
        self.assertEqual(clock.tick, 6)
        # Reset the gauge (and its regen remainder) so the second cast
        # accrues the same regen; the exact scaled deduction is then the
        # differential between the two command casts.
        self.char1.traits.mp.current = 500
        self.char1.traits.mp.regen_remainder = 0.0
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        one_end = self.char1.traits.mp.value
        self.assertEqual(clock.tick, 12)
        base_mp = int(_T_OOC_HEAL.cost["mp"])
        # The 1/2 rung deducts exactly one half-scale's worth less.
        self.assertEqual(
            half_end - one_end,
            scaled_mp_cost(base_mp, 1.0) - scaled_mp_cost(base_mp, 0.5),
        )

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_invalid_scale_token_rejects_without_effect(self):
        from commands.action import CmdCast

        self._setup_caster(mastery=True)
        read_patch, get_patch, clock = self._clock()
        mp_before = self.char1.traits.mp.value
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_CAST.key}@3",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(self.char1.traits.mp.value, mp_before)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_unauthorized_scale_rejects_without_effect(self):
        from commands.action import CmdCast

        # Same non-damage scalable shape as the success-path test: the
        # unauthorized-scale rejection comes from the freeform gate, and the
        # fixture must not be gated earlier by the damaging-action gate.
        self._setup_caster(mastery=False)
        read_patch, get_patch, clock = self._clock()
        mp_before = self.char1.traits.mp.value
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@2",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(self.char1.traits.mp.value, mp_before)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_on_an_ineligible_spell_rejects_with_the_stable_message(self):
        from commands.action import CmdCast

        self._setup_caster(mastery=True)
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_VEIL.key}@2",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_one_stays_the_ordinary_command_path(self):
        from commands.action import CmdCast

        # Non-damage scalable shape (see the scaled-cast test above): the
        # ordinary room command path must not trip the damaging-action gate.
        self._setup_caster(mastery=True)
        self._setup_target()
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        one_end = self.char1.traits.mp.value
        # Reset the gauge (and its regen remainder) so the second cast
        # accrues the same regen; the exact deduction is the differential.
        self.char1.traits.mp.current = 500
        self.char1.traits.mp.regen_remainder = 0.0
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@2=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        two_end = self.char1.traits.mp.value
        self.assertEqual(clock.tick, 12)
        base_mp = int(_T_OOC_HEAL.cost["mp"])
        # The ×2 rung deducts exactly one double-scale's worth more.
        self.assertEqual(
            one_end - two_end,
            scaled_mp_cost(base_mp, 2.0) - scaled_mp_cost(base_mp, 1.0),
        )
