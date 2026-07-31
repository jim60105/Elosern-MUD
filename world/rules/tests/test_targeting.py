"""Tests for shared target validation."""

from dataclasses import replace
import unittest

from world.rules.action import ActionRequest, RejectReason, RejectedAction
from world.rules.targeting import (
    Relation,
    RoomActionContext,
    resolve_targets,
    validate_faction,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    TargetSpec,
)


class _Trait:
    trait_type = "gauge"

    def __init__(self):
        self._data = {
            "base": 1,
            "mod": 0,
            "mult": 1,
            "current": 1,
        }

    @property
    def value(self):
        return self._data["current"]

    @value.setter
    def value(self, value):
        self._data["current"] = value


class _Traits:
    def __init__(self):
        self.hp = _Trait()


class _Entity:
    def __init__(self, key, location):
        self.key = key
        self.location = location
        self.traits = _Traits()


class TargetingTests(unittest.TestCase):
    def test_faction_truth_table(self):
        self.assertTrue(validate_faction(Relation.ENEMY, FactionConstraint.ANY))
        self.assertTrue(validate_faction(Relation.SELF, FactionConstraint.ALLY))
        self.assertTrue(validate_faction(Relation.ALLY, FactionConstraint.ALLY))
        self.assertTrue(validate_faction(Relation.ENEMY, FactionConstraint.ENEMY))
        self.assertFalse(validate_faction(Relation.ALLY, FactionConstraint.ENEMY))

    def test_room_context_never_invents_hostility(self):
        room = object()
        actor = _Entity("actor", room)
        target = _Entity("target", room)
        context = RoomActionContext(room)
        self.assertIs(context.relation_to(actor, target), Relation.ALLY)
        self.assertTrue(context.is_in_range(actor, target, SKILL_REGISTRY["fire_ball"]))

    def test_area_filters_invalid_candidates(self):
        room = object()
        actor = _Entity("actor", room)
        present = _Entity("present", room)
        absent = _Entity("absent", object())
        skill = replace(
            SKILL_REGISTRY["wind_blade"],
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [present, absent], RoomActionContext(room))
        self.assertEqual(resolve_targets(request, skill, [present, absent]), [present])

    def test_single_reports_presence_before_later_checks(self):
        room = object()
        actor = _Entity("actor", room)
        absent = _Entity("absent", object())
        absent.traits.hp.value = 0
        skill = replace(
            SKILL_REGISTRY["fire_ball"],
            target_spec=TargetSpec.SINGLE,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [absent], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [absent])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_NOT_PRESENT)

    def test_missing_hp_is_not_treated_as_a_living_target(self):
        room = object()
        actor = _Entity("actor", room)
        item = _Entity("item", room)
        del item.traits.hp
        skill = replace(
            SKILL_REGISTRY["fire_ball"],
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [item], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [item])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_DEAD)

    def test_context_polymorphism_changes_relation_not_skill_policy(self):
        room = object()
        actor = _Entity("actor", room)
        target = _Entity("target", room)
        skill = SKILL_REGISTRY["fire_ball"]
        room_request = ActionRequest(
            actor,
            skill.key,
            [target],
            RoomActionContext(room),
        )
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(room_request, skill, [target])
        self.assertIs(
            caught.exception.reason,
            RejectReason.TARGET_FACTION_FORBIDDEN,
        )

        class EnemyContext(RoomActionContext):
            battlefield = object()

            def relation_to(self, actor, target):
                return Relation.ENEMY

        enemy_request = ActionRequest(
            actor,
            skill.key,
            [target],
            EnemyContext(room),
        )
        self.assertEqual(
            resolve_targets(enemy_request, skill, [target]),
            [target],
        )
