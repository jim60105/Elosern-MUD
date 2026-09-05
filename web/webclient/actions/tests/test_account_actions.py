"""Account action adapter, transition, and dispatcher integration tests (MC3).

Tests the ``account.character.switch`` action:
- Exact payload validation ({character_id} positive int, no booleans, no extras).
- Synchronous authorization decisions (foreign ID, combat lock, self-switch).
- Result-only presentation contract (no_presentation=True, no retiring-epoch snapshot).
- Deferred transition execution on the Twisted reactor turn via an injectable clock seam.
- Verify-and-recover ladder (rungs 1, 2, 3, unexpected puppet, stale puppet cancellation).
- Dispatcher ordering: result delivered before detach signal and new-epoch snapshot.
- Cross-puppet session presentation isolation (options state, barriers, proposals cleared).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import unittest

from twisted.internet.task import Clock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.account_actions import (
    ALREADY_CURRENT_CODE,
    ALREADY_CURRENT_MESSAGE,
    AFFECTED_PANELS,
    AccountActionError,
    IN_COMBAT_CODE,
    IN_COMBAT_MESSAGE,
    INVALID_CHARACTER_CODE,
    INVALID_CHARACTER_MESSAGE,
    RECOVERY_FAILED_MESSAGE,
    RECOVERY_RESTORED_TEMPLATE,
    RECOVERY_RETAINED_TEMPLATE,
    SUCCESS_CODE,
    SUCCESS_MESSAGE,
    _account_character_switch_adapter,
    _attach_puppet,
    _perform_switch,
    _recover_transition,
    set_clock_for_testing,
    validate_account_character_switch_payload,
)
from web.webclient.actions.dispatcher import handle_ui_action, retire_sequence
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import (
    FrozenCard,
    OptionsSnapshot,
    ProposalSnapshot,
    synchronize_session,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock


class AccountActionsValidatorTests(unittest.TestCase):
    """Unit tests for validate_account_character_switch_payload."""

    @covers_requirement(
        "webclient-character-roster::switching-characters-is-an-allowlisted-account-scoped-action"
    )
    def test_valid_payload_accepted(self):
        self.assertEqual(
            validate_account_character_switch_payload({"character_id": 42}),
            {"character_id": 42},
        )
        self.assertEqual(
            validate_account_character_switch_payload({"character_id": 1}),
            {"character_id": 1},
        )

    @covers_requirement(
        "webclient-character-roster::switching-characters-is-an-allowlisted-account-scoped-action"
    )
    def test_invalid_payload_rejected(self):
        bad_payloads = [
            {},
            {"character_id": 42, "extra": "forbidden"},
            {"other_id": 42},
            {"character_id": True},   # bool is int subclass in Python
            {"character_id": False},
            {"character_id": 0},
            {"character_id": -1},
            {"character_id": 3.14},
            {"character_id": "42"},
            {"character_id": None},
            "not_a_dict",
            [42],
            None,
        ]
        for bad in bad_payloads:
            with self.subTest(payload=bad):
                with self.assertRaises(AccountActionError):
                    validate_account_character_switch_payload(bad)


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
    # Synchronous Decisions and Rejections
    # -------------------------------------------------------------------------

    @covers_requirement(
        "webclient-character-roster::switching-is-refused-for-a-foreign-current-or-combat-locked-target"
    )
    def test_switch_rejected_for_foreign_character_id(self):
        """A character owned by a different account is refused synchronously."""
        result = _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.foreign_char.pk)},
            session=self.session,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], INVALID_CHARACTER_CODE)
        self.assertEqual(result["message"], INVALID_CHARACTER_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Nothing was scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)
        # Puppet is untouched
        self.assertIs(self.session.puppet, self.char1)

    @covers_requirement(
        "webclient-character-roster::switching-is-refused-for-a-foreign-current-or-combat-locked-target"
    )
    def test_switch_rejected_when_currently_in_combat(self):
        """Switching while in active combat is blocked synchronously."""
        with patch(
            "web.webclient.actions.account_actions.is_in_active_session",
            return_value=True,
        ):
            result = _account_character_switch_adapter(
                self.char1,
                {"character_id": int(self.char2.pk)},
                session=self.session,
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], IN_COMBAT_CODE)
        self.assertEqual(result["message"], IN_COMBAT_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Nothing was scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)
        self.assertIs(self.session.puppet, self.char1)

    @covers_requirement(
        "webclient-character-roster::switching-is-refused-for-a-foreign-current-or-combat-locked-target"
    )
    def test_switch_rejected_for_already_current_puppet(self):
        """Switching to the currently attached character is rejected as already_current."""
        result = _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.char1.pk)},
            session=self.session,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], ALREADY_CURRENT_CODE)
        self.assertEqual(result["message"], ALREADY_CURRENT_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # Nothing was scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)
        self.assertIs(self.session.puppet, self.char1)

    @covers_requirement(
        "webclient-character-roster::switching-is-refused-for-a-foreign-current-or-combat-locked-target"
    )
    def test_switch_rejected_for_unresolvable_nonexistent_id(self):
        """A character ID not existing on the account is refused as invalid_character."""
        result = _account_character_switch_adapter(
            self.char1,
            {"character_id": 999999},
            session=self.session,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], INVALID_CHARACTER_CODE)
        self.assertTrue(result["no_presentation"])
        self.assertEqual(len(self.clock.getDelayedCalls()), 0)

    # -------------------------------------------------------------------------
    # Acceptance & Clock Advance
    # -------------------------------------------------------------------------

    @covers_requirement(
        "webclient-character-roster::a-character-changing-action-reports-its-decision-before-its-transition"
    )
    def test_successful_switch_deferred_transition(self):
        """Accepted switch returns success immediately and transitions on clock advance."""
        initial_epoch = self.coordinator.epoch

        result = _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.char2.pk)},
            session=self.session,
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], SUCCESS_CODE)
        self.assertEqual(result["message"], SUCCESS_MESSAGE)
        self.assertTrue(result["no_presentation"])

        # One transition is scheduled on the reactor
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)
        # Puppet is still unchanged before clock advances
        self.assertIs(self.account.get_puppet(self.session), self.char1)

        # Advance the clock
        self.clock.advance(0)

        # Now puppet is char2
        self.assertIs(self.account.get_puppet(self.session), self.char2)
        self.assertIs(self.account.db._last_puppet, self.char2)

        # The session sent messages including ui_protocol_error(no_puppet) and fresh snapshot
        protocol_errors = [call for call in self.session.sent if "ui_protocol_error" in call]
        self.assertTrue(protocol_errors)
        self.assertEqual(protocol_errors[-1]["ui_protocol_error"][0][0]["code"], "no_puppet")

        snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
        self.assertTrue(snapshots)
        # The snapshot was published under a new epoch
        new_epoch = snapshots[-1]["ui_snapshot"][0][0]["presentation_epoch"]
        self.assertNotEqual(new_epoch, initial_epoch)

    # -------------------------------------------------------------------------
    # Recovery Ladder (Rungs 1, 2, 3)
    # -------------------------------------------------------------------------

    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    def test_recovery_rung_1_silent_refusal_retains_current_puppet(self):
        """Rung 1: puppet_object refuses silently without releasing previous character."""
        account_msgs = []
        original_msg = self.account.msg

        def fake_msg(text, *args, **kwargs):
            account_msgs.append(text)
            return original_msg(text, *args, **kwargs)

        with patch.object(self.account, "msg", side_effect=fake_msg), \
             patch.object(self.account, "puppet_object") as mock_puppet, \
             patch("web.webclient.actions.account_actions.log_warn") as mock_warn:
            # puppet_object does nothing (simulates returning without unpuppeting)
            mock_puppet.return_value = None

            result = _account_character_switch_adapter(
                self.char1,
                {"character_id": int(self.char2.pk)},
                session=self.session,
            )
            self.assertEqual(result["outcome"], "success")

            self.clock.advance(0)

            # Verification failed, session still holds char1
            self.assertIs(self.session.puppet, self.char1)
            # log_warn was called with char_switch_retained
            mock_warn.assert_called_once()
            self.assertEqual(mock_warn.call_args[0][0], "char_switch_retained")

            # Player was notified with retained template
            expected_line = RECOVERY_RETAINED_TEMPLATE.format(name=self.char1.name)
            self.assertIn(expected_line, account_msgs)

            # A fresh snapshot for char1 was published
            snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
            self.assertTrue(snapshots)

    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    def test_recovery_rung_2_repaired_after_unpuppet(self):
        """Rung 2: target attach fails after unpuppet, re-attaching previous succeeds."""
        account_msgs = []
        original_msg = self.account.msg

        def fake_msg(text, *args, **kwargs):
            account_msgs.append(text)
            return original_msg(text, *args, **kwargs)

        call_count = 0

        def fake_puppet_object(session, target):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (target): simulate Evennia unpuppeting previous then failing
                session.puppet = None
                return None
            else:
                # Second call (recovery of char1): succeeds
                session.puppet = target
                return None

        with patch.object(self.account, "msg", side_effect=fake_msg), \
             patch.object(self.account, "puppet_object", side_effect=fake_puppet_object), \
             patch("web.webclient.actions.account_actions.log_error") as mock_err:

            _account_character_switch_adapter(
                self.char1,
                {"character_id": int(self.char2.pk)},
                session=self.session,
            )
            self.clock.advance(0)

            # Repaired to char1
            self.assertIs(self.session.puppet, self.char1)
            self.assertIs(self.account.db._last_puppet, self.char1)

            # log_error was called with char_switch_repaired
            mock_err.assert_called_once()
            self.assertEqual(mock_err.call_args[0][0], "char_switch_repaired")

            # Player notified with restored template
            expected_line = RECOVERY_RESTORED_TEMPLATE.format(name=self.char1.name)
            self.assertIn(expected_line, account_msgs)

            # Snapshot sent for char1
            snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
            self.assertTrue(snapshots)

    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    def test_recovery_rung_3_unrecoverable_failure_leaves_session_ooc(self):
        """Rung 3: both target attach and previous re-attach fail; leaves session OOC."""
        account_msgs = []
        original_msg = self.account.msg

        def fake_msg(text, *args, **kwargs):
            account_msgs.append(text)
            return original_msg(text, *args, **kwargs)

        def failing_puppet_object(session, target):
            # Unpuppets session and returns None every time
            session.puppet = None
            return None

        with patch.object(self.account, "msg", side_effect=fake_msg), \
             patch.object(self.account, "puppet_object", side_effect=failing_puppet_object), \
             patch("web.webclient.actions.account_actions.log_error") as mock_err:

            _account_character_switch_adapter(
                self.char1,
                {"character_id": int(self.char2.pk)},
                session=self.session,
            )
            self.clock.advance(0)

            # Session holds None (OOC)
            self.assertIsNone(self.session.puppet)

            # log_error was called with char_switch_recovery_failed
            mock_err.assert_called_once()
            self.assertEqual(mock_err.call_args[0][0], "char_switch_recovery_failed")
            context = mock_err.call_args[1]["context"]
            self.assertIn("account", context)
            self.assertIn("session", context)
            self.assertIn("previous", context)
            self.assertIn("target", context)

            # Explicit line naming 進入世界
            self.assertIn(RECOVERY_FAILED_MESSAGE, account_msgs)

            # NO snapshot published
            snapshots = [call for call in self.session.sent if "ui_snapshot" in call]
            self.assertEqual(len(snapshots), 0)

    # -------------------------------------------------------------------------
    # Late Re-validation and Edge Cases
    # -------------------------------------------------------------------------

    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    def test_late_revalidation_failure_when_combat_entered_before_transition(self):
        """If actor enters combat after decision but before transition, cancels to Rung 1."""
        account_msgs = []
        original_msg = self.account.msg

        def fake_msg(text, *args, **kwargs):
            account_msgs.append(text)
            return original_msg(text, *args, **kwargs)

        _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.char2.pk)},
            session=self.session,
        )

        # Before clock advances, char1 enters combat
        with patch.object(self.account, "msg", side_effect=fake_msg), \
             patch("web.webclient.actions.account_actions.is_in_active_session", return_value=True), \
             patch("web.webclient.actions.account_actions.log_warn") as mock_warn:

            self.clock.advance(0)

            # Session still holds char1
            self.assertIs(self.session.puppet, self.char1)
            mock_warn.assert_called_once()
            self.assertEqual(mock_warn.call_args[0][0], "char_switch_retained")
            self.assertIn(RECOVERY_RETAINED_TEMPLATE.format(name=self.char1.name), account_msgs)

    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    def test_late_revalidation_failure_when_target_removed_from_account(self):
        """If target character is removed before transition, cancels to Rung 1."""
        _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.char2.pk)},
            session=self.session,
        )

        # Remove char2 from account characters
        self.account.characters.remove(self.char2)

        with patch("web.webclient.actions.account_actions.log_warn") as mock_warn:
            self.clock.advance(0)

            self.assertIs(self.session.puppet, self.char1)
            mock_warn.assert_called_once()
            self.assertEqual(mock_warn.call_args[0][0], "char_switch_retained")

    def test_stale_puppet_session_cancels_transition_without_detach(self):
        """If the session puppet changed before the scheduled timer, transition cancels cleanly."""
        _account_character_switch_adapter(
            self.char1,
            {"character_id": int(self.char2.pk)},
            session=self.session,
        )

        # External event changed session puppet to char3
        self.session.puppet = self.char3

        with patch("web.webclient.actions.account_actions.send_unpuppet_transition") as mock_detach, \
             patch("web.webclient.actions.account_actions.log_warn") as mock_warn:

            self.clock.advance(0)

            # Did NOT send unpuppet transition signal
            mock_detach.assert_not_called()
            # Stale puppet warning logged
            mock_warn.assert_called_once()
            self.assertEqual(mock_warn.call_args[0][0], "char_switch_stale_puppet")
            # Session puppet remains char3
            self.assertIs(self.session.puppet, self.char3)

    def test_unexpected_puppet_recovers_gracefully(self):
        """If transition unexpectedly results in a third puppet, logs error and syncs actual."""
        def attach_to_char3(session, account, target):
            session.puppet = self.char3
            return False

        with patch("web.webclient.actions.account_actions._attach_puppet", side_effect=attach_to_char3), \
             patch("web.webclient.actions.account_actions.log_error") as mock_err:

            _perform_switch(self.session, self.account, int(self.char2.pk), self.char1)

            mock_err.assert_called_once()
            self.assertEqual(mock_err.call_args[0][0], "char_switch_unexpected_puppet")
            self.assertIs(self.session.puppet, self.char3)

    def test_puppet_object_raising_runtime_error_is_contained(self):
        """If puppet_object raises an unexpected exception, recovery ladder handles it."""
        with patch.object(self.account, "puppet_object", side_effect=RuntimeError("simulated crash")), \
             patch("web.webclient.actions.account_actions.log_warn") as mock_warn:

            # char1 is still puppet
            _perform_switch(self.session, self.account, int(self.char2.pk), self.char1)

            # Handled via recovery ladder Rung 1
            self.assertIs(self.session.puppet, self.char1)
            event_names = [call[0][0] for call in mock_warn.call_args_list]
            self.assertIn("char_switch_retained", event_names)

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
