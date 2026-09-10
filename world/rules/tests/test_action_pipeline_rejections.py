"""Integration tests for named action-pipeline rejections."""

from tools.spec_traceability import covers_requirement

import inspect
from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    _adjusted_costs,
    _EFFECT_HANDLERS,
    ActionRequest,
    ActionResolver,
    CommitFailed,
    RejectedAction,
    RejectReason,
    SKILL_TIME_OVERRIDES,
)
from world.rules.action_preview import preview_skill
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.targeting import RoomActionContext, damage_requires_battlefield
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillDef, SkillKind, TargetSpec


_DAMAGE_PROBE = SkillDef(
    key="gate_probe",
    label="試探突刺",
    description="測試用的單體物理傷害技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 1},
    usable_out_of_combat=True,
    element="fire",
    effects=["damage:fire:physical"],
    category=SkillCategory.MARTIAL_ARTS,
)
_DRAIN_PROBE = replace(
    _DAMAGE_PROBE,
    key="gate_drain_probe",
    label="試探汲取",
    description="測試用的純粹愉悅汲取技能。",
    effects=["divine_drain:試探"],
)


class OutOfCombatDamageGateTests(EvenniaTestCase):
    """The second sanctioned combat-state gate: damage requires a battlefield."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="gate actor")
        self.target = create_object(PlayerCharacter, key="gate target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.db.skills = {
            "active": ["gate_probe", "gate_drain_probe"],
            "passive": [],
        }
        self.target.db.skills = {"active": [], "passive": []}
        for probe in (_DAMAGE_PROBE, _DRAIN_PROBE):
            SKILL_REGISTRY[probe.key] = probe
            self.addCleanup(SKILL_REGISTRY.pop, probe.key, None)
        self.room_context = RoomActionContext(self.actor.location)
        self.battlefield = Battlefield(
            {
                "party": frozenset({self.actor.key}),
                "foes": frozenset({self.target.key}),
            },
            {self.actor.key: self.actor, self.target.key: self.target},
        )

    def _request(self, skill_key, context, targets=()):
        return ActionRequest(self.actor, skill_key, list(targets), context)

    def _field_context(self):
        return BattlefieldActionContext(self.battlefield)

    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_damaging_usable_out_of_combat_skill_is_refused_without_battlefield(self):
        before_actor = deepcopy(dict(self.actor.traits.trait_data))
        before_target = deepcopy(dict(self.target.traits.trait_data))
        with (
            patch("world.rules.combat.roll_d100") as roller,
            patch("world.rules.action._commit", side_effect=AssertionError("committed")) as commit,
        ):
            result = ActionResolver.resolve(
                self._request("gate_probe", self.room_context, [self.target])
            )
        self.assertIs(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertIsNone(result.event_log)
        roller.assert_not_called()
        commit.assert_not_called()
        self.assertEqual(dict(self.actor.traits.trait_data), before_actor)
        self.assertEqual(dict(self.target.traits.trait_data), before_target)

    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_the_same_skill_resolves_normally_with_a_battlefield(self):
        before = self.target.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100) as roller:
            result = ActionResolver.resolve(
                self._request("gate_probe", self._field_context(), [self.target])
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(roller.call_count, 1)
        self.assertLess(self.target.traits.hp.value, before)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )

    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_non_damaging_out_of_combat_skill_is_unaffected(self):
        result = self.resolve_status_disguise()
        self.assertEqual(result.outcome, "success")
        self.assertIsNot(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)

    def resolve_status_disguise(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original, cost={}, effects=["set_disguise"]
        )
        self.addCleanup(SKILL_REGISTRY.__setitem__, "status_disguise", original)
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        context = RoomActionContext(
            self.actor.location, {"disguise": {"atk_phys": 1}}
        )
        return ActionResolver.resolve(
            ActionRequest(self.actor, "status_disguise", [], context)
        )

    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_indirect_hp_movement_is_not_damage_for_the_gate(self):
        result = ActionResolver.resolve(
            self._request("gate_drain_probe", self.room_context, [self.target])
        )
        self.assertIsNot(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertIsNot(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)

    @covers_requirement("action-resolution-pipeline::the-out-of-combat-gates-fire-in-a-fixed-specified-order")
    def test_unflagged_damage_skill_still_reports_the_flag_rejection(self):
        SKILL_REGISTRY["gate_probe"] = replace(_DAMAGE_PROBE, usable_out_of_combat=False)
        result = ActionResolver.resolve(
            self._request("gate_probe", self.room_context, [self.target])
        )
        self.assertIs(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)

    @covers_requirement("action-resolution-pipeline::the-out-of-combat-gates-fire-in-a-fixed-specified-order")
    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_preview_and_preflight_agree_on_which_reason_applies(self):
        for skill_key, expected in (
            ("gate_probe", RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET),
            ("flee", RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT),
        ):
            with self.subTest(skill_key=skill_key):
                if skill_key == "gate_probe":
                    actor_skills = ["gate_probe"]
                else:
                    actor_skills = ["flee"]
                self.actor.db.skills = {"active": actor_skills, "passive": []}
                preview = preview_skill(self.actor, skill_key, self.room_context)
                preflight = ActionResolver.preflight(
                    self._request(skill_key, self.room_context)
                )
                self.assertFalse(preview.enabled)
                self.assertIs(preview.reason, expected)
                self.assertIs(preflight.reason, expected)

    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_gate_is_per_request_not_a_catalog_snapshot(self):
        source = inspect.getsource(damage_requires_battlefield)
        self.assertNotIn("SKILL_REGISTRY", source)

        class _Ctx:
            def __init__(self, battlefield):
                self.battlefield = battlefield

        room, field = _Ctx(None), _Ctx(object())
        self.assertTrue(damage_requires_battlefield(_DAMAGE_PROBE, room))
        self.assertFalse(damage_requires_battlefield(_DAMAGE_PROBE, field))
        self.assertFalse(damage_requires_battlefield(_DRAIN_PROBE, room))
        self.assertFalse(
            damage_requires_battlefield(
                replace(_DRAIN_PROBE, effects=["set_disguise"]), room
            )
        )
        # A definition mutated per-request proves no registry-key dependence.
        per_call = replace(_DAMAGE_PROBE, effects=["set_disguise"])
        self.assertFalse(damage_requires_battlefield(per_call, room))


class ActionPipelineRejectionTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        self.context = RoomActionContext(
            self.actor.location,
            {"disguise": {"atk_phys": 1}},
        )

    def resolve(self, skill_key="status_disguise"):
        return ActionResolver.resolve(
            ActionRequest(self.actor, skill_key, [], self.context)
        )

    def test_unknown_skill(self):
        self.assertIs(self.resolve("missing").reason, RejectReason.UNKNOWN_SKILL)

    @covers_requirement("action-resolution-pipeline::actionresolver-is-the-sole-entry-point-for-every-skill-invocation")
    def test_passive_skill(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, kind=SkillKind.PASSIVE)
        try:
            self.assertIs(self.resolve().reason, RejectReason.SKILL_NOT_ACTIVE)
        finally:
            SKILL_REGISTRY["status_disguise"] = original

    @covers_requirement("skill-registry::body-enhancement-family-is-passive-not-active")
    def test_cast_of_reclassified_body_enhancement_is_rejected_as_passive(self):
        self.actor.db.skills = {"active": [], "passive": ["body_enhancement"]}
        self.assertIs(
            self.resolve("body_enhancement").reason,
            RejectReason.SKILL_NOT_ACTIVE,
        )

    @covers_requirement("skill-registry::flight-and-flash-step-are-passive")
    def test_cast_of_reclassified_flight_is_rejected_as_passive(self):
        self.actor.db.skills = {"active": [], "passive": ["flight"]}
        self.assertIs(
            self.resolve("flight").reason,
            RejectReason.SKILL_NOT_ACTIVE,
        )

    @covers_requirement("skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill")
    def test_cast_of_reclassified_dual_wield_style_is_rejected_as_passive(self):
        self.actor.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        self.assertIs(
            self.resolve("dual_wield_style").reason,
            RejectReason.SKILL_NOT_ACTIVE,
        )

    def test_unknown_effect(self):
        # An unregistered handler for the skill's own (non-damaging) effect:
        # the gate is irrelevant here — effect registration is checked later
        # in the pipeline, and the rejection must not commit anything.
        with patch.dict(_EFFECT_HANDLERS, {"set_disguise": None}):
            self.assertIs(self.resolve().reason, RejectReason.UNKNOWN_EFFECT_ID)
        self.assertIsNone(self.actor.db.disguised_stats)

    def test_malformed_time_cost_does_not_commit(self):
        SKILL_TIME_OVERRIDES["status_disguise"] = -1
        try:
            result = self.resolve()
            self.assertIs(result.reason, RejectReason.TIME_COST_LOOKUP_FAILED)
            self.assertIsNone(self.actor.db.disguised_stats)
        finally:
            SKILL_TIME_OVERRIDES.pop("status_disguise")

    def test_success_commits_disguise_and_emits_log(self):
        result = self.resolve()
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.db.disguised_stats, {"atk_phys": 1})
        self.assertEqual(result.time_cost_seconds, 6)
        self.assertEqual(result.event_log.entries[0].kind, "disguise_set")

    def test_every_named_rejection_maps_to_no_event_log(self):
        before = deepcopy(dict(self.actor.traits.trait_data))
        for reason in RejectReason:
            with self.subTest(reason=reason):
                if reason in {
                    RejectReason.COMMIT_FAILED,
                    RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                }:
                    patches = patch(
                        "world.rules.action._commit",
                        side_effect=CommitFailed(reason, "injected"),
                    )
                else:
                    patches = patch(
                        "world.rules.action._step1_ownership",
                        side_effect=RejectedAction(reason, "injected"),
                    )
                with patches:
                    result = self.resolve()
                self.assertIs(result.reason, reason)
                self.assertIsNone(result.event_log)
                self.assertEqual(dict(self.actor.traits.trait_data), before)

    def test_resource_read_does_not_advance_gauge_timestamp(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            cost={"mp": 100000},
        )
        self.actor.traits.mp._data["rate"] = 1
        self.actor.traits.mp._data["last_update"] = 123.0
        before = deepcopy(dict(self.actor.traits.trait_data))
        try:
            result = self.resolve()
        finally:
            SKILL_REGISTRY["status_disguise"] = original
        self.assertIs(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(dict(self.actor.traits.trait_data), before)


class AdjustedCostResolverTests(EvenniaTestCase):
    """mp_cost/sp_cost bundle sinks in the step-2 check, step-6 deduction, and log."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="cost-actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.traits.mp.base = 20
        self.actor.traits.mp.current = 20
        self.actor.traits.sp.base = 20
        self.actor.traits.sp.current = 20
        self.context = RoomActionContext(
            self.actor.location,
            {"disguise": {"atk_phys": 1}},
        )
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, cost={"mp": 10})
        self.addCleanup(
            lambda: SKILL_REGISTRY.__setitem__("status_disguise", original)
        )

    def _request(self):
        return ActionRequest(self.actor, "status_disguise", [], self.context)

    def _spend(self, result):
        return next(
            e for e in result.event_log.entries if e.kind == "resource_spend"
        )

    def _delta(self, result):
        return next(
            e for e in result.event_log.entries if e.kind == "trait_delta"
        )

    @covers_requirement(
        "combat-modifier-table::percentage-mp-cost-and-sp-cost-bundle-values-adjust-resource-checks-and-deductions"
    )
    def test_reduction_enables_a_cast_the_declared_cost_would_reject(self):
        self.actor.db.skills = {
            "active": ["status_disguise"],
            "passive": ["precise_mana_control"],
        }
        self.actor.traits.mp.current = 9
        result = ActionResolver.resolve(self._request())
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, 0)
        self.assertEqual(
            self._spend(result).data, {"resource_key": "mp", "amount": 9}
        )
        self.assertEqual(self._delta(result).data, {"trait_key": "mp", "delta": -9})

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_sp_reduction_floors_identically_in_check_and_deduction(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, cost={"sp": 10})
        try:
            self.actor.db.skills = {
                "active": ["status_disguise"],
                "passive": ["extreme_endurance"],
            }
            self.actor.traits.sp.current = 9
            result = ActionResolver.resolve(self._request())
        finally:
            SKILL_REGISTRY["status_disguise"] = original
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.sp.value, 0)
        self.assertEqual(
            self._spend(result).data, {"resource_key": "sp", "amount": 9}
        )

    @covers_requirement(
        "combat-modifier-table::percentage-mp-cost-and-sp-cost-bundle-values-adjust-resource-checks-and-deductions"
    )
    def test_adjusted_cost_clamps_at_zero_without_negative_staging(self):
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        self.actor.traits.mp.current = 0
        with patch(
            "world.rules.action.evaluate_combat_modifiers",
            return_value={"mp_cost": "-100%"},
        ):
            result = ActionResolver.resolve(self._request())
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, 0)
        self.assertEqual(
            self._spend(result).data, {"resource_key": "mp", "amount": 0}
        )
        self.assertEqual(self._delta(result).data, {"trait_key": "mp", "delta": 0})

    @covers_requirement(
        "combat-modifier-table::percentage-mp-cost-and-sp-cost-bundle-values-adjust-resource-checks-and-deductions"
    )
    def test_fractional_grant_percentage_floors_deterministically(self):
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        self.actor.traits.mp.current = 9
        with patch(
            "world.rules.action.evaluate_combat_modifiers",
            return_value={"mp_cost": "-5%"},
        ):
            result = ActionResolver.resolve(self._request())
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.value, 0)
        self.assertEqual(
            self._spend(result).data, {"resource_key": "mp", "amount": 9}
        )

    @covers_requirement(
        "combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment"
    )
    def test_zero_cost_skill_and_unmapped_resource_keys_are_unchanged(self):
        with patch(
            "world.rules.action.evaluate_combat_modifiers",
            return_value={"sp_cost": "-10%"},
        ):
            self.assertEqual(_adjusted_costs(self.actor, SKILL_REGISTRY["flee"]), {})
            original = SKILL_REGISTRY["status_disguise"]
            SKILL_REGISTRY["status_disguise"] = replace(original, cost={"mp": 10, "sp": 10})
            try:
                costs = _adjusted_costs(self.actor, SKILL_REGISTRY["status_disguise"])
            finally:
                SKILL_REGISTRY["status_disguise"] = original
        self.assertEqual(costs, {"mp": 10, "sp": 9})
