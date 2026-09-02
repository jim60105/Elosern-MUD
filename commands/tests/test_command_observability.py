"""Command-boundary observability: cmd_in/cmd_done bracket normal execution.

The events are emitted by the repo command base class, so the assertions
patch the base-module binding (``commands.command.log_info``) and drive
commands through the Evennia command-execution sequence (pre/parse/func/post)
rather than calling ``.func()`` directly. Two commands from two different
command modules prove the wiring is inherited, not per-module.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter

from commands.background import CmdBackground
from commands.lore import CmdLore


class CommandBoundaryEventTests(EvenniaCommandTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def _events(self, cmd, args=""):
        with patch("commands.command.log_info") as emit:
            self.call(cmd, args)
        return [
            (call.args[0], call.kwargs["context"])
            for call in emit.call_args_list
        ]

    def test_background_command_emits_one_bracketing_pair(self):
        events = self._events(CmdBackground(), "觀測測試")
        self.assertEqual([name for name, _ in events], ["cmd_in", "cmd_done"])
        started, done = events
        self.assertEqual(started[1]["char"], self.char1.pk)
        self.assertEqual(started[1]["cmd"], CmdBackground.key)
        self.assertEqual(started[1]["args"], "觀測測試")
        self.assertEqual(done[1]["char"], self.char1.pk)
        self.assertEqual(done[1]["cmd"], CmdBackground.key)
        self.assertEqual(done[1]["outcome"], "ok")
        self.assertIsInstance(done[1]["ms"], int)
        self.assertGreaterEqual(done[1]["ms"], 0)

    def test_lore_command_from_another_module_emits_the_pair(self):
        events = self._events(CmdLore(), "")
        self.assertEqual([name for name, _ in events], ["cmd_in", "cmd_done"])
        self.assertEqual(events[0][1]["cmd"], CmdLore.key)
        self.assertEqual(events[1][1]["outcome"], "ok")

    def test_args_are_truncated_to_two_hundred_characters(self):
        events = self._events(CmdBackground(), "長" * 260)
        self.assertEqual(events[0][1]["args"], "長" * 200)

    def test_failed_command_body_emits_no_cmd_done(self):
        # The mixin runs at_post_cmd only when func() completes, mirroring the
        # cmdhandler: a raising body leaves an unpaired cmd_in, and no
        # outcome=ok may ever be claimed for it.
        with (
            patch("commands.command.log_info") as emit,
            patch.object(CmdLore, "func", side_effect=RuntimeError("boom")),
        ):
            with self.assertRaises(RuntimeError):
                self.call(CmdLore(), "")
        events = [call.args[0] for call in emit.call_args_list]
        self.assertEqual(events, ["cmd_in"])
