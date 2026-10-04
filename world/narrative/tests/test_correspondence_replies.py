"""Synthetic recorded/offline acceptance for optional remote correspondence."""

import json
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from server.correspondence_service import request_letter_reply
from tools.spec_traceability import covers_requirement
from world.ai.correspondence import LetterReply, register_correspondence
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.narrative.correspondence import (
    correspondence_event_source_id,
    get_letter,
    send_letter,
    settle_correspondence_delivery,
)
from world.narrative.memory import record_memory
from world.narrative.models import (
    LetterReplyWork,
    LetterSend,
    MemoryRecord,
    NarrativeEvent,
    ProjectionProgress,
)
from world.narrative.replies import attempt_reply, prepare_reply, settle_reply
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import AffinityConfig
from world.rules.clock import get_world_clock


def recorded(body="我願意日後和你見面，請再寫信告訴我你的想法。", effect=None):
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, json.dumps({
        "body": body, "effect": effect or {"kind": "none"},
    }, ensure_ascii=False))
    return client


class CorrespondenceReplyTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        register_correspondence()
        self.settings = override_settings(LLM_PROFILES=default_profiles())
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        affinity = patch("world.rules.affinity.get_config", return_value=AffinityConfig(
            invite_threshold=50, daily_interaction_cap=12, quest_completion_gain=5,
            friendly_fire_penalty_per_hit=2, sexual_forced_penalty=3,
            cap_breaks=(), stages=(),
        ))
        affinity.start()
        self.addCleanup(affinity.stop)
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic recipient")
        self.player = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic correspondent")
        self.clock = get_world_clock()
        self.tick(17)

    def tick(self, tick):
        self.clock._persist(tick)
        self.clock.tick = tick

    def incoming(self, identity="synthetic-incoming", body="我願意日後見面，這封信只是一份邀請。", delivered=True):
        letter = send_letter(sender_id=self.player.pk, recipient_id=self.npc.pk,
                             body=body, source_id=identity)
        if delivered:
            settle_correspondence_delivery(letter.sent_tick, letter.due_tick)
            self.tick(letter.due_tick)
        return letter

    @covers_requirement(
        "correspondence-delivery::accepted-letters-have-fixed-guaranteed-delivery",
        "correspondence-npc-replies::replies-use-delivered-inputs-and-remain-optional",
    )
    def test_offline_delivery_pending_and_explicit_recorded_smoke(self):
        profiles = default_profiles()
        profiles["correspondence"]["enabled"] = False
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=profiles):
            letter = self.incoming()
            self.assertEqual(get_letter(letter.source_id).status, "delivered")
            self.assertIsNone(request_letter_reply(letter.source_id, client=client).result)
        self.assertEqual(client.calls, [])
        self.assertEqual(LetterReplyWork.objects.get().status, "pending")
        self.assertEqual(LetterSend.objects.count(), 1)
        self.tick(20000)
        outgoing = request_letter_reply(letter.source_id, client=recorded()).result
        self.assertEqual((outgoing.sent_tick, outgoing.due_tick), (20000, 23600))
        self.assertEqual(outgoing.status, "sent")
        settle_correspondence_delivery(20000, 23599)
        self.assertEqual(get_letter(outgoing.source_id).status, "sent")
        settle_correspondence_delivery(23599, 23600)
        self.assertEqual(get_letter(outgoing.source_id).status, "available")

    @covers_requirement(
        "narrative-context::generation-retains-an-immutable-source-snapshot",
        "correspondence-npc-replies::replies-use-delivered-inputs-and-remain-optional",
    )
    def test_delivered_only_permissions_and_immutable_linked_snapshot(self):
        letter = self.incoming(delivered=False)
        with self.assertRaises(LetterReplyWork.DoesNotExist):
            prepare_reply(letter.source_id)
        record_memory(owner_id=str(self.npc.pk), content={"summary": "合成核心準則"},
                      tier="core", source_id="synthetic:permitted")
        record_memory(owner_id=str(self.player.pk), content={"summary": "不應洩漏的秘密"},
                      tier="core", source_id="synthetic:private")
        settle_correspondence_delivery(letter.sent_tick, letter.due_tick)
        snapshot = prepare_reply(letter.source_id)
        self.assertIn("合成核心準則", str(snapshot.rendered_payload))
        self.assertNotIn("不應洩漏", str(snapshot.rendered_payload))
        # The drained delivered letter is permitted owner cognition: it joins the
        # core selection's source in the captured provenance.
        self.assertEqual(
            [row["source_id"] for row in snapshot.sources],
            ["synthetic:permitted",
             correspondence_event_source_id(letter.source_id, "delivered")],
        )
        outgoing = settle_reply(letter.source_id, snapshot.snapshot_id, LetterReply("我記得你的來信。"))
        row = LetterSend.objects.get(source_id=outgoing.source_id)
        self.assertEqual(row.reply_to, letter.source_id)
        self.assertEqual(row.source_snapshot_id, snapshot.snapshot_id)
        with self.assertRaises(ValueError):
            snapshot.save()
        with self.assertRaises(ValueError):
            row.save()

    @covers_requirement("correspondence-npc-replies::replies-use-delivered-inputs-and-remain-optional")
    def test_restart_replay_deduplicates_outgoing_and_relationship(self):
        incoming = self.incoming()
        snapshot = prepare_reply(incoming.source_id)
        proposal = LetterReply("謝謝你告訴我。", 5)
        first = settle_reply(incoming.source_id, snapshot.snapshot_id, proposal)
        restarted = LetterReplyWork.objects.get(letter__source_id=incoming.source_id)
        self.assertEqual(restarted.status, "complete")
        self.assertEqual(settle_reply(incoming.source_id, snapshot.snapshot_id, proposal), first)
        never_called = FakeLLMClient()
        self.assertEqual(attempt_reply(incoming.source_id, never_called).result, first)
        self.assertEqual(never_called.calls, [])
        self.assertEqual(LetterSend.objects.count(), 2)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 5)

    @covers_requirement(
        "correspondence-npc-replies::replies-use-delivered-inputs-and-remain-optional",
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe",
        "correspondence-memory::letter-knowledge-enters-at-the-approved-boundary",
    )
    def test_delayed_delivery_projection_settles_before_capture_or_waits(self):
        incoming = self.incoming()
        source_id = correspondence_event_source_id(incoming.source_id, "delivered")
        self.assertEqual(
            ProjectionProgress.objects.get(source_id=source_id).status, "pending"
        )
        self.assertFalse(MemoryRecord.objects.filter(source_id=source_id).exists())

        # Catch up: capture drains the durable delivery source before recall.
        snapshot = prepare_reply(incoming.source_id)
        self.assertEqual(
            ProjectionProgress.objects.get(source_id=source_id).status, "completed"
        )
        record = MemoryRecord.objects.get(source_id=source_id)
        self.assertEqual(record.owner_id, str(self.npc.pk))
        self.assertEqual(record.knowledge_scope, "told")
        self.assertIn(source_id, [row["source_id"] for row in snapshot.sources])

        # Wait: a delivery source that cannot settle never lets capture proceed.
        ProjectionProgress.objects.filter(source_id=source_id).update(status="pending")
        NarrativeEvent.objects.filter(source_id=source_id).delete()
        with self.assertRaises(ValueError):
            prepare_reply(incoming.source_id)
        self.assertEqual(LetterReplyWork.objects.get().status, "pending")

    @covers_requirement(
        "affinity-system::apply-affinity-change-is-the-sole-affinity-writer-with-a-source-capped-daily-budget",
        "correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions",
    )
    def test_remote_relation_routes_existing_rules_budget_without_colocation(self):
        self.npc.location = create_object("typeclasses.rooms.Room", key="Synthetic distant room")
        self.player.location = create_object("typeclasses.rooms.Room", key="Synthetic origin room")
        first = self.incoming(identity="synthetic-remote-first")
        accepted = attempt_reply(first.source_id, recorded(effect={"kind": "adjust_relation", "delta": 5})).result
        self.assertIsNotNone(accepted)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 5)
        apply_affinity_change(self.npc, self.player, AffinitySource.AI_DIALOGUE, 99)
        before = self.npc.relations._load(self.player)
        incoming = self.incoming()
        result = attempt_reply(incoming.source_id, recorded(effect={"kind": "adjust_relation", "delta": 10})).result
        self.assertIsNotNone(result)
        after = self.npc.relations._load(self.player)
        self.assertEqual(after.value, before.value)
        self.assertEqual(after.daily_gain, before.daily_gain)
        self.assertNotEqual(self.npc.location, self.player.location)

    @covers_requirement(
        "guardrail::guarded-generative-calls-validate-retry-then-degrade",
        "correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions",
    )
    def test_forbidden_channel_effects_never_reach_other_owners(self):
        incoming = self.incoming()
        before = (self.player.db.inventory, self.player.db.quest_records,
                  self.player.db.appointments, self.npc.db.relations_data)
        for kind in ("offer_quest", "accept_quest", "complete_objective", "confirm_appointment",
                     "give_item", "take_item", "physical_action", "reveal_lore", "party_invite"):
            with self.subTest(kind=kind):
                client = recorded(body="我已完成你提到的工作。", effect={"kind": kind})
                self.assertIsNone(attempt_reply(incoming.source_id, client).result)
                self.assertGreaterEqual(len(client.calls), 1)
                self.assertEqual(LetterSend.objects.count(), 1)
                self.assertEqual(LetterReplyWork.objects.get().status, "pending")
        self.assertEqual(before, (self.player.db.inventory, self.player.db.quest_records,
                                 self.player.db.appointments, self.npc.db.relations_data))

    @covers_requirement("correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions")
    def test_willingness_and_quest_claim_are_only_stored_statements(self):
        incoming = self.incoming()
        body = "我願意和你見面；我認為信中提到的工作已經完成。"
        before = (self.player.db.quest_records, self.player.db.inventory, self.player.db.appointments)
        result = attempt_reply(incoming.source_id, recorded(body=body)).result
        self.assertEqual(result.body, body)
        self.assertEqual(before, (self.player.db.quest_records, self.player.db.inventory,
                                 self.player.db.appointments))
        self.assertEqual(self.npc.db.relations_data, None)

    @covers_requirement("correspondence-npc-replies::replies-use-delivered-inputs-and-remain-optional")
    def test_transport_failure_keeps_work_pending_without_text(self):
        incoming = self.incoming()
        offline = FakeLLMClient()
        offline.add_timeout(lambda descriptor: True)
        self.assertIsNone(attempt_reply(incoming.source_id, offline).result)
        work = LetterReplyWork.objects.get()
        self.assertEqual(work.status, "pending")
        self.assertTrue(work.snapshot_id)
        self.assertEqual(LetterSend.objects.count(), 1)

    @covers_requirement("correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions")
    def test_relationship_payload_bounds_reject_extra_authority(self):
        incoming = self.incoming()
        for effect in (
            {"kind": "adjust_relation", "delta": -1},
            {"kind": "adjust_relation", "delta": 11},
            {"kind": "adjust_relation", "delta": True},
            {"kind": "adjust_relation", "delta": 3, "item": "synthetic-item"},
            {"kind": "none", "quest": "synthetic-quest"},
        ):
            with self.subTest(effect=effect):
                self.assertIsNone(attempt_reply(incoming.source_id, recorded(effect=effect)).result)
                self.assertEqual(LetterSend.objects.count(), 1)
                self.assertIsNone(self.npc.db.relations_data)

    def test_zero_delta_proposal_sends_without_materializing_a_record(self):
        # A zero delta means "no relationship change", like the face-to-face
        # seam: the rules writer is never called, so its lazy day-tick reset
        # cannot materialize an affinity record for a pair that had none.
        self.tick(100000)
        incoming = self.incoming()
        result = attempt_reply(
            incoming.source_id, recorded(effect={"kind": "adjust_relation", "delta": 0})
        ).result
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "sent")
        self.assertIsNone(self.npc.db.relations_data)
        self.assertFalse(self.npc.relations.has_record(self.player))

    def test_stale_attempt_revalidates_and_later_explicit_attempt_succeeds(self):
        incoming = self.incoming()
        snapshot = prepare_reply(incoming.source_id)
        record_memory(owner_id=str(self.npc.pk), content={"summary": "新的準則"},
                      tier="core", source_id="synthetic:new")
        self.assertIsNone(settle_reply(incoming.source_id, snapshot.snapshot_id, LetterReply("謝謝你的邀請。", 3)))
        self.assertEqual(LetterSend.objects.count(), 1)
        self.assertIsNone(self.npc.db.relations_data)
        self.assertIsNotNone(attempt_reply(incoming.source_id, recorded()).result)

    def test_superseded_snapshot_cannot_settle(self):
        incoming = self.incoming()
        first = prepare_reply(incoming.source_id)
        second = prepare_reply(incoming.source_id)
        self.assertIsNone(settle_reply(incoming.source_id, first.snapshot_id, LetterReply("謝謝你的邀請。")))
        self.assertIsNotNone(settle_reply(incoming.source_id, second.snapshot_id, LetterReply("謝謝你的邀請。")))

    def test_send_failure_rolls_back_relationship_and_work(self):
        incoming = self.incoming()
        snapshot = prepare_reply(incoming.source_id)
        before = self.npc.db.relations_data
        with patch("world.narrative.replies.send_letter", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                settle_reply(incoming.source_id, snapshot.snapshot_id, LetterReply("謝謝你的邀請。", 4))
        self.assertEqual(self.npc.db.relations_data, before)
        self.assertEqual(LetterReplyWork.objects.get().status, "pending")
        self.assertEqual(LetterSend.objects.count(), 1)

    def test_full_length_delivered_input_is_not_silently_truncated(self):
        incoming = self.incoming(body="信" * 8000)
        snapshot = prepare_reply(incoming.source_id)
        self.assertIn("信" * 8000, snapshot.rendered_payload["user_prompt"])

    def test_boundary_logs_contain_only_ids_and_context(self):
        incoming = self.incoming()
        with patch("world.narrative.replies.log_info") as logged:
            snapshot = prepare_reply(incoming.source_id)
            with self.captureOnCommitCallbacks(execute=True):
                result = settle_reply(incoming.source_id, snapshot.snapshot_id, LetterReply("私人回信內容。"))
        events = {call.args[0] for call in logged.call_args_list}
        self.assertIn("correspondence_reply_captured", events)
        self.assertIn("correspondence_reply_committed", events)
        self.assertNotIn(result.body, str(logged.call_args_list))
        self.assertNotIn(incoming.body, str(logged.call_args_list))
        for call in logged.call_args_list:
            self.assertIn("context", call.kwargs)
