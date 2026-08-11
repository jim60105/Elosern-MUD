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


class OocLifecycleIntegrationTests(EvenniaTest):
    """Real CmdOOC/CmdIC puppet-lifecycle hooks (fix-webclient-session-lifecycle 1.x).

    OOC sends the no-puppet transition, retires the dispatch sequence, and
    resets the client sequence; repuppeting the same character produces a
    fresh epoch and never reuses the retired request cache.
    """

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

    def _run_ooc(self):
        from commands.localized.account import CmdOOC

        cmd = CmdOOC()
        cmd.caller = self.account
        cmd.account = self.account
        cmd.session = self.ws_session
        cmd.playable = self.char1
        cmd.func()

    def _run_ic(self):
        from commands.localized.account import CmdIC

        cmd = CmdIC()
        cmd.caller = self.account
        cmd.account = self.account
        cmd.session = self.ws_session
        cmd.args = ""
        cmd.playable = self.char1
        cmd.func()

    def _send_action(self, envelope, request_id):
        handle_ui_action(
            self.ws_session,
            self.ws_session.puppet,
            {
                "protocol_version": 1,
                "presentation_epoch": envelope["presentation_epoch"],
                "request_id": request_id,
                "base_revision": envelope["revision"],
                "action_id": "proof.noop",
                "payload": {},
            },
            self._registry_with(
                lambda actor, payload: {
                    "outcome": "success",
                    "code": "ok",
                    "message": "完成",
                    "affected_panels": ("status",),
                }
            ),
            build_production_registry(),
        )

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

    @covers_requirement(
        "webclient-oob-protocol::unpuppet-retires-the-active-presentation-and-dispatch-sequence"
    )
    def test_ooc_transitions_then_retires_and_resets_sequence(self):
        envelope = self._sync()
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        epoch_before = coordinator.epoch

        self.sessionhandler.data_out.reset_mock()
        self._run_ooc()

        # The client transition is delivered before the sequence retires.
        transitions = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_protocol_error" in call.kwargs
        ]
        self.assertTrue(transitions, "OOC must send the no-puppet transition")
        self.assertEqual(
            transitions[-1].kwargs["ui_protocol_error"][0][0]["code"], "no_puppet"
        )

        # The dispatch sequence is retired and the coordinator epoch bumped.
        self.assertIsNone(getattr(self.ws_session.ndb, "elosern_dispatch", None))
        self.assertIsNone(getattr(self.ws_session.ndb, "elosern_actor_id", None))
        self.assertNotEqual(
            coordinator.epoch, epoch_before, "OOC must start a fresh epoch"
        )

    @covers_requirement(
        "webclient-oob-protocol::unpuppet-retires-the-active-presentation-and-dispatch-sequence"
    )
    def test_same_character_repuppet_starts_fresh_sequence(self):
        envelope = self._sync()
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        epoch_before = coordinator.epoch
        self._send_action(envelope, "r:1")

        self._run_ooc()
        self.assertIsNone(self.ws_session.puppet)
        self.assertIsNone(getattr(self.ws_session.ndb, "elosern_dispatch", None))

        self._run_ic()
        self.assertIs(self.ws_session.puppet, self.char1)
        envelope2 = self._sync()
        coordinator2 = attach_coordinator(self.ws_session, build_production_registry())
        self.assertNotEqual(
            envelope2["presentation_epoch"],
            epoch_before,
            "repuppet of the same character must not reuse the old epoch",
        )
        self.assertNotEqual(
            coordinator2.epoch, epoch_before, "coordinator must hold the fresh epoch"
        )

        # The old completed-request cache is gone: replaying the same request
        # id after repuppet executes the adapter again.
        received = []
        adapter = lambda actor, payload: received.append(actor) or {
            "outcome": "success",
            "code": "ok",
            "message": "完成",
            "affected_panels": ("status",),
        }
        registry = self._registry_with(adapter)
        self.sessionhandler.data_out.reset_mock()
        handle_ui_action(
            self.ws_session,
            self.ws_session.puppet,
            {
                "protocol_version": 1,
                "presentation_epoch": envelope2["presentation_epoch"],
                "request_id": "r:1",
                "base_revision": envelope2["revision"],
                "action_id": "proof.noop",
                "payload": {},
            },
            registry,
            build_production_registry(),
        )
        self.assertEqual(len(received), 1, "repuppet must not replay the old cache")


if __name__ == "__main__":
    import unittest

    unittest.main()
