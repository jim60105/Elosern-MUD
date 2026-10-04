"""Synthetic offline correspondence behavior and clock transaction contracts."""

from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from world.narrative.correspondence import (
    CORRESPONDENCE_PROJECTOR_VERSION, MAX_BODY_CHARACTERS, get_letter, register_correspondence_delivery,
    send_letter, settle_correspondence_delivery,
)
from world.narrative.models import LetterSend, LetterState, NarrativeEvent, ProjectionProgress
from world.rules.clock import (
    AdvanceSource, ClockAdvanceBoundError, MAX_ADVANCE_SECONDS, WorldClock,
    _EVENT_SOURCES, get_world_clock, register_event_source,
)


class CorrespondenceDeliveryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        register_correspondence_delivery()
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic courier recipient")
        self.player = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic sender")
        self.clock = get_world_clock()
        self.clock._persist(17)
        self.clock.tick = 17

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self.sources)
        super().tearDown()

    def send(self, recipient=None, identity="synthetic-letter", body="Synthetic private message"):
        return send_letter(sender_id=self.player.pk, recipient_id=(recipient or self.npc).pk,
                           body=body, source_id=identity)

    @covers_requirement(
        "correspondence-delivery::accepted-letters-have-fixed-guaranteed-delivery"
    )
    def test_preflight_is_write_free_and_send_is_immutable_idempotent(self):
        for kwargs in (
            {"recipient_id": 999999999, "body": "message"},
            {"recipient_id": self.room1.pk, "body": "message"},
            {"recipient_id": self.npc.pk, "body": ""},
            {"recipient_id": self.npc.pk, "body": "x" * (MAX_BODY_CHARACTERS + 1)},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                send_letter(sender_id=self.player.pk, **kwargs)
        self.assertEqual(LetterSend.objects.count(), 0)
        first = self.send()
        self.assertEqual(first, self.send())
        self.assertEqual(first.due_tick - first.sent_tick, 3600)
        with self.assertRaises(ValueError):
            self.send(body="conflicting message")
        with self.assertRaises(ValueError):
            LetterSend.objects.update(body="replacement")
        row = LetterSend.objects.get()
        with self.assertRaises(ValueError):
            row.save()
        self.assertEqual(LetterState.objects.count(), 1)

    @covers_requirement(
        "correspondence-delivery::accepted-letters-have-fixed-guaranteed-delivery"
    )
    def test_boundary_movement_and_uninstantiated_recipient(self):
        original = self.send()
        self.npc.location = self.room2
        self.clock.advance(3599, AdvanceSource.COMMAND, [])
        self.assertEqual(get_letter(original.source_id).status, "sent")
        self.npc.location = None
        with patch("world.narrative.correspondence._character",
                   side_effect=AssertionError("delivery cannot load recipients")):
            events = self.clock.advance(1, AdvanceSource.COMMAND, [])
        self.assertEqual([(e.kind, e.due_tick) for e in events],
                         [("correspondence_delivery", 3617)])
        self.assertEqual(get_letter(original.source_id).status, "delivered")
        self.assertEqual(original.status, "sent")

    @covers_requirement(
        "correspondence-delivery::delivery-follows-only-committed-authoritative-time"
    )
    def test_command_combat_skip_and_player_availability_offline(self):
        for source in (AdvanceSource.COMMAND, AdvanceSource.COMBAT, AdvanceSource.SKIP):
            with self.subTest(source=source):
                record = self.send(self.player, identity=f"synthetic-{source}")
                self.clock = get_world_clock()
                self.clock.advance(3600, source, [])
                self.assertEqual(get_letter(record.source_id).status, "available")
                state = LetterState.objects.get(letter__source_id=record.source_id)
                self.assertIsNone(state.collection_tick)
                self.assertIsNone(state.read_tick)
                self.assertEqual(get_world_clock().tick, record.due_tick)

    @covers_requirement(
        "world-clock::advance-persists-the-tick-and-entity-state-atomically",
        "world-clock::delivery-table-changes-participate-in-clock-rollback",
    )
    def test_late_failure_rolls_back_tables_progress_clock_and_detached_reads(self):
        before = self.send()
        register_event_source("instance_reclamation",
                              lambda start, end: (_ for _ in ()).throw(RuntimeError("late")))
        with self.assertRaisesRegex(RuntimeError, "late"):
            self.clock.advance(3600, AdvanceSource.SKIP, [])
        self.assertEqual(self.clock.tick, 17)
        self.assertEqual(get_world_clock().tick, 17)
        self.assertEqual(get_letter(before.source_id), before)
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        self.assertEqual(ProjectionProgress.objects.count(), 0)
        register_event_source("instance_reclamation", lambda start, end: [])
        self.clock.advance(3600, AdvanceSource.SKIP, [])
        self.assertEqual(get_letter(before.source_id).status, "delivered")

    @covers_requirement(
        "correspondence-delivery::delivery-follows-only-committed-authoritative-time"
    )
    def test_restart_repetition_is_idempotent_and_leaves_work_pending(self):
        from world.narrative.memory import process_pending_narrative_memory_projections

        record = self.send()
        self.clock.advance(3600, AdvanceSource.COMBAT, [])
        register_correspondence_delivery()
        restarted = get_world_clock()
        self.assertEqual(restarted.tick, record.due_tick)
        self.assertEqual(settle_correspondence_delivery(17, 3617), [])
        self.assertEqual(process_pending_narrative_memory_projections(), 0)
        self.assertEqual(NarrativeEvent.objects.count(), 1)
        self.assertEqual(ProjectionProgress.objects.get().status, "pending")
        self.assertEqual(ProjectionProgress.objects.get().projector_version,
                         CORRESPONDENCE_PROJECTOR_VERSION)
        self.assertEqual(NarrativeEvent.objects.get().tick, record.due_tick)
        self.assertEqual(self.npc.location, None)

    @covers_requirement(
        "settlement-stage-order::due-letters-settle-at-their-exact-deadlines"
    )
    def test_rejected_or_short_actual_windows_do_not_settle_future_deadlines(self):
        record = self.send()
        with self.assertRaises(ClockAdvanceBoundError):
            self.clock.advance(MAX_ADVANCE_SECONDS + 1, AdvanceSource.SKIP, [])
        self.assertEqual(self.clock.tick, 17)
        self.clock.advance(1800, AdvanceSource.SKIP, [])
        self.assertEqual(get_letter(record.source_id).status, "sent")
        self.assertEqual(settle_correspondence_delivery(record.due_tick, record.due_tick), [])
        self.clock.advance(1800, AdvanceSource.SKIP, [])
        self.assertEqual(get_letter(record.source_id).status, "delivered")

    @covers_requirement(
        "world-clock::delivery-table-changes-participate-in-clock-rollback"
    )
    def test_outer_rollback_and_facade_privacy(self):
        with patch("world.narrative.correspondence.log_info") as log:
            with self.captureOnCommitCallbacks(execute=True):
                record = self.send()
            self.assertEqual(log.call_args.args, ("correspondence_sent",))
            self.assertNotIn(record.body, str(log.call_args))
            log.reset_mock()
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    settle_correspondence_delivery(17, 3617)
                    raise RuntimeError("outer rollback")
            self.assertEqual(get_letter(record.source_id).status, "sent")
            log.assert_not_called()
            with self.captureOnCommitCallbacks(execute=True):
                self.clock.advance(3600, AdvanceSource.COMMAND, [])
            self.assertEqual(log.call_args.args, ("correspondence_settled",))
            self.assertNotIn(record.body, str(log.call_args))
