"""Synthetic correspondence cognition projection across both channel boundaries."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import LLMNPC
from typeclasses.rooms import Room
from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.narrative import player_correspondence as surface
from world.narrative.correspondence import (
    CORRESPONDENCE_PROJECTOR_VERSION,
    correspondence_event_source_id,
    send_letter,
    settle_correspondence_delivery,
)
from world.narrative.correspondence_memory import (
    LETTER_MEMORY_CATEGORY,
    LETTER_MEMORY_CONFIDENCE,
    LETTER_MEMORY_SCOPE,
    LETTER_MEMORY_TIER,
    process_pending_correspondence_projections,
    project_correspondence_event,
    settle_delivery_cognition,
)
from world.narrative.dialogue import build_dialogue_context, submit_turn
from world.narrative.memory import get_owner_memories
from world.narrative.models import (
    DialogueTurn,
    LetterSend,
    LetterState,
    MemoryRecord,
    NarrativeContextSnapshot,
    NarrativeEvent,
    ProjectionProgress,
)
from world.narrative.recall import fast_recall
from world.rules.clock import get_world_clock


class CorrespondenceCognitionProjectionTests(EvenniaTest):
    """The receipt occurrence settles told owner cognition, never world truth."""

    def setUp(self):
        super().setUp()
        self.sender = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic correspondent"
        )
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic letter recipient")
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic letter owner",
            location=self.room1,
        )
        self.room1.tags.add("synthetic_memory_branch")
        self.registry_patch = patch.object(surface, "PLACE_REGISTRY", {
            "synthetic_memory_branch": PlaceDefinition(
                "synthetic_memory_branch", "synthetic_memory_settlement",
                PlaceKind.COURIER_STATION, "合成驛站", "合成分站。", (1, 1), "驛站", (),
                letter_service=True,
            ),
        })
        self.registry_patch.start()
        self.clock = get_world_clock()
        self.clock._persist(17)
        self.clock.tick = 17

    def tearDown(self):
        self.registry_patch.stop()
        super().tearDown()

    def tick(self, value):
        self.clock._persist(value)
        self.clock.tick = value

    def deliver_npc(self, *, identity="synthetic-memory-npc", body="合成收件內容"):
        record = send_letter(sender_id=self.sender.pk, recipient_id=self.npc.pk,
                             body=body, source_id=identity)
        settle_correspondence_delivery(record.sent_tick, record.due_tick)
        self.tick(record.due_tick)
        return record

    def deliver_player(self, *, identity="synthetic-memory-player", body="合成玩家內容"):
        record = send_letter(sender_id=self.sender.pk, recipient_id=self.owner.pk,
                             body=body, source_id=identity)
        settle_correspondence_delivery(record.sent_tick, record.due_tick)
        self.tick(record.due_tick)
        return record

    def statements(self, owner_id):
        views = get_owner_memories(owner_id=str(owner_id), requester_id=str(owner_id))
        return [view.content["statement"] for view in views
                if view.category == LETTER_MEMORY_CATEGORY]

    def fixed_selection(self, owner_id):
        result = fast_recall(owner_id=str(owner_id), requester_id=str(owner_id), query="")
        return [view.content["statement"] for view in result.all_selected
                if view.category == LETTER_MEMORY_CATEGORY]

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
        "correspondence-delivery::accepted-letters-have-fixed-guaranteed-delivery",
    )
    def test_paired_boundary_roles_admit_only_the_approved_owner(self):
        npc_body = "合成收件人得知的內容：北方森林有一頭龍。"
        player_body = "合成玩家得知的內容：南方港口已經開放。"
        undelivered_body = "合成尚未送達的內容"
        delivered = self.deliver_npc(body=npc_body)
        unread = self.deliver_player(body=player_body)
        # Accepted but not yet due: no occurrence, so no source and no cognition.
        send_letter(sender_id=self.sender.pk, recipient_id=self.npc.pk,
                    body=undelivered_body, source_id="synthetic-still-sent")
        surface.collect(self.owner)

        self.assertEqual(process_pending_correspondence_projections(), 2)
        self.assertEqual(self.statements(self.npc.pk), [npc_body])
        self.assertEqual(self.fixed_selection(self.npc.pk), [npc_body])
        self.assertNotIn(undelivered_body, self.statements(self.npc.pk))
        self.assertFalse(ProjectionProgress.objects.filter(
            source_id=correspondence_event_source_id("synthetic-still-sent", "delivered"),
        ).exists())
        # Collected but unread: the occurrence settled without granting content.
        available_source = correspondence_event_source_id(unread.source_id, "available")
        self.assertEqual(ProjectionProgress.objects.get(source_id=available_source).status,
                         "completed")
        self.assertFalse(MemoryRecord.objects.filter(source_id=available_source).exists())
        self.assertEqual(self.statements(self.owner.pk), [])
        self.assertEqual(self.fixed_selection(self.owner.pk), [])
        self.assertIsNone(LetterState.objects.get(
            letter__source_id=unread.source_id).read_tick)

        surface.read(self.owner, unread.source_id)
        self.assertEqual(self.statements(self.owner.pk), [player_body])
        self.assertEqual(self.fixed_selection(self.owner.pk), [player_body])
        self.assertEqual(MemoryRecord.objects.filter(
            source_id=correspondence_event_source_id(delivered.source_id, "delivered"),
        ).count(), 1)

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe",
        "correspondence-player-surface::collection-and-reading-remain-distinct",
    )
    def test_first_read_projects_once_with_letter_provenance(self):
        body = "合成閱讀內容：北方森林已經開放。"
        letter = self.deliver_player(body=body)
        surface.collect(self.owner)
        state = LetterState.objects.get(letter__source_id=letter.source_id)
        self.assertEqual((state.status, state.read_tick), ("collected", None))
        self.assertEqual(self.statements(self.owner.pk), [])

        surface.read(self.owner, letter.source_id)
        source_id = correspondence_event_source_id(letter.source_id, "read")
        state.refresh_from_db()
        record = MemoryRecord.objects.get(source_id=source_id)
        self.assertEqual(record.owner_id, str(self.owner.pk))
        self.assertEqual(record.projector_version, CORRESPONDENCE_PROJECTOR_VERSION)
        self.assertEqual(record.knowledge_scope, LETTER_MEMORY_SCOPE)
        self.assertEqual(record.category, LETTER_MEMORY_CATEGORY)
        self.assertEqual(record.effective_tier, LETTER_MEMORY_TIER)
        self.assertEqual(record.confidence, LETTER_MEMORY_CONFIDENCE)
        self.assertEqual(record.subjects, [str(self.sender.pk)])
        self.assertEqual(record.tick, state.read_tick)
        self.assertEqual(record.content["letter_source_id"], letter.source_id)
        self.assertEqual(record.content["statement"], body)
        self.assertEqual(ProjectionProgress.objects.get(source_id=source_id).status, "completed")

        # A replay of the same durable first-read source adds no cognition.
        project_correspondence_event(NarrativeEvent.objects.get(source_id=source_id))
        self.assertEqual(MemoryRecord.objects.filter(source_id=source_id).count(), 1)
        self.assertEqual(self.statements(self.owner.pk), [body])

    @covers_requirement("narrative-memory::memory-projection-is-idempotent-and-restart-safe")
    def test_replay_and_restart_drain_settle_one_memory(self):
        body = "合成重播內容"
        letter = self.deliver_npc(body=body)
        source_id = correspondence_event_source_id(letter.source_id, "delivered")
        self.assertEqual(ProjectionProgress.objects.get(source_id=source_id).status, "pending")
        self.assertFalse(MemoryRecord.objects.filter(source_id=source_id).exists())

        self.assertTrue(settle_delivery_cognition(letter.source_id))
        self.assertTrue(settle_delivery_cognition(letter.source_id))
        self.assertEqual(process_pending_correspondence_projections(), 0)
        self.assertEqual(MemoryRecord.objects.filter(source_id=source_id).count(), 1)
        self.assertEqual(MemoryRecord.objects.filter(owner_id=str(self.npc.pk)).count(), 1)
        self.assertEqual(ProjectionProgress.objects.get(source_id=source_id).status, "completed")
        self.assertEqual(self.statements(self.npc.pk), [body])

    @covers_requirement("narrative-memory::memory-projection-is-idempotent-and-restart-safe")
    def test_pending_source_without_occurrence_stays_pending_and_is_reported(self):
        ProjectionProgress.objects.create(
            source_id="correspondence:synthetic-missing:delivered", status="pending",
            projector_version=CORRESPONDENCE_PROJECTOR_VERSION,
        )
        with patch("world.narrative.correspondence_memory.log_warn") as warned:
            self.assertEqual(process_pending_correspondence_projections(), 0)
        self.assertEqual(warned.call_args.args[0], "correspondence_memory_projection_skipped")
        self.assertEqual(warned.call_args.kwargs["context"],
                         {"source_id": "correspondence:synthetic-missing:delivered",
                          "projector_version": CORRESPONDENCE_PROJECTOR_VERSION})
        self.assertEqual(ProjectionProgress.objects.get(
            source_id="correspondence:synthetic-missing:delivered").status, "pending")

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
        "correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions",
    )
    def test_claimed_deed_stays_told_speech_without_objective_progress(self):
        body = "合成信件聲稱：我已在北方森林擊敗那頭龍，任務已經完成。"
        letter = self.deliver_npc(body=body)
        source_id = correspondence_event_source_id(letter.source_id, "delivered")

        def state():
            return (
                self.sender.db.quest_records, self.sender.db.inventory,
                self.sender.db.appointments, self.npc.db.relations_data,
                NarrativeEvent.objects.count(), LetterSend.objects.count(),
                LetterState.objects.get(letter__source_id=letter.source_id).status,
            )

        before = state()
        self.assertEqual(process_pending_correspondence_projections(), 1)
        record = MemoryRecord.objects.get(source_id=source_id)
        self.assertEqual(record.knowledge_scope, LETTER_MEMORY_SCOPE)
        self.assertEqual(record.category, LETTER_MEMORY_CATEGORY)
        self.assertEqual(record.content["statement"], body)
        self.assertEqual(state(), before)
        self.assertFalse(NarrativeEvent.objects.filter(event_type__contains="quest").exists())

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe",
        "observability-logging::facade-is-the-sole-game-code-log-entry-point",
    )
    def test_projection_event_carries_identifiers_without_letter_text(self):
        body = "合成信件機密內容"
        letter = self.deliver_npc(body=body)
        with patch("world.narrative.correspondence_memory.log_info") as logged, \
                self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(process_pending_correspondence_projections(), 1)
        self.assertEqual([call.args[0] for call in logged.call_args_list],
                         ["correspondence_memory_projected"])
        self.assertEqual(logged.call_args.kwargs["context"], {
            "source_id": correspondence_event_source_id(letter.source_id, "delivered"),
            "owner_id": str(self.npc.pk),
            "projector_version": CORRESPONDENCE_PROJECTOR_VERSION,
            "records_count": 1,
        })
        self.assertNotIn(body, str(logged.call_args_list))


class CorrespondenceFaceToFaceTests(EvenniaTestCase):
    """Scenario: the NPC later discusses a delivered letter in person."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="Synthetic letter room")
        self.npc = create_object(LLMNPC, key="Synthetic letter reader", location=self.room)
        self.player = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic letter writer",
            location=self.room,
        )
        self.clock = get_world_clock()
        self.clock._persist(17)
        self.clock.tick = 17

    @covers_requirement(
        "npc-dialogue::npc-context-recalls-only-permitted-committed-experience",
        "narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring",
    )
    def test_delivered_letter_supplies_dialogue_continuity_without_turn_copies(self):
        head = "合成信件開頭：" + "北方森林的龍。" * 30
        tail = "獨特尾端詞"
        body = head + tail
        letter = send_letter(sender_id=self.player.pk, recipient_id=self.npc.pk,
                             body=body, source_id="synthetic-face-to-face")
        settle_correspondence_delivery(letter.sent_tick, letter.due_tick)
        source_id = correspondence_event_source_id(letter.source_id, "delivered")
        # Delivery leaves its durable projection pending; the recall boundary drains it.
        self.assertEqual(ProjectionProgress.objects.get(source_id=source_id).status, "pending")
        self.assertFalse(MemoryRecord.objects.filter(source_id=source_id).exists())

        speech = "請說說那封信"
        submit_turn(self.npc, self.player, speech)
        messages, snapshot_id = build_dialogue_context(self.npc, self.player, speech)
        cognition = messages[1]["content"]
        self.assertIn("北方森林的龍。", cognition)
        self.assertNotIn(tail, cognition)
        self.assertEqual(ProjectionProgress.objects.get(source_id=source_id).status, "completed")
        record = MemoryRecord.objects.get(source_id=source_id)
        self.assertEqual(record.owner_id, str(self.npc.pk))
        self.assertEqual(record.knowledge_scope, LETTER_MEMORY_SCOPE)
        self.assertIn(tail, record.content["statement"])
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
        self.assertIn(source_id, [row["source_id"] for row in snapshot.sources])
        # Continuity rides selected cognition, never a copy of the letter archive.
        self.assertEqual([row.speech for row in DialogueTurn.objects.all()], [speech])
        self.assertFalse(DialogueTurn.objects.filter(speech__contains=tail).exists())
