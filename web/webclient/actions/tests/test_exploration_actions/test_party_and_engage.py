"""Party invite/leave and engage adapter tests."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
)
from evennia.utils.test_resources import EvenniaTestCase
from world.ai.fake_client import FakeLLMClient
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.monsters import Monster
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from django.test import override_settings
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _T_SKILL,
    _T_SKILL_ROW,
    _raw,
    _reply_text,
    _reset_guardrail,
    _t_dialogue_scope,
    await_result,
)


class ExplorationActionAdapterTests(BattlefieldIsolation, EvenniaTestCase):

    def setUp(self):
        # Scope before construction: dialogue hosts answer from the kit
        # table (shipped guild-staff row merged for the production turnin
        # special case), and the practice suite resolves its drill skill in
        # a scoped registry (the kit's forced-innate rows ride along so the
        # engage path's production innate keys still resolve).
        _t_dialogue_scope(self, with_staff=True)
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    **synth_innate_overlay()["skills"],
                    _T_SKILL: _T_SKILL_ROW,
                }
            },
        )
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="探索行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)
        from typeclasses.exits import Exit

        self.exit_obj = create_object(
            Exit,
            key="東",
            location=self.room1,
            destination=self.destination,
        )


    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        _reset_guardrail()
        super().tearDown()


    def _move(self, payload):
        return _move_adapter(self.player, payload)



    # ------------------------------------------------------------------
    # explore.party_invite / explore.party_leave
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_accept_joins_and_notifies(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我願意與你同行。",
                intent={"kind": "party_invite", "accept": True},
            ),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg") as msg:
            result = await_result(
                _party_invite_adapter(
                    self.player, {"npc_id": int(npc.pk), "message": "你願意嗎？"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import JOINED_MESSAGE, is_companion

        self.assertTrue(is_companion(npc, self.player))
        texts = " ".join(str(call.args[0]) for call in msg.call_args_list if call.args)
        self.assertIn(JOINED_MESSAGE, texts)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_threshold_decides_with_no_client_call(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 70)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_below_threshold_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertFalse(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_threshold_is_gated_when_the_npc_becomes_busy(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 70)
        npc.db.schedule_state = "busy"
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("無法交談", result["message"])
        from world.rules.party import is_companion

        self.assertFalse(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_full_party_rejects_before_the_ai_call(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.room1),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "party_full")
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_already_companion_rejects_before_the_ai_call(self):
        from world.rules.party import join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        join_party(npc, self.player)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_companion")
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_non_llm_npc_rejects(self):
        npc = create_object(NPC, key="普通村民", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        self.assertEqual(len(client.calls), 0)


    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_dismisses_without_affinity_change(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change
        from world.rules.party import is_companion, join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 55)
        join_party(npc, self.player)
        before = npc.relations.affinity_for(self.player)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertFalse(is_companion(npc, self.player))
        self.assertIsNone(npc.db.party_member)
        self.assertEqual(npc.relations.affinity_for(self.player), before)


    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_unbound_target_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_companion")


    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_tampered_npc_id_rejects(self):
        result = _party_leave_adapter(self.player, {"npc_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")



    # ------------------------------------------------------------------
    # explore.engage
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    def test_engage_transitions_to_combat(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        # Engage clears the dialogue session inside the deterministic core, so
        # the partial update must re-render ``dialogue`` too (webclient-align-10).
        self.assertEqual(
            result["affected_panels"], ("status", "context_actions", "dialogue")
        )
        self.assertTrue(is_in_active_session(self.player))


    def test_engage_rejects_remote_or_dead_target_without_session(self):
        result = _engage_adapter(self.player, {"monster_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_monster")
        self.assertFalse(is_in_active_session(self.player))

        monster = create_object(Monster, key="死掉的哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 0
        monster.save()
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "target_dead")
        self.assertFalse(is_in_active_session(self.player))


    def test_engage_already_in_combat_and_session_failures_are_rejected(self):
        first = create_object(Monster, key="哥布林甲", location=self.room1)
        first.threat_tier = "low"
        first.apply_monster_tier("floor")
        second = create_object(Monster, key="哥布林乙", location=self.room1)
        second.threat_tier = "low"
        second.apply_monster_tier("floor")
        engage(self.player, first)
        self.assertTrue(is_in_active_session(self.player))
        result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "already_in_combat")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError(SessionReason.NOT_PRESENT),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "no_monster")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError("unexpected"),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "engage_failed")

if __name__ == "__main__":
    unittest.main()
