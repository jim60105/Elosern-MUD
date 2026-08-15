"""Tests for effect registration and commit safety."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff, _handle_cleanse, growth_rate_multiplier
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    SNAPSHOTTED_SURFACES,
    UnsnapshottedSurfaceError,
    _EFFECT_HANDLERS,
    _commit,
    _handle_sexual_event,
    _handle_buff_apply,
    _handle_confer_growth_rate,
    _handle_self_buff_apply,
    _step5_effect_resolution,
    _step7_build_event_log,
    register_effect_handler,
)
from world.rules.targeting import RoomActionContext
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)

# Test-only skill: no shipped skill declares `cleanse:status` yet (the
# spell-catalog changes own that content), and the end-to-end scenario needs
# exactly one such castable entry.
PURIFY_TEST_SKILL = SkillDef(
    key="test_purify",
    label="測試淨化",
    description="測試用：清除目標的異常狀態。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element="light",
    effects=["cleanse:status"],
    faction_constraint=FactionConstraint.ANY,
)


class EffectRegistryTests(unittest.TestCase):
    def test_supported_handler_can_be_registered(self):
        register_effect_handler(
            "test_supported",
            lambda actor, targets, effect_id, context, scale: [],
            frozenset({"traits"}),
            requires_event_context=frozenset(),
        )

    def test_unsupported_surface_fails_at_registration(self):
        with self.assertRaises(UnsnapshottedSurfaceError):
            register_effect_handler(
                "test_inventory",
                lambda actor, targets, effect_id, context, scale: [],
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
                    1.0,
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
            1.0,
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
            1.0,
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
            1.0,
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
            "fire_ball",
            [],
            RoomActionContext(None),
        )
        skill = SKILL_REGISTRY["fire_ball"]
        with patch.dict(
            _EFFECT_HANDLERS,
            {"damage": lambda actor, targets, effect_id, context, scale: [object()]},
        ):
            with self.assertRaises(Exception) as caught:
                _step5_effect_resolution(request, skill, [])
        self.assertEqual(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )


class DamagingBuffSourceIdentityTests(EvenniaTest):
    """fix-dot-kill-credit: damaging rate buffs carry authoritative source identity."""

    def setUp(self):
        super().setUp()
        self.caster = create_object(PlayerCharacter, key="source-caster")
        self.caster.race = "human"
        self.caster.apply_race_baseline()
        self.target = create_object(PlayerCharacter, key="source-target")
        self.target.race = "human"
        self.target.apply_race_baseline()

    def _stage_and_commit(self, effects):
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in effects
        ]
        _commit(effects)
        return effects

    @covers_requirement("buff-handler-integration::damaging-rate-buffs-persist-a-validated-effect-source-identity-in-the-buff-cache")
    def test_damaging_buff_apply_stores_the_caster_dbref(self):
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                "buff_apply:fire_scorch",
                {},
                1.0,
            )
        )
        buff = self.target.buffs.all["fire_scorch"]
        self.assertEqual(buff.source_pk, int(self.caster.pk))

    def test_caller_supplied_source_pk_cannot_override_attribution(self):
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                "buff_apply:fire_scorch",
                {"buff_kwargs": {"source_pk": int(self.target.pk)}},
                1.0,
            )
        )
        buff = self.target.buffs.all["fire_scorch"]
        self.assertEqual(buff.source_pk, int(self.caster.pk))

    def test_actor_without_positive_int_pk_rejects_before_commit(self):
        class Actor:
            key = "no-dbref"

        with self.assertRaises(Exception) as caught:
            _handle_buff_apply(
                Actor(),
                [self.target],
                "buff_apply:fire_scorch",
                {},
                1.0,
            )
        self.assertEqual(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )
        self.assertNotIn("fire_scorch", self.target.buffs.all)

    def test_direct_add_buff_omits_source_pk_for_unattributed_ticks(self):
        _add_buff(self.target, "poisoned")
        buff = self.target.buffs.all["poisoned"]
        self.assertIsNone(getattr(buff, "source_pk", None))

    def test_reapplication_replaces_source_with_the_new_caster(self):
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                "buff_apply:fire_scorch",
                {},
                1.0,
            )
        )
        other = create_object(PlayerCharacter, key="other-caster")
        other.race = "human"
        other.apply_race_baseline()
        self._stage_and_commit(
            _handle_buff_apply(
                other,
                [self.target],
                "buff_apply:fire_scorch",
                {},
                1.0,
            )
        )
        buff = self.target.buffs.all["fire_scorch"]
        self.assertEqual(buff.source_pk, int(other.pk))

    def test_refresh_without_source_keeps_prior_attribution(self):
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                "buff_apply:fire_scorch",
                {},
                1.0,
            )
        )
        _add_buff(self.target, "fire_scorch")
        buff = self.target.buffs.all["fire_scorch"]
        self.assertEqual(buff.source_pk, int(self.caster.pk))

    def test_non_damaging_buff_apply_stores_no_source_pk(self):
        self._stage_and_commit(
            _handle_buff_apply(
                self.caster,
                [self.target],
                "buff_apply:paralysis",
                {},
                1.0,
            )
        )
        buff = self.target.buffs.all["paralysis"]
        self.assertIsNone(getattr(buff, "source_pk", None))


class CleanseHandlerTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="cleanse-target")
        self.entity.race = "human"
        self.entity.apply_race_baseline()

    def _stage_and_commit(self, effects):
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in effects
        ]
        _commit(effects)
        return effects

    @covers_requirement("cleanse-effect-handler::cleanse-status-removes-every-active-debuff-polarity-buff-from-the-target")
    def test_cleanse_removes_an_active_debuff(self):
        _add_buff(self.entity, "poisoned")
        effects = self._stage_and_commit(
            _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        )
        self.assertNotIn("poisoned", self.entity.buffs.all)
        self.assertEqual(
            effects[0].description,
            "buffs_cleansed|cleanse-target|1",
        )

    @covers_requirement("cleanse-effect-handler::cleanse-status-removes-every-active-debuff-polarity-buff-from-the-target")
    def test_cleanse_does_not_remove_a_beneficial_buff(self):
        _add_buff(self.entity, "focus")
        effects = _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        self.assertEqual(effects, [])
        self._stage_and_commit(effects)
        self.assertIn("focus", self.entity.buffs.all)

    def test_cleanse_removes_only_debuffs_when_both_are_active(self):
        _add_buff(self.entity, "poisoned")
        _add_buff(self.entity, "focus")
        self._stage_and_commit(
            _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        )
        self.assertNotIn("poisoned", self.entity.buffs.all)
        self.assertIn("focus", self.entity.buffs.all)

    def test_cleanse_with_no_active_debuffs_stages_nothing(self):
        effects = _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        self.assertEqual(effects, [])
        self._stage_and_commit(effects)

    def test_cleanse_multi_target_stages_one_entry_per_target(self):
        other = create_object(PlayerCharacter, key="cleanse-target-2")
        other.race = "human"
        other.apply_race_baseline()
        for entity in (self.entity, other):
            _add_buff(entity, "poisoned")
        effects = self._stage_and_commit(
            _handle_cleanse(
                self.entity,
                [self.entity, other],
                "cleanse:status",
                {},
                1.0,
            )
        )
        self.assertNotIn("poisoned", self.entity.buffs.all)
        self.assertNotIn("poisoned", other.buffs.all)
        self.assertEqual(len(effects), 2)

    def test_cleanse_ignores_paused_and_expired_debuffs(self):
        _add_buff(self.entity, "poisoned")
        _add_buff(self.entity, "paralysis")
        _add_buff(self.entity, "fear")
        self.entity.buffs.all["poisoned"].remaining_seconds = 0
        self.entity.buffs.all["paralysis"].paused = True
        effects = self._stage_and_commit(
            _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        )
        self.assertNotIn("fear", self.entity.buffs.all)
        self.assertIn("poisoned", self.entity.buffs.all)
        self.assertIn("paralysis", self.entity.buffs.all)
        self.assertEqual(effects[0].description, "buffs_cleansed|cleanse-target|1")

    def test_cleanse_commit_failure_restores_the_debuff(self):
        _add_buff(self.entity, "poisoned")
        effects = [
            replace(effect, surfaces=frozenset({"buffs"}))
            for effect in _handle_cleanse(
                self.entity, [self.entity], "cleanse:status", {}, 1.0
            )
        ]
        effects.append(
            PendingEffect(
                self.entity,
                "injected failure",
                frozenset({"traits"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            )
        )
        with self.assertRaises(CommitFailed):
            _commit(effects)
        self.assertIn("poisoned", self.entity.buffs.all)

    def test_cleanse_resolves_end_to_end_through_the_action_resolver(self):
        SKILL_REGISTRY[PURIFY_TEST_SKILL.key] = PURIFY_TEST_SKILL
        try:
            self.entity.db.skills = {
                "active": [PURIFY_TEST_SKILL.key],
                "passive": [],
            }
            _add_buff(self.entity, "poisoned")
            request = ActionRequest(
                self.entity,
                PURIFY_TEST_SKILL.key,
                [self.entity],
                RoomActionContext(self.room1),
            )
            result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "success")
            self.assertNotIn("poisoned", self.entity.buffs.all)
            self.assertIn(
                "buffs_cleansed",
                [entry.kind for entry in result.event_log.entries],
            )
        finally:
            SKILL_REGISTRY.pop(PURIFY_TEST_SKILL.key, None)

    def test_cleanse_rejects_an_unknown_scope(self):
        with self.assertRaises(ValueError):
            _handle_cleanse(self.entity, [self.entity], "cleanse:banana", {}, 1.0)

    def test_cleanse_event_log_entry_reports_the_cleansed_count(self):
        class Actor:
            key = "cleanse-caster"

        _add_buff(self.entity, "poisoned")
        _add_buff(self.entity, "paralysis")
        effects = self._stage_and_commit(
            _handle_cleanse(self.entity, [self.entity], "cleanse:status", {}, 1.0)
        )
        request = ActionRequest(
            Actor(),
            "fire_ball",
            [],
            RoomActionContext(None),
        )
        log = _step7_build_event_log(request, SKILL_REGISTRY["fire_ball"], effects)
        entry = log.entries[0]
        self.assertEqual(entry.kind, "buffs_cleansed")
        self.assertEqual(entry.data, {"count": 2})
        self.assertEqual(entry.text_template, "{actor} 淨化了 {target} 的異常狀態。")
