"""Command-level tests for the ``invite`` / ``leave`` party commands (party-core).

Drives ``invite`` end to end through the guarded dialogue seam with a replay
client (AI accept/decline/illegal-intent), the degraded fixed-threshold path
(offline profile), the deterministic preflight rejections (already a
companion, full party, non-dialogue NPC), the mid-decision full-party
notification, and ``leave`` dismissal with no affinity change.
"""

from tools.spec_traceability import covers_requirement

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from commands.invite import CmdInvite
from commands.leave import CmdLeave
from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.npc_intents import STALE_CONTEXT_NOTE
from world.rules.party import (
    ALREADY_COMPANION_MESSAGE,
    DEGRADED_ACCEPT_MESSAGE,
    DEGRADED_REJECT_MESSAGE,
    JOINED_MESSAGE,
    LEAVE_DISMISSED_MESSAGE,
    NOT_COMPANION_MESSAGE,
    NOT_DIALOGUE_MESSAGE,
    PARTY_FULL_MESSAGE,
    REFUSED_MESSAGE,
    PARTY_MAX_COMPANIONS,
    PartyJoinError,
    is_companion,
    join_party,
)


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _reset_all():
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _reply_text(speech="我會考慮看看。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


class PartyCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_all()
        register_npc_dialogue()
        self.hall = create_object(Room, key="party hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.npc = create_object(LLMNPC, key="艾洛希雅", location=self.hall)

    def tearDown(self):
        _reset_all()
        super().tearDown()

    @covers_requirement('npc-identity-titles::command-and-search-targeting-matches-the-plain-npc-key-only')
    def test_titled_npc_resolves_by_plain_key_only(self):
        # npc-title-identity-core D8: targeting never learns the title. The
        # composed string is not a key, alias, or search hit; the plain name
        # resolves exactly as before the title existed.
        self.npc.npc_title = "南門守衛"
        found = self.char1.search("艾洛希雅", quiet=True)
        first = found[0] if isinstance(found, list) and found else found
        self.assertEqual(int(getattr(first, "pk", -1)), int(self.npc.pk))
        missed = self.char1.search("艾洛希雅\u3000南門守衛", quiet=True)
        self.assertFalse(missed)
        self.assertNotIn(
            "南門守衛", {str(alias) for alias in self.npc.aliases.all()}
        )

    def _client(self, intent=None, speech="我會考慮看看。"):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech=speech, intent=intent or {"kind": "none"}),
        )
        return client

    def _bind(self, affinity):
        apply_affinity_change(self.npc, self.char1, AffinitySource.QUEST_COMPLETION, affinity)

    def _patch_client(self, client):
        return patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        )

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_ai_accept_shows_speech_joins_and_notifies(self):
        self._bind(10)
        client = self._client(
            intent={"kind": "party_invite", "accept": True}, speech="我願意與你同行。"
        )
        with self._patch_client(client):
            output = self.call(CmdInvite(), "艾洛希雅 你願意與我同行嗎？")
        self.assertIn("我願意與你同行。", output)
        self.assertIn(JOINED_MESSAGE, output)
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertEqual(int(self.npc.db.party_member), int(self.char1.pk))
        self.assertEqual(
            self.npc._chat_lines(self.char1),
            [f"{self.char1.key}: 你願意與我同行嗎？", "艾洛希雅: 我願意與你同行。"],
        )

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_ai_decline_is_never_overridden_by_the_threshold(self):
        self._bind(90)
        client = self._client(
            intent={"kind": "party_invite", "accept": False}, speech="我還是想一個人。"
        )
        with self._patch_client(client):
            output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn("我還是想一個人。", output)
        self.assertIn(REFUSED_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_illegal_intent_keeps_the_speech_and_changes_nothing(self):
        client = self._client(
            intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
            speech="我想要一瓶藥水。",
        )
        with self._patch_client(client):
            output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn("我想要一瓶藥水。", output)
        self.assertNotIn(JOINED_MESSAGE, output)
        self.assertNotIn(REFUSED_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_full_party_preflight_blocks_before_any_dialogue_call(self):
        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.hall),
                self.char1,
            )
        client = self._client(intent={"kind": "party_invite", "accept": True})
        with self._patch_client(client):
            output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(PARTY_FULL_MESSAGE, output)
        self.assertEqual(len(client.calls), 0)
        self.assertFalse(is_companion(self.npc, self.char1))

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_offline_threshold_accepts_with_a_deterministic_line(self):
        self._bind(70)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with self._patch_client(client):
                output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(DEGRADED_ACCEPT_MESSAGE, output)
        self.assertIn(JOINED_MESSAGE, output)
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_offline_threshold_rejects_below_the_bound(self):
        self._bind(69)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with self._patch_client(client):
                output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(DEGRADED_REJECT_MESSAGE, output)
        self.assertNotIn(JOINED_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_offline_threshold_is_gated_when_the_npc_becomes_busy(self):
        self._bind(70)
        self.npc.db.schedule_state = "busy"
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with self._patch_client(client):
                output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(STALE_CONTEXT_NOTE, output)
        self.assertNotIn(JOINED_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_already_companion_rejected_before_any_dialogue_call(self):
        join_party(self.npc, self.char1)
        client = self._client(intent={"kind": "party_invite", "accept": True})
        with self._patch_client(client):
            output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(ALREADY_COMPANION_MESSAGE, output)
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(int(self.npc.db.party_member), int(self.char1.pk))

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_non_dialogue_npc_cannot_be_invited(self):
        plain = create_object(NPC, key="普通村民", location=self.hall)
        with self._patch_client(FakeLLMClient()):
            output = self.call(CmdInvite(), "普通村民")
        self.assertIn(NOT_DIALOGUE_MESSAGE, output)
        self.assertFalse(is_companion(plain, self.char1))

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    def test_join_rejected_after_the_reply_surfaces_the_fixed_message(self):
        self._bind(10)
        client = self._client(
            intent={"kind": "party_invite", "accept": True}, speech="我願意與你同行。"
        )
        with self._patch_client(client), patch(
            "world.rules.party.join_party",
            side_effect=PartyJoinError("party_full"),
        ):
            output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn("我願意與你同行。", output)
        self.assertIn(PARTY_FULL_MESSAGE, output)
        self.assertNotIn(JOINED_MESSAGE, output)

    @covers_requirement("party-system::the-leave-command-dismisses-a-companion-without-affinity-change")
    def test_leave_dismisses_without_affinity_change(self):
        self._bind(55)
        join_party(self.npc, self.char1)
        before = self.npc.relations.affinity_for(self.char1)
        output = self.call(CmdLeave(), "艾洛希雅")
        self.assertIn(LEAVE_DISMISSED_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))
        self.assertIsNone(self.npc.db.party_member)
        self.assertEqual(self.npc.relations.affinity_for(self.char1), before)

    @covers_requirement("party-system::the-leave-command-dismisses-a-companion-without-affinity-change")
    def test_leave_of_an_unbound_target_reports_the_error(self):
        output = self.call(CmdLeave(), "艾洛希雅")
        self.assertIn(NOT_COMPANION_MESSAGE, output)
        self.assertFalse(is_companion(self.npc, self.char1))

    @covers_requirement("party-system::the-leave-command-dismisses-a-companion-without-affinity-change")
    def test_leave_missing_target_reports_usage(self):
        output = self.call(CmdLeave(), "")
        self.assertIn("leave <npc>", output)


if __name__ == "__main__":
    unittest.main()
