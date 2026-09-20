"""Synchronous switch admission decisions and rejections."""
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
from twisted.internet.task import Clock
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
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

if __name__ == "__main__":
    unittest.main()
