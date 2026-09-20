"""Slice of ``test_option_proposal_service``: ReconnectTriggerTests.
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
    _make_session,
    _raw,
    _valid_options_json,
    await_result,
)


class ReconnectTriggerTests(_BaseServiceTests):
    """The reconnect trigger through the real ``ui_sync`` ingress path: the
    snapshot is emitted first and the service is called once with the
    requesting session as the only watcher; a still-current ``ready`` state
    and a degraded-but-cached state schedule nothing (the service's stale
    predicate decides, never the hook)."""

    def _sync(self, sessid=51):
        from server.conf import inputfuncs

        session = _make_session(self.sessionhandler, sessid, self.player)
        inputfuncs.ui_sync(session, {"protocol_version": 1})
        self._session = session
        return session

    def _wrapped(self, client):
        """Patch the service entry with a capturing wrapper around the real
        implementation; the hook's fire-and-forget call is observable and its
        in-flight Deferred is collectible for awaiting."""
        real = service.schedule_action_options
        captured = []
        deferreds = []

        def _wrapping(actor, *, watchers, client=None):
            captured.append((actor, watchers))
            deferred = real(actor, watchers=watchers, client=client)
            deferreds.append(deferred)
            return deferred

        patch_object = patch.object(service, "schedule_action_options", side_effect=_wrapping)
        patch_client = patch.object(service.clients, "_build_action_options_client", return_value=client)
        return patch_object, patch_client, captured, deferreds

    @covers_requirement(
        "action-options-trigger-hooks::reconnect-triggers-a-proposal-subject-to-the-stale-predicate"
    )
    def test_first_sync_schedules_one_generation_after_the_snapshot(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        patch_object, patch_client, captured, deferreds = self._wrapped(client)
        snapshot_before = len(self.sessionhandler.data_out.call_args_list)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch_object,
            patch_client,
        ):
            session = self._sync()
        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0][0], self.player)
        self.assertEqual(len(captured[0][1]), 1)
        self.assertIs(captured[0][1][0][0], session)
        envelopes = self.sessionhandler.data_out.call_args_list[snapshot_before:]
        self.assertTrue(
            any("ui_snapshot" in call.kwargs for call in envelopes),
            "the snapshot reaches the wire before the scheduling call",
        )
        await_result(deferreds[0])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self._state()["status"], "ready")

    def test_reconnect_with_a_current_ready_state_schedules_nothing(self):
        from server.conf import inputfuncs

        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        patch_object, patch_client, captured, deferreds = self._wrapped(client)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch_object,
            patch_client,
        ):
            session = self._sync()
            await_result(deferreds[0])
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(self._state()["status"], "ready")
            fingerprint = self._state()["fingerprint"]
            inputfuncs.ui_sync(session, {"protocol_version": 1})
        self.assertEqual(len(captured), 2, "the hook still calls the service")
        self.assertEqual(len(client.calls), 1, "a current ready state never schedules")
        self.assertEqual(self._state()["fingerprint"], fingerprint)
        self.assertEqual(self._state()["status"], "ready")

    def test_reconnect_with_a_degraded_but_cached_state_schedules_nothing(self):
        from server.conf import inputfuncs

        client = FakeLLMClient()
        client.add_response(lambda d: True, _valid_options_json(self._eligible()))
        patch_object, patch_client, captured, deferreds = self._wrapped(client)
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch_object,
            patch_client,
        ):
            session = self._sync()
            await_result(deferreds[0])
            self.assertEqual(self._state()["status"], "ready")
            fingerprint = self._state()["fingerprint"]
            self.assertIn(fingerprint, service._cache)
        # Force a degraded display for the same cached fingerprint: the stale
        # predicate must republish the cached set without any transport work.
        self._session.ndb.options_state["status"] = "degraded"
        with (
            override_settings(LLM_PROFILES=_raw()),
            patch_object,
            patch_client,
        ):
            inputfuncs.ui_sync(session, {"protocol_version": 1})
        self.assertEqual(len(captured), 2, "the hook still calls the service")
        self.assertEqual(len(client.calls), 1, "a degraded-but-cached state never schedules")
        self.assertEqual(self._state()["fingerprint"], fingerprint)
        self.assertEqual(self._state()["status"], "ready")

    @covers_requirement("action-options-trigger-hooks::every-trigger-is-fire-and-forget-non-raising-and-non-mutating")
    def test_reconnect_scheduling_failure_never_breaks_the_snapshot(self):
        snapshot_before = len(self.sessionhandler.data_out.call_args_list)
        with patch.object(
            service,
            "schedule_action_options",
            side_effect=RuntimeError("transport unavailable"),
        ):
            session = self._sync()
        self.assertIsNotNone(self._session)
        self.assertIs(session.puppet, self.player)
        envelopes = self.sessionhandler.data_out.call_args_list[snapshot_before:]
        self.assertTrue(
            any("ui_snapshot" in call.kwargs for call in envelopes),
            "the snapshot still reaches the wire when scheduling fails",
        )

    def test_caps_match_the_layer(self):
        self.assertEqual(
            service.MAX_OPTIONSET_CACHE_ENTRIES, LAYER_CACHE_ENTRIES
        )
        self.assertEqual(service.NEGATIVE_MEMO_TTL, LAYER_NEGATIVE_MEMO_TTL)

    def test_module_defers_its_world_imports(self):
        import ast
        from pathlib import Path

        package_dir = Path(__file__).resolve().parents[3] / "option_proposal_service"
        for module_path in sorted(package_dir.glob("*.py")):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                modules = (
                    [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                )
                for name in modules:
                    # The observability facade lazily binds the Evennia logger at
                    # first emit, so importing it pre-init cannot capture a None
                    # logger — the deferred-import ban exists for the guardrail's
                    # import-time capture, which the facade deliberately avoids.
                    if name == "world.observability":
                        continue
                    self.assertFalse(
                        name and (name == "world" or name.startswith("world.")),
                        f"module-level import {name} must be deferred to the call path",
                    )
                    self.assertFalse(
                        name and (name == "web" or name.startswith("web.")),
                        f"module-level import {name} must be deferred to the call path",
                    )
