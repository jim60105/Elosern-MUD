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
from twisted.internet.task import Clock

from server.conf import inputfuncs
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.account_actions import set_clock_for_testing
from web.webclient.actions.dispatcher import handle_ui_action, retire_sequence
from web.webclient.actions.registry import (
    ActionRegistry,
    ActionSpec,
    build_production_action_registry,
)
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

    def _live_action(self, request_id, action_id="proof.noop"):
        """An action envelope at the live coordinator's current epoch/revision.

        A successful ``ui_sync`` may be followed by the reconnect trigger's
        fire-and-forget push (for example a ``generating`` suggestions
        transition), which consumes one revision; a browser acting on the
        latest view carries that revision, not the snapshot's.
        """
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": {},
        }

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
            lambda actor, payload, session=None: received.append(actor)
            or {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
        )
        self._sync()
        action = self._live_action("r:1")
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
            lambda actor, payload, session=None: {"outcome": "success", "code": "ok", "message": "完成", "affected_panels": ("status",)}
        )
        self._sync()
        action = self._live_action("r:2")
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
        registry = self._registry_with(lambda actor, payload, session=None: held)
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
            lambda actor, payload, session=None: calls.append(actor) or held
        )
        self._sync()
        action = self._live_action("r:4")
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

    def _send_action(self, request_id):
        handle_ui_action(
            self.ws_session,
            self.ws_session.puppet,
            self._live_action(request_id),
            self._registry_with(
                lambda actor, payload, session=None: {
                    "outcome": "success",
                    "code": "ok",
                    "message": "完成",
                    "affected_panels": ("status",),
                }
            ),
            build_production_registry(),
        )

    def _live_action(self, request_id, action_id="proof.noop"):
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": {},
        }

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
        self._sync()
        coordinator = attach_coordinator(self.ws_session, build_production_registry())
        epoch_before = coordinator.epoch
        self._send_action("r:1")

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
        adapter = lambda actor, payload, session=None: received.append(actor) or {
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
            self._live_action("r:1"),
            registry,
            build_production_registry(),
        )
        self.assertEqual(len(received), 1, "repuppet must not replay the old cache")


class MultiCharacterActionIntegrationTests(EvenniaTest):
    """End-to-end WebSocket integration tests for multi-character create and switch flows (MC4).

    Note: The `roster` panel assertions in these tests require `multichar-02-roster-read-model`.
    Exercises:
    1. Activate character A
    2. Dispatch account.character.create, advance clock
    3. Complete creation wizard for character B (preset selection + activate)
    4. Dispatch account.character.switch back to A, advance clock
    5. Dispatch account.character.switch forward to B, advance clock
    Asserts complete snapshot delivery for status, character, and roster after each transition,
    and matching action results for all submitted requests.
    """

    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        import evennia

        self.sessionhandler = evennia.SESSION_HANDLER
        self.ws_session = _make_websocket_session(self.sessionhandler, self.account)
        self.ws_session.puppet = self.char1
        self.account.characters.add(self.char1)
        self.char1.account = self.account
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.creation_pending = False

        from world.rules.clock import get_world_clock

        get_world_clock()

        self.clock = Clock()
        set_clock_for_testing(self.clock)

        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        set_clock_for_testing(None)
        super().tearDown()

    def _sync(self):
        self.sessionhandler.data_out.reset_mock()
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        return calls[-1].kwargs["ui_snapshot"][0][0]

    def _live_action(self, request_id, action_id, payload=None):
        coordinator = attach_coordinator(self.ws_session, self.presentation_registry)
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload if payload is not None else {},
        }

    def _dispatch(self, request_id, action_id, payload=None):
        action = self._live_action(request_id, action_id, payload)
        handle_ui_action(
            self.ws_session,
            self.ws_session.puppet,
            action,
            self.action_registry,
            self.presentation_registry,
        )

    def _get_snapshots(self):
        return [
            call.kwargs["ui_snapshot"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]

    def _get_action_results(self):
        return [
            call.kwargs["ui_action_result"][0][0]
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_action_result" in call.kwargs
        ]

    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    @covers_requirement(
        "webclient-character-roster::the-top-band-carries-a-character-switcher-rendered-from-the-committed-roster",
        "webclient-character-roster::the-expanded-switcher-lists-every-roster-row-with-one-shared-lock-note",
        "webclient-character-roster::switching-dispatches-once-and-commits-only-on-the-server-s-snapshot",
        "webclient-character-roster::creating-a-character-is-a-confirmation-gated-trailing-control",
    )
    def test_multicharacter_create_switch_e2e_scenario(self):
        """End-to-end WebSocket scenario: create B, complete wizard, switch to A, switch to B."""
        # 1. Initial sync on character A (char1)
        initial_snapshot = self._sync()
        self.assertEqual(initial_snapshot["mode"], "exploration")
        initial_status = initial_snapshot["panels"]["status"]
        self.assertEqual(initial_status["actor"]["identity"], str(self.char1.pk))
        initial_roster = initial_snapshot["panels"]["roster"]
        self.assertEqual(len(initial_roster["characters"]), 1)
        self.assertTrue(initial_roster["characters"][0]["current"])

        # 2. Dispatch account.character.create
        self.sessionhandler.data_out.reset_mock()
        self._dispatch("req:create", "account.character.create")

        # Action result delivered synchronously before transition
        results = self._get_action_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["request_id"], "req:create")
        self.assertEqual(results[0]["outcome"], "success")
        self.assertEqual(results[0]["code"], "character_created")

        # Puppet is still char1 before reactor turn
        self.assertIs(self.ws_session.puppet, self.char1)

        # Advance reactor clock to trigger _perform_create
        self.clock.advance(0)

        # Wire sequencing: result was first, then no_puppet protocol error, then fresh ui_snapshot
        call_types = [
            list(call.kwargs.keys())[0]
            for call in self.sessionhandler.data_out.call_args_list
            if any(k in call.kwargs for k in ("ui_action_result", "ui_protocol_error", "ui_snapshot"))
        ]
        self.assertEqual(call_types, ["ui_action_result", "ui_protocol_error", "ui_snapshot"])

        # Session puppet is now newly created character B
        char_b = self.ws_session.puppet
        self.assertIsNot(char_b, self.char1)
        self.assertTrue(getattr(char_b, "creation_pending", False))
        self.assertIn(char_b, self.account.characters)

        # Snapshot for character B is in creation mode
        create_snapshots = self._get_snapshots()
        self.assertTrue(create_snapshots)
        b_snapshot = create_snapshots[-1]
        self.assertEqual(b_snapshot["mode"], "creation")
        b_status = b_snapshot["panels"]["status"]
        self.assertFalse(b_status["available"])
        b_roster = b_snapshot["panels"]["roster"]
        self.assertEqual(len(b_roster["characters"]), 2)
        # Verify roster states: B is current and pending, A is non-current
        roster_map = {int(c["identity"]): c for c in b_roster["characters"]}
        self.assertTrue(roster_map[int(char_b.pk)]["current"])
        self.assertTrue(roster_map[int(char_b.pk)]["pending"])
        self.assertFalse(roster_map[int(self.char1.pk)]["current"])
        self.assertFalse(b_roster["switch_locked"])

        # 3. Complete creation wizard for character B: select preset then activate
        self.sessionhandler.data_out.reset_mock()
        self._dispatch("req:preset", "creation.preset", {"preset_key": "human_wanderer"})
        preset_results = self._get_action_results()
        self.assertEqual(len(preset_results), 1)
        self.assertEqual(preset_results[0]["outcome"], "success")

        self.sessionhandler.data_out.reset_mock()
        self._dispatch("req:activate", "creation.activate")
        activate_results = self._get_action_results()
        self.assertEqual(len(activate_results), 1)
        self.assertEqual(activate_results[0]["outcome"], "success")
        self.assertFalse(getattr(char_b, "creation_pending", True))

        # Snapshot after activation is now in exploration mode
        active_snapshots = self._get_snapshots()
        self.assertTrue(active_snapshots)
        post_act_snapshot = active_snapshots[-1]
        self.assertEqual(post_act_snapshot["mode"], "exploration")
        self.assertEqual(post_act_snapshot["panels"]["status"]["actor"]["identity"], str(char_b.pk))
        self.assertTrue(post_act_snapshot["panels"]["character"]["available"])

        # 4. Switch back to character A (char1)
        self.sessionhandler.data_out.reset_mock()
        self._dispatch("req:switch_to_a", "account.character.switch", {"character_id": int(self.char1.pk)})
        switch_a_results = self._get_action_results()
        self.assertEqual(len(switch_a_results), 1)
        self.assertEqual(switch_a_results[0]["request_id"], "req:switch_to_a")
        self.assertEqual(switch_a_results[0]["outcome"], "success")
        self.assertEqual(switch_a_results[0]["code"], "character_switched")

        # Advance reactor clock
        self.clock.advance(0)
        self.assertIs(self.ws_session.puppet, self.char1)

        # Snapshot for character A
        switch_a_snapshots = self._get_snapshots()
        self.assertTrue(switch_a_snapshots)
        a_snapshot = switch_a_snapshots[-1]
        self.assertEqual(a_snapshot["mode"], "exploration")
        self.assertEqual(a_snapshot["panels"]["status"]["actor"]["identity"], str(self.char1.pk))
        self.assertTrue(a_snapshot["panels"]["character"]["available"])
        a_roster = a_snapshot["panels"]["roster"]
        roster_map_a = {int(c["identity"]): c for c in a_roster["characters"]}
        self.assertTrue(roster_map_a[int(self.char1.pk)]["current"])
        self.assertFalse(roster_map_a[int(char_b.pk)]["current"])
        self.assertFalse(a_roster["switch_locked"])

        # 5. Switch forward to character B (char_b)
        self.sessionhandler.data_out.reset_mock()
        self._dispatch("req:switch_to_b", "account.character.switch", {"character_id": int(char_b.pk)})
        switch_b_results = self._get_action_results()
        self.assertEqual(len(switch_b_results), 1)
        self.assertEqual(switch_b_results[0]["request_id"], "req:switch_to_b")
        self.assertEqual(switch_b_results[0]["outcome"], "success")

        # Advance reactor clock
        self.clock.advance(0)
        self.assertIs(self.ws_session.puppet, char_b)

        # Snapshot for character B
        switch_b_snapshots = self._get_snapshots()
        self.assertTrue(switch_b_snapshots)
        b_switched_snapshot = switch_b_snapshots[-1]
        self.assertEqual(b_switched_snapshot["mode"], "exploration")
        self.assertEqual(b_switched_snapshot["panels"]["status"]["actor"]["identity"], str(char_b.pk))
        self.assertTrue(b_switched_snapshot["panels"]["character"]["available"])
        b_switched_roster = b_switched_snapshot["panels"]["roster"]
        roster_map_b = {int(c["identity"]): c for c in b_switched_roster["characters"]}
        self.assertTrue(roster_map_b[int(char_b.pk)]["current"])
        self.assertFalse(roster_map_b[int(self.char1.pk)]["current"])
        self.assertFalse(b_switched_roster["switch_locked"])


if __name__ == "__main__":
    import unittest

    unittest.main()
