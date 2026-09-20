"""Slice of ``test_character_creation``: CharacterCreationCommandTests (pending-gate half).
"""
from tools.spec_traceability import covers_requirement
from copy import replace
from django.db import transaction
from unittest.mock import Mock, patch
from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT
from evennia.utils.evmenu import CmdGetInput, InputCmdSet
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    resolve_starting_profile,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.lore.starting_kits import SubraceStartingKit
from world.tests.synthetic_data import (
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SUBRACES,
    _SYNTH_ELEMENT,
    make_subrace,
)
from commands.character_creation import (
    ALLOCATION_AXIS_EXPLANATIONS,
    MAX_CONCEPT_LENGTH,
    CmdCharacter,
    CmdCharacterConcept,
    CmdCreationRequired,
    CharacterCreationCmdSet,
    _age_prompt,
    _name_prompt,
    _proposal_summary,
    _terminal_safe,
    creation_start_screen,
)
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.ai.character_creation import CharacterProposal

from ._support import (
    _messages,
    _open_creation_scope,
    _prompt_stub,
)


class CharacterCreationCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_creation_scope(self)
        super().setUp()
        self.account.at_post_create_character(self.char1)

    @covers_requirement("player-character-creation::newly-registered-accounts-have-an-inert-pending-player-character")
    def test_pending_gate_is_replace_and_blocks_world_commands(self):
        gate = CharacterCreationCmdSet(self.char1)
        self.assertEqual(gate.mergetype, "Replace")
        self.assertTrue(gate.no_exits)
        self.assertTrue(gate.no_objs)
        self.assertGreater(gate.priority, 10)
        self.char1.at_cmdset_get()
        self.assertTrue(self.char1.cmdset.has("CharacterCreation"))
        self.assertNotIn("rest", gate.get_all_cmd_keys_and_aliases(self.char1))
        self.assertIs(self.account.db._last_puppet, self.char1)
        self.assertTrue(self.char1.locks.check(self.account, "puppet"))

    def test_real_command_handler_rejects_rest_before_clock_access(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with patch("commands.skip.get_world_clock") as clock:
                self.char1.execute_cmd("rest 5s", session=self.session)
            messages = " ".join(str(call.args[0]) for call in message_mock.call_args_list)
        finally:
            self.char1.msg = original_msg
        self.assertIn("先完成角色建立", messages)
        clock.assert_not_called()

    def test_real_command_handler_blocks_exit_object_and_combat_commands(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        old_location = self.char1.location
        old_object_location = self.obj1.location
        try:
            for raw in (self.exit.key, f"get {self.obj1.key}", "engage"):
                self.char1.execute_cmd(raw, session=self.session)
        finally:
            self.char1.msg = original_msg
        self.assertEqual(self.char1.location, old_location)
        self.assertEqual(self.obj1.location, old_object_location)
        messages = " ".join(str(call.args[0]) for call in message_mock.call_args_list)
        self.assertGreaterEqual(messages.count("先完成角色建立"), 3)

    def test_pending_gate_reappears_from_persistent_state(self):
        self.char1.at_cmdset_get()
        self.char1.cmdset.remove("CharacterCreation")
        self.char1.attributes.reset_cache()
        self.assertTrue(self.char1.creation_pending)
        self.char1.at_cmdset_get()
        self.assertTrue(self.char1.cmdset.has("CharacterCreation"))

    def test_merged_cmdset_gate_wins_prompt_command_dedup(self):
        merged = InputCmdSet(self.char1) + CharacterCreationCmdSet(self.char1)
        nomatch = merged.get(CMD_NOMATCH)
        self.assertIsInstance(nomatch, CmdCreationRequired)
        self.assertFalse(any(isinstance(cmd, CmdGetInput) for cmd in merged.commands))
        noinput = merged.get(CMD_NOINPUT)
        self.assertIsInstance(noinput, CmdCreationRequired)

    def test_gate_handler_forwards_open_prompt_reply_and_cleans_up(self):
        callback = Mock(return_value=False)
        self.char1.ndb._getinput = _prompt_stub(callback)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "自訂者"
        command.func()
        callback.assert_called_once_with(
            self.char1, "角色姓名（輸入 cancel 取消）：", "自訂者"
        )
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))

    def test_gate_handler_keeps_prompt_state_when_callback_returns_truthy(self):
        callback = Mock(return_value=True)
        self.char1.ndb._getinput = _prompt_stub(callback)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "再試"
        command.func()
        callback.assert_called_once_with(
            self.char1, "角色姓名（輸入 cancel 取消）：", "再試"
        )
        self.assertTrue(self.char1.ndb._getinput)
        self.assertTrue(self.char1.cmdset.has("input_cmdset"))

    def test_gate_handler_no_prompt_keeps_creation_required_message(self):
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            command = CmdCreationRequired()
            command.caller = self.char1
            command.raw_string = "rest 5s"
            command.func()
        finally:
            self.char1.msg = original_msg
        messages = _messages(message_mock)
        self.assertTrue(any("先完成角色建立" in text for text in messages))
        self.assertFalse(self.char1.ndb._getinput)

    def test_gate_handler_cleans_up_when_callback_raises(self):
        def boom(caller, prompt, result):
            raise RuntimeError("boom")

        self.char1.ndb._getinput = _prompt_stub(boom)
        self.char1.cmdset.add(InputCmdSet, persistent=False)
        original_msg = self.char1.msg
        message_mock = Mock()
        self.char1.msg = message_mock
        try:
            with patch("commands.character_creation.log_error") as log_trace:
                command = CmdCreationRequired()
                command.caller = self.char1
                command.session = self.session
                command.raw_string = "x"
                command.func()
        finally:
            self.char1.msg = original_msg
        self.assertFalse(self.char1.ndb._getinput)
        self.assertFalse(self.char1.cmdset.has("input_cmdset"))
        log_trace.assert_called_once()
        messages = _messages(message_mock)
        self.assertTrue(any("Error in get_input" in text for text in messages))

    def test_gate_handler_routes_account_level_prompt(self):
        def callback(caller, prompt, result):
            self.assertIs(
                caller, self.account, "account-level prompt routes with the account as caller"
            )
            self.assertIs(
                caller.ndb._getinput._session,
                command.session,
                "the account prompt's session is recorded on the account",
            )
            return False

        self.account.ndb._getinput = _prompt_stub(callback)
        self.account.cmdset.add(InputCmdSet, persistent=False)
        command = CmdCreationRequired()
        command.caller = self.char1
        command.session = self.session
        command.raw_string = "cancel"
        command.func()
        self.assertFalse(self.account.ndb._getinput)
        self.assertFalse(self.account.cmdset.has("input_cmdset"))
