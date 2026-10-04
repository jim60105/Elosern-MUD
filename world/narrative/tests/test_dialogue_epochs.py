"""Synthetic recorded/offline acceptance for explicit dialogue epochs."""

import json
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import LLMNPC
from typeclasses.characters import Character
from typeclasses.rooms import Room
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles, LLMProfile
from world.ai import guardrail
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.npc_dialogue import build_npc_dialogue_prompt, generate_npc_reply, register_npc_dialogue
from world.ai.client import OpenAICompatClient
from world.narrative.dialogue import build_dialogue_context, submit_turn, settle_response
from world.narrative.epochs import compact_epoch, current_epoch, start_epoch
from world.narrative.models import DialogueEpoch, DialogueFrame, DialogueTurn, NarrativeContextSnapshot
from world.narrative.memory import record_memory, revise_memory


def recorded_summary(text="The player asked about repairs; the NPC offered advice."):
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, json.dumps({"summary": text}))
    return client


class DialogueEpochTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="Synthetic room")
        self.npc = create_object(LLMNPC, key="Synthetic speaker", location=self.room)
        self.player = create_object(Character, key="Synthetic player", location=self.room)

    def turn(self, speech):
        identity = submit_turn(self.npc, self.player, speech)
        messages, snapshot = build_dialogue_context(self.npc, self.player, speech)
        settle_response(self.npc, self.player, identity, "Recorded reply", snapshot_id=snapshot)
        return messages, snapshot

    @covers_requirement(
        "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona",
        "dialogue-epochs::stable-prefixes-change-only-at-legitimate-invalidation",
    )
    def test_movement_preserves_prefix_and_original_frame_bytes(self):
        first, _ = self.turn("First question")
        frame = DialogueFrame.objects.get()
        destination = create_object(Room, key="Synthetic destination")
        self.npc.location = destination
        second, snapshot = self.turn("Second question")
        self.assertEqual(first[0], second[0])
        payload = json.loads(second[1]["content"])
        self.assertEqual(payload["frames"][0], frame.content)
        self.assertEqual(json.loads(payload["frames"][0])["location"], self.room.key)
        self.assertEqual(json.loads(payload["current"])["location"], destination.key)
        self.assertIn("supersedes", json.loads(payload["current"])["authority"])
        self.assertEqual(DialogueEpoch.objects.count(), 1)
        self.assertLessEqual(NarrativeContextSnapshot.objects.get(snapshot_id=snapshot).budget_accounting["total_rendered_tokens"], 3078)
        for mutate in (lambda: frame.save(), lambda: frame.delete(), lambda: DialogueFrame.objects.update(tick=9)):
            with self.assertRaises(ValueError):
                mutate()

    @covers_requirement("dialogue-epochs::epoch-compaction-preserves-original-turns-and-provenance")
    def test_successful_compaction_retains_originals_and_exact_generation_sources(self):
        self.turn("Can you repair this?")
        before = list(DialogueTurn.objects.values_list("id", "speech"))
        successor = compact_epoch(self.npc, self.player, recorded_summary()).result
        self.assertIsNotNone(successor)
        self.assertEqual(successor.reason, "compaction")
        self.assertEqual([ref["turn_id"] for ref in successor.source_refs], [row[0] for row in before])
        self.assertEqual(list(DialogueTurn.objects.values_list("id", "speech")), before)
        self.assertTrue(successor.generation_id)
        self.assertTrue(successor.snapshot_id)
        self.assertEqual(successor.start_turn_id, before[-1][0])
        messages, _ = self.turn("Thanks")
        self.assertIn(successor.summary, messages[1]["content"])
        with self.assertRaises(ValueError):
            successor.save()

    @covers_requirement(
        "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline",
        "dialogue-epochs::epoch-compaction-preserves-original-turns-and-provenance",
    )
    def test_offline_and_oversized_summary_leave_current_epoch_usable(self):
        self.turn("First question")
        original = current_epoch(self.npc, self.player)
        profiles = default_profiles()
        profiles["dialogue_summary"]["enabled"] = False
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=profiles):
            self.assertIsNone(compact_epoch(self.npc, self.player, client).result)
        self.assertEqual(client.calls, [])
        self.assertIsNone(compact_epoch(self.npc, self.player, recorded_summary("字" * 1000)).result)
        self.assertEqual(current_epoch(self.npc, self.player).pk, original.pk)
        self.turn("Still playable")
        self.assertEqual(DialogueTurn.objects.count(), 4)

    @covers_requirement("dialogue-epochs::stable-prefixes-change-only-at-legitimate-invalidation")
    def test_natural_boundary_and_version_changes_preserve_history(self):
        first, _ = self.turn("First")
        original = current_epoch(self.npc, self.player)
        self.npc.key = "Changed synthetic identity"
        second, _ = self.turn("Second")
        self.assertNotEqual(first[0], second[0])
        changed = current_epoch(self.npc, self.player)
        self.assertNotEqual(changed.pk, original.pk)
        boundary = start_epoch(self.npc, self.player)
        self.assertEqual(boundary.reason, "natural_boundary")
        self.assertEqual(DialogueTurn.objects.count(), 4)
        self.assertEqual(DialogueFrame.objects.count(), 2)

    @covers_requirement("dialogue-epochs::stable-prefixes-change-only-at-legitimate-invalidation")
    def test_persona_revision_invalidates_epoch_even_when_text_is_identical(self):
        self.npc.db.npc_persona_meta = {"persona_version": 1}
        first, _ = self.turn("First")
        original = current_epoch(self.npc, self.player)
        self.npc.db.npc_persona_meta = {"persona_version": 2}
        second, _ = self.turn("Second")
        self.assertEqual(first[0], second[0])
        self.assertNotEqual(current_epoch(self.npc, self.player).pk, original.pk)
        self.assertEqual(DialogueFrame.objects.filter(epoch=original).count(), 1)

    @covers_requirement("dialogue-epochs::stable-prefixes-change-only-at-legitimate-invalidation")
    def test_historical_frame_preserves_original_memory_revision_after_inactivation(self):
        memory, _, _ = record_memory(owner_id=str(self.npc.pk), tier="core",
                               source_id="synthetic:epoch-memory", content={"summary": "Synthetic remembered claim"})
        self.turn("First question")
        original = DialogueFrame.objects.get()
        original_sources = original.sources
        revise_memory(record=memory, availability="inactive")
        second, _ = self.turn("Second question")
        payload = json.loads(second[1]["content"])
        self.assertEqual(payload["frames"][0], original.content)
        original.refresh_from_db()
        self.assertEqual(original.sources, original_sources)
        self.assertEqual(original.sources[0]["revision_number"], 1)
        self.assertNotIn("cognition", json.loads(payload["current"]))

    @covers_requirement("dialogue-epochs::epoch-compaction-preserves-original-turns-and-provenance")
    def test_invalid_summary_and_oversized_original_never_destroy_history(self):
        self.turn("First")
        epoch = current_epoch(self.npc, self.player)
        invalid = FakeLLMClient()
        invalid.add_response(lambda descriptor: True, json.dumps({"summary": 42}))
        self.assertIsNone(compact_epoch(self.npc, self.player, invalid).result)
        self.assertEqual(current_epoch(self.npc, self.player).pk, epoch.pk)
        self.assertEqual(DialogueTurn.objects.count(), 2)
        boundary = start_epoch(self.npc, self.player)
        identity = submit_turn(self.npc, self.player, "字" * 10000)
        client = recorded_summary()
        self.assertIsNone(compact_epoch(self.npc, self.player, client).result)
        self.assertEqual(client.calls, [])
        self.assertEqual(DialogueTurn.objects.get(submission_id=identity).speech, "字" * 10000)
        self.assertEqual(current_epoch(self.npc, self.player).pk, boundary.pk)

    @covers_requirement("dialogue-epochs::epoch-compaction-preserves-original-turns-and-provenance")
    def test_offline_history_tail_remains_bounded_with_required_current_state(self):
        for index in range(15):
            messages, snapshot_id = self.turn("合成問題" * 80 + str(index))
        payload = json.loads(messages[1]["content"])
        current = json.loads(payload["current"])
        self.assertEqual(current["location"], self.room.key)
        self.assertEqual(current["player"]["name"], self.player.key)
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
        self.assertLessEqual(snapshot.budget_accounting["total_rendered_tokens"],
                             snapshot.budget_accounting["max_input_budget"])
        self.assertEqual(DialogueTurn.objects.count(), 30)
        self.assertEqual(DialogueFrame.objects.count(), 15)
        self.assertEqual(DialogueEpoch.objects.count(), 1)

    @covers_requirement("dialogue-epochs::stable-prefixes-change-only-at-legitimate-invalidation")
    def test_global_prefix_shared_and_logging_contains_only_metadata(self):
        with patch("world.narrative.dialogue.log_info") as logged:
            first, _ = self.turn("Private player text")
        other = create_object(LLMNPC, key="Other synthetic actor", location=self.room)
        second, _ = build_dialogue_context(other, self.player, "Private player text")
        self.assertEqual(first[0]["content"].split("\n\n")[:2], second[0]["content"].split("\n\n")[:2])
        self.assertNotIn("Private player text", repr(logged.call_args_list))
        self.assertIn("prefix_sha256", repr(logged.call_args_list))

    @covers_requirement("dialogue-epochs::epoch-compaction-preserves-original-turns-and-provenance")
    def test_stale_summary_cannot_replace_new_natural_boundary(self):
        self.turn("First question")
        captured = current_epoch(self.npc, self.player)
        client = FakeLLMClient()
        def change_boundary(descriptor):
            start_epoch(self.npc, self.player)
            return True
        client.add_response(change_boundary, json.dumps({"summary": "Recorded summary"}))
        self.assertIsNone(compact_epoch(self.npc, self.player, client).result)
        self.assertNotEqual(current_epoch(self.npc, self.player).pk, captured.pk)
        self.assertEqual(DialogueEpoch.objects.count(), 2)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_superseded_affinity_numbers_remain_secret_in_replayed_frames(self):
        # The registration leaks unless undone: later suites install their own
        # npc_dialogue degrade fallback and would see this layer's real
        # validators reject their synthetic payloads (same snapshot discipline
        # as test_dream_surface).
        saved_validators = {key: dict(value) for key, value in guardrail._semantic_validators.items()}
        saved_fallbacks = dict(guardrail._degrade_fallbacks)
        saved_schemas = dict(_OUTPUT_SCHEMAS)

        def restore() -> None:
            guardrail._semantic_validators.clear()
            guardrail._semantic_validators.update(saved_validators)
            guardrail._degrade_fallbacks.clear()
            guardrail._degrade_fallbacks.update(saved_fallbacks)
            _OUTPUT_SCHEMAS.clear()
            _OUTPUT_SCHEMAS.update(saved_schemas)

        self.addCleanup(restore)
        register_npc_dialogue()
        old = build_npc_dialogue_prompt({"name": "Synthetic NPC"}, {"name": "Synthetic player"}, [],
                                       affinity_context={"value": 55, "cap": 99, "stage": "Synthetic stage"})
        current = build_npc_dialogue_prompt({"name": "Synthetic NPC"}, {"name": "Synthetic player"}, [],
                                           affinity_context={"value": 60, "cap": 99, "stage": "Synthetic stage"},
                                           historical_frames=(old[1]["content"],))
        client = FakeLLMClient()
        client.add_response(lambda descriptor: len(descriptor.messages) == 2,
                            json.dumps({"speech": "先前是 55。", "intent": {"kind": "none"}}))
        client.add_response(lambda descriptor: len(descriptor.messages) > 2,
                            json.dumps({"speech": "合成安全回覆。", "intent": {"kind": "none"}}))
        reply = generate_npc_reply(client, npc_context={}, player_context={}, memory=[],
                                   prepared_messages=current).result
        self.assertEqual(reply.speech, "合成安全回覆。")
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("dialogue-epochs::caching-is-optional-observability")
    def test_cached_tokens_are_optional_transport_observability(self):
        client = OpenAICompatClient(LLMProfile(**default_profiles()["npc_dialogue"]))
        payload = {"choices": [{"message": {"role": "assistant", "content": "Recorded response"}}]}
        with patch("world.ai.client.log_info") as logged:
            self.assertEqual(client._parse_response((200, json.dumps(payload))), "Recorded response")
            logged.assert_not_called()
            payload["usage"] = {"prompt_tokens_details": {"cached_tokens": 123}}
            self.assertEqual(client._parse_response((200, json.dumps(payload))), "Recorded response")
        self.assertEqual(logged.call_args.args, ("llm_cached_tokens_reported",))
        self.assertEqual(logged.call_args.kwargs["context"]["cached_tokens"], 123)
