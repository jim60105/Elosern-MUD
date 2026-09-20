"""Unit tests for the account switch/create payload validators."""
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
from tools.spec_traceability import covers_requirement
import unittest


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

    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_valid_payload_accepted(self):
        self.assertEqual(validate_account_character_create_payload({}), {})

    @covers_requirement(
        "webclient-character-roster::creating-a-character-is-an-allowlisted-account-scoped-action"
    )
    def test_create_invalid_payload_rejected(self):
        bad_payloads = [
            {"character_id": 42},
            {"extra": "forbidden"},
            {"name": "test"},
            "not_a_dict",
            [],
            None,
            123,
            True,
        ]
        for bad in bad_payloads:
            with self.subTest(payload=bad):
                with self.assertRaises(AccountActionError):
                    validate_account_character_create_payload(bad)

if __name__ == "__main__":
    unittest.main()
