"""MC6 transition-pending admission serialization."""
from twisted.internet.task import Clock
from evennia.utils.test_resources import EvenniaTest
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
    # MC6: Transition-Pending Admission Serialization
    # -------------------------------------------------------------------------
    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_second_switch_while_pending_refused(self):
        """A rapid double submission admits exactly one switch; the other gets transition_pending."""
        epoch_before = self.coordinator.epoch

        first = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char2.pk)}, session=self.session
        )
        self.assertEqual(first["outcome"], "success")

        # Do not advance the clock: the first transition is scheduled but unexecuted.
        second = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(second["outcome"], "rejected")
        self.assertEqual(second["code"], TRANSITION_PENDING_CODE)
        self.assertEqual(second["message"], TRANSITION_PENDING_MESSAGE)
        self.assertTrue(second["no_presentation"])

        # Only the first transition was ever scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)
        # Session and epoch untouched until the first transition runs
        self.assertIs(self.account.get_puppet(self.session), self.char1)
        self.assertEqual(self.coordinator.epoch, epoch_before)

        # The refused second request leaves the first transition's outcome unaffected
        self.clock.advance(0)
        self.assertIs(self.account.get_puppet(self.session), self.char2)


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_create_while_switch_pending_refused(self):
        """A scheduled switch blocks a subsequent create; no character is created."""
        chars_before = list(self.account.characters)

        first = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char2.pk)}, session=self.session
        )
        self.assertEqual(first["outcome"], "success")

        result = _account_character_create_adapter(self.char1, {}, session=self.session)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], TRANSITION_PENDING_CODE)
        self.assertTrue(result["no_presentation"])

        # No character object was created, nothing extra scheduled
        self.assertEqual(list(self.account.characters), chars_before)
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_switch_while_create_pending_refused(self):
        """A scheduled create blocks a subsequent switch; no second puppet change is scheduled."""
        first = _account_character_create_adapter(self.char1, {}, session=self.session)
        self.assertEqual(first["outcome"], "success")

        result = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], TRANSITION_PENDING_CODE)
        self.assertTrue(result["no_presentation"])

        # Exactly the create remains scheduled
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)

        # Advancing runs only the create: the puppet becomes the new shell, never char3
        self.clock.advance(0)
        self.assertIsNot(self.session.puppet, self.char3)
        self.assertIsNot(self.session.puppet, self.char1)
        self.assertTrue(getattr(self.session.puppet, "creation_pending", False))


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_pending_refusal_takes_precedence_over_other_reasons(self):
        """While pending, a request that would fail for its own reason is refused as pending."""
        first = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char2.pk)}, session=self.session
        )
        self.assertEqual(first["outcome"], "success")

        with self.subTest(reason="foreign_character"):
            result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.foreign_char.pk)}, session=self.session
            )
            self.assertEqual(result["code"], TRANSITION_PENDING_CODE)

        with self.subTest(reason="already_current"):
            result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char1.pk)}, session=self.session
            )
            self.assertEqual(result["code"], TRANSITION_PENDING_CODE)

        with self.subTest(reason="in_combat"):
            with patch(
                "web.webclient.actions.account_actions.is_in_active_session", return_value=True
            ):
                result = _account_character_switch_adapter(
                    self.char1, {"character_id": int(self.char3.pk)}, session=self.session
                )
            self.assertEqual(result["code"], TRANSITION_PENDING_CODE)

        with self.subTest(reason="combat_lookup_never_reached"):
            # The refusal is decided before any combat-session lookup: a combat check
            # that explodes must never be reached while the marker is set.
            with patch(
                "web.webclient.actions.account_actions.is_in_active_session",
                side_effect=AssertionError("combat lookup must not run while pending"),
            ):
                result = _account_character_switch_adapter(
                    self.char1, {"character_id": int(self.char3.pk)}, session=self.session
                )
            self.assertEqual(result["code"], TRANSITION_PENDING_CODE)

        # None of the refused requests scheduled anything
        self.assertEqual(len(self.clock.getDelayedCalls()), 1)


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_third_request_while_pending_refused_same_way(self):
        """Rejections never reset, clear, or extend the marker; the first transition still runs."""
        first = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char2.pk)}, session=self.session
        )
        self.assertEqual(first["outcome"], "success")

        for n in (2, 3):
            with self.subTest(request=n):
                result = _account_character_switch_adapter(
                    self.char1, {"character_id": int(self.char3.pk)}, session=self.session
                )
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], TRANSITION_PENDING_CODE)
                self.assertEqual(len(self.clock.getDelayedCalls()), 1)
                self.assertTrue(_transition_pending(self.session))

        # The marker still clears exactly when the first transition finishes
        self.clock.advance(0)
        self.assertIs(self.account.get_puppet(self.session), self.char2)
        self.assertFalse(_transition_pending(self.session))


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_next_request_admitted_after_successful_transition(self):
        """After a successful switch completes, further switch and create are admitted normally."""
        first = _account_character_switch_adapter(
            self.char1, {"character_id": int(self.char2.pk)}, session=self.session
        )
        self.assertEqual(first["outcome"], "success")
        self.clock.advance(0)
        self.assertIs(self.account.get_puppet(self.session), self.char2)

        follow_switch = _account_character_switch_adapter(
            self.char2, {"character_id": int(self.char3.pk)}, session=self.session
        )
        self.assertEqual(follow_switch["outcome"], "success")
        self.assertNotEqual(follow_switch.get("code"), TRANSITION_PENDING_CODE)
        self.clock.advance(0)

        follow_create = _account_character_create_adapter(self.char3, {}, session=self.session)
        self.assertEqual(follow_create["outcome"], "success")
        self.assertNotEqual(follow_create.get("code"), TRANSITION_PENDING_CODE)
        self.clock.advance(0)
        self.assertTrue(getattr(self.session.puppet, "creation_pending", False))


    @covers_requirement(
        "webclient-character-roster::a-session-admits-at-most-one-scheduled-puppet-transition-at-a-time"
    )
    def test_exception_in_scheduled_callbacks_still_clears_marker(self):
        """An uncaught exception escaping either callback must clear the pending marker (D4)."""
        with self.subTest(callback="_perform_switch"):
            first = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char2.pk)}, session=self.session
            )
            self.assertEqual(first["outcome"], "success")

            with patch.object(
                self.account, "get_puppet", side_effect=RuntimeError("simulated crash")
            ):
                with self.assertRaises(RuntimeError):
                    self.clock.advance(0)

            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char3.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)
            # Do not execute this second transition; each subTest owns its scenario
            # state. Cancelling a scheduled call in tests (never possible in production)
            # also removes its only finally-clear path, so release the marker here.
            for call_ in self.clock.getDelayedCalls():
                call_.cancel()
            _clear_transition_pending(self.session)

        with self.subTest(callback="_perform_create"):
            first = _account_character_create_adapter(self.char1, {}, session=self.session)
            self.assertEqual(first["outcome"], "success")

            with patch.object(
                self.account, "get_puppet", side_effect=RuntimeError("simulated crash")
            ):
                with self.assertRaises(RuntimeError):
                    self.clock.advance(0)

            self.assertFalse(_transition_pending(self.session))
            next_result = _account_character_switch_adapter(
                self.char1, {"character_id": int(self.char3.pk)}, session=self.session
            )
            self.assertEqual(next_result["outcome"], "success")
            self.assertNotEqual(next_result.get("code"), TRANSITION_PENDING_CODE)
            for call_ in self.clock.getDelayedCalls():
                call_.cancel()
            _clear_transition_pending(self.session)

if __name__ == "__main__":
    unittest.main()
