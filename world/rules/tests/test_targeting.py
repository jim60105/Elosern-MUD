"""Tests for shared target validation."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from types import SimpleNamespace
import unittest

from world.rules.action import ActionRequest, RejectReason, RejectedAction
from world.rules.targeting import (
    Relation,
    RoomActionContext,
    expand_target_shorthand,
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

    @covers_requirement("targeting-validation::out-of-combat-targeting-has-no-hostility-model", "targeting-validation::target-resolution-runs-four-ordered-validations")
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

    @covers_requirement("targeting-validation::factionconstraint-is-read-from-skilldef-not-declared-by-the-caller")
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


class _BattlefieldContext(RoomActionContext):
    """A room-like context backed by a fake battlefield roster."""

    def __init__(self, room, roster):
        self.room = room
        self.battlefield = SimpleNamespace(roster=roster)
        self.event_context = {}

    def relation_to(self, actor, target):
        return Relation.ALLY if target is not actor else Relation.SELF


class TightenedShapeTests(unittest.TestCase):
    def _actor(self):
        return _Entity("actor", object())

    def _target(self, key="target"):
        return _Entity(key, object())

    def _request(self, actor, skill_key, targets, context=None):
        context = context or RoomActionContext(object())
        return ActionRequest(actor, skill_key, targets, context)

    def test_none_rejects_supplied_targets(self):
        actor = self._actor()
        skill = replace(
            SKILL_REGISTRY["basic_attack"], target_spec=TargetSpec.NONE
        )
        target = self._target()
        request = self._request(actor, skill.key, [target])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [target])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

        request = self._request(actor, skill.key, [])
        self.assertEqual(resolve_targets(request, skill, []), [])

    def test_self_accepts_empty_or_actor_only(self):
        actor = self._actor()
        skill = SKILL_REGISTRY["body_enhancement"]
        request = self._request(actor, skill.key, [])
        self.assertEqual(resolve_targets(request, skill, []), [actor])

        request = self._request(actor, skill.key, [actor])
        self.assertEqual(resolve_targets(request, skill, [actor]), [actor])

        other = self._target("other")
        request = self._request(actor, skill.key, [other])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [other])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_single_rejects_non_unit_cardinality(self):
        actor = self._actor()
        skill = SKILL_REGISTRY["basic_attack"]
        request = self._request(actor, skill.key, [])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_single_rejects_shorthand_even_when_one_target(self):
        actor = self._actor()
        skill = replace(SKILL_REGISTRY["basic_attack"], target_spec=TargetSpec.SINGLE)
        roster = {actor.key: actor}
        context = _BattlefieldContext(object(), roster)
        request = self._request(actor, skill.key, "all-enemies", context)
        from world.rules.action import _step3_targeting

        with self.assertRaises(RejectedAction) as caught:
            _step3_targeting(request, skill)
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_area_rejects_duplicate_explicit_targets(self):
        actor = self._actor()
        target = self._target()
        skill = replace(SKILL_REGISTRY["wind_blade"], faction_constraint=FactionConstraint.ANY)
        request = self._request(actor, skill.key, [target, target])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [target, target])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_area_rejects_empty_explicit_input(self):
        actor = self._actor()
        skill = SKILL_REGISTRY["wind_blade"]
        request = self._request(actor, skill.key, [])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [])
        self.assertIs(caught.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_area_filters_invalid_candidates_and_keeps_valid(self):
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

    def test_area_rejects_when_all_candidates_filtered(self):
        actor = self._actor()
        room = object()
        dead = _Entity("dead", room)
        dead.traits.hp.value = 0
        skill = replace(
            SKILL_REGISTRY["wind_blade"],
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [dead], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request, skill, [dead])
        self.assertIs(caught.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_expand_shorthand_out_of_combat_rejects(self):
        actor = self._actor()
        context = RoomActionContext(object())
        with self.assertRaises(RejectedAction) as caught:
            expand_target_shorthand(actor, context, "all-enemies")
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_all_allies_includes_actor_and_team(self):
        actor = _Entity("actor", object())
        ally = _Entity("ally", object())
        roster = {actor.key: actor, ally.key: ally}
        context = _BattlefieldContext(object(), roster)
        expanded = expand_target_shorthand(actor, context, "all-allies")
        self.assertEqual(set(expanded), {actor, ally})

    def test_mapping_roster_expands_to_values_not_keys(self):
        actor = _Entity("actor", object())
        ally = _Entity("ally", object())
        roster = {actor.key: actor, ally.key: ally}
        context = _BattlefieldContext(object(), roster)
        expanded = expand_target_shorthand(actor, context, "all")
        self.assertTrue(all(hasattr(item, "traits") for item in expanded))
