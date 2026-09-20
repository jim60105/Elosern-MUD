"""Slice of ``test_option_proposal_service``: DismissalBarrierTests.
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


class DismissalBarrierTests(_BaseServiceTests):
    """Dismissal barriers and the per-fingerprint successor chain.

    Covers the wiring-hardening delta: a dismissing session records a minimum
    displayable generation, can never join or replay an older generation
    (another window's in-flight delivery is preserved), a queued successor
    starts exactly once behind the settling predecessor, barriers clear on
    eligible delivery and puppet reset, and the barrier store stays bounded.
    """

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_one_window_dismisses_while_another_stays_pending(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1)
        service.evict(a, self.player)
        self.assertEqual(a.ndb.options_state["status"], "unavailable")
        # A's next trigger queues on the successor: never a second call.
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1, "the successor is queued, not started")
        self.assertEqual(a.ndb.options_state["status"], "generating")
        # The old generation completes: B receives it, A receives none of it.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(b.ndb.options_state["status"], "ready")
        self.assertEqual(
            a.ndb.options_state["status"], "generating",
            "the dismissing window never receives the pre-dismiss generation",
        )
        # The settling predecessor starts the successor exactly once; the
        # successor outcome clears A's barrier.
        self.assertEqual(client.calls, 2, "the successor starts on settlement")
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(a.ndb.options_state["status"], "ready")
        fingerprint = a.ndb.options_state["fingerprint"]
        self.assertTrue(fingerprint)
        self.assertNotIn(fingerprint, a.ndb.options_barriers or {})

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_repeated_triggers_coalesce_into_one_successor(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
            self._schedule(client=client)
            self._schedule(client=client)
        self.assertEqual(client.calls, 1, "repeated triggers never parallelize")
        chain = next(iter(service._chains.values()))
        self.assertIsNotNone(chain.successor)
        self.assertEqual(len(chain.successor.subscribers), 1)
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(client.calls, 2, "the successor starts exactly once")

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_below_barrier_cache_entry_is_not_replayed(self):
        """A cache entry produced by a pre-dismiss generation must never be
        replayed for the dismissing session: a fresh generation runs."""
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        fingerprint = a.ndb.options_state["fingerprint"]
        service.evict(a, self.player)
        self.assertNotIn(fingerprint, service._cache)
        with override_settings(LLM_PROFILES=_raw()):
            client.add_response(lambda d: True, _valid_options_json(self._eligible()))
            await_result(self._schedule(client=client))
        self.assertEqual(
            len(client.calls), 2,
            "the dismissed cache entry is never replayed; transport runs again",
        )
        self.assertEqual(a.ndb.options_state["status"], "ready")
        self.assertNotIn(
            fingerprint, a.ndb.options_barriers,
            "the eligible successor delivery clears the barrier",
        )

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_detached_predecessor_hands_off_exactly_once(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            old = self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1)
        service.evict(b, self.player)
        # The final subscriber dismissed the active: it left the joinable
        # registry immediately and remains only as the chain's detached ref.
        self.assertNotIn(fingerprint, service._pending)
        chain = service._chains[fingerprint]
        self.assertIs(chain.detached, service._chains[fingerprint].detached)
        self.assertIsNotNone(chain.detached)
        # The detached Deferred completes: identity checks start the current
        # successor exactly once and discard the reference.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
            await_result(old)
        self.assertEqual(client.calls, 2)
        self.assertIn(fingerprint, service._pending)
        self.assertIsNone(chain.detached)
        # A receives only that successor outcome.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(a.ndb.options_state["status"], "ready")
        self.assertEqual(b.ndb.options_state["status"], "unavailable")

    @covers_requirement(
        "action-options-trigger-service::retired-pending-generations-are-removed-by-identity-immediately"
    )
    def test_retired_completion_cannot_remove_replacement_work(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        with override_settings(LLM_PROFILES=_raw()):
            old = self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        first_pending = client.pending
        service.evict(a, self.player)
        self.assertNotIn(fingerprint, service._pending, "retired leaves at once")
        with override_settings(LLM_PROFILES=_raw()):
            fresh = self._schedule(client=client)
        self.assertEqual(client.calls, 2, "the later trigger starts generation N+1")
        self.assertIsNot(fresh, old)
        # Generation N completes: writes no cache or session state, and its
        # cleanup cannot remove the newer generation N+1.
        with override_settings(LLM_PROFILES=_raw()):
            first_pending.callback(_valid_options_json(self._eligible()))
            await_result(old)
        self.assertEqual(
            a.ndb.options_state["status"], "generating",
            "the retired generation N writes no state",
        )
        self.assertIn(fingerprint, service._pending, "N+1 remains in the registry")
        # N+1 settles normally afterwards.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
            await_result(fresh)
        self.assertEqual(a.ndb.options_state["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::retired-pending-generations-are-removed-by-identity-immediately"
    )
    def test_evict_removes_the_session_from_a_queued_successor(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        service.evict(a, self.player)
        chain = next(iter(service._chains.values()))
        self.assertIsNone(chain.successor, "an emptied successor is dropped")
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(
            client.calls, 1,
            "no successor starts for a dropped queue (the old settles clean)",
        )
        # A's next trigger starts a fresh generation above the new barrier.
        fresh_client = FakeLLMClient()
        fresh_client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.clients, "_build_action_options_client", return_value=fresh_client),
        ):
            await_result(self._schedule(client=None))
        self.assertEqual(len(fresh_client.calls), 1)
        self.assertEqual(a.ndb.options_state["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_generation_numbers_are_monotonic_and_cache_writes_are_versioned(self):
        self.assertEqual(service._next_generation("fp-monotonic"), 1)
        self.assertEqual(service._next_generation("fp-monotonic"), 2)
        self.assertEqual(service._current_generation("fp-monotonic"), 2)
        service._cache_put("fp-versioned", OptionSet(fingerprint="fp-versioned"), 5)
        service._cache_put("fp-versioned", OptionSet(fingerprint="fp-versioned"), 3)
        self.assertEqual(
            service._cache["fp-versioned"][2], 5,
            "an older completion never overwrites a newer cache entry",
        )
        service._cache_put("fp-versioned", OptionSet(fingerprint="fp-versioned"), 6)
        self.assertEqual(service._cache["fp-versioned"][2], 6)

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_barrier_store_is_bounded_to_the_cache_capacity(self):
        a = self._puppet_session(31)
        for index in range(service.MAX_OPTIONSET_CACHE_ENTRIES + 3):
            service._set_barrier_min(a, "fp-%d" % index, index + 1)
        self.assertEqual(
            len(a.ndb.options_barriers), service.MAX_OPTIONSET_CACHE_ENTRIES
        )

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_puppet_reset_clears_the_barrier_store(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        a = self._puppet_session(31)
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        service.evict(a, self.player)
        self.assertTrue(a.ndb.options_barriers)
        reset_client_sequence(a)
        self.assertIsNone(a.ndb.options_barriers)
        self.assertIsNone(a.ndb.options_state)

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_successor_registers_before_its_deferred_can_settle(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            old = self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        service.evict(b, self.player)
        # The successor's Deferred settles synchronously the moment it
        # starts: the chain and pending registry must already own it, or the
        # settlement is lost and the generation strands in the registry.
        fired = Deferred()
        fired.callback(None)
        with patch.object(service.lifecycle, "_run_generation", return_value=fired):
            with override_settings(LLM_PROFILES=_raw()):
                client.pending.callback(_valid_options_json(self._eligible()))
                await_result(old)
        self.assertNotIn(
            fingerprint, service._pending,
            "a synchronously settled successor is not left in the registry",
        )
        self.assertNotIn(
            fingerprint, service._chains,
            "an emptied chain is removed after the handoff",
        )

    @covers_requirement(
        "action-options-trigger-service::retired-pending-generations-are-removed-by-identity-immediately"
    )
    def test_detached_predecessor_does_not_wipe_a_newer_active(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        with override_settings(LLM_PROFILES=_raw()):
            old = self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        first_pending = client.pending
        service.evict(a, self.player)
        self.assertNotIn(fingerprint, service._pending, "retired leaves at once")
        with override_settings(LLM_PROFILES=_raw()):
            fresh = self._schedule(client=client)
        self.assertEqual(client.calls, 2, "the later trigger starts generation N+1")
        newer = service._pending[fingerprint]
        chain = service._chains[fingerprint]
        self.assertIs(chain.active, newer)
        # Generation N completes while N+1 owns the chain: the detached
        # predecessor clears only its own reference and never starts a
        # successor ahead of the current active.
        with override_settings(LLM_PROFILES=_raw()):
            first_pending.callback(_valid_options_json(self._eligible()))
            await_result(old)
        self.assertEqual(client.calls, 2, "no successor starts for the obsolete predecessor")
        self.assertIs(chain.active, newer, "the newer active survives the detached settlement")
        self.assertIsNone(chain.detached)
        # N+1 settles normally afterwards.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
            await_result(fresh)
        self.assertEqual(a.ndb.options_state["status"], "ready")

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_a_second_dismissal_cannot_rejoin_the_queued_successor(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1, "A queues on the successor")
        service.evict(b, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(
            b.ndb.options_state["status"], "degraded",
            "a below-barrier successor is never rejoined",
        )
        self.assertEqual(
            b.ndb.options_barriers[fingerprint], 3,
            "the second dismissal's barrier stands through the degraded settle",
        )
        # The old generation settles: the successor runs for its remaining
        # subscriber only, and B receives none of the pre-dismiss work.
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(client.calls, 2)
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(_valid_options_json(self._eligible()))
        self.assertEqual(a.ndb.options_state["status"], "ready")
        self.assertEqual(b.ndb.options_state["status"], "degraded")
        self.assertEqual(b.ndb.options_barriers[fingerprint], 3)
        # B's next trigger starts fresh work above the barrier.
        fresh_client = FakeLLMClient()
        fresh_client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service.clients, "_build_action_options_client", return_value=fresh_client),
        ):
            await_result(self._schedule(client=None))
        self.assertEqual(len(fresh_client.calls), 1)
        self.assertEqual(b.ndb.options_state["status"], "ready")
        self.assertNotIn(
            fingerprint, b.ndb.options_barriers,
            "the eligible fresh delivery clears the barrier",
        )

    @covers_requirement(
        "action-options-trigger-service::dismissal-prevents-replay-from-a-concurrent-older-generation"
    )
    def test_moved_situation_successor_settle_preserves_the_old_barrier(self):
        client = _PendingFakeClient()
        a = self._puppet_session(31)
        b = self._puppet_session(32)
        payload = _valid_options_json(self._eligible())
        with override_settings(LLM_PROFILES=_raw()):
            old = self._schedule(client=client)
        fingerprint = a.ndb.options_state["fingerprint"]
        service.evict(a, self.player)
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(client.calls, 1, "A queues on the successor")
        # The actor moves to another room before the active settles: the
        # successor's fresh derivation names a different situation.
        new_room = create_object(Room, key="另一間房", location=None)
        new_room.db.desc = "另一座安靜的廣場。"
        self.player.location = new_room
        with override_settings(LLM_PROFILES=_raw()):
            client.pending.callback(payload)
            await_result(old)
        self.assertEqual(
            a.ndb.options_state["status"], "degraded",
            "the moved successor settles its queued watcher degraded",
        )
        self.assertIn(
            fingerprint, a.ndb.options_barriers,
            "an ineligible settle never clears the old fingerprint's barrier",
        )
