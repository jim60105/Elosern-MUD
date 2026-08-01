"""Integration tests for the pending character command boundary."""

from tools.spec_traceability import covers_requirement

from unittest.mock import Mock, patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.character_creation import CmdCharacter, CharacterCreationCmdSet
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter


class CharacterCreationCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
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

    def test_status_and_preset_activation(self):
        output = self.call(CmdCharacter(), "")
        self.assertIn("preset", output)
        output = self.call(CmdCharacter(), "preset human_wanderer")
        self.assertIn("已建立", output)
        self.assertFalse(self.char1.creation_pending)
        self.char1.at_cmdset_get()
        self.assertFalse(self.char1.cmdset.has("CharacterCreation"))
        self.assertIsNotNone(self.char1.traits.magic_level)

    def test_real_rest_reaches_clock_after_activation(self):
        self.call(CmdCharacter(), "preset human_wanderer")
        original_msg = self.char1.msg
        self.char1.msg = Mock()
        try:
            with patch("commands.skip.get_world_clock") as get_clock:
                get_clock.return_value.advance.return_value = []
                self.char1.execute_cmd("rest 5s", session=self.session)
            get_clock.return_value.advance.assert_called_once()
        finally:
            self.char1.msg = original_msg

    def test_custom_wizard_activates_the_existing_shell(self):
        old_id, old_location = self.char1.id, self.char1.location
        replies = [
            "自訂者", "20", "20", "human", "none",
            "100", "50", "31", "0", "0", "0", "yes",
        ]
        output = self.call(
            CmdCharacter(), "create", inputs=[*reversed(replies), None]
        )
        self.assertIn("已建立", output)
        self.assertEqual(self.char1.key, "自訂者")
        self.assertEqual(self.char1.id, old_id)
        self.assertEqual(self.char1.location, old_location)
        self.assertIn(self.char1, self.account.characters)

    def test_abandoned_prompt_keeps_the_shell_unchanged(self):
        command = CmdCharacter()
        command.caller = self.char1
        command.account = self.account
        command.args = "create"
        generator = command.func()
        next(generator)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
        self.assertIsNone(self.char1.age)
        self.assertIsNone(self.char1.apparent_age)

    def test_cancelled_custom_wizard_changes_nothing(self):
        old_key = self.char1.key
        output = self.call(CmdCharacter(), "create", inputs=["cancel", None])
        self.assertIn("已取消", output)
        self.assertEqual(self.char1.key, old_key)
        self.assertTrue(self.char1.creation_pending)
        self.assertEqual(self.char1.traits.all(), [])
