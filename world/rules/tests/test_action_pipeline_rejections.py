"""Integration tests for named action-pipeline rejections."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.elements import ELEMENT_REGISTRY
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
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, SkillKind


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
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            effects=["damage:fire:magic"],
        )
        try:
            with patch.dict(_EFFECT_HANDLERS, {"damage": None}):
                self.assertIs(self.resolve().reason, RejectReason.UNKNOWN_EFFECT_ID)
            self.assertIsNone(self.actor.db.disguised_stats)
        finally:
            SKILL_REGISTRY["status_disguise"] = original

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


class ElementTierCastGateTests(EvenniaTestCase):
    """element-mastery cast gate wired into the action pipeline.

    ``status_disguise`` is re-registered as a 賢者-tier fire spell (SELF
    target, 78 MP sits in the 賢者 single/direct band) so the gate scenarios
    have a real 賢者-tier elemental spell to cast without adding catalog
    content that belongs to the ``spell-catalog-*`` changes.
    """

    SAGE_FIRE_MP = 78

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="tier-caster")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.traits.mp.current = 200
        self.context = RoomActionContext(
            self.actor.location,
            {"disguise": {"atk_phys": 1}},
        )
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            element=ELEMENT_REGISTRY["fire"],
            cost={"mp": self.SAGE_FIRE_MP},
        )
        self.addCleanup(
            lambda: SKILL_REGISTRY.__setitem__("status_disguise", original)
        )

    def _request(self):
        return ActionRequest(self.actor, "status_disguise", [], self.context)

    @covers_requirement("action-resolution-pipeline::casting-an-elemental-spell-above-the-caster-s-tier-without-mastery-is-rejected")
    def test_preflight_rejects_under_tier_cast_without_mastery(self):
        self.actor.traits.magic_level.current = 20
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        result = ActionResolver.preflight(self._request())
        self.assertIs(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)

    def test_preflight_succeeds_via_numeric_level_alone(self):
        self.actor.traits.magic_level.current = 71
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        result = ActionResolver.preflight(self._request())
        self.assertIs(result.outcome, "success")

    def test_preflight_succeeds_via_mastery_ownership_alone(self):
        self.actor.traits.magic_level.current = 1
        self.actor.db.skills = {
            "active": ["status_disguise"],
            "passive": ["fire_mastery"],
        }
        result = ActionResolver.preflight(self._request())
        self.assertIs(result.outcome, "success")

    def test_preflight_rejects_malformed_elemental_cost_fail_closed(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            element=ELEMENT_REGISTRY["fire"],
            cost={"mp": 5},
        )
        try:
            self.actor.traits.magic_level.current = 71
            self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
            result = ActionResolver.preflight(self._request())
            self.assertIs(result.outcome, "rejected")
            self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)
        finally:
            SKILL_REGISTRY["status_disguise"] = original

    def test_resolve_rejects_under_tier_without_mastery(self):
        self.actor.traits.magic_level.current = 20
        self.actor.db.skills = {"active": ["status_disguise"], "passive": []}
        result = ActionResolver.resolve(self._request())
        self.assertIs(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.UNKNOWN_SKILL)
        self.assertIsNone(self.actor.db.disguised_stats)

    def test_resolve_succeeds_via_mastery_ownership_at_level_one(self):
        self.actor.traits.magic_level.current = 1
        self.actor.db.skills = {
            "active": ["status_disguise"],
            "passive": ["fire_mastery"],
        }
        result = ActionResolver.resolve(self._request())
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.db.disguised_stats, {"atk_phys": 1})


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
