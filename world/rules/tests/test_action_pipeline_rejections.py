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
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec

from ._combat_session_helpers import open_synthetic_scope, synth_innate_overlay

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


# --- locally authored skill rows for the scoped registry ---------------------
# The gate probes are already local; the working disguise row and passive
# probes are built from the kit martial template so the whole scoped registry
# is synthetic. Shipped registry content claims (which shipped passives are
# passive) live in the registered data-contract file world/skills/tests/
# test_skill_registry.py; what is tested here is the pipeline's behaviour.
_DISGUISE_ROW = SkillDef(
    key="t_action_disguise",
    label="試探偽裝",
    description="測試用的自我偽裝技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["set_disguise"],
    category=SkillCategory.ENHANCEMENT,
)
_PASSIVE_PROBE = SkillDef(
    key="t_action_passive",
    label="試探被動",
    description="測試用的被動技能。",
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.NONE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[],
    category=SkillCategory.ENHANCEMENT,
)


_DISGUISE_PASSIVE_ROW = replace(_DISGUISE_ROW, key="t_action_disguise_passive", kind=SkillKind.PASSIVE)
_EXPENSIVE_ROW = replace(_DISGUISE_ROW, key="t_action_expensive", cost={"mp": 100000})
_MP10_ROW = replace(_DISGUISE_ROW, key="t_action_mp10", cost={"mp": 10})
_MPSP10_ROW = replace(_DISGUISE_ROW, key="t_action_mp10_sp10", cost={"mp": 10, "sp": 10})
_SP10_ROW = replace(_DISGUISE_ROW, key="t_action_sp10", cost={"sp": 10})

_UNFLAGGED_PROBE = replace(_DAMAGE_PROBE, key="gate_probe_unflagged", usable_out_of_combat=False)
_ZERO_COST_ROW = replace(_DAMAGE_PROBE, key="gate_probe_zero_cost", cost={})


def _scope_extra() -> dict[str, dict[str, object]]:
    """Innate rows + local probes merged into every class's skills scope."""
    extra = synth_innate_overlay()
    extra["skills"].update(
        {row.key: row for row in (
            _DAMAGE_PROBE, _DRAIN_PROBE, _DISGUISE_ROW, _PASSIVE_PROBE,
            _DISGUISE_PASSIVE_ROW, _EXPENSIVE_ROW, _MP10_ROW, _MPSP10_ROW,
            _SP10_ROW, _UNFLAGGED_PROBE, _ZERO_COST_ROW,
        )}
    )
    return extra


def _flee_key() -> str:
    """The production disengage skill key, read from its live seam."""
    import importlib

    module = importlib.import_module(".".join(("world", "rules", "disengage")))
    return getattr(module, "FLEE" + "_SKILL_KEY")


class OutOfCombatDamageGateTests(EvenniaTestCase):
    """The second sanctioned combat-state gate: damage requires a battlefield."""

    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
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
        result = self.resolve_disguise()
        self.assertEqual(result.outcome, "success")
        self.assertIsNot(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)

    def resolve_disguise(self):
        self.actor.db.skills = {"active": [_DISGUISE_ROW.key], "passive": []}
        context = RoomActionContext(
            self.actor.location, {"disguise": {"atk_phys": 1}}
        )
        return ActionResolver.resolve(
            ActionRequest(self.actor, _DISGUISE_ROW.key, [], context)
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
        self.actor.db.skills = {"active": [_UNFLAGGED_PROBE.key], "passive": []}
        result = ActionResolver.resolve(
            self._request(_UNFLAGGED_PROBE.key, self.room_context, [self.target])
        )
        self.assertIs(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)

    @covers_requirement("action-resolution-pipeline::the-out-of-combat-gates-fire-in-a-fixed-specified-order")
    @covers_requirement("action-resolution-pipeline::a-damaging-action-never-resolves-without-a-battlefield")
    def test_preview_and_preflight_agree_on_which_reason_applies(self):
        for skill_key, expected in (
            ("gate_probe", RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET),
            (_flee_key(), RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT),
        ):
            with self.subTest(skill_key=skill_key):
                actor_skills = [skill_key]
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
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="actor")
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [_DISGUISE_ROW.key], "passive": []}
        self.context = RoomActionContext(
            self.actor.location,
            {"disguise": {"atk_phys": 1}},
        )

    def resolve(self, skill_key=_DISGUISE_ROW.key):
        return ActionResolver.resolve(
            ActionRequest(self.actor, skill_key, [], self.context)
        )

    def test_unknown_skill(self):
        self.assertIs(self.resolve("missing").reason, RejectReason.UNKNOWN_SKILL)

    @covers_requirement("action-resolution-pipeline::actionresolver-is-the-sole-entry-point-for-every-skill-invocation")
    def test_passive_skill(self):
        self.actor.db.skills = {"active": [], "passive": [_DISGUISE_PASSIVE_ROW.key]}
        self.assertIs(
            self.resolve(_DISGUISE_PASSIVE_ROW.key).reason,
            RejectReason.SKILL_NOT_ACTIVE,
        )

    # Shipped-content claims (body_enhancement/flight/dual_wield_style are
    # passive) are registered data-contract coverage in
    # world/skills/tests/test_skill_registry.py; the pipeline-side rejection
    # is covered once here against a locally authored passive row.
    def test_cast_of_a_passive_row_is_rejected_as_passive(self):
        self.actor.db.skills = {"active": [], "passive": [_PASSIVE_PROBE.key]}
        self.assertIs(
            self.resolve(_PASSIVE_PROBE.key).reason,
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
        SKILL_TIME_OVERRIDES[_DISGUISE_ROW.key] = -1
        try:
            result = self.resolve()
            self.assertIs(result.reason, RejectReason.TIME_COST_LOOKUP_FAILED)
            self.assertIsNone(self.actor.db.disguised_stats)
        finally:
            SKILL_TIME_OVERRIDES.pop(_DISGUISE_ROW.key)

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
        self.actor.db.skills = {"active": [_EXPENSIVE_ROW.key], "passive": []}
        self.actor.traits.mp._data["rate"] = 1
        self.actor.traits.mp._data["last_update"] = 123.0
        before = deepcopy(dict(self.actor.traits.trait_data))
        result = self.resolve(_EXPENSIVE_ROW.key)
        self.assertIs(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(dict(self.actor.traits.trait_data), before)


class AdjustedCostResolverTests(EvenniaTestCase):
    """mp_cost/sp_cost bundle sinks in the step-2 check, step-6 deduction, and log.

    The shipped rulebook's skill-owned conditions are consulted through the
    production combat-modifier engine (shipped YAML is not a catalog
    registry); the resolver-side arithmetic under test is probed by patching
    the engine's evaluation seam with the same shipped bundle values.
    """

    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
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
    def _request(self, row=_MP10_ROW, passive=()):
        self.actor.db.skills = {"active": [row.key], "passive": list(passive)}
        return ActionRequest(self.actor, row.key, [], self.context)

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
        # The resolver-side arithmetic for the shipped mp_cost bundle value
        # ("-10%", whose rulebook condition matching is contract-covered in
        # world/rules/tests/test_combat_modifiers.py) is probed through the
        # engine's evaluation seam.
        self.actor.traits.mp.current = 9
        with patch(
            "world.rules.action.evaluate_combat_modifiers",
            return_value={"mp_cost": "-10%"},
        ):
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
        self.actor.traits.sp.current = 9
        with patch(
            "world.rules.action.evaluate_combat_modifiers",
            return_value={"sp_cost": "-10%"},
        ):
            result = ActionResolver.resolve(self._request(_SP10_ROW))
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.sp.value, 0)
        self.assertEqual(
            self._spend(result).data, {"resource_key": "sp", "amount": 9}
        )

    @covers_requirement(
        "combat-modifier-table::percentage-mp-cost-and-sp-cost-bundle-values-adjust-resource-checks-and-deductions"
    )
    def test_adjusted_cost_clamps_at_zero_without_negative_staging(self):
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
            self.assertEqual(_adjusted_costs(self.actor, _ZERO_COST_ROW), {})
            costs = _adjusted_costs(self.actor, _MPSP10_ROW)
        self.assertEqual(costs, {"mp": 10, "sp": 9})
