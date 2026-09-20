"""Slice of ``test_option_proposal_service``: SchedulingContractTests.
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
    _PendingFakeClient,
    _raw,
    _valid_options_json,
    await_result,
)


class SchedulingContractTests(_BaseServiceTests):
    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
        "action-options-trigger-service::session-scoped-options-presentation-state-survives-async-completion-and-puppet-change",
    )
    def test_ready_success_caches_and_publishes_per_session(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            deferred = self._schedule(client=client)
            await_result(deferred)
        self.assertEqual(len(client.calls), 1)
        state = self._state()
        self.assertEqual(state["status"], "ready")
        self.assertTrue(state["fingerprint"])
        self.assertEqual(len(state["displayed"]), min(5, len(self._eligible())))
        updates = self._envelopes("ui_update")
        suggestions = updates[-1]["panels"]["context_actions"]["suggestions"]
        self.assertEqual(suggestions["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
    )
    def test_unchanged_situation_replays_without_a_second_transport_call(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
            first_fingerprint = self._state()["fingerprint"]
            before = len(self._envelopes("ui_update"))
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["fingerprint"], first_fingerprint)
        self.assertEqual(self._state()["status"], "ready")
        self.assertGreater(
            len(self._envelopes("ui_update")), before, "the replay republishes"
        )

    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
    )
    def test_a_second_session_receives_the_cache_hit_without_transport(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        self._puppet_session(31)
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        client.calls_snapshot = len(client.calls)
        second = self._puppet_session(32)
        self._session = second
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), client.calls_snapshot)
        self.assertEqual(self._state()["status"], "ready")
        self.assertTrue(self._state()["fingerprint"])

    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
        "action-options-trigger-service::session-scoped-options-presentation-state-survives-async-completion-and-puppet-change",
    )
    def test_cache_evicted_ready_display_replays_without_transport(self):
        """A ready display takes precedence over the cache even after the
        global LRU entry has been evicted (delta requirement 2 scenario)."""
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
            first = self._state()["fingerprint"]
        for index in range(17):
            service._cache_put(
                "fp-%d" % index, OptionSet(fingerprint="fp-%d" % index), index + 1
            )
        self.assertNotIn(first, service._cache)
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["fingerprint"], first)
        self.assertEqual(self._state()["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
    )
    def test_pending_generation_is_shared_by_a_new_watcher(self):
        client = _PendingFakeClient()
        first = self._puppet_session(31)
        with override_settings(LLM_PROFILES=_raw()):
            pending = self._schedule(client=client)
        self.assertEqual(first.ndb.options_state["status"], "generating")
        self.assertEqual(client.calls, 1)
        second = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            reattached = self._schedule(client=client)
        self.assertIs(reattached, pending, "only the original generation runs")
        self.assertEqual(client.calls, 1, "no second transport call")
        # The re-trigger must not have missed the first session's token.
        self.assertEqual(first.ndb.options_state["status"], "generating")
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
            await_result(pending)
        self.assertEqual(first.ndb.options_state["status"], "ready")
        self.assertEqual(second.ndb.options_state["status"], "ready")
        self.assertEqual(client.calls, 1)

    @covers_requirement(
        "action-options-trigger-service::one-llm-call-per-cache-residency-with-replay-and-pending-semantics",
    )
    def test_mid_flight_retrigger_does_not_start_a_second_generation(self):
        client = _PendingFakeClient()
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
            self._schedule(client=client)
            self._schedule(client=client)
        self.assertEqual(client.calls, 1)
