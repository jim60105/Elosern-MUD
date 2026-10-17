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
from world.quests.escort_lifecycle import escort_compensation
from world.rules.party import (
    combat_companions,
    follow_companions,
    is_companion,
    join_party,
    leave_party,
    party_ids,
)
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_NOT_CO_LOCATED,
    REASON_RELEASE_REFUSED,
    REASON_TRANSFER_REFUSED,
    UNPOSSESS_REFUSED_RETURN_MESSAGE,
    PossessionGateError,
    PossessionWriteError,
    current_possession,
    enter_possession,
    release_for_party_change,
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
        # The occupied room and the logout metadata come back too.
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertEqual(self.npc.attributes.get("prelogout_location"), self.room1)
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
        npc_reloaded = LLMNPC.objects.get(id=self.npc.id)
        self.assertEqual(npc_reloaded.db_location_id, self.room1.pk)

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
        self.account.unpuppet_object(self.session)
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
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_two_session_retire_all_before_grant(self):
        """Ordering pin: with two acting sessions, all sessions retire before the single lock grant."""
        sess2 = MagicMock()
        sess2.sessid = 8888
        sess2.logged_in = True
        sess2.puppet = self.char1

        puppet_map = {self.session: self.char1, sess2: self.char1}

        def fake_puppet(session, target):
            puppet_map[session] = target
            session.puppet = target

        def fake_get_puppet(session):
            return puppet_map.get(session)

        call_order = []

        with patch.object(self.account.sessions, "all", return_value=[self.session, sess2]), \
             patch.object(self.account, "puppet_object", side_effect=fake_puppet), \
             patch.object(self.account, "get_puppet", side_effect=fake_get_puppet), \
             patch("web.webclient.actions.dispatcher.retire_sequence", side_effect=lambda s: call_order.append(("retire", s))), \
             patch("world.rules.possession._grant_puppet_lock", side_effect=lambda n, a: call_order.append(("grant", n))):
            enter_possession(self.char1, self.npc)

        # Both sessions retired
        self.assertIn(("retire", self.session), call_order)
        self.assertIn(("retire", sess2), call_order)
        self.assertIn(("grant", self.npc), call_order)

        # Both retires occur BEFORE the grant
        self.assertLess(call_order.index(("retire", self.session)), call_order.index(("grant", self.npc)))
        self.assertLess(call_order.index(("retire", sess2)), call_order.index(("grant", self.npc)))

        # Exactly ONE grant occurred
        self.assertEqual(call_order.count(("grant", self.npc)), 1)

        # Both sessions finish puppeting the NPC
        self.assertEqual(self.session.puppet, self.npc)
        self.assertEqual(sess2.puppet, self.npc)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_no_session_refusal_never_grants_puppet_lock(self):
        """If account has no live acting session, enter_possession refuses before any lock grant."""
        self.char1.sessions.remove(self.session)
        self.session.puppet = None

        with patch("world.rules.possession._grant_puppet_lock") as mock_grant:
            with self.assertRaises(PossessionGateError) as ctx:
                enter_possession(self.char1, self.npc)
            self.assertEqual(ctx.exception.reason, REASON_TRANSFER_REFUSED)
            mock_grant.assert_not_called()

        # Observable cleanup: no grant, mirrors untouched
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_multi_session_transfer_failure_rolls_back_all_sessions(self):
        """If session 1 succeeds but session 2 fails transfer, all sessions roll back to player."""
        sess2 = MagicMock()
        sess2.sessid = 7777
        sess2.logged_in = True
        sess2.puppet = self.char1
        sess2.msg = MagicMock()

        puppet_map = {self.session: self.char1, sess2: self.char1}

        def fake_puppet(session, target):
            if session == sess2 and target == self.npc:
                # Session 2 fails to puppet NPC
                return
            puppet_map[session] = target
            session.puppet = target

        def fake_get_puppet(session):
            return puppet_map.get(session)

        with patch.object(self.account.sessions, "all", return_value=[self.session, sess2]), \
             patch.object(self.account, "puppet_object", side_effect=fake_puppet), \
             patch.object(self.account, "get_puppet", side_effect=fake_get_puppet):
            with self.assertRaises(PossessionGateError) as ctx:
                enter_possession(self.char1, self.npc)
            self.assertEqual(ctx.exception.reason, REASON_TRANSFER_REFUSED)

        # Observable postconditions: both sessions rolled back to char1
        self.assertEqual(self.session.puppet, self.char1)
        self.assertEqual(sess2.puppet, self.char1)

        # Mirrors untouched / cleaned up
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

        # Puppet lock stripped
        puppet_lock = self.npc.locks.get("puppet") or ""
        self.assertNotIn(f"id({self.account.id})", puppet_lock)

        # Both sessions received the refusal message
        sess2.msg.assert_called_with(POSSESSION_REJECTION_MESSAGES[REASON_TRANSFER_REFUSED])

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

        from web.webclient.presentation import ingress

        account = self.account
        real_puppet_object = account.puppet_object
        real_synchronize = ingress.synchronize_session
        rooms_at_synchronize: list[tuple[object, object]] = []

        def _silent_refuse_return(session, target):
            if target == self.char1:
                return
            real_puppet_object(session, target)

        def _spy_synchronize(session, obj):
            rooms_at_synchronize.append((obj, self.npc.location))
            return real_synchronize(session, obj)

        with patch.object(account, "puppet_object", side_effect=_silent_refuse_return), patch(
            "web.webclient.presentation.ingress.synchronize_session", side_effect=_spy_synchronize
        ):
            with patch("world.rules.possession.log_error") as mock_log, patch(
                "world.rules.possession.log_info"
            ) as mock_info:
                with self.assertRaises(PossessionWriteError) as ctx:
                    release_possession(self.char1, npc=self.npc, reason="handback")
                self.assertEqual(ctx.exception.reason, REASON_RELEASE_REFUSED)

                # Facade logs error with step="possession_release"
                mock_log.assert_called_once()
                self.assertEqual(
                    mock_log.call_args[1].get("context", {}).get("step"),
                    "possession_release",
                )
                # No successful-release boundary event is emitted on failure.
                self.assertEqual(
                    [
                        call
                        for call in mock_info.call_args_list
                        if call.args and call.args[0] == "possession_release"
                    ],
                    [],
                )

        # The refusal path already sees the companion back in its room.
        refusal_synchronizations = [
            room for obj, room in rooms_at_synchronize if obj is self.npc
        ]
        self.assertTrue(refusal_synchronizations)
        for room in refusal_synchronizations:
            self.assertIs(room, self.room1)

        # Attributes remain set; room and metadata survive compensation.
        self.assertIsNotNone(self.char1.db.possession)
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertTrue(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")
        self.assertEqual(self.npc.attributes.get("prelogout_location"), self.room1)

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
        self.account.unpuppet_object(self.session)
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
    def test_direct_release_on_disconnect_skips_when_session_still_puppets_npc(self):
        """release_on_disconnect directly returns without releasing if a session still puppets NPC."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)

        # Calling release_on_disconnect while self.session still puppets self.npc
        release_on_disconnect(self.account)

        # Observable postconditions: mirrors, lock grant, and puppet are unchanged
        self.assertIsNotNone(self.char1.db.possession)
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
        self.assertIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")
        self.assertEqual(self.session.puppet, self.npc)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_direct_release_on_disconnect_releases_when_driving_session_unpuppets(self):
        """release_on_disconnect fully releases possession once driving session has unpuppeted."""
        enter_possession(self.char1, self.npc)
        self.account.unpuppet_object(self.session)
        self.assertIsNone(self.session.puppet)

        release_on_disconnect(self.account)

        # Observable postconditions: mirrors cleared, grant stripped, account puppeting nothing
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertNotIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")
        self.assertEqual(self.char1.sessions.count(), 0)
        self.assertEqual(self.npc.sessions.count(), 0)

    @covers_requirement(
        "companion-possession-transition::disconnecting-while-possessing-releases-possession-through-the-account-disconnect-hook"
    )
    def test_release_on_disconnect_not_blocked_by_session_puppeting_ordinary_character(self):
        """A second session puppeting an ordinary character does not block release of possessed companion."""
        enter_possession(self.char1, self.npc)

        # Session 1 (which puppeted NPC) unpuppets on disconnect
        self.account.unpuppet_object(self.session)
        self.assertIsNone(self.session.puppet)

        # Session 2 puppets an ordinary character (char2) with possessed_by = None
        sess2 = MagicMock()
        sess2.sessid = 8888
        sess2.logged_in = True
        sess2.puppet = self.char2
        self.assertIsNone(getattr(self.char2.db, "possessed_by", None))

        with patch.object(self.account.sessions, "all", return_value=[self.session, sess2]):
            release_on_disconnect(self.account)

        # Possession is released despite sess2 being connected and puppeting char2
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertNotIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")
        self.assertEqual(sess2.puppet, self.char2)

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

    # ------------------------------------------------------------------
    # Normal release preserves the companion's room presence
    # ------------------------------------------------------------------

    def _make_combat_eligible(self, hp: int = 50) -> None:
        """Give the synthetic companion a stored HP above the nonlethal floor."""
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.traits.hp.base = hp
        self.npc.traits.hp.current = hp

    def _release_for_reason(self, reason: str) -> None:
        """Run the normal release ladder for one of the two release reasons."""
        if reason == "handback":
            release_possession(self.char1, npc=self.npc, reason="handback")
        else:
            release_for_party_change(self.npc, self.char1)

    def _release_failing_after_residual_cleanup(self) -> None:
        """Run a release whose unpuppet finishes and then raises.

        The real ``_unpuppet`` completes, including the new residual cleanup, so
        the raised error exercises the compensation surface.
        """
        import world.rules.possession as possession_mod

        real_unpuppet = possession_mod._unpuppet

        def cleanup_then_raise(*args, **kwargs):
            real_unpuppet(*args, **kwargs)
            raise RuntimeError("failure injected after residual cleanup")

        with patch("world.rules.possession._unpuppet", side_effect=cleanup_then_raise):
            with self.assertRaises(PossessionWriteError):
                release_possession(self.char1, npc=self.npc, reason="handback")

    def _assert_companion_release_kept_the_room(self) -> None:
        """Shared postconditions of a co-located normal release."""
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertIn(self.char1, self.room1.contents)
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIn(self.npc.pk, party_ids(self.char1))
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertFalse(self.npc.attributes.has("prelog_location"))
        self.assertFalse(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertNotIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")
        npc_reloaded = LLMNPC.objects.get(id=self.npc.id)
        self.assertEqual(npc_reloaded.db_location_id, self.room1.pk)
        self.assertFalse(npc_reloaded.attributes.has("prelogout_location"))

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_handback_keeps_both_party_members_in_the_shared_room(self):
        """歸位 returns control without stashing the companion off-grid."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)
        self.assertIn(self.npc, self.room1.contents)
        self.assertIn(self.char1, self.room1.contents)

        release_possession(self.char1, npc=self.npc, reason="handback")

        self._assert_companion_release_kept_the_room()

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_party_change_handback_keeps_the_companion_in_the_shared_room(self):
        """release_for_party_change leaves the companion in its room and in the party."""
        enter_possession(self.char1, self.npc)

        release_for_party_change(self.npc, self.char1)

        self._assert_companion_release_kept_the_room()

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_handback_sequence_restores_the_room_before_owner_synchronization(self):
        """The release ladder keeps its order and the companion is in-room at sync."""
        enter_possession(self.char1, self.npc)

        from web.webclient.presentation import ingress

        order: list[str] = []
        room_at_synchronize: list[tuple[object, object]] = []
        real_unpuppet_object = self.account.unpuppet_object
        real_puppet_object = self.account.puppet_object
        real_synchronize = ingress.synchronize_session

        def spy_unpuppet(session):
            order.append("unpuppet")
            return real_unpuppet_object(session)

        def spy_puppet(session, target):
            order.append("puppet_owner" if target is self.char1 else "puppet_other")
            return real_puppet_object(session, target)

        def spy_synchronize(session, obj):
            order.append("synchronize")
            room_at_synchronize.append((obj, self.npc.location))
            return real_synchronize(session, obj)

        with patch.object(self.account, "unpuppet_object", side_effect=spy_unpuppet), patch.object(
            self.account, "puppet_object", side_effect=spy_puppet
        ), patch(
            "web.webclient.actions.dispatcher.retire_sequence",
            side_effect=lambda session: order.append("retire"),
        ), patch(
            "web.webclient.presentation.ingress.reset_client_sequence",
            side_effect=lambda session: order.append("reset"),
        ), patch(
            "web.webclient.presentation.ingress.send_unpuppet_transition",
            side_effect=lambda session: order.append("detach"),
        ), patch(
            "web.webclient.presentation.ingress.synchronize_session",
            side_effect=spy_synchronize,
        ):
            release_possession(self.char1, npc=self.npc, reason="handback")

        self.assertIn("detach", order)
        self.assertLess(order.index("detach"), order.index("retire"))
        self.assertLess(order.index("retire"), order.index("reset"))
        self.assertLess(order.index("reset"), order.index("unpuppet"))
        self.assertLess(order.index("unpuppet"), order.index("puppet_owner"))
        self.assertLess(order.index("puppet_owner"), order.index("synchronize"))
        owner_synchronizations = [room for obj, room in room_at_synchronize if obj is self.char1]
        self.assertTrue(owner_synchronizations)
        for room in owner_synchronizations:
            self.assertIs(room, self.room1)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_stash_then_raise_during_unpuppet_still_restores_the_room(self):
        """A hook that stashes the room and then raises cannot skip restoration."""
        enter_possession(self.char1, self.npc)
        real_unpuppet_object = self.account.unpuppet_object

        def stash_then_raise(session):
            real_unpuppet_object(session)
            raise RuntimeError("hook raised after the last-session stash")

        with patch.object(self.account, "unpuppet_object", side_effect=stash_then_raise):
            release_possession(self.char1, npc=self.npc, reason="handback")

        self._assert_companion_release_kept_the_room()

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_multi_session_handback_restores_the_original_room_for_every_attempt(self):
        """Every attempt restores the pre-release room, never a re-read one.

        The two-session ladder emulates Evennia's last-session stash per
        attempt, so a second-iteration read of the stashed location would
        restore ``None`` instead of the original room.
        """
        enter_possession(self.char1, self.npc)
        sess2 = MagicMock()
        sess2.sessid = 7777
        sess2.logged_in = True
        sess2.puppet = self.npc
        puppet_map = {self.session: self.npc, sess2: self.npc}
        room_at_repuppet: list[object] = []

        def fake_get_puppet(session):
            return puppet_map.get(session)

        def fake_puppet(session, target):
            room_at_repuppet.append(self.npc.location)
            puppet_map[session] = target
            session.puppet = target

        def fake_unpuppet(session):
            self.npc.db.prelogout_location = self.npc.location
            self.npc.location = None
            puppet_map[session] = None
            session.puppet = None

        with patch.object(
            self.account.sessions, "all", return_value=[self.session, sess2]
        ), patch.object(
            self.account, "unpuppet_object", side_effect=fake_unpuppet
        ), patch.object(
            self.account, "puppet_object", side_effect=fake_puppet
        ), patch.object(
            self.account, "get_puppet", side_effect=fake_get_puppet
        ), patch(
            "web.webclient.actions.dispatcher.retire_sequence"
        ), patch(
            "web.webclient.presentation.ingress.reset_client_sequence"
        ), patch(
            "web.webclient.presentation.ingress.send_unpuppet_transition"
        ), patch(
            "web.webclient.presentation.ingress.synchronize_session"
        ):
            release_possession(self.char1, npc=self.npc, reason="handback")

        self.assertEqual(len(room_at_repuppet), 2)
        for room in room_at_repuppet:
            self.assertIs(room, self.room1)
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_release_preserves_an_intentionally_remote_companion_position(self):
        """A companion that moved away keeps its own room; no reunion teleport."""
        enter_possession(self.char1, self.npc)
        self.npc.move_to(self.room2, quiet=True)
        self.assertIs(self.npc.location, self.room2)

        release_possession(self.char1, npc=self.npc, reason="handback")

        self.assertIs(self.npc.location, self.room2)
        self.assertEqual(self.npc.db_location_id, self.room2.pk)
        self.assertIn(self.npc, self.room2.contents)
        self.assertIs(self.char1.location, self.room1)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertTrue(is_companion(self.npc, self.char1))
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_NOT_CO_LOCATED)

    def _assert_repeat_possession_follow_and_combat(self, reason: str) -> None:
        """Both normal reasons survive repeat possession, following and collection."""
        self._make_combat_eligible()
        enter_possession(self.char1, self.npc)
        self._release_for_reason(reason)
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIs(self.npc.location, self.room1)

        # Repeat possession needs no operator repair and no intervening login.
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)
        self._release_for_reason(reason)
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIs(self.npc.location, self.room1)

        self.char1.move_to(self.room2, quiet=True)
        follow_companions(self.char1, self.room1, destination=self.room2)
        self.assertIs(self.npc.location, self.room2)
        self.assertEqual(
            [int(npc.pk) for npc in combat_companions(self.char1)],
            [int(self.npc.pk)],
        )

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_handback_allows_repeat_possession_follow_and_combat_collection(self):
        """Scenario: The released companion can be possessed again, then follows."""
        self._assert_repeat_possession_follow_and_combat("handback")

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_party_change_allows_repeat_possession_follow_and_combat_collection(self):
        """Scenario: A party-change handback leaves the same eligibility."""
        self._assert_repeat_possession_follow_and_combat("party_change")

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_membership_removal_after_release_leaves_the_companion_on_grid(self):
        """Release keeps membership; the owning removal never stashes the body."""
        enter_possession(self.char1, self.npc)

        release_for_party_change(self.npc, self.char1)

        # Release boundary: still a member, still in the shared room.
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIn(self.npc.pk, party_ids(self.char1))
        self.assertIs(self.npc.location, self.room1)

        # The owning operation then removes the legitimate source.
        leave_party(self.npc, self.char1, reason="dismissed")

        self.assertFalse(is_companion(self.npc, self.char1))
        self.assertNotIn(self.npc.pk, party_ids(self.char1))
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_failure_after_residual_cleanup_restores_room_and_logout_metadata(self):
        """The new compensation surface restores room and logout metadata."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.npc.attributes.get("prelogout_location"), self.room1)

        self._release_failing_after_residual_cleanup()

        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertTrue(self.npc.attributes.has("prelogout_location"))
        self.assertEqual(self.npc.attributes.get("prelogout_location"), self.room1)
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
        self.assertEqual(self.session.puppet, self.npc)
        self.assertTrue(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")

        # A successful retry then leaves the room and the metadata clean.
        release_possession(self.char1, npc=self.npc, reason="handback")
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertFalse(self.npc.attributes.has("prelog_location"))
        self.assertEqual(self.session.puppet, self.char1)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_rollback_restores_absent_logout_attributes(self):
        """Compensation re-removes logout Attributes that were absent at snapshot."""
        enter_possession(self.char1, self.npc)
        self.npc.attributes.remove("prelogout_location")
        self.npc.attributes.remove("prelog_location")

        self._release_failing_after_residual_cleanup()

        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertFalse(self.npc.attributes.has("prelog_location"))
        self.assertEqual(self.session.puppet, self.npc)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_rollback_restores_present_logout_attribute_values(self):
        """Compensation restores a present-None and a foreign logout target exactly."""
        enter_possession(self.char1, self.npc)
        self.npc.attributes.add("prelogout_location", None)
        self.npc.attributes.add("prelog_location", self.room2)

        self._release_failing_after_residual_cleanup()

        self.assertTrue(self.npc.attributes.has("prelogout_location"))
        self.assertIsNone(self.npc.attributes.get("prelogout_location"))
        self.assertTrue(self.npc.attributes.has("prelog_location"))
        self.assertEqual(self.npc.attributes.get("prelog_location"), self.room2)

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_outer_party_control_rollback_restores_room_and_logout_metadata(self):
        """An outer escort compensation boundary restores every companion surface."""
        enter_possession(self.char1, self.npc)

        with self.assertRaises(RuntimeError):
            with escort_compensation(self.char1, (self.npc,)):
                release_for_party_change(self.npc, self.char1)
                self.assertIs(self.npc.location, self.room1)
                raise RuntimeError("outer escort operation failed")

        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertEqual(self.npc.attributes.get("prelogout_location"), self.room1)
        self.assertEqual(self.char1.db.possession["npc_dbid"], self.npc.pk)
        self.assertEqual(self.npc.db.possessed_by, self.char1.pk)
        self.assertEqual(self.session.puppet, self.npc)
        self.assertTrue(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_release_event_records_the_reason_and_the_companion_room(self):
        """One release boundary event per reason, carrying the final room."""
        for reason in ("handback", "party_change"):
            with self.subTest(reason=reason):
                enter_possession(self.char1, self.npc)
                with patch("world.rules.possession.log_info") as info:
                    self._release_for_reason(reason)
                info.assert_called_once()
                event = info.call_args_list[0]
                self.assertEqual(event.args[0], "possession_release")
                context = event.kwargs["context"]
                self.assertEqual(context["char"], str(self.char1.pk))
                self.assertEqual(context["npc"], str(self.npc.pk))
                self.assertEqual(context["reason"], reason)
                self.assertEqual(context["room"], str(self.room1.pk))

    @covers_requirement(
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_repeated_release_is_a_noop_without_a_duplicate_event(self):
        """A repeated normal release moves nothing and logs nothing."""
        enter_possession(self.char1, self.npc)
        release_possession(self.char1, npc=self.npc, reason="handback")
        party_before = party_ids(self.char1)
        location_before = self.npc.location

        with patch("world.rules.possession.log_info") as info:
            release_possession(self.char1, npc=self.npc, reason="handback")

        info.assert_not_called()
        self.assertIs(self.npc.location, location_before)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertEqual(party_ids(self.char1), party_before)
        self.assertIsNone(self.npc.db.possessed_by)

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
        # The owner's body stays physically in the room while possessed.
        self.assertIn(self.char1, self.room1.contents)
        self.assertIn(self.npc, self.room1.contents)

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
        self.assertIn(self.char1, self.room1.contents)
        self.assertIn(self.npc, self.room1.contents)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))


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
        "companion-possession-transition::releasing-possession-returns-the-puppet-to-the-owner-with-the-same-ladder"
    )
    def test_unpossess_command_keeps_the_companion_in_the_shared_room(self):
        """The 歸位 command returns control without stashing the companion."""
        enter_possession(self.char1, self.npc)
        self.assertEqual(self.session.puppet, self.npc)
        self.assertIn(self.npc, self.room1.contents)

        cmd = CmdUnpossess()
        cmd.caller = self.npc
        cmd.session = self.session
        cmd.args = ""
        cmd.raw_string = "unpossess"
        with patch.object(self.npc, "msg"):
            cmd.func()

        self.assertEqual(self.session.puppet, self.char1)
        self.assertIs(self.npc.location, self.room1)
        self.assertEqual(self.npc.db_location_id, self.room1.pk)
        self.assertIn(self.npc, self.room1.contents)
        self.assertIn(self.char1, self.room1.contents)
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIn(self.npc.pk, party_ids(self.char1))
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertFalse(self.npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertNotIn(f"id({self.account.id})", self.npc.locks.get("puppet") or "")

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
