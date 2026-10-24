"""Tests for companion possession writer, entry gates, and exit-path cleanup.

Pins the single-writer, mirrored, transactional possession binding
(companion-possession-core capability).
"""

from unittest.mock import patch
from types import SimpleNamespace

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
from world.rules.clock import get_world_clock
from world.rules.buffs import apply_buff
from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state
from world.rules.possession import (
    POSSESSION_REJECTION_MESSAGES,
    REASON_ALREADY_POSSESSING,
    REASON_DIALOGUE_OPEN,
    REASON_IN_COMBAT,
    REASON_NOT_BOUND,
    REASON_NOT_CO_LOCATED,
    REASON_NOT_POSSESSING,
    REASON_NOT_SLEEPING,
    REASON_SESSION_MISMATCH,
    REASON_STALE_HANDOFF,
    SLEEP_HANDOFF_POSSESS,
    SLEEP_HANDOFF_RETURN,
    PossessionGateError,
    PossessionWriteError,
    confirm_sleep_handoff,
    current_possession,
    enter_possession,
    release_for_party_change,
    release_on_disconnect,
    release_possession,
    sleep_handoff_candidates,
)
from world.rules.time_skip import (
    accepted_wait_handoff_offer,
    advance_wait,
    continue_sleep,
    enter_sleep,
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
        self.char2.db.party_meta = {str(self.npc.pk): {"general": True, "reasons": []}}
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
        register_catalog()
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

        self.account.unpuppet_object(self.session)
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


class SleepHandoffTests(EvenniaTest):
    """Contextual sleep-driven handoff: candidates, confirmation, staleness."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()
        # A real accepted recovery plan needs unmet reserve; a full body now
        # reconciles awake at zero elapsed time instead of holding a pose.
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)

    def _companion(self, key="同伴"):
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        write_fatigue_state(npc, 180000, SleepPosture.AWAKE)
        return npc

    def _sleeping_possession(self):
        """Possess a companion and commit its voluntary sleep at zero time."""
        sleeper = self._companion("沉睡者")
        enter_possession(self.player, sleeper)
        before = int(get_world_clock().tick)
        entry = enter_sleep(sleeper)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY)
        return sleeper, entry

    def _transition_id(self, sleeper):
        return sleep_handoff_candidates(
            self.account, self.player, sleeper
        ).transition_id

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_sleep_entry_offers_the_awake_owner_as_a_return_choice(self):
        sleeper, entry = self._sleeping_possession()
        self.assertTrue(entry.handoff_offered)
        self.assertEqual(
            [candidate.kind for candidate in entry.handoff_candidates],
            [SLEEP_HANDOFF_RETURN],
        )
        owner = entry.handoff_candidates[0]
        self.assertEqual(owner.dbid, int(self.player.pk))
        self.assertEqual(owner.reserve_percent, 50)
        # Entry alone never takes control away from the selected body.
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(sleeper.pk))
        options = sleep_handoff_candidates(
            self.account, self.player, sleeper, session=self.session
        )
        self.assertTrue(options.available)
        self.assertEqual(options.transition_id, self._transition_id(sleeper))

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_unselected_sleep_never_steals_control(self):
        sleeper, _entry = self._sleeping_possession()
        awake = self._companion("清醒者")
        # An explicitly selected, uncontrolled member sleeps without an offer.
        unselected_entry = enter_sleep(self.player, member_id=int(awake.pk))
        self.assertFalse(unselected_entry.handoff_offered)
        self.assertEqual(unselected_entry.handoff_candidates, ())
        self.assertIs(read_fatigue_state(awake).posture, SleepPosture.VOLUNTARY)
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(sleeper.pk))
        self.assertEqual(self.session.puppet, sleeper)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_owner_wake_never_steals_control(self):
        witness = self._companion("見證者")
        self.assertIsNone(current_possession(self.player))
        owner_entry = enter_sleep(self.player)
        self.assertTrue(owner_entry.handoff_offered)
        self.assertEqual(
            [candidate.dbid for candidate in owner_entry.handoff_candidates],
            [int(witness.pk)],
        )
        continue_sleep(self.player, owner_entry)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertIsNone(current_possession(self.player))
        self.assertEqual(self.session.puppet, self.player)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_forged_account_and_foreign_session_are_refused(self):
        sleeper, _entry = self._sleeping_possession()
        forged = SimpleNamespace(pk=987654)
        options = sleep_handoff_candidates(forged, self.player, sleeper)
        self.assertFalse(options.available)
        self.assertEqual(options.reason, REASON_SESSION_MISMATCH)
        foreign_session = SimpleNamespace(
            logged_in=True, puppet=self.player, account=self.account
        )
        options = sleep_handoff_candidates(
            self.account, self.player, sleeper, session=foreign_session
        )
        self.assertFalse(options.available)
        self.assertEqual(options.reason, REASON_SESSION_MISMATCH)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_stale_or_ineligible_candidates_are_rejected_with_current_choices(self):
        sleeper, _entry = self._sleeping_possession()
        candidate = self._companion("候選者")
        transition_id = self._transition_id(sleeper)
        options = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertIn(
            (int(candidate.pk), SLEEP_HANDOFF_POSSESS),
            [(item.dbid, item.kind) for item in options.candidates],
        )

        candidate.location = self.room2
        with self.assertRaises(PossessionGateError) as ctx:
            confirm_sleep_handoff(
                self.account,
                self.player,
                sleeper,
                int(candidate.pk),
                transition_id=transition_id,
            )
        self.assertEqual(ctx.exception.reason, REASON_STALE_HANDOFF)
        self.assertEqual(
            [item.dbid for item in ctx.exception.candidates], [int(self.player.pk)]
        )
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(sleeper.pk))

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_wake_and_resleep_change_the_transition_identity(self):
        sleeper, entry = self._sleeping_possession()
        first = self._transition_id(sleeper)
        continue_sleep(sleeper, entry)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.AWAKE)
        write_fatigue_state(sleeper, 180000, SleepPosture.AWAKE)
        enter_sleep(sleeper)
        self.assertNotEqual(first, self._transition_id(sleeper))
        with self.assertRaises(PossessionGateError) as ctx:
            confirm_sleep_handoff(
                self.account,
                self.player,
                sleeper,
                int(self.player.pk),
                transition_id=first,
            )
        self.assertEqual(ctx.exception.reason, REASON_STALE_HANDOFF)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_return_confirmation_hands_control_back_to_the_owner(self):
        sleeper, _entry = self._sleeping_possession()
        confirm_sleep_handoff(
            self.account,
            self.player,
            sleeper,
            int(self.player.pk),
            transition_id=self._transition_id(sleeper),
            session=self.session,
        )
        self.assertIsNone(current_possession(self.player))
        self.assertIsNone(sleeper.db.possessed_by)
        self.assertEqual(self.session.puppet, self.player)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY)
        self.assertEqual(sleeper.location, self.room1)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work",
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder",
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_ordinary_combat_gate_stays_while_contextual_handoff_is_lawful(self):
        sleeper, _entry = self._sleeping_possession()
        candidate = self._companion("接手者")
        before = int(get_world_clock().tick)
        with patch("world.rules.combat_session.is_in_active_session", return_value=True):
            with self.assertRaises(PossessionGateError) as ctx:
                enter_possession(self.player, candidate)
            self.assertEqual(ctx.exception.reason, REASON_IN_COMBAT)
            confirm_sleep_handoff(
                self.account,
                self.player,
                sleeper,
                int(candidate.pk),
                transition_id=self._transition_id(sleeper),
                session=self.session,
            )
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(candidate.pk))
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.VOLUNTARY)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_sleeping_owner_can_hand_control_to_an_awake_companion(self):
        awake = self._companion("清醒同伴")
        entry = enter_sleep(self.player)
        self.assertTrue(entry.handoff_offered)
        self.assertEqual(
            [(item.dbid, item.kind) for item in entry.handoff_candidates],
            [(int(awake.pk), SLEEP_HANDOFF_POSSESS)],
        )
        confirm_sleep_handoff(
            self.account,
            self.player,
            self.player,
            int(awake.pk),
            transition_id=self._transition_id(self.player),
        )
        self.assertEqual(current_possession(self.player)["npc_dbid"], int(awake.pk))
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY)
        options = sleep_handoff_candidates(self.account, self.player, awake)
        self.assertFalse(options.available)
        self.assertEqual(options.reason, REASON_NOT_SLEEPING)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_awake_controlled_body_reports_not_sleeping(self):
        sleeper = self._companion("清醒的同伴")
        enter_possession(self.player, sleeper)
        options = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertFalse(options.available)
        self.assertEqual(options.reason, REASON_NOT_SLEEPING)
        self.assertIsNone(options.transition_id)
        # Not controlling the body at all is its own stable reason.
        other = self._companion("另一位同伴")
        options = sleep_handoff_candidates(self.account, self.player, other)
        self.assertEqual(options.reason, REASON_NOT_POSSESSING)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_forced_sleep_episode_identity_never_replays(self):
        sleeper, entry = self._sleeping_possession()
        continue_sleep(sleeper, entry)
        write_fatigue_state(sleeper, 0, SleepPosture.FORCED)
        first = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertTrue(first.available)
        self.assertIn(
            int(self.player.pk), [candidate.dbid for candidate in first.candidates]
        )

        # A forced sleeper wakes only after elapsed time; the next collapse runs
        # in a later episode and cannot reuse the captured identity.
        advance_wait(self.player, 6000)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.AWAKE)
        write_fatigue_state(sleeper, 0, SleepPosture.FORCED)
        second = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertNotEqual(first.transition_id, second.transition_id)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_action_locked_candidate_is_not_lawful(self):
        sleeper, _entry = self._sleeping_possession()
        candidate = self._companion("麻痺者")
        options = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertIn(int(candidate.pk), [item.dbid for item in options.candidates])
        apply_buff(candidate, "paralysis")
        options = sleep_handoff_candidates(self.account, self.player, sleeper)
        self.assertNotIn(int(candidate.pk), [item.dbid for item in options.candidates])
        with self.assertRaises(PossessionGateError) as ctx:
            confirm_sleep_handoff(
                self.account,
                self.player,
                sleeper,
                int(candidate.pk),
                transition_id=options.transition_id,
            )
        self.assertEqual(ctx.exception.reason, REASON_STALE_HANDOFF)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work",
        "time-skip-commands::recovery-waiting-preserves-skip-safety",
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_accepted_wait_offers_handoff_after_a_forced_collapse(self):
        sleeper = self._companion("力竭者")
        enter_possession(self.player, sleeper)
        write_fatigue_state(sleeper, 24, SleepPosture.AWAKE)
        advance_wait(self.player, 60)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.FORCED)
        offer = accepted_wait_handoff_offer(sleeper)
        self.assertIsNotNone(offer)
        self.assertIn("回到自己的身體", offer)
        self.assertIn("精神儲備", offer)
