"""Slice of ``test_gauge_transfer``: regen-lock interaction with the
world clock.
"""
import importlib
from typing import Any
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _handle_gauge_transfer,
    _stored_trait_value,
    plan_effect_audiences,
    stored_gauge_pair,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    active_stack_count,
    apply_buff,
)
from world.rules.clock import AdvanceSource, WorldClock, _settle_gauge_regen
from world.rules.clock import _settle_buffs_and_decay
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.mp_flow import apply_mp_change
from world.rules.targeting import RoomActionContext
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferEffect,
    GaugeTransferPolicy,
    parse_effect,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)


from ._support import (
    GaugeTransferTestBase,
)


class RegenLockAndClockTests(GaugeTransferTestBase):
    """Behavior tests for mp_regen_lock, closed-form regen scale, and item bypass."""

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_mp_regen_lock_freezes_regen_and_preserves_remainder(self):
        """Scenario: Locked gauge regenerates nothing while the lock lives."""
        self.target.traits.mp.current = 20
        self.target.traits.mp.regen_remainder = 0.5

        # Apply mp_regen_lock debuff
        apply_buff(self.target, "mp_regen_lock")

        # Verify combat modifier reports mp_regen_scale: 0
        mods = evaluate_combat_modifiers(self.target)
        self.assertEqual(mods.get("mp_regen_scale"), 0)

        # Advance gauge regen
        _settle_gauge_regen([self.target], 30)
        self.assertEqual(int(self.target.traits.mp.current), 20)
        self.assertEqual(self.target.traits.mp.regen_remainder, 0.5)

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_authored_grants_bypass_regen_lock(self):
        """Scenario: Authored grants bypass the lock: direct MP changes work while regen is locked."""
        self.target.traits.mp.current = 20
        apply_buff(self.target, "mp_regen_lock")

        # Authored restore / direct change
        apply_mp_change(self.target, 30)
        self.assertEqual(int(self.target.traits.mp.current), 50)

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_mp_regen_lock_expiry_resumes_closed_form_regen(self):
        """Scenario: Locked gauge freezes regen, and expiry resumes closed-form regen with remainder intact."""
        self.target.traits.mp.current = 20
        self.target.traits.mp.rate = 1.0
        self.target.traits.mp.regen_remainder = 0.35

        apply_buff(self.target, "mp_regen_lock")

        # Locked: 30s yields 0 gain, remainder untouched
        _settle_gauge_regen([self.target], 30)
        self.assertEqual(int(self.target.traits.mp.current), 20)
        self.assertEqual(self.target.traits.mp.regen_remainder, 0.35)

        # Decay buffs past duration (60s duration -> 61s elapsed)
        _settle_buffs_and_decay([self.target], 61)
        mods = evaluate_combat_modifiers(self.target)
        self.assertNotIn("mp_regen_scale", mods)

        # Lock expired: 10s yields +10 MP, remainder preserved
        _settle_gauge_regen([self.target], 10)
        self.assertEqual(int(self.target.traits.mp.current), 30)
        self.assertAlmostEqual(self.target.traits.mp.regen_remainder, 0.35, places=5)
