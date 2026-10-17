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
from commands.combat import CmdCombatForfeit, CmdCombatRetreat
from typeclasses.rooms import Room
from world.rules.combat_session import (
    PARTY_EXIT_RETREAT,
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

    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_combat_retreat_prompts_and_its_token_confirms_the_retreat(self):
        from world.rules.combat_session import (
            engage,
            party_exit_operation_of_token,
        )

        # The party is clearly faster than its pursuer, so the confirmed
        # contested retreat succeeds deterministically.
        self.player.traits.agility.base = 200
        self.monster.traits.agility.base = 0
        engage(self.player, self.monster)
        before = read_session(self.player)
        prompt = self._run(CmdCombatRetreat, "")
        self.assertIn("撤退", prompt)
        self.assertIn(before.session_id, prompt)
        self.assertIn("combat retreat confirm", prompt)
        token = _TOKEN_PATTERN.search(prompt).group(1)
        self.assertEqual(party_exit_operation_of_token(token), PARTY_EXIT_RETREAT)
        # The bare request changed nothing.
        self.assertEqual(read_session(self.player), before)
        # Any other continuation is a cancellation: it neither settles nor
        # reports an error, and the pending prompt stays valid.
        cancelled = self._run(CmdCombatRetreat, "cancel")
        self.assertIn("用法", cancelled)
        self.assertEqual(read_session(self.player), before)
        settled = self._run(CmdCombatRetreat, f"confirm {token}")
        self.assertTrue(settled.strip())
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_stale_and_replayed_exit_tokens_settle_nothing(self):
        from world.rules.combat_session import engage
        from world.rules.player_messages import session_reason_message

        # The pursuer is far faster, so the contested retreat fails and the
        # session survives with one consumed round.
        self.player.traits.agility.base = 0
        self.monster.traits.agility.base = 500
        engage(self.player, self.monster)
        token = _TOKEN_PATTERN.search(self._run(CmdCombatRetreat, "")).group(1)
        self.assertTrue(self._run(CmdCombatRetreat, f"confirm {token}").strip())
        record = read_session(self.player)
        self.assertTrue(is_in_active_session(self.player))
        self.assertEqual(record.rounds_elapsed, 1)
        self.assertEqual(record.draft_entries, {})
        # Replaying the settled round's token is stale: the round moved past
        # it, so it can never settle a second time.
        self.assertEqual(
            self._run(CmdCombatRetreat, f"confirm {token}"),
            session_reason_message("stale_round_revision"),
        )
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        # A fresh prompt's live token settles exactly once, and the settled
        # session leaves no route to settle anything again.
        self.player.traits.agility.base = 500
        self.monster.traits.agility.base = 0
        fresh = _TOKEN_PATTERN.search(self._run(CmdCombatRetreat, "")).group(1)
        self.assertTrue(self._run(CmdCombatRetreat, f"confirm {fresh}").strip())
        self.assertIsNone(self.player.db.active_combat)
        self.assertEqual(
            self._run(CmdCombatRetreat, f"confirm {fresh}"),
            session_reason_message("no_active_session"),
        )

    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_enemy_flee_mechanism_is_untouched_by_the_exit_routes(self):
        from world.rules.combat_session import (
            CombatSessionError,
            PARTY_EXIT_OPERATIONS,
            SessionReason,
            engage,
            party_exit_operation_of_token,
            submit_player_action,
        )
        from world.rules.disengage import FLEE_SKILL_KEY

        engage(self.player, self.monster)
        before = read_session(self.player)
        token = _TOKEN_PATTERN.search(self._run(CmdCombatRetreat, "")).group(1)
        # Every exit prompt binds one of the two party operations, never an
        # individual escape, so no token can put an ally's personal flee into
        # the draft or mutate the fled set.
        self.assertEqual(party_exit_operation_of_token(token), PARTY_EXIT_RETREAT)
        self.assertNotIn("flee", PARTY_EXIT_OPERATIONS)
        self.assertFalse(read_session(self.player).fled_ids)
        # An allied personal flee stays a hard rejection in the shared facade:
        # the enemy's own disengagement policy is the only remaining flee path.
        with self.assertRaises(CombatSessionError) as caught:
            submit_player_action(self.player, FLEE_SKILL_KEY, [])
        self.assertEqual(caught.exception.args[0], SessionReason.PERSONAL_FLEE_FORBIDDEN)
        self.assertEqual(read_session(self.player), before)
