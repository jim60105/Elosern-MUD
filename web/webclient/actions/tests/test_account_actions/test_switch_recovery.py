"""The deferred switch transition and its verify-and-recover ladder."""
from twisted.internet.task import Clock
from evennia.utils.test_resources import EvenniaTest
from web.webclient.actions.dispatcher import (
    NO_PUPPET_CODE,
    handle_ui_action,
    retire_sequence,
)
from typeclasses.characters import PlayerCharacter
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
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.registry import build_production_registry
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.clock import get_world_clock
from unittest.mock import MagicMock, patch
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

            # MC6: the transition finished; the marker cleared and a fresh request is admitted
            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char3.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


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

            # MC6: the transition finished; the marker cleared and a fresh request is admitted
            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char3.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


    @covers_requirement(
        "webclient-character-roster::a-scheduled-puppet-transition-verifies-its-outcome-and-recovers-explicitly"
    )
    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
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

            # MC6: even the terminal rung clears the marker, and the puppet-less session is
            # answered by the ORDINARY no-puppet entry gate at the production surface — the
            # pending refusal must never shadow it.
            self.assertFalse(_transition_pending(self.session))
            self.assertIsNone(self.session.puppet)
            from server.conf import inputfuncs

            inputfuncs.ui_action(
                self.session,
                self._envelope(
                    {"character_id": int(self.char2.pk)}, request_id="r-after-ooc"
                ),
            )
            results = [
                call for call in self.session.sent if "ui_action_result" in call
            ]
            self.assertTrue(results)
            rejection = results[-1]["ui_action_result"][0][0]
            self.assertEqual(rejection["request_id"], "r-after-ooc")
            self.assertEqual(rejection["outcome"], "rejected")
            self.assertEqual(rejection["code"], NO_PUPPET_CODE)
            self.assertNotEqual(rejection["code"], TRANSITION_PENDING_CODE)
            # The gate path never schedules a transition and never re-arms the marker.
            self.assertEqual(len(self.clock.getDelayedCalls()), 0)
            self.assertFalse(_transition_pending(self.session))



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

        # MC6: the transition finished; the marker cleared and a fresh request is
        # admitted (outside the combat patch, so the adapter sees the real state).
        self.assertFalse(_transition_pending(self.session))
        next_result = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(next_result["outcome"], "success")
        self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


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

            # MC6: the transition finished; the marker cleared and a fresh request is admitted
            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char3.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


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

            # MC6: the transition finished; the marker cleared and a fresh request is admitted
            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char3, {"character_id": int(self.char1.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)


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

if __name__ == "__main__":
    unittest.main()
