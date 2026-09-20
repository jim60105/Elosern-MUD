"""Switch presentation silence, dispatcher ordering, and session isolation."""
from twisted.internet.task import Clock
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.registry import build_production_registry
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.clock import get_world_clock
from web.webclient.actions.dispatcher import (
    NO_PUPPET_CODE,
    handle_ui_action,
    retire_sequence,
)
from unittest.mock import MagicMock, patch
from web.webclient.actions.account_actions import (
    ALREADY_CURRENT_CODE,
    ALREADY_CURRENT_MESSAGE,
    AFFECTED_PANELS,
    AccountActionError,
    CHARACTER_SLOTS_FULL_CODE,
    CHARACTER_SLOTS_FULL_MESSAGE,
    CREATE_FAILED_MESSAGE,
    CREATE_IN_COMBAT_MESSAGE,
    CREATE_SUCCESS_CODE,
    CREATE_SUCCESS_MESSAGE,
    IN_COMBAT_CODE,
    IN_COMBAT_MESSAGE,
    INVALID_CHARACTER_CODE,
    INVALID_CHARACTER_MESSAGE,
    NO_ACTIVE_SESSION_CODE,
    NO_ACTIVE_SESSION_MESSAGE,
    RECOVERY_FAILED_MESSAGE,
    RECOVERY_RESTORED_TEMPLATE,
    RECOVERY_RETAINED_TEMPLATE,
    SUCCESS_CODE,
    SUCCESS_MESSAGE,
    TRANSITION_PENDING_CODE,
    TRANSITION_PENDING_MESSAGE,
    _account_character_create_adapter,
    _account_character_switch_adapter,
    _attach_puppet,
    _perform_create,
    _perform_switch,
    _clear_transition_pending,
    _recover_transition,
    _transition_pending,
    set_clock_for_testing,
    validate_account_character_create_payload,
    validate_account_character_switch_payload,
)
import unittest


class AccountActionsIntegrationTests(EvenniaTest):
    """Integration tests for account.character.switch against real Evennia state."""

    def setUp(self):
        super().setUp()
        get_world_clock()

        # Injected deterministic clock
        self.clock = Clock()
        set_clock_for_testing(self.clock)

        # Set up characters on self.account
        self.account.characters.add(self.char1)
        self.char1.account = self.account

        self.char2 = create_object(
            PlayerCharacter,
            key="SecondChar",
            location=self.room1,
            home=self.room1,
        )
        self.char2.account = self.account
        self.account.characters.add(self.char2)

        self.char3 = create_object(
            PlayerCharacter,
            key="ThirdChar",
            location=self.room1,
            home=self.room1,
        )
        self.char3.account = self.account
        self.account.characters.add(self.char3)

        # Foreign character owned by self.account2
        self.foreign_char = self.char2_from_account2 if hasattr(self, "char2_from_account2") else create_object(
            PlayerCharacter,
            key="ForeignChar",
            location=self.room1,
            home=self.room1,
        )
        self.foreign_char.account = self.account2
        self.account2.characters.add(self.foreign_char)

        # Registries
        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()

        # Configure self.session (the real ServerSession created by EvenniaTest)
        self.session.puppet = self.char1
        self.session.puid = self.char1.id
        self.session.protocol_key = "websocket"
        self.session.sent = []

        def recording_msg(*args, **kwargs):
            self.session.sent.append(kwargs)
        self.session.msg = recording_msg

        self.char1.sessions.add(self.session)
        self.coordinator = attach_coordinator(self.session, self.presentation_registry)


    def tearDown(self):
        set_clock_for_testing(None)
        super().tearDown()


    def _envelope(self, payload, request_id="r1", epoch=None, base_revision=None):
        if epoch is None:
            epoch = self.coordinator.epoch
        if base_revision is None:
            base_revision = self.coordinator.revision
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "base_revision": base_revision,
            "action_id": "account.character.switch",
            "payload": payload,
        }



    # -------------------------------------------------------------------------
    # No Completion Presentation & Dispatcher Ordering
    # -------------------------------------------------------------------------
    @covers_requirement(
        "webclient-character-roster::the-switch-action-publishes-no-completion-snapshot"
    )
    def test_rejection_publishes_no_presentation(self):
        """Rejected switch emits ui_action_result with no update and no snapshot."""
        envelope = self._envelope({"character_id": int(self.char1.pk)})  # self-switch
        handle_ui_action(
            self.session,
            self.char1,
            envelope,
            self.action_registry,
            self.presentation_registry,
        )

        results = [call for call in self.session.sent if "ui_action_result" in call]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ui_action_result"][0][0]["outcome"], "rejected")

        # No snapshot or update was sent
        snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
        updates = [call for call in self.session.sent if "ui_update" in call]
        self.assertEqual(len(snapshots), 0)
        self.assertEqual(len(updates), 0)


    @covers_requirement(
        "webclient-action-dispatch::admitted-action-completion-publishes-canonical-state-before-unlocking"
    )
    def test_real_dispatcher_wire_ordering_result_before_detach_and_snapshot(self):
        """Action result delivers FIRST, releasing in-flight, followed by detach and snapshot."""
        initial_epoch = self.coordinator.epoch
        envelope = self._envelope({"character_id": int(self.char2.pk)})

        in_flight_states_at_detach = []
        from web.webclient.presentation.ingress import send_unpuppet_transition as real_send_unpuppet

        def record_in_flight_at_detach(session):
            dispatch_state = getattr(session.ndb, "elosern_dispatch", None)
            in_flight_states_at_detach.append(getattr(dispatch_state, "in_flight", None))
            real_send_unpuppet(session)

        with patch(
            "web.webclient.actions.account_actions.send_unpuppet_transition",
            side_effect=record_in_flight_at_detach,
        ):
            handle_ui_action(
                self.session,
                self.char1,
                envelope,
                self.action_registry,
                self.presentation_registry,
            )

            # 1. At this instant (before clock advance), result is ALREADY delivered
            results = [call for call in self.session.sent if "ui_action_result" in call]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["ui_action_result"][0][0]["outcome"], "success")
            self.assertEqual(results[0]["ui_action_result"][0][0]["presentation_epoch"], initial_epoch)
            # At this retiring epoch, NO presentation update or snapshot was published
            self.assertEqual(len([c for c in self.session.sent if "ui_update" in c]), 0)
            self.assertEqual(len([c for c in self.session.sent if "ui_snapshot" in c]), 0)
            self.assertEqual([list(c.keys())[0] for c in self.session.sent], ["ui_action_result"])

            # In-flight marker was released by _settle_in_flight
            dispatch_state = getattr(self.session.ndb, "elosern_dispatch", None)
            self.assertFalse(dispatch_state.in_flight)

            # 2. Advance the clock: scheduled transition runs
            self.clock.advance(0)

            # Assert that when send_unpuppet_transition ran, in_flight was already False
            self.assertEqual(in_flight_states_at_detach, [False])

            # 3. Assert exact sequence on the wire:
            # First: ui_action_result, Second: ui_protocol_error(no_puppet), Third: ui_snapshot
            first_three = [list(call.keys())[0] for call in self.session.sent[:3]]
            self.assertEqual(first_three, ["ui_action_result", "ui_protocol_error", "ui_snapshot"])

            protocol_errors = [call for call in self.session.sent if "ui_protocol_error" in call]
            self.assertEqual(len(protocol_errors), 1)
            self.assertEqual(protocol_errors[0]["ui_protocol_error"][0][0]["code"], "no_puppet")

            snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
            self.assertEqual(len(snapshots), 1)
            new_epoch = snapshots[-1]["ui_snapshot"][0][0]["presentation_epoch"]
            self.assertNotEqual(new_epoch, initial_epoch)



    # -------------------------------------------------------------------------
    # Cross-Puppet Presentation State Isolation
    # -------------------------------------------------------------------------
    @covers_requirement(
        "webclient-character-roster::a-puppet-change-carries-no-session-scoped-state-across-characters"
    )
    def test_cross_puppet_session_state_isolation(self):
        """Switching characters clears ephemeral options state and concept proposals."""
        # Set up ephemeral state for char1
        self.session.ndb.options_state = {
            "owner_actor_id": str(self.char1.pk),
            "fingerprint": "fp_char1",
            "status": "ready",
            "generation_token": 1,
            "displayed": [
                {
                    "kind": "known_action",
                    "action_code": "explore.look",
                    "label": "打量四周",
                    "params": {},
                    "hint": None,
                }
            ],
        }
        self.session.ndb.options_barriers = {"char1_barrier": 1}
        self.session.ndb.concept_proposal = {
            "owner_actor_id": str(self.char1.pk),
            "revision": 1,
            "race": "human",
            "subrace": None,
            "allocations": {},
            "persona": {},
        }

        # Tag/attribute on char1 to verify persistent state survives
        self.char1.tags.add("veteran", category="status")
        self.char1.db.quest_progress = 5
        char1_epoch = self.coordinator.epoch

        # Perform switch to char2
        envelope = self._envelope({"character_id": int(self.char2.pk)})
        handle_ui_action(
            self.session,
            self.char1,
            envelope,
            self.action_registry,
            self.presentation_registry,
        )
        self.clock.advance(0)

        self.assertIs(self.session.puppet, self.char2)

        # Ephemeral session state from char1 must not be inherited
        options_state = getattr(self.session.ndb, "options_state", None)
        if options_state is not None:
            # If reconnect trigger initialized state for char2, verify it's char2's
            self.assertEqual(options_state.get("owner_actor_id"), str(self.char2.pk))
            self.assertNotEqual(options_state.get("fingerprint"), "fp_char1")
        self.assertIsNone(getattr(self.session.ndb, "options_barriers", None))
        self.assertIsNone(getattr(self.session.ndb, "concept_proposal", None))

        # ---------------------------------------------------------------------
        # An in-flight generation or settlement for char1 settling after switch
        # publishes nothing into char2's sequence
        # ---------------------------------------------------------------------
        self.session.sent.clear()

        # 1. Dispatcher action completion from char1's epoch
        from web.webclient.actions.dispatcher import _publish_completion
        _publish_completion(
            self.session,
            self.char1,
            {"outcome": "success", "code": "ok", "message": "done", "affected_panels": ("status",)},
            self.presentation_registry,
            "old-req-1",
            char1_epoch,
        )
        self.assertEqual(len([c for c in self.session.sent if "ui_action_result" in c]), 0)
        self.assertEqual(len([c for c in self.session.sent if "ui_update" in c]), 0)

        # 2. Options proposal subscriber from char1's epoch
        from server.option_proposal_service import _deliver_guarded, _PendingSubscriber
        sub = _PendingSubscriber(self.session, token=1, captured_epoch=char1_epoch, fingerprint="fp_char1")
        _deliver_guarded(sub, self.char1, "ready", None)
        self.assertEqual(len([c for c in self.session.sent if "ui_update" in c]), 0)
        self.assertEqual(len([c for c in self.session.sent if "ui_snapshot" in c]), 0)

        # char1 persistent state is completely intact
        self.assertTrue(self.char1.tags.has("veteran", category="status"))
        self.assertEqual(self.char1.db.quest_progress, 5)


    def test_account_set_last_puppet_guards_ownership(self):
        """Account.set_last_puppet sets _last_puppet for owned characters and rejects foreign."""
        # Owned character succeeds
        self.assertTrue(self.account.set_last_puppet(self.char2))
        self.assertIs(self.account.db._last_puppet, self.char2)

        # Foreign character is rejected and does not mutate _last_puppet
        self.assertFalse(self.account.set_last_puppet(self.foreign_char))
        self.assertIs(self.account.db._last_puppet, self.char2)

        # None is rejected
        self.assertFalse(self.account.set_last_puppet(None))
        self.assertIs(self.account.db._last_puppet, self.char2)

if __name__ == "__main__":
    unittest.main()
