"""Tests for durable narrative event storage, idempotent projection progress, and commit boundaries."""

from unittest.mock import patch
from tools.spec_traceability import covers_requirement

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.narrative.events import (
    build_encounter_source_id,
    get_pending_projections,
    mark_projection_completed,
    record_narrative_event,
    scan_pending_narrative_projections,
)
from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.narrative.projector import select_and_record_protection_event
from world.rules.combat import Battlefield
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.combat_session.settlement import settle_session


class NarrativeEventsStorageTests(EvenniaTestCase):
    """Scenario tests for narrative-events delta capability."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="NarrativeTestRoom")
        self.player = create_object(PlayerCharacter, key="NarrativePlayer", location=self.room)
        self.companion = create_object(NPC, key="YohannaTestCompanion", location=self.room)
        self.player.traits.add("hp", "HP", trait_type="gauge", base=100, current=100)
        self.companion.traits.add("hp", "HP", trait_type="gauge", base=100, current=100)
        self.player.db.active_combat = {}
        self.companion.db.active_combat = {}

    @covers_requirement("narrative-events::narrative-facts-commit-atomically-with-covered-gameplay")
    def test_record_narrative_event_round_trip(self):
        """Test basic creation and round-trip persistence of narrative event and progress."""
        source_id = "test:encounter:1:round:1"
        event, progress, created = record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={"outcome": "victory", "rounds": 1},
            participants=[self.player.pk, self.companion.pk],
            location=str(self.room.pk),
            tick=100,
            visibility="public",
            salience=2,
        )
        self.assertTrue(created)
        self.assertEqual(event.source_id, source_id)
        self.assertEqual(event.event_type, "encounter_protection")
        self.assertEqual(event.participants, [str(self.player.pk), str(self.companion.pk)])
        self.assertEqual(progress.status, "pending")
        self.assertEqual(progress.projector_version, 1)

    @covers_requirement("narrative-events::durable-source-identity-makes-projection-recoverable")
    @covers_requirement("narrative-events::narrative-facts-commit-atomically-with-covered-gameplay")
    def test_idempotent_reprocessing_preserves_immutable_facts(self):
        """Scenario: Reprocessing a source SHALL NOT duplicate facts or progress."""
        source_id = "test:encounter:idempotent:1"
        event1, prog1, created1 = record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={"outcome": "victory"},
            participants=[self.player.pk],
        )
        self.assertTrue(created1)

        # Mark completed
        mark_projection_completed(source_id, projector_version=1)

        # Reprocess same source
        event2, prog2, created2 = record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={"outcome": "altered_outcome"},
            participants=[self.player.pk],
        )
        self.assertFalse(created2)
        self.assertEqual(event1.pk, event2.pk)
        self.assertEqual(event2.content["outcome"], "victory")
        self.assertEqual(prog2.status, "completed")
        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)

    @covers_requirement("narrative-events::durable-source-identity-makes-projection-recoverable")
    def test_equal_prose_distinct_sources(self):
        """Scenario: Equal prose is repeated - distinct committed occurrences have distinct source IDs."""
        source_a = build_encounter_source_id("sess_1", kind="settlement", ordinal=1)
        source_b = build_encounter_source_id("sess_2", kind="settlement", ordinal=1)
        self.assertNotEqual(source_a, source_b)

        content = {"rendered_text": "勇者保護了同伴。"}
        ev_a, _, _ = record_narrative_event(
            source_id=source_a,
            event_type="encounter_protection",
            content=content,
            participants=[self.player.pk],
        )
        ev_b, _, _ = record_narrative_event(
            source_id=source_b,
            event_type="encounter_protection",
            content=content,
            participants=[self.player.pk],
        )
        self.assertNotEqual(ev_a.pk, ev_b.pk)
        self.assertEqual(ev_a.content["rendered_text"], ev_b.content["rendered_text"])

    @covers_requirement("narrative-events::narrative-facts-commit-atomically-with-covered-gameplay")
    def test_failed_outer_transaction_rolls_back_narrative_events(self):
        """Scenario: Outer settlement fails -> events, progress roll back with transaction."""
        source_id = "test:rollback:source:1"
        try:
            with transaction.atomic():
                record_narrative_event(
                    source_id=source_id,
                    event_type="encounter_protection",
                    content={"outcome": "victory"},
                    participants=[self.player.pk],
                )
                raise RuntimeError("Injected outer failure")
        except RuntimeError:
            pass

        self.assertFalse(NarrativeEvent.objects.filter(source_id=source_id).exists())
        self.assertFalse(ProjectionProgress.objects.filter(source_id=source_id).exists())

    @covers_requirement("narrative-events::durable-source-identity-makes-projection-recoverable")
    def test_callback_never_runs_restart_discovers_pending(self):
        """Scenario: Callback never runs -> restart discovers the pending source."""
        source_id = "test:pending:restart:1"
        record_narrative_event(
            source_id=source_id,
            event_type="encounter_protection",
            content={"outcome": "victory"},
            participants=[self.player.pk, self.companion.pk],
        )

        # Simulate process restart / scanner discovering pending rows
        pending_count = scan_pending_narrative_projections(projector_version=1)
        self.assertGreaterEqual(pending_count, 1)

        pending_items = list(get_pending_projections(projector_version=1))
        self.assertTrue(any(item.source_id == source_id for item in pending_items))

    @covers_requirement("narrative-events::narrative-facts-commit-atomically-with-covered-gameplay")
    def test_compressed_encounter_retains_sources(self):
        """Scenario: Compressed encounter retains sources."""
        record = CombatSessionRecord(
            session_id="compress_sess_99",
            mode="hostile",
            room_id=self.room.pk,
            player_ids=(self.player.pk,),
            enemy_ids=(999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=3,
            exam_id=None,
        )
        battlefield = Battlefield(
            teams={"players": frozenset({str(self.player.key), str(self.companion.key)}), "enemies": frozenset()},
            roster={
                str(self.player.key): self.player,
                str(self.companion.key): self.companion,
            },
        )

        # Settle session via compressed opening
        settle_session(
            self.player,
            record,
            battlefield,
            "victory",
            (),
            opening="overwhelm",
        )

        expected_source = build_encounter_source_id("compress_sess_99", kind="compressed_settlement", ordinal=3)
        events = NarrativeEvent.objects.filter(source_id=expected_source)
        self.assertEqual(events.count(), 1)
        event = events.first()
        self.assertEqual(event.event_type, "encounter_protection")
        self.assertEqual(event.content["opening"], "overwhelm")
        self.assertIn(str(self.companion.pk), event.participants)

    @covers_requirement("narrative-events::narrative-facts-commit-atomically-with-covered-gameplay")
    def test_rejected_or_defeated_action_produces_no_protection_fact(self):
        """Defeated outcome or knocked-out companion records no protection event."""
        record = CombatSessionRecord(
            session_id="defeat_sess_1",
            mode="hostile",
            room_id=self.room.pk,
            player_ids=(self.player.pk,),
            enemy_ids=(999,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=None,
        )
        battlefield = Battlefield(
            teams={"players": frozenset({str(self.player.key), str(self.companion.key)}), "enemies": frozenset()},
            roster={
                str(self.player.key): self.player,
                str(self.companion.key): self.companion,
            },
        )

        # 1. Defeat outcome -> no record
        recorded_defeat = select_and_record_protection_event(
            actor=self.player,
            record=record,
            battlefield=battlefield,
            outcome="defeat",
            opening="round",
        )
        self.assertFalse(recorded_defeat)

        # 2. Companion was knocked out -> no record
        battlefield.knocked_out.add(str(self.companion.key))
        recorded_knocked = select_and_record_protection_event(
            actor=self.player,
            record=record,
            battlefield=battlefield,
            outcome="victory",
            opening="round",
        )
        self.assertFalse(recorded_knocked)
