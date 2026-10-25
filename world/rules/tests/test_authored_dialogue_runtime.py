"""Data-contract test: authored dialogue runtime selection and transactional session delivery

Covers:
- select_authored_topic context validation and stale envelope rejection.
- Duplicate selection dedup: idempotent return for current request.
- Duplicate selection rejection after intervening different topic.
- Selection failure / session-write failure with rollback compensation.
- No time advancement on selection or replay.
- Snapshot replay verification.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from world.quests.catalog import register_catalog
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.affinity import AffinitySource
from world.rules.clock import get_world_clock
from world.rules.dialogue import (
    DialogueSession,
    DialogueBudgetExceededError,
    DuplicateSelectionError,
    SceneDelivery,
    StaleContextError,
    StaleSelectionError,
    TopicLockedError,
    TopicNotFoundError,
    clear_dialogue_session,
    live_dialogue_session,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_context import resolve_dialogue_context


class AuthoredDialogueRuntimeTests(EvenniaTest):
    """Integration and transactional tests for select_authored_topic."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.room1 = create_object(Room, key="大廳")
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()

        self.host = create_object(NPC, key="公會職員", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key="guild_staff")
        )

    def tearDown(self):
        clear_dialogue_session(self.char1)
        super().tearDown()

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_selection_delivers_complete_scene_and_updates_session(self):
        context = resolve_dialogue_context(self.char1, self.host)
        # Direct entry (no live context)
        affinity_before = self.host.relations.affinity_for(self.char1)
        delivery = select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-1",
            expected_context_id=None,
        )
        self.assertIsInstance(delivery, SceneDelivery)
        self.assertEqual(delivery.topic_id, "guild_staff.topic_01")
        self.assertEqual(delivery.kind, "formal")
        self.assertGreaterEqual(len(delivery.lines), 2)
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before + 1)

        # Session should now be in scene mode
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        self.assertEqual(session.kind, "scene")
        self.assertIsNone(session.line)
        self.assertIsNotNone(session.delivery)
        self.assertEqual(session.delivery.delivery_id, delivery.delivery_id)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_stale_envelope_context_id_rejected(self):
        open_or_refresh_dialogue(self.char1, self.host, "Hello")
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        valid_context_id = session.context_id

        # Mismatched context_id
        with self.assertRaises(StaleContextError):
            select_authored_topic(
                self.char1,
                self.host,
                "guild_staff.topic_01",
                selection_id="req-bad",
                expected_context_id="wrong_context_id",
            )

        # Null context_id when conversation is already live
        with self.assertRaises(StaleContextError):
            select_authored_topic(
                self.char1,
                self.host,
                "guild_staff.topic_01",
                selection_id="req-bad",
                expected_context_id=None,
            )

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_duplicate_selection_id_is_idempotent_without_second_affinity(self):
        delivery1 = select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-same",
            expected_context_id=None,
        )
        session = live_dialogue_session(self.char1)
        affinity_after_first = self.host.relations.affinity_for(self.char1)

        # Retry with identical selection_id
        delivery2 = select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-same",
            expected_context_id=session.context_id,
        )
        self.assertEqual(delivery1.delivery_id, delivery2.delivery_id)
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_after_first)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_duplicate_request_after_intervening_topic_is_rejected(self):
        delivery_a = select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-a",
            expected_context_id=None,
        )
        session1 = live_dialogue_session(self.char1)

        # Intervening topic B
        delivery_b = select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_02",
            selection_id="req-b",
            expected_context_id=session1.context_id,
        )
        session2 = live_dialogue_session(self.char1)
        affinity_after_b = self.host.relations.affinity_for(self.char1)

        # Replaying req-a after intervening topic B must be rejected as stale
        with self.assertRaises(StaleSelectionError):
            select_authored_topic(
                self.char1,
                self.host,
                "guild_staff.topic_01",
                selection_id="req-a",
                expected_context_id=session2.context_id,
            )
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_after_b)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_session_write_failure_rolls_back_relations_and_session(self):
        affinity_before = self.host.relations.affinity_for(self.char1)
        session_before = self.char1.db.dialogue_session

        with patch("world.rules.dialogue.open_or_refresh_dialogue", side_effect=RuntimeError("injected_write_fail")):
            with self.assertRaises(RuntimeError):
                select_authored_topic(
                    self.char1,
                    self.host,
                    "guild_staff.topic_01",
                    selection_id="req-fail",
                    expected_context_id=None,
                )

        # Assert rollback of relations and session
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)
        self.assertEqual(self.char1.db.dialogue_session, session_before)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_no_time_advancement_on_selection_or_replay(self):
        clock = get_world_clock()
        tick_before = clock.tick

        select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-tick-1",
            expected_context_id=None,
        )
        self.assertEqual(clock.tick, tick_before)

        session = live_dialogue_session(self.char1)
        select_authored_topic(
            self.char1,
            self.host,
            "guild_staff.topic_01",
            selection_id="req-tick-1",
            expected_context_id=session.context_id,
        )
        self.assertEqual(clock.tick, tick_before)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_oversized_scene_rejected_before_effects(self):
        affinity_before = self.host.relations.affinity_for(self.char1)
        session_before = self.char1.db.dialogue_session

        with patch("world.rules.dialogue.scene_canonical_bytes", return_value=8193):
            with self.assertRaises(DialogueBudgetExceededError):
                select_authored_topic(
                    self.char1,
                    self.host,
                    "guild_staff.topic_01",
                    selection_id="req-over-scene",
                    expected_context_id=None,
                )

        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)
        self.assertEqual(self.char1.db.dialogue_session, session_before)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_oversized_bundle_rejected_before_effects(self):
        affinity_before = self.host.relations.affinity_for(self.char1)
        session_before = self.char1.db.dialogue_session

        with patch("world.rules.dialogue.DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES", 100):
            with self.assertRaises(DialogueBudgetExceededError):
                select_authored_topic(
                    self.char1,
                    self.host,
                    "guild_staff.topic_01",
                    selection_id="req-over-bundle",
                    expected_context_id=None,
                )

        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)
        self.assertEqual(self.char1.db.dialogue_session, session_before)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_oversized_panel_rejected_before_effects(self):
        affinity_before = self.host.relations.affinity_for(self.char1)
        session_before = self.char1.db.dialogue_session

        with patch("world.rules.dialogue.DIALOGUE_PANEL_MAX_BYTES", 500):
            with self.assertRaises(DialogueBudgetExceededError):
                select_authored_topic(
                    self.char1,
                    self.host,
                    "guild_staff.topic_01",
                    selection_id="req-over-panel",
                    expected_context_id=None,
                )

        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)
        self.assertEqual(self.char1.db.dialogue_session, session_before)
