"""Tests for effect registration and commit safety."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import growth_rate_multiplier
from world.rules.action import (
    ActionRequest,
    PendingEffect,
    RejectReason,
    SNAPSHOTTED_SURFACES,
    UnsnapshottedSurfaceError,
    _commit,
    _handle_sexual_event,
    _handle_buff_apply,
    _handle_confer_growth_rate,
    _handle_self_buff_apply,
    _step5_effect_resolution,
    register_effect_handler,
)
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY


class EffectRegistryTests(unittest.TestCase):
    def test_supported_handler_can_be_registered(self):
        register_effect_handler(
            "test_supported",
            lambda actor, targets, effect_id, context: [],
            frozenset({"traits"}),
            requires_event_context=frozenset(),
        )

    def test_unsupported_surface_fails_at_registration(self):
        with self.assertRaises(UnsnapshottedSurfaceError):
            register_effect_handler(
                "test_inventory",
                lambda actor, targets, effect_id, context: [],
                frozenset({"inventory"}),
                requires_event_context=frozenset(),
            )

    @covers_requirement("effect-context-validation::effect-handlers-declare-their-required-event-context")
    def test_every_registered_handler_declares_its_context_requirements(self):
        from world.rules.action import (
            _EFFECT_HANDLERS,
            _EFFECT_HANDLER_REQUIRED_CONTEXT,
        )

        self.assertEqual(
            set(_EFFECT_HANDLER_REQUIRED_CONTEXT),
            set(_EFFECT_HANDLERS),
        )
        for prefix, required in _EFFECT_HANDLER_REQUIRED_CONTEXT.items():
            self.assertIsInstance(required, frozenset, prefix)
            self.assertTrue(
                all(isinstance(key, str) for key in required),
                f"{prefix} declares non-string context keys",
            )

    @covers_requirement("action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated", "targeting-validation::single-and-area-target-specs-filter-candidates-differently")
    def test_commit_surface_gate_runs_before_any_mutation(self):
        applied = []
        effect = PendingEffect(
            entity=object(),
            description="bad",
            surfaces=frozenset({"inventory"}),
            apply=lambda: applied.append(True),
        )
        with self.assertRaises(Exception) as caught:
            _commit([effect])
        self.assertEqual(caught.exception.reason, RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE)
        self.assertEqual(applied, [])
        self.assertEqual(
            SNAPSHOTTED_SURFACES,
            frozenset(
                {
                    "traits",
                    "sexual",
                    "buffs",
                    "skill_grants",
                    "progression",
                    "battlefield",
                    "quest_log",
                    "instance_pin",
                }
            ),
        )

    def test_sexual_handler_rejects_cleanly_when_module_is_unavailable(self):
        with patch.dict(
            "sys.modules",
            {"world.rules.sexual_transitions": None},
        ):
            with self.assertRaises(Exception) as caught:
                _handle_sexual_event(
                    object(),
                    [object()],
                    "sexual_event:stimulus_applied",
                    {},
                )
        self.assertEqual(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )


class LandedEffectHandlerTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="effect-target")
        self.entity.race = "human"
        self.entity.apply_race_baseline()

    def test_buff_apply_stages_and_commits_each_target(self):
        effects = _handle_buff_apply(
            self.entity,
            [self.entity],
            "buff_apply:paralysis",
            {},
        )
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in effects
        ]
        _commit(effects)
        self.assertIn("paralysis", self.entity.buffs.all)

    def test_self_buff_apply_targets_the_caster_without_a_target(self):
        effects = _handle_self_buff_apply(
            self.entity,
            [],
            "self_buff_apply:focus",
            {},
        )
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in effects
        ]
        _commit(effects)
        self.assertIn("focus", self.entity.buffs.all)

    def test_conferred_growth_rate_uses_landed_buff_seam(self):
        effects = _handle_confer_growth_rate(
            self.entity,
            [self.entity],
            "confer_growth_rate",
            {"confer_scale": 0.5},
        )
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in effects
        ]
        _commit(effects)
        self.assertEqual(growth_rate_multiplier(self.entity), 0.5)

    def test_malformed_handler_result_is_a_named_rejection(self):
        class Actor:
            key = "actor"

        request = ActionRequest(
            Actor(),
            "status_disguise",
            [],
            RoomActionContext(None),
        )
        skill = replace(
            SKILL_REGISTRY["status_disguise"],
            effects=["test_malformed:value"],
        )
        register_effect_handler(
            "test_malformed",
            lambda actor, targets, effect_id, context: [object()],
            frozenset({"traits"}),
            requires_event_context=frozenset(),
        )
        with self.assertRaises(Exception) as caught:
            _step5_effect_resolution(request, skill, [])
        self.assertEqual(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )
