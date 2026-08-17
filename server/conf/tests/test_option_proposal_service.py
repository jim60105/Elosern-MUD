"""Tests for the action-options trigger service (composition root).

Covers the scheduling contract: ready success caches and publishes per
session; replays and cache hits skip transport; a pending generation is
shared (one in-flight call, many subscribers) with stale tokens muted;
transport failures memoize (30 s) while validation exhaustion and a disabled
profile never do; eviction clears cache/memo/pending and retires an emptied
generation; the LRU cap; the cap parity with the layer; the puppet-change
state cleanup; and fire-and-forget failure isolation (vanished room,
preflight no-ops never raise).
"""

from unittest.mock import patch
import unittest

from django.test import override_settings

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.defer import Deferred

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


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _install_action_options():
    from world.ai import action_options

    guardrail._semantic_validators.pop("action_options", None)
    guardrail._degrade_fallbacks.pop("action_options", None)
    action_options.register_action_options()


def _uninstall_action_options():
    guardrail._semantic_validators.pop("action_options", None)
    guardrail._degrade_fallbacks.pop("action_options", None)


def await_result(d):
    if d is None:
        return None
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _valid_options_json(candidates):
    """The payload a compliant model would emit for the eligible affordances."""
    import json

    suffixes = "甲乙丙丁戊"
    cards = []
    for index, entry in enumerate(candidates[:5]):
        cards.append(
            {
                "action_code": entry.action_id,
                "label": "提示%s" % suffixes[index],
                "params": dict(entry.params),
            }
        )
    return json.dumps(
        {"context_kind": "exploration", "cards": cards}, ensure_ascii=False
    )


class _PendingFakeClient:
    """A client whose get_response hangs until the test fires the Deferred."""

    def __init__(self):
        self.calls = 0
        self.pending = Deferred()

    def get_response(self, descriptor):
        self.calls += 1
        self.pending = Deferred()
        return self.pending


def _make_session(sessionhandler, sessid, puppet):
    session = ServerSession()
    session.init_session("webclient/websocket", ("localhost", 9999), sessionhandler)
    session.sessid = sessid
    session.protocol_key = "webclient/websocket"
    session.puppet = puppet
    session.logged_in = True
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = str(getattr(puppet, "pk", ""))
    session.ndb.options_state = None
    puppet.sessions.add(session)
    sessionhandler[session.sessid] = session
    return session


class _BaseServiceTests(EvenniaTest):
    """Shared fixtures: one grid room, one player, one NPC, one monster."""

    def setUp(self):
        super().setUp()
        _install_action_options()
        service._reset_service_state()
        watchers.clear_watchers()
        # The affinity rulebook validates against the quest registry; the
        # shipped catalog must be registered before any tier label resolves.
        register_catalog()
        get_world_clock()
        self.room = create_object(Room, key="選項廣場", location=None)
        self.room.db.desc = "一座安靜的廣場。"
        self.player = create_object(PlayerCharacter, key="選項玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="店員", location=self.room)
        self.npc.components.add(
            ScriptedDialogue.create(self.npc, dialogue_key="guild_staff")
        )
        self.monster = create_object(Monster, key="哥布林", location=self.room)
        self._session = None

    def tearDown(self):
        _uninstall_action_options()
        service._reset_service_state()
        watchers.clear_watchers()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def _puppet_session(self, sessid=31):
        session = _make_session(self.sessionhandler, sessid, self.player)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        self._session = session
        return session

    def _watchers(self):
        return watchers.watchers_for(self.player)

    def _envelopes(self, message_name):
        calls = self.sessionhandler.data_out.call_args_list
        return [
            call.kwargs[message_name][0][0]
            for call in calls
            if message_name in call.kwargs
        ]

    def _state(self):
        return self._session.ndb.options_state

    def _schedule(self, client=None):
        return service.schedule_action_options(
            self.player, watchers=self._watchers(), client=client
        )

    def _eligible(self):
        vocab = exploration_affordances(self.player)
        return list(suggestible_candidates(vocab, actor=self.player))


class SchedulingContractTests(_BaseServiceTests):
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
                "fp-%d" % index, OptionSet(fingerprint="fp-%d" % index)
            )
        self.assertNotIn(first, service._cache)
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["fingerprint"], first)
        self.assertEqual(self._state()["status"], "ready")

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

    def test_mid_flight_retrigger_does_not_start_a_second_generation(self):
        client = _PendingFakeClient()
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
            self._schedule(client=client)
            self._schedule(client=client)
        self.assertEqual(client.calls, 1)


class StaleTokenAndEvictionTests(_BaseServiceTests):
    def test_evict_mutes_the_in_flight_completion(self):
        client = _PendingFakeClient()
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            self._schedule(client=client)
        self.assertEqual(self._state()["status"], "generating")
        service.evict(session, self.player)
        state = self._state()
        self.assertEqual(state["status"], "unavailable")
        published = len(self._envelopes("ui_update"))
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

    def test_evict_clears_the_negative_memo_for_the_displayed_fingerprint(self):
        fake_clock = [1000.0]
        session = self._puppet_session()
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        fingerprint = self._state()["fingerprint"]
        self.assertIn(fingerprint, service._negative_memo)
        service.evict(session, self.player)
        self.assertNotIn(fingerprint, service._negative_memo)
        self.assertEqual(service._cache, {})

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


class MemoContractTests(_BaseServiceTests):
    def _fail_client(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        return client

    def test_transport_failure_memos_for_30_seconds(self):
        fake_clock = [1000.0]
        session = self._puppet_session()
        client = self._fail_client()
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "degraded")
        self.assertEqual(len(client.calls), 1)
        self.assertIn(self._state()["fingerprint"], service._negative_memo)
        # Within the TTL: no transport work, immediate degraded.
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service, "_clock", lambda: fake_clock[0] + 10),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["status"], "degraded")
        # After the TTL: one more attempt.
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch.object(service, "_clock", lambda: fake_clock[0] + 31),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(len(client.calls), 2)

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
            patch.object(service, "_clock", lambda: fake_clock[0]),
        ):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "degraded")
        self.assertIn(self._state()["fingerprint"], service._negative_memo)

    def test_success_is_never_negatively_memed(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(service._negative_memo, {})
        self.assertEqual(self._state()["status"], "ready")


class FailureIsolationTests(_BaseServiceTests):
    def test_vanished_room_resolves_to_nothing_without_raising(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json([]))
        self._puppet_session()
        self.player.location = None
        with override_settings(LLM_PROFILES=_raw()):
            self.assertIsNone(self._schedule(client=client))
        self.assertEqual(len(client.calls), 0)
        self.assertIsNone(self._state())

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

    def test_out_of_exploration_mode_is_a_no_op(self):
        client = FakeLLMClient()
        self._puppet_session()
        self.player.creation_pending = True
        with override_settings(LLM_PROFILES=_raw()):
            result = self._schedule(client=client)
            await_result(result)
        self.assertIsNone(self._state())
        self.assertEqual(len(client.calls), 0)

    def test_preflight_client_construction_failure_degrades_without_stranding(self):
        """A broken client construction after pending registration must settle
        the sessions degraded — never leave them in "generating" behind a
        dead pending generation (B1 regression)."""
        self._puppet_session()
        broken = patch.object(
            service, "_build_action_options_client",
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

    def test_puppet_change_clears_the_session_options_state(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        session = self._puppet_session()
        with override_settings(LLM_PROFILES=_raw()):
            await_result(self._schedule(client=client))
        self.assertEqual(self._state()["status"], "ready")
        reset_client_sequence(session)
        self.assertIsNone(self._state())

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
            service._cache_put("fp-%02d" % index, OptionSet(fingerprint="fp-%02d" % index))
        self.assertEqual(len(service._cache), 16)
        # Touch the oldest so it is no longer the LRU victim.
        service._cache_get("fp-00")
        service._cache_put("fp-16", OptionSet(fingerprint="fp-16"))
        self.assertEqual(len(service._cache), 16)
        self.assertNotIn("fp-01", service._cache)
        self.assertIn("fp-00", service._cache)
        service._reset_service_state()

    def test_caps_match_the_layer(self):
        self.assertEqual(
            service.MAX_OPTIONSET_CACHE_ENTRIES, LAYER_CACHE_ENTRIES
        )
        self.assertEqual(service.NEGATIVE_MEMO_TTL, LAYER_NEGATIVE_MEMO_TTL)

    def test_module_defers_its_world_imports(self):
        import ast
        from pathlib import Path

        module_path = Path(__file__).resolve().parents[2] / "option_proposal_service.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            modules = (
                [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
            )
            for name in modules:
                self.assertFalse(
                    name and (name == "world" or name.startswith("world.")),
                    f"module-level import {name} must be deferred to the call path",
                )
                self.assertFalse(
                    name and (name == "web" or name.startswith("web.")),
                    f"module-level import {name} must be deferred to the call path",
                )
