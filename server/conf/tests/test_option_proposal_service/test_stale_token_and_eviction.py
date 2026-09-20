"""Slice of ``test_option_proposal_service``: StaleTokenAndEvictionTests.
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


class StaleTokenAndEvictionTests(_BaseServiceTests):
    @covers_requirement(
        "action-options-trigger-service::delivery-is-guarded-by-token-and-epoch-and-retired-generations-write-nothing",
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation",
    )
    def test_evict_mutes_the_in_flight_completion(self):
        client = _PendingFakeClient()
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(self._state()["status"], "generating")
        published = len(self._envelopes("ui_update"))
        self.assertIs(service.evict(session, self.player), True)
        # The state-only evict contract (dismiss-options-action D1): eviction
        # itself sends nothing; the dismissal's single ui_update is published
        # by the dispatcher completion path.
        self.assertEqual(len(self._envelopes("ui_update")), published)
        state = self._state()
        self.assertEqual(state["status"], "unavailable")
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        # The retired generation must write nothing.
        self.assertEqual(state["status"], "unavailable")
        self.assertIsNone(state["displayed"])
        updates = self._envelopes("ui_update")
        for envelope in updates[published:]:
            suggestions = envelope["panels"]["context_actions"]["suggestions"]
            self.assertNotEqual(suggestions["status"], "ready")
        self.assertEqual(service._cache, {})

    @covers_requirement(
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation",
    )
    def test_dismiss_token_increments_and_retrigger_regenerates(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            deferred = self._schedule(client=client)
            await_result(deferred)
            first_token = self._state()["generation_token"]
        service.evict(session, self.player)
        self.assertGreater(self._state()["generation_token"], first_token)
        with override_settings(LLM_PROFILES=_raw()):
            client.add_response(lambda d: True, _valid_options_json(self._eligible()))
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(self._state()["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::delivery-is-guarded-by-token-and-epoch-and-retired-generations-write-nothing",
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation",
    )
    def test_dismiss_is_isolated_per_session_among_watched_sessions(self):
        client = _PendingFakeClient()
        first = self._puppet_session(31)
        second = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1)
        service.evict(first, self.player)
        self.assertEqual(first.ndb.options_state["status"], "unavailable")
        self.assertEqual(second.ndb.options_state["status"], "generating")
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(first.ndb.options_state["status"], "unavailable")
        self.assertEqual(second.ndb.options_state["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation"
    )
    def test_evict_returns_false_and_leaves_state_unchanged_when_it_cannot_apply(self):
        """A corrupt options state fails the eviction: ``evict`` reports
        ``False`` (never raises) and the session state is left untouched, so
        the dismiss adapter rejects instead of reporting success."""
        session = self._puppet_session()
        session.ndb.options_state = {
            "owner_actor_id": str(self.player.pk),
            "fingerprint": "situation-fp",
            "status": "ready",
            "generation_token": "corrupt",
            "displayed": [],
        }
        self.assertIs(service.evict(session, self.player), False)
        self.assertEqual(session.ndb.options_state["status"], "ready")
        self.assertEqual(session.ndb.options_state["generation_token"], "corrupt")

    @covers_requirement(
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation"
    )
    def test_evict_clears_the_cache_for_the_displayed_fingerprint(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        fingerprint = self._state()["fingerprint"]
        self.assertIn(fingerprint, service._cache)
        service.evict(session, self.player)
        self.assertNotIn(fingerprint, service._cache)

    @covers_requirement(
        "action-options-trigger-service::eviction-is-per-session-and-clears-the-displayed-situation"
    )
    def test_evict_clears_the_negative_memo_for_the_displayed_fingerprint(self):
        fake_clock = [1000.0]
        session = self._puppet_session()
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.state, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        fingerprint = self._state()["fingerprint"]
        self.assertIn(fingerprint, service._negative_memo)
        service.evict(session, self.player)
        self.assertNotIn(fingerprint, service._negative_memo)
        self.assertEqual(service._cache, {})

    @covers_requirement(
        "action-options-trigger-service::delivery-is-guarded-by-token-and-epoch-and-retired-generations-write-nothing",
    )
    def test_sequence_reset_mutes_the_completion_push(self):
        """A coordinator reset between scheduling and completion writes the
        session state but pushes nothing (delta requirement 4 scenario: the
        epoch guard mutes the stale push)."""
        client = _PendingFakeClient()
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            pending = self._schedule(client=client)
        self.assertEqual(self._state()["status"], "generating")
        session.ndb.elosern_coordinator.reset()
        published = len(self._envelopes("ui_update"))
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
            await_result(pending)
        self.assertEqual(self._state()["status"], "ready")
        self.assertEqual(
            len(self._envelopes("ui_update")),
            published,
            "the stale-epoch push must be a silent no-op",
        )
