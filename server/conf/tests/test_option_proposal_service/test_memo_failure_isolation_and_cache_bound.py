"""Slice of ``test_option_proposal_service``: MemoContractTests, FailureIsolationTests, CacheBoundTests.
"""
from unittest.mock import patch
import unittest
from django.test import override_settings
from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.defer import Deferred
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from typeclasses.components import ScriptedDialogue
from world.ai import guardrail
from world.ai.action_options import (
    MAX_OPTIONSET_CACHE_ENTRIES as LAYER_CACHE_ENTRIES,
    NEGATIVE_MEMO_TTL as LAYER_NEGATIVE_MEMO_TTL,
    OptionSet,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.quests.catalog import register_catalog
from world.rules.clock import get_world_clock
from server import option_proposal_service as service
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import (
    exploration_affordances,
    suggestible_candidates,
)
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import reset_client_sequence
from web.webclient.presentation.registry import build_production_registry

from ._support import (
    _BaseServiceTests,
    _raw,
    _valid_options_json,
    await_result,
)


class MemoContractTests(_BaseServiceTests):
    def _fail_client(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        return client

    @covers_requirement(
        "action-options-trigger-service::the-negative-memo-applies-to-transport-failures-only",
    )
    def test_transport_failure_memos_for_30_seconds(self):
        fake_clock = [1000.0]
        session = self._puppet_session()
        client = self._fail_client()
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.state, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "degraded")
        self.assertEqual(len(client.calls), 1)
        self.assertIn(self._state()["fingerprint"], service._negative_memo)
        # Within the TTL: no transport work, immediate degraded.
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.state, "_clock", lambda: fake_clock[0] + 10),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["status"], "degraded")
        # After the TTL: one more attempt.
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.state, "_clock", lambda: fake_clock[0] + 31),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 2)

    @covers_requirement(
        "action-options-trigger-service::the-negative-memo-applies-to-transport-failures-only",
    )
    def test_non_transport_degrades_never_memo(self):
        self._puppet_session()

        def _fresh_state():
            self._session.ndb.options_state = None

        with override_settings(LLM_PROFILES=_raw()):
            with self.subTest(case="unparseable model text"):
                client = FakeLLMClient()
                client.add_response(lambda d: True, "不是 JSON 的回應。")
                await_result(self._schedule(client=client))
                self.assertEqual(self._state()["status"], "degraded")
                self.assertTrue(client.calls)
                self.assertEqual(service._negative_memo, {})
            with self.subTest(case="valid JSON failing the ladder"):
                _fresh_state()
                client = FakeLLMClient()
                client.add_response(
                    lambda d: True,
                    '{"context_kind": "exploration", "cards": []}',
                )
                await_result(self._schedule(client=client))
                self.assertEqual(self._state()["status"], "degraded")
                self.assertTrue(client.calls)
                self.assertEqual(service._negative_memo, {})
                calls = len(client.calls)
                with self.subTest(case="a retrigger calls transport again"):
                    _fresh_state()
                    await_result(self._schedule(client=client))
                self.assertGreaterEqual(len(client.calls), calls + 1)

    @covers_requirement(
        "action-options-trigger-service::scheduling-never-raises-and-never-blocks",
        "action-options-trigger-service::the-negative-memo-applies-to-transport-failures-only",
    )
    def test_disabled_profile_degrades_without_a_client_call_or_memo(self):
        """``client=None`` with a disabled profile builds the offline stub (not
        the live client), the layer degrades before any transport work, the
        stub is never invoked, and nothing is memoized (delta requirement 6 /
        the offline-stub scenario)."""
        disabled = _raw(action_options={"enabled": False})
        session = self._puppet_session()
        with (
            override_settings(LLM_PROFILES=disabled),
            patch(
                "world.ai.client.OpenAICompatClient",
                side_effect=AssertionError(
                    "must not construct the live client when the profile is disabled"
                ),
            ),
            patch.object(
                service._OfflineStubClient,
                "get_response",
                side_effect=AssertionError("the offline stub must never be invoked"),
            ),
        ):
            result = self._schedule(client=None)
            await_result(result)
            self.assertEqual(self._state()["status"], "degraded")
            self.assertEqual(service._negative_memo, {})

    @covers_requirement(
        "action-options-trigger-service::the-negative-memo-applies-to-transport-failures-only",
    )
    def test_client_raised_malformed_transport_error_is_memoized(self):
        """The memo discrimination is positional, not by failure kind: a
        client that itself raises ``LLMTransportError("malformed")`` IS the
        memoized class (observed at the client boundary), while the
        guardrail's own malformed detection after a successful round-trip
        (covered above) is not."""
        from world.ai.errors import LLMTransportError

        client = FakeLLMClient()
        client.add_failure(
            lambda d: True, LLMTransportError("malformed", "simulated malformed body")
        )
        session = self._puppet_session()
        fake_clock = [1000.0]
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.state, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "degraded")
        self.assertIn(self._state()["fingerprint"], service._negative_memo)

    @covers_requirement(
        "action-options-trigger-service::the-negative-memo-applies-to-transport-failures-only",
    )
    def test_success_is_never_negatively_memed(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(service._negative_memo, {})
        self.assertEqual(self._state()["status"], "ready")


class FailureIsolationTests(_BaseServiceTests):
    @covers_requirement(
        "action-options-trigger-service::scheduling-never-raises-and-never-blocks",
    )
    def test_vanished_room_resolves_to_nothing_without_raising(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json([]))
        self._puppet_session()
        self.player.location = None
        with override_settings(LLM_PROFILES=_raw()):
            self.assertIsNone(self._schedule(client=client))
        self.assertEqual(len(client.calls), 0)
        self.assertIsNone(self._state())

    @covers_requirement(
        "action-options-trigger-service::scheduling-never-raises-and-never-blocks",
    )
    def test_no_watchers_is_a_no_op(self):
        client = FakeLLMClient()
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            result = service.schedule_action_options(
                self.player, watchers=(), client=client
            )
            await_result(result)
        self.assertIsNone(self._state())
        self.assertEqual(len(client.calls), 0)

    @covers_requirement(
        "action-options-trigger-service::scheduling-never-raises-and-never-blocks",
    )
    def test_out_of_exploration_mode_is_a_no_op(self):
        client = FakeLLMClient()
        self._puppet_session()
        self.player.creation_pending = True
        with override_settings(LLM_PROFILES=_raw()):
            result = self._schedule(client=client)
            await_result(result)
        self.assertIsNone(self._state())
        self.assertEqual(len(client.calls), 0)

    @covers_requirement(
        "action-options-trigger-service::scheduling-never-raises-and-never-blocks"
    )
    def test_preflight_client_construction_failure_degrades_without_stranding(self):
        """A broken client construction after pending registration must settle
        the sessions degraded — never leave them in "generating" behind a
        dead pending generation (B1 regression)."""
        self._puppet_session()
        broken = patch.object(
            service.clients, "_build_action_options_client",
            side_effect=RuntimeError("broken profile environment"),
        )
        with (
            override_settings(LLM_PROFILES=_raw()),
            broken,
        ):
            self.assertIsNone(self._schedule(client=None))
        self.assertEqual(self._state()["status"], "degraded")
        self.assertEqual(service._pending, {})
        with (
            override_settings(LLM_PROFILES=_raw()),
            broken,
        ):
            self.assertIsNone(self._schedule(client=None))
        # The retrigger attempts a fresh generation instead of silently
        # joining a dead pending entry.
        self.assertEqual(self._state()["status"], "degraded")
        self.assertEqual(service._pending, {})
        self.assertGreater(self._state()["generation_token"], 1)

    @covers_requirement(
        "action-options-trigger-service::session-scoped-options-presentation-state-survives-async-completion-and-puppet-change",
    )
    def test_puppet_change_clears_the_session_options_state(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "ready")
        reset_client_sequence(session)
        self.assertIsNone(self._state())

    @covers_requirement(
        "action-options-trigger-service::fingerprint-identifies-the-situation-not-the-moment",
    )
    def test_situation_change_invalidates_the_fingerprint(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
            first = self._state()["fingerprint"]
        self.monster.delete()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertNotEqual(self._state()["fingerprint"], first)
        self.assertEqual(len(client.calls), 2)


class CacheBoundTests(unittest.TestCase):
    def test_cache_cap_is_16_with_lru_eviction(self):
        self.assertEqual(service.MAX_OPTIONSET_CACHE_ENTRIES, 16)
        for index in range(16):
            service._cache_put(
                "fp-%02d" % index,
                OptionSet(fingerprint="fp-%02d" % index),
                index + 1,
            )
        self.assertEqual(len(service._cache), 16)
        # Touch the oldest so it is no longer the LRU victim.
        service._cache_get("fp-00")
        service._cache_put("fp-16", OptionSet(fingerprint="fp-16"), 17)
        self.assertEqual(len(service._cache), 16)
        self.assertNotIn("fp-01", service._cache)
        self.assertIn("fp-00", service._cache)
        service._reset_service_state()
