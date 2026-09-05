"""Tests for companion possession control transition (companion-possession-transition).

Pins the real puppet-transfer ladder, dynamic cmdset mount, account disconnect
hook, and entranced rendering.
"""

from unittest.mock import MagicMock, call, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.default_cmdsets import POSSESSED_DENYLIST, CharacterCmdSet, PossessedCharacterCmdSet
from commands.possess import CmdUnpossess
from tools.spec_traceability import covers_requirement
from typeclasses.characters import Character, PlayerCharacter
from typeclasses.npcs import NPC, LLMNPC
from world.quests.catalog import register_catalog
from world.rules.party import join_party
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_RELEASE_REFUSED,
    REASON_TRANSFER_REFUSED,
    UNPOSSESS_REFUSED_RETURN_MESSAGE,
    PossessionGateError,
    PossessionWriteError,
    current_possession,
    enter_possession,
    release_on_disconnect,
    release_possession,
)


class PossessionTransitionTests(EvenniaTest):
    """Integration tests for companion possession control transfer."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(LLMNPC, key="同伴小艾", location=self.room1)
        join_party(self.npc, self.char1)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_verified_possession_swap_leaves_npc_puppeted_and_char_released(self):
        """Scenario: A verified possession swap leaves B puppeted and A released."""
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIn(self.session, self.char1.sessions.all())

        enter_possession(self.char1, self.npc)

        # B is now puppeted by the session
        self.assertEqual(self.session.puppet, self.npc)
        self.assertIn(self.session, self.npc.sessions.all())

        # A's sessions are now empty
        self.assertEqual(self.char1.sessions.count(), 0)

        # NPC's lock contains the account grant alongside its default rule
        puppet_lock = self.npc.locks.get("puppet")
        self.assertIn(f"id({self.account.id})", puppet_lock)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_silent_refusal_leaves_world_byte_identical(self):
        """Scenario: A silent refusal leaves the world exactly as it was."""
        account = self.account
        real_puppet_object = account.puppet_object

        def _silent_refuse(session, target):
            if target == self.npc:
                # Silently do not attach target
                return
            real_puppet_object(session, target)

        with patch.object(account, "puppet_object", side_effect=_silent_refuse):
            with self.assertRaises(PossessionGateError) as ctx:
                enter_possession(self.char1, self.npc)
            self.assertEqual(ctx.exception.reason, REASON_TRANSFER_REFUSED)

        # A is re-puppeted on the session
        self.assertEqual(self.session.puppet, self.char1)

        # Lock grant is stripped from NPC
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)

        # Possession attributes are cleared
        self.assertIsNone(self.char1.db.possession)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_injected_mirror_write_failure_during_release_triggers_inverse_compensation(self):
        """If mirror write raises after unpuppet, full inverse compensation restores B."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Patch ObjectDB select_for_update inside release_possession to simulate DB failure after unpuppet
        import world.rules.possession as possession_mod
        real_unpuppet = possession_mod._unpuppet

        def _unpuppet_then_fail(*args, **kwargs):
            real_unpuppet(*args, **kwargs)
            raise RuntimeError("simulated DB failure on mirror clear")

        with patch("world.rules.possession._unpuppet", side_effect=_unpuppet_then_fail):
            with self.assertRaises(PossessionWriteError):
                release_possession(self.char1, npc=self.npc, reason="handback")

        # Control was compensated back to npc
        self.assertEqual(self.session.puppet, self.npc)
        self.assertIn(f"id({self.account.id})", self.npc.locks.get("puppet"))
        self.assertTrue(self.npc.cmdset.has(PossessedCharacterCmdSet))

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_partial_mirror_repair_performs_full_lifecycle_cleanup(self):
        """If player mirror is missing but NPC has possessed_by, repair cleans cmdset, lock, and sessions."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Simulate inconsistent state: player mirror corrupted/missing
        self.char1.db.possession = None

        # release_possession called with player holding no possession
        release_possession(self.char1, npc=self.npc, reason="handback")

        # NPC mirror cleared
        self.assertIsNone(self.npc.db.possessed_by)

        # Lock stripped and cmdset unmounted
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)
        self.assertFalse(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertEqual(self.npc.sessions.count(), 0)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_enter_possession_requires_live_session_when_account_present(self):
        """If account has no live acting session, enter_possession rejects with transfer_refused."""
        # Remove session from char1
        self.char1.sessions.remove(self.session)
        self.session.puppet = None
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_TRANSFER_REFUSED)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_multisession_disconnect_only_releases_when_controlling_session_leaves(self):
        """Disconnect of an auxiliary OOC session does NOT release possession if NPC session is live."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Create a second session for this account (OOC session)
        sess2 = MagicMock()
        sess2.sessid = 9999
        sess2.logged_in = True
        sess2.puppet = None

        with patch.object(self.account.sessions, "all", return_value=[self.session, sess2]):
            # Disconnect sess2 (account remains connected with sess1 puppeting NPC)
            self.account.is_connected = True
            self.account.at_post_disconnect()

            # Possession is NOT released because sess1 still puppets NPC
            self.assertIsNotNone(self.char1.db.possession)
            self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
            self.assertEqual(self.session.puppet, self.npc)

        # Now sess1 disconnects
        self.account.is_connected = False
        self.account.at_post_disconnect()

        # Now possession IS released
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::the-possessed-npc-carries-a-trimmed-character-act-cmdset"
    )
    def test_switcher_commands_masked_with_rejection_message_while_possessing(self):
        """Typing ooc while possessing hits CmdBlockedUnderPossession."""
        enter_possession(self.char1, self.npc)
        current_cmdset = self.npc.cmdset.current
        ooc_cmds = [c for c in current_cmdset if c.key == "ooc"]
        self.assertTrue(len(ooc_cmds) > 0)
        ooc_cmds[0].caller = self.npc
        ooc_cmds[0].session = self.session
        with patch.object(self.npc, "msg") as mock_msg:
            ooc_cmds[0].func()
            self.assertEqual(
                mock_msg.call_args.kwargs.get("text") or mock_msg.call_args.args[0],
                "附身狀態下無法執行此操作，請先歸位（unpossess）。",
            )

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_unpossess_command_executed_from_account_caller_in_ooc_state(self):
        """An account caller without a puppet can invoke unpossess to release an active possession."""
        enter_possession(self.char1, self.npc)
        cmd = CmdUnpossess()
        cmd.caller = self.account
        cmd.session = self.session
        cmd.args = ""
        cmd.raw_string = "unpossess"
        with patch.object(self.account, "msg") as mock_msg:
            cmd.func()
            mock_msg.assert_called_with("你的意識回到了自己的身體。")
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_epoch_retires_before_swap(self):
        """Scenario: The epoch retires before the swap."""
        call_order = []

        with patch(
            "web.webclient.actions.dispatcher.retire_sequence",
            side_effect=lambda s: call_order.append("retire"),
        ), patch(
            "web.webclient.presentation.ingress.reset_client_sequence",
            side_effect=lambda s: call_order.append("reset"),
        ), patch(
            "web.webclient.presentation.ingress.send_unpuppet_transition",
            side_effect=lambda s: call_order.append("detach_signal"),
        ), patch.object(
            self.account,
            "puppet_object",
            side_effect=lambda s, o: (call_order.append("puppet"), super(type(self.account), self.account).puppet_object(s, o)),
        ):
            enter_possession(self.char1, self.npc)

        self.assertIn("retire", call_order)
        self.assertIn("reset", call_order)
        self.assertIn("puppet", call_order)
        self.assertLess(call_order.index("retire"), call_order.index("puppet"))
        self.assertLess(call_order.index("reset"), call_order.index("puppet"))

    @covers_requirement(
        "companion-possession-transition::the-possessed-npc-carries-a-trimmed-character-act-cmdset"
    )
    def test_unpossess_is_reachable_while_possessing(self):
        """Scenario: 歸位 is reachable while possessing."""
        enter_possession(self.char1, self.npc)
        current_cmdset = self.npc.cmdset.current

        # unpossess and 歸位 resolve within it
        match_unpossess = [c for c in current_cmdset if c.key == "unpossess"]
        self.assertTrue(len(match_unpossess) > 0)
        self.assertIn("歸位", match_unpossess[0].aliases)

    @covers_requirement(
        "companion-possession-transition::the-possessed-npc-carries-a-trimmed-character-act-cmdset"
    )
    def test_switcher_family_is_absent_while_possessing(self):
        """Scenario: The switcher family is absent while possessing."""
        enter_possession(self.char1, self.npc)
        current_cmdset = self.npc.cmdset.current

        # Denylist membership is pinned against CharacterCmdSet
        for denylisted_cls in POSSESSED_DENYLIST:
            matches = [c for c in current_cmdset if isinstance(c, denylisted_cls)]
            self.assertEqual(
                len(matches),
                0,
                f"Command {denylisted_cls} from POSSESSED_DENYLIST must be absent from mounted cmdset",
            )

    @covers_requirement(
        "companion-possession-transition::the-possessed-npc-carries-a-trimmed-character-act-cmdset"
    )
    def test_release_restores_the_npcs_own_cmdset(self):
        """Scenario: Release restores the NPC's own cmdset."""
        enter_possession(self.char1, self.npc)
        self.assertTrue(self.npc.cmdset.has(PossessedCharacterCmdSet))

        release_possession(self.char1, npc=self.npc, reason="handback")
        self.assertFalse(self.npc.cmdset.has(PossessedCharacterCmdSet))

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_clean_release_leaves_a_puppeted_and_b_lock_free(self):
        """Scenario: A clean release leaves A puppeted and B lock-free."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        release_possession(self.char1, npc=self.npc, reason="handback")

        # Session puppets A again
        self.assertEqual(self.session.puppet, self.char1)

        # NPC holds no account grant
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)

        # Possession attributes are clear
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_refused_return_keeps_the_state_and_says_so(self):
        """Scenario: A refused return keeps the state and says so."""
        enter_possession(self.char1, self.npc)

        account = self.account
        real_puppet_object = account.puppet_object

        def _silent_refuse_return(session, target):
            if target == self.char1:
                return
            real_puppet_object(session, target)

        with patch.object(account, "puppet_object", side_effect=_silent_refuse_return):
            with patch("world.rules.possession.log_error") as mock_log:
                with self.assertRaises(PossessionWriteError) as ctx:
                    release_possession(self.char1, npc=self.npc, reason="handback")
                self.assertEqual(ctx.exception.reason, REASON_RELEASE_REFUSED)

                # Facade logs error with step="possession_release"
                mock_log.assert_called_once()
                self.assertEqual(
                    mock_log.call_args[1].get("context", {}).get("step"),
                    "possession_release",
                )

        # Attributes remain set
        self.assertIsNotNone(self.char1.db.possession)
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)

        # Idempotent retry completes return
        release_possession(self.char1, npc=self.npc, reason="handback")
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_disconnect_drops_the_puppet_and_the_state_together(self):
        """Scenario: Disconnect drops the puppet and the state together."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Simulate disconnect of the account
        self.account.is_connected = False
        self.account.at_post_disconnect()

        # NPC is unpuppeted, grant stripped, attributes cleared
        self.assertEqual(self.npc.sessions.count(), 0)
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

        # A is not force-puppeted anywhere
        self.assertEqual(self.char1.sessions.count(), 0)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_possession_internal_unpuppet_never_triggers_the_release(self):
        """Scenario: A possession-internal unpuppet never triggers the release."""
        enter_possession(self.char1, self.npc)

        # Evennia unpuppet_object called internally during character actions does NOT clear possession
        self.account.unpuppet_object(self.session)
        self.assertIsNotNone(self.char1.db.possession)
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_reload_preserves_a_live_possession(self):
        """Scenario: Reload preserves a live possession."""
        enter_possession(self.char1, self.npc)

        # Save and reload simulation (re-read from DB)
        char_reloaded = Character.objects.get(id=self.char1.id)
        npc_reloaded = LLMNPC.objects.get(id=self.npc.id)

        self.assertIsNotNone(char_reloaded.db.possession)
        self.assertEqual(npc_reloaded.db.possessed_by, self.char1.pk)
        self.assertIn(f"id({self.account.id})", npc_reloaded.locks.get("puppet"))

    @covers_requirement(
        "companion-possession-transition::a-possessed-character-reads-as-entranced-in-the-room"
    )
    def test_left_behind_body_shows_entranced_and_clears_after_release(self):
        """Scenario: The left-behind body shows entranced; normal presence after release."""
        # Pre-possession: normal display
        name_normal = self.char1.get_display_name(self.char2)
        self.assertNotIn("呆立入神", name_normal)

        # Possessing: entranced line renders with character
        enter_possession(self.char1, self.npc)
        name_entranced = self.char1.get_display_name(self.char2)
        self.assertIn("呆立入神", name_entranced)
        self.assertEqual(name_entranced, f"{self.char1.name}（呆立入神）")

        desc_entranced = self.char1.get_display_desc(self.char2)
        self.assertIn("呆立入神", desc_entranced)

        # Room character listing includes entranced marker
        room_chars = self.room1.get_display_characters(self.char2)
        self.assertIn("呆立入神", room_chars)

        # Post-release: normal presence restored
        release_possession(self.char1, npc=self.npc, reason="handback")
        name_after = self.char1.get_display_name(self.char2)
        self.assertNotIn("呆立入神", name_after)
        room_chars_after = self.room1.get_display_characters(self.char2)
        self.assertNotIn("呆立入神", room_chars_after)


class PossessionTransitionCommandTests(EvenniaTest):
    """Integration tests for possession commands under real puppet transfer."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(LLMNPC, key="同伴小艾", location=self.room1)
        join_party(self.npc, self.char1)

    @covers_requirement(
        "companion-possession-transition::the-possessed-npc-carries-a-trimmed-character-act-cmdset"
    )
    def test_unpossess_command_executed_from_possessed_npc_caller(self):
        """When player is possessing NPC, self.caller on CmdUnpossess is the NPC."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Caller is the NPC!
        cmd = CmdUnpossess()
        cmd.caller = self.npc
        cmd.session = self.session
        cmd.args = ""
        cmd.raw_string = "unpossess"

        with patch.object(self.npc, "msg") as mock_msg:
            cmd.func()
            mock_msg.assert_called_with("你的意識回到了自己的身體。")

        # Session returned to char1
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_enter_possession_post_transfer_failure_compensates_all_surfaces(self):
        """If failure occurs after puppet transfer (e.g. mount error), state is compensated."""
        with patch("world.rules.possession._mount_cmdset", side_effect=RuntimeError("mount failed")):
            with self.assertRaises(PossessionWriteError):
                enter_possession(self.char1, self.npc)

        # Puppet restored to char1
        self.assertEqual(self.session.puppet, self.char1)

        # Lock grant stripped
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)

        # Cmdset unmounted
        self.assertFalse(self.npc.cmdset.has(PossessedCharacterCmdSet))

        # Attributes clean
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_orphan_npc_release_repairs_player_without_raising(self):
        """If target NPC was deleted, release repairs player possession mirror cleanly."""
        enter_possession(self.char1, self.npc)
        npc_id = self.npc.id

        # Delete the NPC directly to create orphan state
        self.npc.delete()

        # release_possession should repair player mirror without raising
        release_possession(self.char1, reason="handback")
        self.assertIsNone(self.char1.db.possession)
