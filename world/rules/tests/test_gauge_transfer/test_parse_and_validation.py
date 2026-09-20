"""Slice of ``test_gauge_transfer``: effect-string parsing and
fail-closed policy validation.
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
    _SKILL_MAP,
    _make_synth_transfer_skill,
)


class GaugeTransferParseAndValidationTests(GaugeTransferTestBase):
    """Tests for parse_effect, GaugeTransferEffect, GaugeTransferPolicy, and SkillDef policy validation."""

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_gauge_transfer_modes_parse_into_typed_dataclasses(self):
        # MP modes
        eff1 = parse_effect("gauge_transfer:mp:drain:fixed:5")
        self.assertEqual(eff1, GaugeTransferEffect("mp", "drain", "fixed", 5))

        eff2 = parse_effect("gauge_transfer:mp:drain:fraction:0.2")
        self.assertEqual(eff2, GaugeTransferEffect("mp", "drain", "fraction", 0.2))

        eff3 = parse_effect("gauge_transfer:mp:drain:all")
        self.assertEqual(eff3, GaugeTransferEffect("mp", "drain", "all", None))

        eff4 = parse_effect("gauge_transfer:mp:restore:fixed:40")
        self.assertEqual(eff4, GaugeTransferEffect("mp", "restore", "fixed", 40))

        # HP drain modes
        eff5 = parse_effect("gauge_transfer:hp:drain:fixed:10")
        self.assertEqual(eff5, GaugeTransferEffect("hp", "drain", "fixed", 10))

        eff6 = parse_effect("gauge_transfer:hp:drain:fraction:0.5")
        self.assertEqual(eff6, GaugeTransferEffect("hp", "drain", "fraction", 0.5))

        eff7 = parse_effect("gauge_transfer:hp:drain:all")
        self.assertEqual(eff7, GaugeTransferEffect("hp", "drain", "all", None))

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_closed_gauge_set_rejects_sp_and_unknown_gauges(self):
        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:sp:drain:fixed:5")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:stamina:drain:fixed:5")

        with self.assertRaises(ValueError):
            GaugeTransferEffect(gauge="sp", direction="drain", magnitude_mode="fixed", magnitude=5)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_hp_restore_rejected_at_parse_and_construction(self):
        # HP restoration is the heal effect's exclusive verb; gauge_transfer:hp:restore is forbidden
        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:fixed:40")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:fraction:0.5")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:all")

        with self.assertRaises(ValueError):
            GaugeTransferEffect(gauge="hp", direction="restore", magnitude_mode="fixed", magnitude=40)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_malformed_modes_and_magnitudes_fail_closed(self):
        malformed = [
            "gauge_transfer:mp:drain",
            "gauge_transfer:mp:drain:half",
            "gauge_transfer:mp:drain:fraction:1.5",
            "gauge_transfer:mp:drain:fraction:0.0",
            "gauge_transfer:mp:drain:fraction:-0.2",
            "gauge_transfer:mp:drain:fixed:0",
            "gauge_transfer:mp:drain:fixed:-5",
            "gauge_transfer:mp:drain:fixed:abc",
            "gauge_transfer:mp:drain:all:extra",
            "gauge_transfer",
            "gauge_transfer:mp",
        ]
        for m in malformed:
            with self.subTest(m=m):
                with self.assertRaises(ValueError):
                    parse_effect(m)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_gauge_transfer_policy_fail_closed_validation(self):
        # Invalid caster_recovery_share
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share=-0.1)
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share=1.5)
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share="0.5")  # not numeric

        # Valid share
        policy = GaugeTransferPolicy(caster_recovery_share=0.5)
        self.assertEqual(policy.caster_recovery_share, 0.5)

        # Unknown buff key in restore_bonus_per_stack
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(restore_bonus_per_stack=(("nonexistent_buff_key", 10),))

        # Valid restore_bonus_per_stack with ebbing keys
        policy_bonus = GaugeTransferPolicy(
            restore_bonus_per_stack=(("ebbing", 10), ("ebbing_deep", 10), ("ebbing_maelstrom", 10))
        )
        self.assertEqual(len(policy_bonus.restore_bonus_per_stack), 3)

        # Bonus on drain direction rejected at SkillDef construction
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_drain_with_bonus",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(
                    EffectPolicy(
                        transfer=GaugeTransferPolicy(restore_bonus_per_stack=(("ebbing", 10),))
                    ),
                ),
            )

        # Non-identity potency coefficient rejected at SkillDef construction
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_scaled_transfer",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(EffectPolicy(coefficient=1.5),),
            )

        # DamagePolicy on GaugeTransferEffect rejected
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_dmg_on_transfer",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(EffectPolicy(damage=DamagePolicy(predicate=())),),
            )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_every_shipped_registry_effect_still_parses(self):
        for skill in _SKILL_MAP.values():
            for effect_id in skill.effects:
                parsed = parse_effect(effect_id)
                self.assertIsNotNone(parsed)
