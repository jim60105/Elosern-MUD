"""Tests for companion possession writer, entry gates, and exit-path cleanup.

Pins the single-writer, mirrored, transactional possession binding
(companion-possession-core capability).
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.npcs import LLMNPC
from world.quests.catalog import register_catalog
from world.rules.affinity import AffinityRecord, AffinitySource, apply_affinity_change
from world.rules.dialogue import open_or_refresh_dialogue
from world.rules.party import (
    PartyJoinError,
    REASON_HANDBACK_FIRST,
    is_companion,
    join_party,
    leave_party,
    party_ids,
)
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_ALREADY_POSSESSING,
    REASON_DIALOGUE_OPEN,
    REASON_IN_COMBAT,
    REASON_NOT_BOUND,
    REASON_NOT_CO_LOCATED,
    PossessionGateError,
    PossessionWriteError,
    current_possession,
    enter_possession,
    release_for_party_change,
    release_on_disconnect,
    release_possession,
)


class PossessionGateMatrixTests(EvenniaTest):
    """Gate tests: every gate names its reason with zero writes."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(NPC, key="同伴A", location=self.room1)
        self.npc2 = create_object(NPC, key="同伴B", location=self.room1)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_not_bound_refused_with_zero_writes(self):
        """Scenario: Every gate names its reason with zero writes (not_bound)."""
        # npc is not bound to char1
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_NOT_BOUND)
        self.assertIn(REASON_NOT_BOUND, POSSESSION_REJECTION_MESSAGES)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_not_co_located_refused_with_zero_writes(self):
        """Scenario: Every gate names its reason with zero writes (not_co_located)."""
        join_party(self.npc, self.char1)
        self.npc.location = self.room2

        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_NOT_CO_LOCATED)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_in_combat_refused_with_zero_writes(self):
        """Scenario: Every gate names its reason with zero writes (in_combat)."""
        join_party(self.npc, self.char1)

        with patch("world.rules.combat_session.is_in_active_session", return_value=True):
            with self.assertRaises(PossessionGateError) as ctx:
                enter_possession(self.char1, self.npc)
            self.assertEqual(ctx.exception.reason, REASON_IN_COMBAT)
            self.assertIsNone(self.char1.db.possession)
            self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_dialogue_open_refused_with_zero_writes(self):
        """Scenario: Every gate names its reason with zero writes (dialogue_open)."""
        join_party(self.npc, self.char1)

        # 1. Caller in dialogue with npc
        open_or_refresh_dialogue(self.char1, self.npc, "你好")
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_DIALOGUE_OPEN)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

        # Clear char1 dialogue
        self.char1.db.dialogue_session = None

        # 2. Third party in room in dialogue with npc
        self.char2.location = self.room1
        open_or_refresh_dialogue(self.char2, self.npc, "問候")
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_DIALOGUE_OPEN)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_already_possessing_refused_with_zero_writes(self):
        """Scenario: Every gate names its reason with zero writes (already_possessing)."""
        join_party(self.npc, self.char1)
        join_party(self.npc2, self.char1)

        enter_possession(self.char1, self.npc)
        self.assertIsNotNone(self.char1.db.possession)

        # 1. Same player attempting to possess npc2
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char1, self.npc2)
        self.assertEqual(ctx.exception.reason, REASON_ALREADY_POSSESSING)

        # 2. Another player attempting to possess npc (which is already possessed)
        # with npc.db.possessed_by set:
        self.npc.db.party_member = self.char2.pk
        self.char2.db.party = [self.npc.pk]
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char2, self.npc)
        self.assertEqual(ctx.exception.reason, REASON_ALREADY_POSSESSING)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_one_account_possesses_at_most_one_npc(self):
        """Scenario: One account possesses at most one NPC."""
        join_party(self.npc, self.char1)
        join_party(self.npc2, self.char2)

        # Both characters share self.account
        self.char2.account = self.account
        self.char2.db_account = self.account
        self.char2.save()
        if hasattr(self.account, "characters"):
            self.account.characters.add(self.char2)

        enter_possession(self.char1, self.npc)

        # Attempting possession on char2 under the same account
        with self.assertRaises(PossessionGateError) as ctx:
            enter_possession(self.char2, self.npc2)
        self.assertEqual(ctx.exception.reason, REASON_ALREADY_POSSESSING)


class PossessionAtomicLifecycleTests(EvenniaTest):
    """Lifecycle tests: atomic enter/rollback, release idempotence."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(NPC, key="同伴A", location=self.room1)
        join_party(self.npc, self.char1)

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_enter_mirrors_both_surfaces_atomically(self):
        """Scenario: Enter mirrors both surfaces atomically."""
        enter_possession(self.char1, self.npc)

        possession = current_possession(self.char1)
        self.assertIsNotNone(possession)
        self.assertEqual(possession["npc_dbid"], int(self.npc.pk))
        self.assertIn("since_tick", possession)
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_failed_write_restores_both_surfaces(self):
        """Scenario: A failed write restores both in-process surfaces."""
        with patch("world.rules.possession._mount_cmdset", side_effect=RuntimeError("injected write crash")):
            with self.assertRaises(PossessionWriteError):
                enter_possession(self.char1, self.npc)

        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_release_is_idempotent(self):
        """Scenario: Release is idempotent."""
        # Player holding no possession
        self.assertIsNone(current_possession(self.char1))
        release_possession(self.char1)
        self.assertIsNone(self.char1.db.possession)

        # Enter then release
        enter_possession(self.char1, self.npc)
        release_possession(self.char1, self.npc)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

        # Second release is a clean no-op
        release_possession(self.char1, self.npc)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_foreign_npc_release_refused(self):
        """Release cannot clear another player's possession."""
        other_npc = create_object(NPC, key="他人NPC", location=self.room1)
        other_npc.db.possessed_by = self.char2.pk

        with self.assertRaises(PossessionWriteError):
            release_possession(self.char1, other_npc)

        # other_npc is still possessed by char2!
        self.assertEqual(int(other_npc.db.possessed_by), int(self.char2.pk))

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_mismatched_npc_release_refused(self):
        """Release requires canonical NPC match when supplied."""
        enter_possession(self.char1, self.npc)
        other_npc = create_object(NPC, key="無關NPC", location=self.room1)

        with self.assertRaises(PossessionWriteError):
            release_possession(self.char1, other_npc)

        # char1 still possesses self.npc
        self.assertEqual(current_possession(self.char1)["npc_dbid"], self.npc.pk)


class PossessionExitPathTests(EvenniaTest):
    """Exit-path coverage: dismissal refusal, auto-leave ordering, purge, disconnect."""

    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="同伴A", location=self.room1)
        join_party(self.npc, self.char1)

    @covers_requirement(
        "companion-possession-core::every-exit-path-releases-the-possession",
        "party-system::the-leave-command-dismisses-a-companion-without-affinity-change",
    )
    def test_dismissing_a_possessed_companion_is_refused(self):
        """Scenario: Dismissing a possessed companion is refused."""
        enter_possession(self.char1, self.npc)

        with self.assertRaises(PartyJoinError) as ctx:
            leave_party(self.npc, self.char1, reason="dismissed")
        self.assertEqual(ctx.exception.reason, REASON_HANDBACK_FIRST)

        # Attributes remain intact
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))
        self.assertIn(self.npc.pk, party_ids(self.char1))

    @covers_requirement(
        "companion-possession-core::every-exit-path-releases-the-possession",
        "party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold",
    )
    def test_auto_leave_releases_before_the_affinity_write_opens(self):
        """Scenario: Auto-leave releases before the affinity write opens."""
        # Set affinity to threshold (70)
        self.npc.relations._save(self.char1, AffinityRecord(value=70))
        self.assertEqual(self.npc.relations.affinity_for(self.char1), 70)

        enter_possession(self.char1, self.npc)
        self.assertIsNotNone(current_possession(self.char1))

        # Negative delta drops from 70 to 68
        outcome = apply_affinity_change(self.npc, self.char1, AffinitySource.TALK, -2)
        self.assertTrue(outcome.applied)
        self.assertEqual(self.npc.relations.affinity_for(self.char1), 68)

        # Possession is released!
        self.assertIsNone(current_possession(self.char1))
        self.assertIsNone(self.npc.db.possessed_by)
        # Party ended!
        self.assertFalse(is_companion(self.npc, self.char1))

    @covers_requirement(
        "companion-possession-core::every-exit-path-releases-the-possession",
        "party-system::companions-auto-leave-when-affinity-drops-below-the-invite-threshold",
    )
    def test_failed_release_aborts_auto_leave_write(self):
        """Scenario: A failed release aborts the auto-leave write."""
        self.npc.relations._save(self.char1, AffinityRecord(value=70))
        enter_possession(self.char1, self.npc)

        with patch("world.rules.possession.release_for_party_change", side_effect=RuntimeError("injected release crash")):
            with self.assertRaises(RuntimeError):
                apply_affinity_change(self.npc, self.char1, AffinitySource.TALK, -2)

        # Affinity is UNTOUCHED (still 70)!
        self.assertEqual(self.npc.relations.affinity_for(self.char1), 70)
        # Companion remains bound and possessed!
        self.assertTrue(is_companion(self.npc, self.char1))
        self.assertIsNotNone(current_possession(self.char1))
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))

    @covers_requirement(
        "companion-possession-core::every-exit-path-releases-the-possession"
    )
    def test_deletion_purge_unwinds_possession(self):
        """Scenario: Deletion purge unwinds possession."""
        enter_possession(self.char1, self.npc)

        # Delete the NPC
        self.npc.delete()

        # Possession attributes released and party unwound
        self.assertIsNone(current_possession(self.char1))
        self.assertNotIn(self.npc.pk, party_ids(self.char1))

    @covers_requirement(
        "companion-possession-core::every-exit-path-releases-the-possession"
    )
    def test_disconnect_release_is_account_keyed_and_idempotent(self):
        """Scenario: Disconnect release is account-keyed and idempotent."""
        enter_possession(self.char1, self.npc)

        release_on_disconnect(self.account)
        self.assertIsNone(current_possession(self.char1))
        self.assertIsNone(self.npc.db.possessed_by)

        # Second call is idempotent
        release_on_disconnect(self.account)
        self.assertIsNone(current_possession(self.char1))


class PossessionAutonomySilenceTests(EvenniaTest):
    """Autonomy silencing tests: talking to possessed self is refused without state."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(LLMNPC, key="對話同伴", location=self.room1)
        join_party(self.npc, self.char1)

    @covers_requirement(
        "companion-possession-core::a-possessed-npc-is-autonomy-silent-and-unreachable-by-dialogue"
    )
    def test_talking_to_possessed_self_is_refused_without_state(self):
        """Scenario: Talking to the possessed self is refused without state."""
        enter_possession(self.char1, self.npc)

        # 1. Direct LLMNPC.at_talked_to
        from unittest.mock import MagicMock
        client = MagicMock()
        with patch.object(self.char1, "msg") as msg:
            self.npc.at_talked_to("你好", self.char1, client)
        msg.assert_called_with("他現在無法回應你。")
        self.assertEqual(client.call_count, 0)
        self.assertIsNone(self.char1.db.dialogue_session)

        # 2. Freeform action adapter rejection
        from web.webclient.actions.exploration_actions import _talk_freeform_adapter
        result = _talk_freeform_adapter(self.char1, {"npc_id": int(self.npc.pk), "speech": "你好"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "possessed")
        self.assertEqual(result["message"], "他現在無法回應你。")
