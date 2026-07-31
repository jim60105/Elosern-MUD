"""Integration tests for named action-pipeline rejections."""

from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    RejectedAction,
    RejectReason,
    SKILL_TIME_OVERRIDES,
)
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, SkillKind


class ActionPipelineRejectionTests(EvenniaTest):
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

    def test_passive_skill(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(original, kind=SkillKind.PASSIVE)
        try:
            self.assertIs(self.resolve().reason, RejectReason.SKILL_NOT_ACTIVE)
        finally:
            SKILL_REGISTRY["status_disguise"] = original

    def test_unknown_effect(self):
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            effects=["unknown:test"],
        )
        try:
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
