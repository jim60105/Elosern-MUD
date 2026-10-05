"""Synthetic letter surface acceptance and actual changed-path offline smoke."""

from unittest.mock import Mock, patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.correspondence import CmdLetters
from tools.spec_traceability import covers_requirement
from web.webclient.actions import correspondence_actions as actions
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.protocol import _validate_result_data
from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.narrative import player_correspondence as surface
from world.narrative.correspondence import get_letter, register_correspondence_delivery, send_letter
from world.narrative.models import LetterSend, LetterState, NarrativeEvent, ProjectionProgress
from world.rules.clock import AdvanceSource, _EVENT_SOURCES, get_world_clock


class PlayerCorrespondenceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        register_correspondence_delivery()
        self.player = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic letter owner", location=self.room1)
        self.other = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic other owner")
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic addressee")
        self.room1.tags.add("synthetic_branch_a")
        self.room2.tags.add("synthetic_branch_b")
        registry = {}
        for key, settlement in (("synthetic_branch_a", "synthetic_settlement_a"), ("synthetic_branch_b", "synthetic_settlement_b")):
            registry[key] = PlaceDefinition(key, settlement, PlaceKind.COURIER_STATION,
                                           "合成驛站", "合成分站。", (1, 1), "驛站", (), letter_service=True)
        self.registry_patch = patch.object(surface, "PLACE_REGISTRY", registry)
        self.registry_patch.start()
        self.clock = get_world_clock()
        self.clock.tick = 17
        self.clock._persist(17)

    def tearDown(self):
        self.registry_patch.stop()
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self.sources)
        super().tearDown()

    def due_letter(self, owner=None, source="synthetic_incoming", body="合成私密來信"):
        record = send_letter(sender_id=self.npc.pk, recipient_id=(owner or self.player).pk,
                             body=body, source_id=source)
        self.clock.advance(3600, AdvanceSource.COMMAND, [])
        return record

    @covers_requirement("correspondence-delivery::accepted-letters-have-fixed-guaranteed-delivery")
    def test_send_preflight_and_duplicate_are_atomic(self):
        duplicate = create_object("typeclasses.npcs.NPC", key=self.npc.key)
        for recipient, body in (("unknown synthetic", "text"), (self.npc.key, "text"),
                                (f"#{self.npc.pk}", " "), (f"#{self.npc.pk}", "a" * 8001)):
            with self.subTest(recipient=recipient, size=len(body)), self.assertRaises(surface.CorrespondenceError):
                surface.send(self.player, recipient, body)
        self.assertEqual(LetterSend.objects.count(), 0)
        self.assertEqual(LetterState.objects.count(), 0)
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        duplicate.delete()
        first = surface.send(self.player, self.npc.key, "原文=保留", "synthetic_outgoing")
        self.assertEqual(first, surface.send(self.player, f"#{self.npc.pk}", "原文=保留", "synthetic_outgoing"))
        self.assertEqual(first.due_tick - first.sent_tick, 3600)
        with self.assertRaises(surface.CorrespondenceError):
            surface.send(self.player, self.npc.key, "不同內容", "synthetic_outgoing")
        self.assertEqual(LetterSend.objects.count(), 1)
        self.player.location = None
        with self.assertRaises(surface.CorrespondenceError):
            surface.send(self.player, self.npc.key, "remote")
        with self.assertRaises(surface.CorrespondenceError):
            surface.collect(self.player)
        with self.assertRaises(surface.CorrespondenceError):
            surface.list_letters(self.npc)

    @covers_requirement("correspondence-player-surface::sending-and-collection-require-any-branch")
    def test_any_branch_acquisition_and_write_free_remote_list(self):
        incoming = self.due_letter()
        self.due_letter(source="synthetic_second")
        self.due_letter(self.other, "synthetic_foreign")
        self.player.location = None
        self.assertEqual(surface.list_letters(self.player)["letters"], [])
        self.player.location = self.room2
        ids = surface.collect(self.player)
        self.assertEqual(set(ids), {incoming.source_id, "synthetic_second"})
        states = LetterState.objects.filter(recipient_id=str(self.player.pk))
        self.assertTrue(all(state.status == "collected" and state.read_tick is None for state in states))
        self.assertEqual(NarrativeEvent.objects.filter(event_type="correspondence_read").count(), 0)
        self.assertEqual(surface.collect(self.player), ())
        self.player.location = None
        before = (LetterState.objects.count(), NarrativeEvent.objects.count(), ProjectionProgress.objects.count())
        page = surface.list_letters(self.player)
        self.assertFalse(page["branch"])
        self.assertEqual(len(page["letters"]), 2)
        self.assertNotIn("body", str(page))
        self.assertEqual(before, (LetterState.objects.count(), NarrativeEvent.objects.count(), ProjectionProgress.objects.count()))
        self.assertEqual(LetterState.objects.get(letter__source_id="synthetic_foreign").status, "available")

    @covers_requirement("correspondence-player-surface::collection-and-reading-remain-distinct")
    def test_read_reread_and_late_failure_roll_back_once(self):
        incoming = self.due_letter()
        surface.collect(self.player)
        self.player.location = None
        with patch("world.narrative.player_correspondence.ProjectionProgress.objects.create", side_effect=RuntimeError("late")):
            with self.assertRaisesRegex(RuntimeError, "late"):
                surface.read(self.player, incoming.source_id)
        state = LetterState.objects.get(letter__source_id=incoming.source_id)
        self.assertIsNone(state.read_tick)
        self.assertEqual(state.status, "collected")
        self.assertFalse(NarrativeEvent.objects.filter(event_type="correspondence_read").exists())
        first = surface.read(self.player, incoming.source_id)
        tick = LetterState.objects.get(pk=state.pk).read_tick
        self.clock.advance(1, AdvanceSource.COMMAND, [])
        self.assertEqual(surface.read(self.player, incoming.source_id), first)
        self.assertEqual(LetterState.objects.get(pk=state.pk).read_tick, tick)
        event = NarrativeEvent.objects.get(event_type="correspondence_read")
        self.assertEqual(event.participants, [str(self.player.pk)])
        self.assertEqual(event.content, {"letter_source_id": incoming.source_id})
        self.assertEqual(ProjectionProgress.objects.filter(source_id=event.source_id).count(), 1)

    @covers_requirement("correspondence-player-surface::browser-and-text-channels-share-authoritative-permissions")
    def test_forged_actions_reject_without_body_or_read_event(self):
        mine = self.due_letter(body="synthetic_secret")
        foreign = self.due_letter(self.other, "synthetic_foreign", "foreign_secret")
        for source in (mine.source_id, foreign.source_id, "missing"):
            result = actions.read_adapter(self.player, {"source_id": source})
            self.assertEqual(result["outcome"], "rejected")
            self.assertNotIn("data", result)
            self.assertNotIn("secret", str(result))
        self.other.location = self.room2
        surface.collect(self.other)
        self.assertEqual(actions.read_adapter(self.player, {"source_id": foreign.source_id})["outcome"], "rejected")
        self.assertFalse(NarrativeEvent.objects.filter(event_type="correspondence_read").exists())

    @covers_requirement("webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe")
    def test_exact_actions_and_full_body_protocol_bounds(self):
        registry = build_production_action_registry()
        for name in ("list", "collect", "send", "read"):
            self.assertIn(f"letters.{name}", registry.action_ids)
        for validator, payload in ((actions.validate_list, {"after": True}),
                                   (actions.validate_collect, {"owner": self.other.pk}),
                                   (actions.validate_read, {"source_id": "x", "owner": self.other.pk}),
                                   (actions.validate_send, {"recipient": "x", "body_parts": ["a"] * 5, "source_id": "x"})):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validator(payload)
        incoming = self.due_letter(body="𐀀" * 8000)
        surface.collect(self.player)
        self.player.location = None
        result = actions.read_adapter(self.player, actions.validate_read({"source_id": incoming.source_id}))
        self.assertEqual(result["outcome"], "success")
        _validate_result_data(result["data"])
        self.assertEqual("".join(result["data"]["body_parts"]), "𐀀" * 8000)
        payload = actions.validate_send({"recipient": self.npc.key, "body_parts": ["𐀀" * 2000] * 4, "source_id": "synthetic_browser_send"})
        self.player.location = self.room1
        self.assertEqual(actions.send_adapter(self.player, payload)["outcome"], "success")
        self.assertEqual(actions.send_adapter(self.player, payload)["outcome"], "success")
        self.assertEqual(LetterSend.objects.filter(source_id="synthetic_browser_send").count(), 1)

    def test_real_text_and_browser_offline_smoke_and_log_privacy(self):
        command = CmdLetters()
        command.caller = self.player
        self.player.msg = Mock()
        command.args = f"寄 #{self.other.pk}=合成機密=原文"
        with patch("commands.correspondence.log_info") as cmd_log:
            command.at_pre_cmd()
            command.func()
            self.assertNotIn("合成機密", str(cmd_log.call_args_list))
            self.assertNotIn(str(self.other.pk), str(cmd_log.call_args_list))
        record = LetterSend.objects.get(sender_id=str(self.player.pk))
        self.assertEqual(record.body, "合成機密=原文")
        self.clock.advance(3600, AdvanceSource.COMMAND, [])
        self.other.location = self.room2
        with patch("world.narrative.player_correspondence.log_info") as domain_log:
            with self.captureOnCommitCallbacks(execute=True):
                result = actions.collect_adapter(self.other, {})
                self.assertEqual(result["data"]["count"], 1)
                self.other.location = None
                result = actions.read_adapter(self.other, {"source_id": record.source_id})
                self.assertEqual("".join(result["data"]["body_parts"]), record.body)
                actions.read_adapter(self.other, {"source_id": record.source_id})
            self.assertEqual([call.args[0] for call in domain_log.call_args_list], ["correspondence_collected", "correspondence_read"])
            self.assertNotIn(record.body, str(domain_log.call_args_list))
        command.caller = self.other
        self.other.msg = Mock()
        command.args = f"讀 {record.source_id}"
        command.func()
        self.other.msg.assert_called_once_with(record.body)

    @covers_requirement("correspondence-player-surface::sending-and-collection-require-any-branch")
    @covers_requirement("correspondence-player-surface::letter-panel-state-follows-genuine-lifecycle-boundaries")
    def test_branch_page_after_leaving_grants_no_remote_send_or_collection(self):
        incoming = self.due_letter()
        self.player.location = self.room2
        page = surface.list_letters(self.player)
        self.assertTrue(page["branch"])
        # Walking away from the branch the page was loaded at re-checks
        # server-side on every collect/send: the stale capability grants
        # nothing, and nothing is acquired or sent.
        untagged = create_object("typeclasses.rooms.Room", key="Synthetic untagged room")
        self.player.location = untagged
        self.assertFalse(surface.branch_available(self.player))
        before = (
            LetterSend.objects.count(),
            LetterState.objects.count(),
            NarrativeEvent.objects.count(),
            ProjectionProgress.objects.count(),
        )
        collected = actions.collect_adapter(self.player, {})
        self.assertEqual(collected["outcome"], "rejected")
        self.assertNotIn("data", collected)
        sent = actions.send_adapter(
            self.player,
            actions.validate_send(
                {
                    "recipient": self.npc.key,
                    "body_parts": ["合成遠端內容"],
                    "source_id": "synthetic_remote_send",
                }
            ),
        )
        self.assertEqual(sent["outcome"], "rejected")
        self.assertNotIn("data", sent)
        self.assertEqual(LetterSend.objects.filter(source_id="synthetic_remote_send").count(), 0)
        self.assertEqual(
            before,
            (
                LetterSend.objects.count(),
                LetterState.objects.count(),
                NarrativeEvent.objects.count(),
                ProjectionProgress.objects.count(),
            ),
        )
        state = LetterState.objects.get(letter__source_id=incoming.source_id)
        self.assertEqual(state.status, "available")
        self.assertIsNone(state.read_tick)

    @covers_requirement("correspondence-player-surface::collection-and-reading-remain-distinct")
    @covers_requirement("correspondence-player-surface::letter-loading-has-explicit-recovery-and-authoritative-response-updates")
    def test_collected_unread_letter_is_portable_and_reads_exactly_once(self):
        incoming = self.due_letter(body="合成隨身內容")
        baseline = ProjectionProgress.objects.count()
        self.player.location = self.room1
        collected = actions.collect_adapter(self.player, {})
        self.assertEqual(collected["outcome"], "success")
        self.assertEqual(collected["data"]["count"], 1)
        # Collection is not reading: the acquired letter stays unread and no
        # knowledge source is created.
        state = LetterState.objects.get(letter__source_id=incoming.source_id)
        self.assertEqual(state.status, "collected")
        self.assertIsNone(state.read_tick)
        self.assertFalse(NarrativeEvent.objects.filter(event_type="correspondence_read").exists())
        self.assertEqual(ProjectionProgress.objects.count(), baseline)

        # Portable reading anywhere: away from every branch the owned
        # collected-but-unread letter is listed and still opens.
        self.player.location = None
        page = surface.list_letters(self.player)
        self.assertFalse(page["branch"])
        self.assertEqual([row["source_id"] for row in page["letters"]], [incoming.source_id])
        self.assertIsNone(page["letters"][0]["read_tick"])
        read_result = actions.read_adapter(self.player, {"source_id": incoming.source_id})
        self.assertEqual(read_result["outcome"], "success")
        self.assertEqual("".join(read_result["data"]["body_parts"]), "合成隨身內容")
        first_tick = LetterState.objects.get(pk=state.pk).read_tick
        self.assertIsNotNone(first_tick)
        self.assertEqual(NarrativeEvent.objects.filter(event_type="correspondence_read").count(), 1)
        self.assertEqual(ProjectionProgress.objects.count(), baseline + 1)
        # Rereading, still away from every branch, writes nothing.
        first = surface.read(self.player, incoming.source_id)
        self.clock.advance(1, AdvanceSource.COMMAND, [])
        self.assertEqual(surface.read(self.player, incoming.source_id), first)
        reread_tick = LetterState.objects.get(pk=state.pk).read_tick
        self.assertEqual(reread_tick, first_tick)
        self.assertEqual(NarrativeEvent.objects.filter(event_type="correspondence_read").count(), 1)
        self.assertEqual(ProjectionProgress.objects.count(), baseline + 1)

    @covers_requirement("correspondence-player-surface::browser-and-text-channels-share-authoritative-permissions")
    def test_foreign_and_uncollected_reads_leak_no_prose_or_read_state(self):
        mine = self.due_letter(body="synthetic_secret")
        foreign = self.due_letter(self.other, "synthetic_foreign", "foreign_secret")
        self.player.location = self.room1
        surface.collect(self.player)
        self.other.location = self.room2
        surface.collect(self.other)
        self.player.location = None
        before = (ProjectionProgress.objects.count(), NarrativeEvent.objects.count())
        for source_id in (foreign.source_id, "synthetic_missing"):
            denied = actions.read_adapter(self.player, {"source_id": source_id})
            self.assertEqual(denied["outcome"], "rejected")
            self.assertNotIn("data", denied)
            self.assertNotIn("secret", str(denied))
        # A forged or uncollected read establishes nothing for anyone.
        self.assertEqual(before, (ProjectionProgress.objects.count(), NarrativeEvent.objects.count()))
        self.assertFalse(NarrativeEvent.objects.filter(event_type="correspondence_read").exists())
        self.assertIsNone(LetterState.objects.get(letter__source_id=foreign.source_id).read_tick)
        self.assertIsNone(LetterState.objects.get(letter__source_id=mine.source_id).read_tick)

    @covers_requirement("correspondence-player-surface::personal-letters-load-once-per-opening")
    def test_anchor_duplicates_and_pagination_fail_closed(self):
        duplicate = create_object("typeclasses.rooms.Room", key="Synthetic duplicate anchor", tags=["synthetic_branch_a"])
        self.assertFalse(surface.branch_available(self.player))
        with self.assertRaises(surface.CorrespondenceError):
            surface.collect(self.player)
        # The browser adapters are refused identically: a duplicate-tagged
        # anchor is never an authorized branch, and an unauthored room is not
        # one either.
        rejected = actions.collect_adapter(self.player, {})
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertNotIn("data", rejected)
        self.assertEqual(
            actions.send_adapter(
                self.player,
                actions.validate_send(
                    {
                        "recipient": self.npc.key,
                        "body_parts": ["合成重複錨點"],
                        "source_id": "synthetic_duplicate_anchor",
                    }
                ),
            )["outcome"],
            "rejected",
        )
        self.assertEqual(LetterSend.objects.filter(source_id="synthetic_duplicate_anchor").count(), 0)
        duplicate.delete()
        unauthored = create_object("typeclasses.rooms.Room", key="Synthetic unauthored room")
        self.player.location = unauthored
        self.assertFalse(surface.branch_available(self.player))
        self.assertEqual(actions.collect_adapter(self.player, {})["outcome"], "rejected")
        self.player.location = self.room1
        for index in range(21):
            send_letter(sender_id=self.npc.pk, recipient_id=self.player.pk, body="Synthetic page", source_id=f"synthetic_page_{index}")
        self.clock.advance(3600, AdvanceSource.COMMAND, [])
        surface.collect(self.player)
        first = surface.list_letters(self.player)
        second = surface.list_letters(self.player, first["next"])
        self.assertEqual(len(first["letters"]), 20)
        self.assertEqual(len(second["letters"]), 1)
        self.assertIsNone(second["next"])
        self.assertFalse({row["source_id"] for row in first["letters"]} & {row["source_id"] for row in second["letters"]})
