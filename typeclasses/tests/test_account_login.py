"""Integration tests for the Account login coordinator and world introduction."""

from tools.spec_traceability import covers_requirement

from unittest.mock import Mock

from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter


class LoginIntroductionTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.at_post_create_character(self.char1)

    def _messages_on_login(self):
        original_msg = self.account.msg
        message_mock = Mock()
        self.account.msg = message_mock
        try:
            self.account.at_post_login(session=self.session)
        finally:
            self.account.msg = original_msg
        return " ".join(
            str(call.args[0]) for call in message_mock.call_args_list if call.args
        )

    @covers_requirement("connection-screen::a-newly-registered-account-receives-a-world-introduction-before-character-creation")
    def test_pending_account_sees_introduction_then_creation_start_screen(self):
        messages = self._messages_on_login()
        self.assertIn("伊洛瑟恩大陸", messages)
        self.assertIn("你站在伊洛瑟恩大陸的門口", messages)
        self.assertIn("character preset", messages)

    @covers_requirement("connection-screen::a-newly-registered-account-receives-a-world-introduction-before-character-creation")
    def test_activated_account_sees_neither_introduction_nor_start_screen(self):
        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )

        activate_player_character(
            self.account,
            self.char1,
            CharacterCreationRequest(mode="preset", preset_key="human_wanderer"),
        )
        messages = self._messages_on_login()
        self.assertNotIn("伊洛瑟恩大陸", messages)
        self.assertNotIn("你站在伊洛瑟恩大陸的門口", messages)

    @covers_requirement("webclient-login-gate::the-webclient-overlay-shows-the-waiting-for-login-state-for-anonymous-sessions")
    def test_login_emits_logged_in_oob_to_the_session(self):
        # The webclient login gate is driven by the server's `logged_in` OOB
        # event: evennia's at_post_login notifies the session through
        # session.msg(logged_in={}). The browser's client-local `loggedIn`
        # flag (and the overlay's waiting-for-login state) is set when this
        # event arrives, and cleared on connection_open/connection_close.
        original_msg = self.session.msg
        oob_mock = Mock()
        self.session.msg = oob_mock
        try:
            self.account.at_post_login(session=self.session)
        finally:
            self.session.msg = original_msg
        logged_in_calls = [
            call for call in oob_mock.call_args_list
            if call.kwargs and "logged_in" in call.kwargs
        ]
        self.assertEqual(len(logged_in_calls), 1)
        self.assertEqual(logged_in_calls[0].kwargs["logged_in"], {})
