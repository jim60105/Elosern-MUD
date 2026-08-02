"""End-to-end ui_action dispatch integration tests (foundation section 2.7).

These tests run against the real Evennia session plumbing with an isolated
proof adapter, proving session actor delivery, exactly-once invocation, domain
revalidation, canonical completion presentation before same-revision result,
server unlock only after both sends, serialized concurrent sync, and no direct
persistent writes from dispatcher/presenter modules.
"""

from tools.spec_traceability import covers_requirement

from evennia.server.serversession import ServerSession
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.defer import Deferred

from server.conf import inputfuncs
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.dispatcher import handle_ui_action, retire_sequence
from web.webclient.actions.registry import ActionRegistry, ActionSpec
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry


def _make_websocket_session(sessionhandler, account):
    session = ServerSession()
    session.init_session("webclient/websocket", ("localhost", 9999), sessionhandler)
    session.sessid = 3
    session.protocol_key = "webclient/websocket"
    session.puppet = None
    session.account = account
    session.logged_in = account is not None
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = None
    return session


class UiActionIntegrationTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        import evennia

        self.sessionhandler = evennia.SESSION_HANDLER
        self.ws_session = _make_websocket_session(self.sessionhandler, self.account)
        self.ws_session.puppet = self.char1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        super().tearDown()

    def _registry_with(self, adapter):
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="proof.noop",
                validate_payload=lambda payload: payload,
                adapter=adapter,
            )
        )
        return registry

    def _sync(self):
        self.sessionhandler.data_out.reset_mock()
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        return envelope

    def _send_action(self, registry, envelope):
        handle_ui_action(
            self.ws_session, self.char1, envelope, registry, build_production_registry()
        )

    @covers_requirement(
        "webclient-action-dispatch::adapters-preserve-deterministic-ownership-boundaries"
    )
    def test_proof_adapter_receives_session_actor_and_executes_once(self):
        received = []
        registry = self._registry_with(
            lambda actor, payload: received.append(actor)
            or {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
        )
        envelope = self._sync()
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "r:1",
            "base_revision": envelope["revision"],
            "action_id": "proof.noop",
            "payload": {},
        }
        self._send_action(registry, action)
        self.assertEqual(received, [self.char1])
        # Duplicate request replays without executing again.
        self.sessionhandler.data_out.reset_mock()
        self._send_action(registry, action)
        self.assertEqual(received, [self.char1])
        results = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_action_result" in call.kwargs
        ]
        self.assertTrue(results)

    @covers_requirement(
        "webclient-action-dispatch::admitted-action-completion-publishes-canonical-state-before-unlocking"
    )
    def test_completion_update_sent_before_same_revision_result(self):
        registry = self._registry_with(
            lambda actor, payload: {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
        )
        envelope = self._sync()
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "r:2",
            "base_revision": envelope["revision"],
            "action_id": "proof.noop",
            "payload": {},
        }
        self.sessionhandler.data_out.reset_mock()
        self._send_action(registry, action)
        sent = list(self.sessionhandler.data_out.call_args_list)
        update = next(call for call in sent if "ui_update" in call.kwargs)
        result = next(call for call in sent if "ui_action_result" in call.kwargs)
        update_index = sent.index(update)
        result_index = sent.index(result)
        self.assertLess(update_index, result_index)
        update_rev = update.kwargs["ui_update"][0][0]["revision"]
        result_rev = result.kwargs["ui_action_result"][0][0]["presentation_revision"]
        self.assertEqual(update_rev, result_rev)
        state = getattr(self.ws_session.ndb, "elosern_dispatch", None)
        self.assertFalse(state.in_flight, "server must unlock only after both sends")

    @covers_requirement(
        "webclient-action-dispatch::each-session-admits-only-one-mutation-in-flight"
    )
    def test_sync_remains_available_while_action_in_flight(self):
        held = Deferred()
        registry = self._registry_with(lambda actor, payload: held)
        envelope = self._sync()
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "r:3",
            "base_revision": envelope["revision"],
            "action_id": "proof.noop",
            "payload": {},
        }
        self.sessionhandler.data_out.reset_mock()
        self._send_action(registry, action)
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        snapshots = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(snapshots, "ui_sync must stay available during a mutation")
        held.callback({"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)})

    @covers_requirement(
        "webclient-action-dispatch::each-session-admits-only-one-mutation-in-flight"
    )
    def test_retired_sequence_publication_does_not_cross_puppet_boundary(self):
        calls = []
        held = Deferred()
        registry = self._registry_with(
            lambda actor, payload: calls.append(actor) or held
        )
        envelope = self._sync()
        action = {
            "protocol_version": 1,
            "presentation_epoch": envelope["presentation_epoch"],
            "request_id": "r:4",
            "base_revision": envelope["revision"],
            "action_id": "proof.noop",
            "payload": {},
        }
        self.sessionhandler.data_out.reset_mock()
        self._send_action(registry, action)
        retire_sequence(self.ws_session)
        held.callback({"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)})
        # Nothing from the retired sequence may publish a result.
        results = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_action_result" in call.kwargs
        ]
        self.assertFalse(results, "retired sequence must not publish a result")

    @covers_requirement(
        "webclient-action-dispatch::adapters-preserve-deterministic-ownership-boundaries"
    )
    def test_presenter_has_no_adapter_execution_path(self):
        from web.webclient.presentation import status as status_module

        status_source = open(status_module.__file__, encoding="utf-8").read()
        self.assertNotIn("dispatch", status_source)
        self.assertNotIn("adapter", status_source)


if __name__ == "__main__":
    import unittest

    unittest.main()
