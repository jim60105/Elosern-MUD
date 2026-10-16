"""The confirming text routes for the party exit (tasks 3.1 and 4.1).

Both entry points are exercised as the player meets them: a bare
``combat forfeit`` returns the party-scope prompt and mutates nothing, the
prompt's own token is what settles, a forged token settles nothing, and an
in-session ``cast flee`` reaches the same boundary without any individual
escape.
"""

from tools.spec_traceability import covers_requirement

import re

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from commands.action import CmdCast
from commands.combat import CmdCombatForfeit
from typeclasses.rooms import Room
from world.rules.combat_session import (
    is_in_active_session,
    read_session,
)
from world.rules.tests._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)

_TOKEN_PATTERN = re.compile(r"confirm ([A-Z0-9]+-[0-9]+-[0-9A-F]{20})")


class CombatExitCommandTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(
            self, "skills", "elements", "items", "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.room = create_object(Room, key="exit command room")
        self.player = _player("exit commander")
        self.player.location = self.room
        self.monster = _monster("exit command goblin")
        self.monster.location = self.room
        self.sent: list[str] = []
        self.player.msg = lambda text="", **kwargs: self.sent.append(str(text))

    def _run(self, command_class, args=""):
        command = command_class()
        command.caller = self.player
        command.args = args
        self.sent.clear()
        command.func()
        return "\n".join(self.sent)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_a_bare_forfeit_returns_the_prompt_and_mutates_nothing(self):
        from world.rules.combat_session import engage

        engage(self.player, self.monster)
        record = read_session(self.player)
        before = read_session(self.player)
        text = self._run(CmdCombatForfeit, "")
        self.assertIn("投降", text)
        self.assertIn(record.session_id, text)
        match = _TOKEN_PATTERN.search(text)
        self.assertIsNotNone(match, text)
        # The bare invocation only prompted: the draft, the revision and the
        # session are exactly where they were.
        self.assertEqual(read_session(self.player), before)
        self.assertTrue(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_the_prompted_token_settles_while_a_forged_token_does_not(self):
        from world.rules.combat_session import engage

        engage(self.player, self.monster)
        text = self._run(CmdCombatForfeit, "")
        token = _TOKEN_PATTERN.search(text).group(1)
        forged = "S-0-" + "0" * 20
        self.assertNotEqual(forged, token)
        from world.rules.player_messages import session_reason_message

        message = self._run(CmdCombatForfeit, f"confirm {forged}")
        self.assertEqual(
            message,
            session_reason_message("invalid_confirmation_token"),
        )
        self.assertTrue(is_in_active_session(self.player))
        message = self._run(CmdCombatForfeit, f"confirm {token}")
        self.assertTrue(message.strip())
        self.assertNotEqual(
            message, session_reason_message("invalid_confirmation_token")
        )
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_in_session_flee_reaches_the_party_boundary_without_escaping(self):
        from world.rules.combat_session import engage

        engage(self.player, self.monster)
        before = read_session(self.player)
        text = self._run(CmdCast, "flee")
        self.assertIn("撤退", text)
        self.assertIn(before.session_id, text)
        self.assertIsNotNone(_TOKEN_PATTERN.search(text), text)
        current = read_session(self.player)
        self.assertEqual(current.draft_entries, {})
        self.assertEqual(current.round_revision, before.round_revision)
        self.assertEqual(current.rounds_elapsed, 0)
        self.assertTrue(is_in_active_session(self.player))
