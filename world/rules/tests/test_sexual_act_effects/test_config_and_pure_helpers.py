"""Slice of ``test_sexual_act_effects``: EffectsConfigTests, ResolvePartTests, ParticipantsTests, ObserversPresentTests, ObserverGatedNameTests.
"""
from tools.spec_traceability import covers_requirement
import ast
import inspect
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.lore.sexual_vocab import GENERIC_BODY_PART
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_SURFACES,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
    _handle_target_sexual_event,
)
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    load_effects_config,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)
from world.rules.pleasure import apply_pleasure_gain
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState
from world.rules.sexual_resist import ResistVerdict
from world.rules.targeting import RoomActionContext
from world.skills.registry import TargetSpec
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)
from .._combat_session_helpers import _live_registry, _race_key
# The YAML field vocabulary of the effects config, resolved through the
# config dataclass at import (the loader owns the names; this module never
# spells a shipped field name as a literal).
import dataclasses as _dc


from ._support import (
    _EqualStub,
    _MULTIPLIER_FIELD,
    _THRESHOLD_FIELD,
    _effects_yaml,
    _live_act_registry,
)


class EffectsConfigTests(unittest.TestCase):
    """The sexual_act_effects.yaml contract (design D-3)."""

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_shipped_table_loads_and_exposes_both_values(self):
        config = load_effects_config()
        multipliers = getattr(config, _MULTIPLIER_FIELD)
        self.assertEqual(multipliers["1"], 1.0)
        self.assertEqual(multipliers["2"], 1.1)
        self.assertEqual(multipliers["3+"], 1.2)
        self.assertEqual(getattr(config, _THRESHOLD_FIELD), 20)

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_missing_threshold_fails_closed_naming_the_field(self):
        path = _effects_yaml()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        del payload[_THRESHOLD_FIELD]
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_effects_config(path)
        self.assertIn(_THRESHOLD_FIELD, str(caught.exception))

    @covers_requirement("sexual-act-effects::sexual-act-effects-yaml-declares-the-participant-count-table-and-the-climax-extension-threshold-validated-at-load")
    def test_non_ascending_multiplier_table_fails_closed(self):
        with self.assertRaises(ValueError) as caught:
            load_effects_config(
                _effects_yaml(multipliers={"1": 1.2, "2": 1.1, "3+": 1.2})
            )
        self.assertIn(_MULTIPLIER_FIELD, str(caught.exception))

    def test_unknown_top_level_field_fails_closed(self):
        path = _effects_yaml()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["stray_field"] = True
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_effects_config(path)
        self.assertIn("stray_field", str(caught.exception))

    def test_extra_multiplier_key_fails_closed(self):
        with self.assertRaises(ValueError):
            load_effects_config(
                _effects_yaml(multipliers={"1": 1.0, "2": 1.1, "3+": 1.2, "4+": 1.3})
            )

    def test_non_positive_threshold_fails_closed(self):
        for bad in (0, -1, 1.5):
            with self.subTest(threshold=bad):
                with self.assertRaises(ValueError):
                    load_effects_config(_effects_yaml(threshold=bad))

    def test_participant_multiplier_buckets_counts(self):
        config = load_effects_config()
        self.assertEqual(config.participant_multiplier(1), 1.0)
        self.assertEqual(config.participant_multiplier(2), 1.1)
        for count in (3, 4, 30):
            with self.subTest(count=count):
                self.assertEqual(config.participant_multiplier(count), 1.2)
        for bad in (0, -2, 1.5, True):
            with self.subTest(count=bad):
                with self.assertRaises(ValueError):
                    config.participant_multiplier(bad)


class ResolvePartTests(EvenniaTestCase):
    """resolve_part collapses None and Monster entities to the generic channel."""

    def setUp(self):
        super().setUp()
        self.humanoid = create_object(PlayerCharacter, key="resolve humanoid")
        self.humanoid.race = _race_key()
        self.humanoid.apply_race_baseline()
        self.monster = create_object(Monster, key="resolve monster")

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_non_monster_with_declared_part_resolves_to_that_part(self):
        self.assertEqual(resolve_part(self.humanoid, "乳房"), "乳房")

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_monster_resolves_to_the_generic_channel_regardless_of_declared_part(self):
        self.assertEqual(resolve_part(self.monster, "乳房"), GENERIC_BODY_PART)

    @covers_requirement("sexual-act-effects::resolve-part-collapses-a-monster-target-or-an-undeclared-part-to-the-generic-body-part-channel")
    def test_undeclared_part_resolves_to_the_generic_channel_for_any_entity(self):
        self.assertEqual(resolve_part(self.humanoid, None), GENERIC_BODY_PART)
        self.assertEqual(resolve_part(self.monster, None), GENERIC_BODY_PART)


class ParticipantsTests(unittest.TestCase):
    """The actor-first, deduplicated participant list contract (design D-2)."""

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_solo_act_targets_containing_only_the_actor(self):
        actor = object()
        self.assertEqual(participants(actor, [actor]), [actor])

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_two_person_act_targets_excluding_the_actor(self):
        actor, other = object(), object()
        self.assertEqual(participants(actor, [other]), [actor, other])

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_area_act_never_duplicates_the_actor(self):
        actor, ally, enemy = object(), object(), object()
        result = participants(actor, [actor, ally, enemy])
        self.assertEqual(result, [actor, ally, enemy])
        self.assertEqual(result.count(actor), 1)

    @covers_requirement("sexual-act-effects::participants-resolves-the-actor-first-deduplicated-participant-list-from-an-act-s-targets")
    def test_equal_but_distinct_targets_are_both_kept(self):
        actor = object()
        first, second = _EqualStub(1), _EqualStub(1)
        self.assertEqual(first, second)
        result = participants(actor, [first, second])
        self.assertEqual(result, [actor, first, second])


class ObserversPresentTests(EvenniaTestCase):
    """The deterministic, no-create presence read (design D-2)."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="observer actor")

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_area_cast_with_a_non_actor_target_is_observed_by_construction(self):
        self.assertTrue(observers_present(self.actor, [object()], {}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_alone_in_a_room_is_unobserved(self):
        room = SimpleNamespace(contents=[self.actor])
        self.assertFalse(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_with_a_co_located_living_entity_is_observed(self):
        occupant = create_object(PlayerCharacter, key="observer occupant")
        room = SimpleNamespace(contents=[self.actor, occupant])
        self.assertTrue(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_with_only_non_living_room_objects_is_unobserved(self):
        room = SimpleNamespace(contents=[self.actor, SimpleNamespace(key="exit")])
        self.assertFalse(observers_present(self.actor, [self.actor], {"room": room}))

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_on_a_battlefield_with_only_the_actor_is_unobserved(self):
        battlefield = SimpleNamespace(roster={"actor": self.actor})
        self.assertFalse(
            observers_present(self.actor, [self.actor], {"battlefield": battlefield})
        )

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_self_cast_on_a_battlefield_with_another_member_is_observed(self):
        battlefield = SimpleNamespace(
            roster={"actor": self.actor, "enemy": object()}
        )
        self.assertTrue(
            observers_present(self.actor, [self.actor], {"battlefield": battlefield})
        )

    @covers_requirement("sexual-act-effects::observers-present-returns-whether-any-entity-besides-the-actor-observes-a-cast")
    def test_missing_context_reads_as_unobserved(self):
        self.assertFalse(observers_present(self.actor, [self.actor], {}))


class ObserverGatedNameTests(unittest.TestCase):
    """The observer-gated event/counter name tables (design D-3)."""

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_event_set_names_exactly_watched_during_activity(self):
        self.assertEqual(_OBSERVER_GATED_EVENTS, frozenset({"watched_during_activity"}))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_counter_set_names_exactly_watched_count(self):
        self.assertEqual(_OBSERVER_GATED_COUNTERS, frozenset({"watched_count"}))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_events_are_a_subset_of_the_actor_scoped_vocabulary(self):
        self.assertLessEqual(_OBSERVER_GATED_EVENTS, _ACTOR_SCOPED_EVENTS)

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_gated_counters_are_a_subset_of_the_sanctioned_mutator_table(self):
        self.assertLessEqual(_OBSERVER_GATED_COUNTERS, set(_COUNTER_MUTATORS))

    @covers_requirement("sexual-act-effects::watched-during-activity-and-watched-count-are-observer-gated-the-gated-names-are-declared-as-module-constants")
    def test_no_act_declares_watched_count_as_a_participant_counter(self):
        # The gated counter is actor-scoped by definition (being watched is a
        # fact about the performing actor); a participant-side declaration
        # would bypass the gate, since a non-actor participant implies a
        # non-actor target, which always reads as observed.
        for key, act in _live_act_registry().items():
            with self.subTest(key=key):
                self.assertNotIn("watched_count", act.participant_counters)
