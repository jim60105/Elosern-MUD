"""Tests for shared target validation."""

from tools.spec_traceability import covers_requirement

from dataclasses import FrozenInstanceError, replace
from inspect import signature
from types import SimpleNamespace
import ast
import pathlib
import unittest

from world.rules.action import ActionRequest, RejectReason, RejectedAction
from world.rules.targeting import (
    Relation,
    RoomActionContext,
    TargetRequirement,
    expand_target_shorthand,
    resolve_targets,
    validate_faction,
)
from world.skills.registry import (
    FactionConstraint,
    TargetSpec,
)
from world.tests.synthetic_data import SYNTH_ACT_SKILL, SYNTH_SKILLS, make_skill

# File-local synthetic skill shapes (test-data-independence): the targeting
# resolver consumes the requirement a SkillDef produces and never consults
# the registry, so invented rows exercise every target-spec/faction branch
# identically.
_T_ANY_SINGLE = SYNTH_SKILLS["t_ember_burst"]  # SINGLE + ANY + damage
_T_ANY_AREA = replace(
    _T_ANY_SINGLE,
    key="t_glitter_cascade",
    label="瀉光瀑",
    description="將熾燼化為覆蓋戰場的光瀑。",
    target_spec=TargetSpec.AREA,
)
_T_ZERO_COST_SINGLE = replace(
    SYNTH_SKILLS["t_cinder_cleave"],
    key="t_plain_thrust",
    label="樸刺",
    description="毫無花樣地刺向單一目標。",
    effects=["damage:physical:physical"],
)
_T_SELF_SHAPE = make_skill(
    "t_bark_skin",
    label="樹皮膚",
    description="讓皮膚硬化如樹皮。",
    target_spec=TargetSpec.SELF,
    effects=["stat_multiply:defense:1.1"],
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


class TargetRequirementTests(unittest.TestCase):
    """TargetRequirement is the resolver's definition-owned input contract."""

    def test_item_relevant_shapes_and_defaults(self):
        # The four distinct requirement shapes covering the five item scopes
        # of the approved item-effect model, plus the skill-side shape the
        # resolver enforces through forbid_self.
        self_only = TargetRequirement(TargetSpec.SELF, FactionConstraint.SELF_ONLY)
        single = TargetRequirement(TargetSpec.SINGLE)
        area = TargetRequirement(TargetSpec.AREA)
        sexual_single = TargetRequirement(
            TargetSpec.SINGLE, FactionConstraint.ANY, forbid_self=True
        )
        self.assertIs(self_only.spec, TargetSpec.SELF)
        self.assertIs(self_only.faction, FactionConstraint.SELF_ONLY)
        self.assertIs(single.spec, TargetSpec.SINGLE)
        self.assertIs(single.faction, FactionConstraint.ANY)
        self.assertIs(area.spec, TargetSpec.AREA)
        self.assertIs(area.faction, FactionConstraint.ANY)
        self.assertTrue(sexual_single.forbid_self)
        # faction defaults to ANY and forbid_self defaults to False.
        self.assertFalse(single.forbid_self)
        self.assertFalse(area.forbid_self)
        self.assertFalse(self_only.forbid_self)
        # The three group scopes (all-allies/all-enemies/all) share this one
        # AREA/ANY value.
        self.assertEqual(area, TargetRequirement(TargetSpec.AREA))

    def test_requirement_is_frozen(self):
        requirement = TargetRequirement(TargetSpec.SINGLE)
        with self.assertRaises(FrozenInstanceError):
            requirement.forbid_self = True
        with self.assertRaises(FrozenInstanceError):
            requirement.spec = TargetSpec.AREA

    def test_skill_produced_and_direct_requirements_resolve_identically(self):
        # The resolver never inspects the definition behind the requirement:
        # one value produced by a skill and one constructed with no
        # definition behind it accept and reject the same candidates for the
        # same reasons.
        room = object()
        actor = _Entity("actor", room)
        from_skill = SYNTH_ACT_SKILL.target_requirement
        direct = TargetRequirement(
            SYNTH_ACT_SKILL.target_spec,
            SYNTH_ACT_SKILL.faction_constraint,
            forbid_self=True,
        )
        self.assertEqual(from_skill, direct)
        partner = _Entity("partner", room)

        for requirement in (from_skill, direct):
            with self.subTest("single-ally-accepted"):
                self.assertEqual(
                    resolve_targets(actor, RoomActionContext(room), requirement, [partner]),
                    [partner],
                )
            with self.subTest("self-rejected"):
                with self.assertRaises(RejectedAction) as caught:
                    resolve_targets(actor, RoomActionContext(room), requirement, [actor])
                self.assertIs(
                    caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH
                )
                self.assertEqual(
                    caught.exception.detail,
                    "a sexual act targeting another entity requires a target "
                    "other than the actor",
                )
            with self.subTest("self-only-parity"):
                # A SELF_ONLY requirement (no forbid_self) rejects a non-actor
                # identically through both producers.
                self_only = TargetRequirement(
                    TargetSpec.SINGLE, FactionConstraint.SELF_ONLY
                )
                with self.assertRaises(RejectedAction) as caught:
                    resolve_targets(
                        actor, RoomActionContext(room), self_only, [partner]
                    )
                self.assertIs(
                    caught.exception.reason, RejectReason.TARGET_FACTION_FORBIDDEN
                )


class ResolverVocabularyTests(unittest.TestCase):
    """Structural guarantees the refactor makes machine-checkable."""

    def _targeting_tree(self) -> ast.Module:
        return ast.parse(
            pathlib.Path(
                pathlib.Path(__file__).resolve().parents[1], "targeting.py"
            ).read_text(encoding="utf-8")
        )

    def _imported_names(self) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(self._targeting_tree()):
            if isinstance(node, ast.ImportFrom):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
        return names

    @covers_requirement("sexual-act-seeds::a-single-target-sexual-act-cannot-be-self-cast")
    def test_targeting_imports_no_skill_category_vocabulary(self):
        imported = self._imported_names()
        for forbidden in ("SkillCategory", "SkillDef", "DamageEffect"):
            self.assertNotIn(forbidden, imported)

    @covers_requirement("targeting-validation::actioncontext-is-a-shared-protocol-implemented-differently-by-combat-and-non-combat")
    def test_is_in_range_exposes_exactly_actor_and_target(self):
        # No shipped implementation can observe what is being used: range is
        # a property of the two entities and the world, never of a
        # definition. The signature itself is the guarantee.
        from world.rules.combat import BattlefieldActionContext

        for implementation in (RoomActionContext, BattlefieldActionContext):
            with self.subTest(implementation=implementation.__name__):
                self.assertEqual(
                    list(signature(implementation.is_in_range).parameters),
                    ["self", "actor", "target"],
                )


class TargetingTests(unittest.TestCase):
    @covers_requirement("targeting-validation::target-resolution-runs-four-ordered-validations")
    def test_faction_truth_table(self):
        # ANY (the only shipped constraint) accepts every relation; SELF_ONLY
        # accepts only the actor; legacy ALLY/ENEMY values restrict nothing.
        self.assertTrue(validate_faction(Relation.SELF, FactionConstraint.ANY))
        self.assertTrue(validate_faction(Relation.ALLY, FactionConstraint.ANY))
        self.assertTrue(validate_faction(Relation.ENEMY, FactionConstraint.ANY))
        self.assertTrue(validate_faction(Relation.SELF, FactionConstraint.SELF_ONLY))
        self.assertFalse(validate_faction(Relation.ALLY, FactionConstraint.SELF_ONLY))
        self.assertFalse(validate_faction(Relation.ENEMY, FactionConstraint.SELF_ONLY))
        self.assertTrue(validate_faction(Relation.ALLY, FactionConstraint.ALLY))
        self.assertTrue(validate_faction(Relation.ENEMY, FactionConstraint.ALLY))
        self.assertTrue(validate_faction(Relation.ALLY, FactionConstraint.ENEMY))
        self.assertTrue(validate_faction(Relation.ENEMY, FactionConstraint.ENEMY))

    def test_room_context_never_invents_hostility(self):
        room = object()
        actor = _Entity("actor", room)
        target = _Entity("target", room)
        context = RoomActionContext(room)
        self.assertIs(context.relation_to(actor, target), Relation.ALLY)
        self.assertTrue(context.is_in_range(actor, target))

    def test_area_filters_invalid_candidates(self):
        room = object()
        actor = _Entity("actor", room)
        present = _Entity("present", room)
        absent = _Entity("absent", object())
        skill = replace(
            _T_ANY_AREA,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [present, absent], RoomActionContext(room))
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, [present, absent]), [present])

    @covers_requirement("targeting-validation::out-of-combat-targeting-has-no-hostility-model", "targeting-validation::target-resolution-runs-four-ordered-validations")
    def test_single_reports_presence_before_later_checks(self):
        room = object()
        actor = _Entity("actor", room)
        absent = _Entity("absent", object())
        absent.traits.hp.value = 0
        skill = replace(
            _T_ANY_SINGLE,
            target_spec=TargetSpec.SINGLE,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [absent], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [absent])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_NOT_PRESENT)

    def test_missing_hp_is_not_treated_as_a_living_target(self):
        room = object()
        actor = _Entity("actor", room)
        item = _Entity("item", room)
        del item.traits.hp
        skill = replace(
            _T_ANY_SINGLE,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [item], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [item])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_DEAD)

    @covers_requirement("targeting-validation::targeting-rules-are-supplied-by-a-definition-owned-targetrequirement")
    def test_context_polymorphism_changes_relation_not_skill_policy(self):
        room = object()
        actor = _Entity("actor", room)
        target = _Entity("target", room)
        skill = replace(
            _T_ANY_SINGLE,
            faction_constraint=FactionConstraint.SELF_ONLY,
        )
        room_request = ActionRequest(
            actor,
            skill.key,
            [target],
            RoomActionContext(room),
        )
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(room_request.actor, room_request.context, skill.target_requirement, [target])
        self.assertIs(
            caught.exception.reason,
            RejectReason.TARGET_FACTION_FORBIDDEN,
        )

        class SelfContext(RoomActionContext):
            battlefield = object()

            def relation_to(self, actor, target):
                return Relation.SELF

        self_request = ActionRequest(
            actor,
            skill.key,
            [target],
            SelfContext(room),
        )
        self.assertEqual(
            resolve_targets(self_request.actor, self_request.context, skill.target_requirement, [target]),
            [target],
        )

    @covers_requirement("targeting-validation::target-resolution-runs-four-ordered-validations")
    def test_any_skill_accepts_every_relation(self):
        room = object()
        actor = _Entity("actor", room)
        self_entity = _Entity("self", room)
        ally = _Entity("ally", room)
        enemy = _Entity("enemy", room)
        skill = _T_ANY_SINGLE

        class _Context(RoomActionContext):
            battlefield = object()

            def __init__(self, relation):
                super().__init__(room)
                self._relation = relation

            def relation_to(self, actor, target):
                return self._relation

        for relation in (Relation.SELF, Relation.ALLY, Relation.ENEMY):
            request = ActionRequest(
                actor, skill.key, [enemy], _Context(relation)
            )
            self.assertEqual(
                resolve_targets(request.actor, request.context, skill.target_requirement, [enemy]),
                [enemy],
                relation,
            )

    @covers_requirement("targeting-validation::target-resolution-runs-four-ordered-validations")
    def test_self_only_rejects_non_actor_targets(self):
        room = object()
        actor = _Entity("actor", room)
        ally = _Entity("ally", room)
        skill = replace(
            _T_ANY_SINGLE,
            faction_constraint=FactionConstraint.SELF_ONLY,
        )
        request = ActionRequest(actor, skill.key, [ally], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [ally])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_FACTION_FORBIDDEN)


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
            _T_ZERO_COST_SINGLE, target_spec=TargetSpec.NONE
        )
        target = self._target()
        request = self._request(actor, skill.key, [target])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [target])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

        request = self._request(actor, skill.key, [])
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, []), [])

    def test_self_accepts_empty_or_actor_only(self):
        actor = self._actor()
        skill = _T_SELF_SHAPE
        request = self._request(actor, skill.key, [])
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, []), [actor])

        request = self._request(actor, skill.key, [actor])
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, [actor]), [actor])

        other = self._target("other")
        request = self._request(actor, skill.key, [other])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [other])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_single_rejects_non_unit_cardinality(self):
        actor = self._actor()
        skill = _T_ZERO_COST_SINGLE
        request = self._request(actor, skill.key, [])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_single_rejects_shorthand_even_when_one_target(self):
        actor = self._actor()
        skill = replace(_T_ZERO_COST_SINGLE, target_spec=TargetSpec.SINGLE)
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
        skill = replace(_T_ANY_AREA, faction_constraint=FactionConstraint.ANY)
        request = self._request(actor, skill.key, [target, target])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [target, target])
        self.assertIs(caught.exception.reason, RejectReason.TARGET_SPEC_MISMATCH)

    def test_area_rejects_empty_explicit_input(self):
        actor = self._actor()
        skill = _T_ANY_AREA
        request = self._request(actor, skill.key, [])
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [])
        self.assertIs(caught.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_area_filters_invalid_candidates_and_keeps_valid(self):
        room = object()
        actor = _Entity("actor", room)
        present = _Entity("present", room)
        absent = _Entity("absent", object())
        skill = replace(
            _T_ANY_AREA,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [present, absent], RoomActionContext(room))
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, [present, absent]), [present])

    def test_area_rejects_when_all_candidates_filtered(self):
        actor = self._actor()
        room = object()
        dead = _Entity("dead", room)
        dead.traits.hp.value = 0
        skill = replace(
            _T_ANY_AREA,
            faction_constraint=FactionConstraint.ANY,
        )
        request = ActionRequest(actor, skill.key, [dead], RoomActionContext(room))
        with self.assertRaises(RejectedAction) as caught:
            resolve_targets(request.actor, request.context, skill.target_requirement, [dead])
        self.assertIs(caught.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    @covers_requirement("targeting-validation::combat-shortcuts-are-convenience-ui-not-permission-boundaries")
    def test_any_area_skill_accepts_explicit_ally_despite_enemy_shorthand(self):
        room = object()
        actor = _Entity("actor", room)
        ally = _Entity("ally", room)
        skill = replace(
            _T_ANY_AREA,
            faction_constraint=FactionConstraint.ANY,
        )
        # RoomActionContext reports Relation.ALLY for co-located non-self
        # entities; an ANY skill validates the explicit ally target just like
        # an explicit enemy list, with no shorthand-based permission change.
        request = ActionRequest(actor, skill.key, [ally], RoomActionContext(room))
        self.assertEqual(resolve_targets(request.actor, request.context, skill.target_requirement, [ally]), [ally])

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


class RoomActionContextEventContextTests(unittest.TestCase):
    """RoomActionContext injects the room into event_context (design D-4)."""

    @covers_requirement("targeting-validation::roomactioncontext-exposes-the-room-through-event-context")
    def test_constructed_context_carries_the_room_key(self):
        room = object()
        context = RoomActionContext(room, {"disguise": {}})
        self.assertEqual(context.event_context, {"disguise": {}, "room": room})

    @covers_requirement("targeting-validation::roomactioncontext-exposes-the-room-through-event-context")
    def test_caller_supplied_room_key_is_replaced_never_duplicated(self):
        room, other_room = object(), object()
        context = RoomActionContext(room, {"room": other_room, "disguise": {}})
        self.assertEqual(context.event_context["room"], room)
        self.assertEqual(context.event_context["disguise"], {})

    @covers_requirement("targeting-validation::roomactioncontext-exposes-the-room-through-event-context")
    def test_none_event_context_gains_only_the_room_key(self):
        room = object()
        self.assertEqual(RoomActionContext(room).event_context, {"room": room})


class ItemSkillResolverParityTests(unittest.TestCase):
    """Delta (item-effect-rulebook): "Item and skill targets validate identically"."""

    @covers_requirement(
        "item-effect-rulebook::an-effect-s-scope-is-fixed-by-the-rulebook-and-maps-to-one-targeting-requirement"
    )
    def test_item_scope_and_single_target_skill_reject_the_same_dead_candidate(self):
        # Task 2.2: the requirement an item scope maps to and the requirement
        # a single-target skill produces are consumed by one resolver, so one
        # dead candidate must be refused for the identical reason through both
        # producers — no second validation chain exists on the item side.
        from world.rules.item_effects import ItemTargetScope, scope_targeting_rule

        room = object()
        actor = _Entity("actor", room)
        dead = _Entity("dead", room)
        dead.traits.hp.value = 0
        item_requirement = scope_targeting_rule(ItemTargetScope.SINGLE).requirement
        skill_requirement = _T_ANY_SINGLE.target_requirement
        with self.subTest(producer="item"):
            with self.assertRaises(RejectedAction) as item_caught:
                resolve_targets(
                    actor, RoomActionContext(room), item_requirement, [dead]
                )
        with self.subTest(producer="skill"):
            with self.assertRaises(RejectedAction) as skill_caught:
                resolve_targets(
                    actor, RoomActionContext(room), skill_requirement, [dead]
                )
        self.assertIs(
            item_caught.exception.reason, RejectReason.TARGET_DEAD
        )
        self.assertEqual(
            item_caught.exception.reason, skill_caught.exception.reason
        )
        self.assertEqual(
            item_caught.exception.detail, skill_caught.exception.detail
        )
