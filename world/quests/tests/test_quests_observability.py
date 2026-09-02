"""Boundary-event assertions for the migrated quest lifecycle (batch 4).

Targets the ``quest-lifecycle`` delta requirement of
``migrate-world-client-observability``: one ``quest_transition`` event per
changed quest at every durable commit of ANY of the three quest-log writers
(replacement, delta, and the pending-effect seam), ``rollback_restore_failed``
on swallowed rollback restores, and NO event for rolled-back operations. The
deadline-failure path shares the replacement writer (``fail_record`` +
replacement), so the failed-transition scenario covers it structurally. The
delta requirement id is now ``covers_requirement``-annotated on its
establishing test: it became a main-spec requirement when the change
archived and synced (the annotation was intentionally withheld while it was
an active delta, same as batches 1-3).

Events fire through ``transaction.on_commit``, so tests capture on-commit
callbacks and patch the migrated module's facade binding; rollback scenarios
assert the callback was discarded, not that the facade was unreachable.
"""

import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from django.db import transaction
from evennia.utils.test_resources import EvenniaTest

from world.quests.runtime import (
    QuestState,
    accept_quest,
    abandon_quest,
    read_records,
)
from world.quests.transitions import (
    _restore_attribute_best_effort,
    apply_quest_log_replacement,
    apply_quest_log_delta,
    pending_effects_for_transition,
)

from ._fixtures import QuestRegistryIsolation, quest, register

from tools.spec_traceability import covers_requirement


class QuestTransitionEventTests(QuestRegistryIsolation, EvenniaTest):
    """One ``quest_transition`` per changed quest, per committed write."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.definition = register(quest("obs_lifecycle"))

    def _events(self, info):
        return [
            (call.args[0], call.kwargs["context"])
            for call in info.call_args_list
            if call.args
        ]

    def test_accept_emits_none_to_in_progress(self):
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            record = accept_quest(self.actor, self.definition.key)
        events = self._events(info)
        self.assertEqual([event for event, _ in events], ["quest_transition"])
        (_, context), = events
        self.assertEqual(context["char"], str(self.actor.pk))
        self.assertEqual(context["quest"], self.definition.key)
        self.assertEqual(context["stage_from"], "none")
        self.assertEqual(context["stage_to"], "in_progress:0:unbound")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)

    @covers_requirement("quest-lifecycle::quest-lifecycle-transitions-emit-boundary-events")
    def test_stage_advance_emits_stage_from_to_stage_to(self):
        record = accept_quest(self.actor, self.definition.key)
        advanced = replace(record, stage_index=1, stage_room_id=None)
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(self.actor, [advanced])
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events[0]["stage_to"], "in_progress:1:unbound")

    def test_abandon_emits_failed_transition(self):
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            # The accept is captured too: its own event fires on the same
            # capture boundary so the assertion sees the full lifecycle.
            record = accept_quest(self.actor, self.definition.key)
            abandoned = abandon_quest(self.actor, record.quest_id)
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        # accept + abandon each emit one event; the abandon one names failed.
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events[-1]["stage_to"], "failed:0:unbound")
        self.assertEqual(abandoned.state, QuestState.FAILED)

    def test_unchanged_replacement_emits_no_event(self):
        record = accept_quest(self.actor, self.definition.key)
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(self.actor, [record])
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(events, [])

    def test_removed_record_emits_removed_transition(self):
        accept_quest(self.actor, self.definition.key)
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(self.actor, [])
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events[0]["stage_to"], "removed")

    def test_malformed_old_log_skips_diff_without_breaking_write(self):
        from world.quests.runtime import QuestRecord

        self.actor.db.quest_log = [{"not": "a record"}]
        candidate = QuestRecord(
            quest_id="obs_lifecycle:1",
            definition_key=self.definition.key,
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(self.actor, [candidate])
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(events, [])
        # The write itself is untouched by the skipped diff.
        stored = list(self.actor.db.quest_log or [])
        self.assertEqual([entry["quest_id"] for entry in stored], ["obs_lifecycle:1"])

    def test_rolled_back_transition_emits_no_event(self):
        with (
            patch("world.quests.transitions.log_info") as info,
            patch(
                "world.quests.transitions._apply_pin_operations",
                side_effect=RuntimeError("injected pin failure"),
            ),
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            accept_quest(self.actor, self.definition.key)
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(events, [])
        self.assertEqual(read_records(self.actor), [])

    def test_delta_writer_emits_inside_caller_transaction(self):
        record = accept_quest(self.actor, self.definition.key)
        advanced = replace(record, stage_index=1)
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                apply_quest_log_delta(self.actor, [advanced])
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events[0]["stage_to"], "in_progress:1:unbound")

    def test_delta_writer_rollback_with_caller_transaction_emits_no_event(self):
        record = accept_quest(self.actor, self.definition.key)
        advanced = replace(record, stage_index=1)
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError), transaction.atomic():
                apply_quest_log_delta(self.actor, [advanced])
                raise RuntimeError("injected caller failure")
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(events, [])
        # The delta writer performs no restore of its own (the CALLER owns
        # rollback restore), so only the no-event contract is asserted here.

    def test_multi_record_write_emits_one_event_per_changed_quest(self):
        first = accept_quest(self.actor, self.definition.key)
        second_definition = register(quest("obs_second"))
        second = accept_quest(self.actor, second_definition.key)
        advanced = [
            replace(first, stage_index=1, stage_room_id=self.room1.pk),
            replace(second, stage_index=1),
        ]
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            apply_quest_log_replacement(self.actor, advanced)
        events = {
            context["quest"]: context
            for event, context in self._events(info)
            if event == "quest_transition"
        }
        # The two accept events share nothing with these; exactly the two
        # advance events name each quest once, with the bound flag from the
        # stage-room binding.
        self.assertEqual(events[self.definition.key]["stage_to"], "in_progress:1:bound")
        self.assertEqual(events[self.definition.key]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events["obs_second"]["stage_to"], "in_progress:1:unbound")

    def test_acceptance_numbering_emits_one_event_per_acceptance(self):
        first = accept_quest(self.actor, self.definition.key)
        apply_quest_log_replacement(
            self.actor, [replace(first, state=QuestState.COMPLETED)]
        )
        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            accept_quest(self.actor, self.definition.key)
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(len(events), 1)
        # Two acceptances of one definition share the emitted quest key but
        # are distinct quest_ids; the re-accept is a fresh none -> in_progress.
        self.assertEqual(events[0]["quest"], self.definition.key)
        self.assertEqual(events[0]["stage_from"], "none")
        self.assertEqual(read_records(self.actor)[-1].quest_id, "obs_lifecycle:2")

    def test_pending_effect_seam_emits_at_action_commit(self):
        record = accept_quest(self.actor, self.definition.key)
        advanced = replace(record, stage_index=1)
        effects = pending_effects_for_transition(self.actor, [advanced])
        from world.rules.action import _commit

        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            _commit(effects, char=self.actor.key, action="quest_step")
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage_from"], "in_progress:0:unbound")
        self.assertEqual(events[0]["stage_to"], "in_progress:1:unbound")

    def test_pending_effect_seam_rollback_emits_no_event(self):
        record = accept_quest(self.actor, self.definition.key)
        advanced = replace(record, stage_index=1)
        effects = pending_effects_for_transition(self.actor, [advanced])
        from world.rules.action import _commit

        with (
            patch("world.quests.transitions.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(Exception):
                # A failing co-effect rolls the whole commit: the quest-log
                # effect applied, then everything rolled back.
                effects.append(
                    type(effects[0])(
                        self.actor,
                        "failing",
                        frozenset({"test"}),
                        lambda: (_ for _ in ()).throw(RuntimeError("injected")),
                    )
                )
                _commit(effects, char=self.actor.key, action="quest_step")
        events = [context for event, context in self._events(info) if event == "quest_transition"]
        self.assertEqual(events, [])
        # The rolled-back log still shows the pre-advance stage.
        self.assertEqual([record.stage_index for record in read_records(self.actor)], [0])


class RestoreFailureEventTests(unittest.TestCase):
    """Swallowed rollback restores become ``rollback_restore_failed`` warns."""

    def test_restore_failure_event_carries_key_entity_and_exc(self):
        entity = Mock()
        entity.attributes.reset_cache.side_effect = RuntimeError("cache reset fails")
        with (
            patch("world.quests.transitions._restore_attribute", side_effect=RuntimeError("injected")),
            patch("world.quests.transitions.log_warn") as warn,
        ):
            _restore_attribute_best_effort(entity, "quest_log", (True, []))
        warn.assert_called_once()
        (event,), kwargs = warn.call_args
        self.assertEqual(event, "rollback_restore_failed")
        self.assertIsInstance(kwargs["exc"], RuntimeError)
        self.assertEqual(kwargs["context"]["key"], "quest_log")
        self.assertIn("entity", kwargs["context"])
        # The swallow keeps its best-effort degradation.
        entity.attributes.reset_cache.assert_called_once()
