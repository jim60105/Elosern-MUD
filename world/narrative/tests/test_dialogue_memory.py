"""Synthetic durable dialogue and protection-to-revisit acceptance tests."""

import json
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from twisted.internet.task import Clock

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import LLMNPC
from typeclasses.rooms import Room
from world.ai.fake_client import FakeLLMClient
from world.ai import guardrail
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.narrative.dialogue import build_dialogue_context, pair_view, settle_response, submit_turn
from world.narrative.memory import process_pending_narrative_memory_projections, record_memory
from world.narrative.models import DialogueTurn, NarrativeContextSnapshot, NarrativeEvent
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session import BASIC_ATTACK_KEY, read_session, submit_player_action
from world.rules.party import leave_party
from world.rules.protection_demo import prepare_protection_demo
from world.rules.tests._combat_session_helpers import _player, open_synthetic_scope
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def synthetic_record():
    return {
        "record_type": "character", "schema_version": 1, "key": "合成工匠",
        "display_name": "合成工匠", "title": "合成修繕工", "age": 27, "apparent_age": 27,
        "race": "t_duskmari", "subrace": "t_duskmari_evensong", "sex": "female",
        "stats": {"hp": 150, "mp": 100, "sp": 150, "atk_phys": 5,
                  "agility": 5, "defense": 5, "magic_power": 10, "guild_merit": 0},
        "disguised_stats": {}, "affinity_elements": [], "skills": [], "passives": [],
        "equipment": {}, "inventory": [],
        "sexual_baseline": {"arousal": "平靜", "wetness": "乾燥", "virgin": False,
                            "sensitivity": {"general": "普通"}},
        "persona": {"identity": {"public": "合成聚落的修繕工。", "hidden": "秘密印記。"},
                    "appearance": "穿著皮圍裙。", "personality": "沉穩。",
                    "speech_style": "用短句說話。", "life_story": "在聚落學習修繕。",
                    "habit": "檢查工具。", "social_connection": "與合成工匠往來。"},
    }


def recorded_client(speech="謝謝你那天保護我。"):
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, json.dumps(
        {"speech": speech, "intent": {"kind": "none"}}, ensure_ascii=False,
    ))
    return client


class DurableDialogueTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "races", "subraces", "static_tiers", "monster_tiers")
        super().setUp()
        # Undo the npc_dialogue registration after each test: the registries
        # are process globals, and a leaked real-validator set makes a later
        # suite's synthetic degrade fixtures fail (same snapshot discipline
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
        self.room = create_object(Room, key="合成小徑")
        self.player = _player("合成旅人")
        self.player.location = self.room
        self.npc = create_object(LLMNPC, key="合成旁觀者", location=self.room)

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_originals_survive_bounded_views_reload_and_duplicate_delivery(self):
        with patch("world.narrative.dialogue.log_info") as logged:
            for index in range(8):
                identity = submit_turn(self.npc, self.player, f"合成問題{index}")
                self.assertEqual(submit_turn(self.npc, self.player, f"合成問題{index}",
                                             submission_id=identity), identity)
                delivered = settle_response(self.npc, self.player, identity, f"合成回答{index}")
                self.assertEqual(settle_response(self.npc, self.player, identity,
                                                 f"合成回答{index}").pk, delivered.pk)
        self.assertEqual(DialogueTurn.objects.count(), 16)
        self.assertEqual(logged.call_count, 16)
        self.assertNotIn("合成問題", repr(logged.call_args_list))
        self.npc.max_chat_memory_size = 2
        self.npc.refresh_from_db()
        view, omitted = pair_view(self.npc, self.player)
        self.assertEqual(omitted, 14)
        self.assertEqual(view[-1], "合成旁觀者: 合成回答7")
        self.assertEqual(DialogueTurn.objects.order_by("id").first().speech, "合成問題0")
        messages, snapshot_id = build_dialogue_context(self.npc, self.player, "最後的問題")
        self.assertIn("省略了較早的 14", messages[1]["content"])
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
        self.assertEqual(snapshot.budget_accounting["pair_turns_omitted"], 14)
        other = _player(self.player.key)
        other.location = self.room
        self.assertEqual(pair_view(self.npc, other)[0], [])
        turn = DialogueTurn.objects.first()
        for mutation in (lambda: turn.save(), lambda: turn.delete(),
                         lambda: DialogueTurn.objects.update(speech="篡改"),
                         lambda: DialogueTurn.objects.all().delete()):
            with self.assertRaises(ValueError):
                mutation()

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_generation_does_not_record_an_undelivered_reply(self):
        client = recorded_client()
        result = self.npc.run_npc_exchange("保護", self.player, client, reactor=Clock()).result
        self.assertIsNotNone(result.reply)
        self.assertEqual(DialogueTurn.objects.filter(kind="npc").count(), 0)
        settle_response(self.npc, self.player, result.submission_id, result.reply.speech,
                        snapshot_id=result.snapshot_id)
        turn = DialogueTurn.objects.get(kind="npc")
        self.assertEqual(turn.provenance["snapshot_id"], result.snapshot_id)
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=result.snapshot_id)
        self.assertEqual(tuple(client.calls[0].messages), (
            {"role": "system", "content": snapshot.rendered_payload["system_prompt"]},
            {"role": "user", "content": snapshot.rendered_payload["user_prompt"]},
        ))

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_offline_delivered_greeting_is_durable_but_silence_is_not(self):
        profiles = default_profiles()
        profiles["npc_dialogue"]["enabled"] = False
        with override_settings(LLM_PROFILES=profiles), patch.object(self.player, "msg"):
            client = FakeLLMClient()
            self.npc.at_talked_to("你好", self.player, client, reactor=Clock())
            self.assertEqual(DialogueTurn.objects.filter(kind="npc").count(), 0)
            self.npc.db.npc_offline_greeting = "合成離線問候。"
            self.npc.at_talked_to("再次問候", self.player, client, reactor=Clock())
            self.assertEqual(DialogueTurn.objects.get(kind="npc").speech, "合成離線問候。")
        self.assertEqual(client.calls, [])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_fixed_memory_and_recall_are_permitted_and_exact_snapshot_is_retained(self):
        record_memory(owner_id=str(self.npc.pk), content={"summary": "合成核心準則"},
                      tier="core", source_id="test:core")
        record_memory(owner_id="other_owner", content={"summary": "不應洩漏的秘密"},
                      tier="core", source_id="test:private")
        first, snapshot_id = build_dialogue_context(self.npc, self.player, "你好")
        second, _ = build_dialogue_context(self.npc, self.player, "你好")
        self.assertEqual(first, second)
        self.assertIn("合成核心準則", first[1]["content"])
        self.assertNotIn("不應洩漏", str(first))
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
        self.assertEqual([source["source_id"] for source in snapshot.sources], ["test:core"])

    @covers_requirement("npc-dialogue::npc-context-recalls-only-permitted-committed-experience",
                        "narrative-events::narrative-facts-commit-atomically-with-covered-gameplay",
                        "narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_real_protection_commit_multi_day_revisit_and_permissioned_recall(self):
        self.npc.delete()
        npc, enemy = prepare_protection_demo(self.player, npc_record=synthetic_record(),
                                              enemy_name="合成威脅")
        self.player.traits.atk_phys.base = 1000
        self.player.traits.agility.base = 1000
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), \
             patch("world.rules.combat.damage.roll_d100", return_value=1), \
             patch("world.rules.combat.rounds.roll_d100", return_value=1):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [enemy])
        self.assertIsNone(read_session(self.player))
        event = NarrativeEvent.objects.get(event_type="encounter_protection")
        self.assertIn(str(npc.pk), event.participants)
        process_pending_narrative_memory_projections()
        leave_party(npc, self.player, reason="dismissed")
        clock = get_world_clock()
        initial_tick = clock.tick
        for _ in range(3):
            clock.advance(86400, AdvanceSource.SKIP, ())
        self.assertGreaterEqual(clock.tick - initial_tick, 3 * 86400)
        informed = recorded_client()
        with patch.object(self.player, "msg") as msg:
            result = npc.at_talked_to("還記得那天遭遇戰鬥時的保護嗎？", self.player,
                                      informed, reactor=Clock())
        self.assertTrue(result.called)
        self.assertEqual(len(informed.calls), 1)
        self.assertIn("Witnessed successful protection", informed.calls[0].messages[1]["content"])
        request_sources = json.loads(informed.calls[0].messages[1]["content"])["cognition_sources"]
        self.assertEqual([source["source_id"] for source in request_sources], [event.source_id])
        self.assertIn("謝謝你那天保護我。", str(msg.call_args_list))
        delivered = DialogueTurn.objects.get(kind="npc")
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=delivered.provenance["snapshot_id"])
        self.assertEqual([source["source_id"] for source in snapshot.sources], [event.source_id])
        # Dialogue originals may still mention protection; only recalled cognition must omit it.
        unrelated, unrelated_id = build_dialogue_context(npc, self.player, "今晚月亮的顏色")
        self.assertNotIn("cognition", json.loads(unrelated[1]["content"]))
        self.assertEqual(NarrativeContextSnapshot.objects.get(snapshot_id=unrelated_id).sources, [])
        uninformed = create_object(LLMNPC, key="合成未見者", location=self.room)
        unknown_client = recorded_client("我沒有見過那場戰鬥。")
        with patch.object(self.player, "msg"):
            uninformed.at_talked_to("還記得那天遭遇戰鬥時的保護嗎？", self.player,
                                    unknown_client, reactor=Clock())
        self.assertNotIn("Witnessed successful protection", str(unknown_client.calls[0].messages))
        self.assertEqual(DialogueTurn.objects.filter(kind="npc").count(), 2)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_omitted_recall_does_not_claim_sources_and_original_turn_is_not_capped(self):
        record_memory(owner_id=str(self.npc.pk), tier="core", source_id="test:oversized",
                      content={"summary": "合成長記憶" * 2000})
        identity = submit_turn(self.npc, self.player, "合成原文" * 500)
        messages, snapshot_id = build_dialogue_context(self.npc, self.player, "你好")
        snapshot = NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
        self.assertEqual(snapshot.sources, [])
        self.assertNotIn("cognition", json.loads(messages[1]["content"]))
        self.assertTrue(snapshot.truncation_decisions)
        self.assertEqual(DialogueTurn.objects.get(submission_id=identity).speech, "合成原文" * 500)
        self.assertLess(len(json.loads(messages[1]["content"])["memory"][-1]), 201)

    def test_failed_demo_setup_rolls_back_party_and_entities(self):
        before = self.room.contents
        with patch("world.rules.protection_demo.engage", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                prepare_protection_demo(self.player, npc_record=synthetic_record(),
                                         enemy_name="合成威脅")
        self.assertEqual(list(self.player.db.party or []), [])
        self.assertIsNone(read_session(self.player))
        self.assertEqual({obj.pk for obj in self.room.contents}, {obj.pk for obj in before})
