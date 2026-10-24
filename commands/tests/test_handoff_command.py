"""Command tests for the sleep-driven control handoff (``handoff``/``交接``).

Pins the text surface of a committed voluntary sleep: the listed choices with
their reserve percentage and return-versus-possess meaning, confirmation of the
exact listed choice, zero-time cancel, stale relisting, and the unchanged
non-acting restrictions of the sleeping body.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.possess import CmdHandoff
from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.rules.clock import get_world_clock
from world.rules.fatigue import (
    FatigueRejectReason,
    FatigueStateError,
    SleepPosture,
    foot_speed_scale,
    read_fatigue_state,
    write_fatigue_state,
)
from world.rules.party import join_party
from world.rules.party_scope import REASON_MEMBER_ASLEEP, PartyScopeError
from world.rules.possession import current_possession, enter_possession
from world.rules.time_skip import enter_sleep


class HandoffCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """Scenario tests for the sleeping-body handoff command."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        self.sleeper = create_object(NPC, key="沉睡同伴", location=self.room1)
        self.sleeper.race = "human"
        self.sleeper.apply_race_baseline()
        join_party(self.sleeper, self.player)
        # Half reserve with full gauges: the voluntary entry must keep a real
        # recovery target instead of being reconciled back to awake, so this
        # fixture stays valid under the per-body sleep receipt lifecycle.
        write_fatigue_state(self.sleeper, 180000, SleepPosture.AWAKE)
        self.candidate = create_object(NPC, key="清醒同伴", location=self.room1)
        self.candidate.race = "human"
        self.candidate.apply_race_baseline()
        join_party(self.candidate, self.player)
        write_fatigue_state(self.candidate, 360000, SleepPosture.AWAKE)
        enter_possession(self.player, self.sleeper)
        entry = enter_sleep(self.sleeper)
        self.assertTrue(entry.handoff_offered)

    def _listing(self):
        return self.call(CmdHandoff(), "", caller=self.sleeper)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_handoff_lists_fatigue_and_return_or_possess_meaning(self):
        output = self._listing()
        self.assertIn("1. 回到自己的身體（精力 100%）", output)
        self.assertIn(f"2. 接手 清醒同伴（精力 100%）", output)
        self.assertIn("handoff <編號>", output)
        self.assertEqual(
            self.session.ndb.sleep_handoff_listing[1],
            (
                (int(self.player.pk), True),
                (int(self.candidate.pk), True),
            ),
        )

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_handoff_confirms_the_exact_listed_candidate_at_zero_time(self):
        self._listing()
        before = int(get_world_clock().tick)
        output = self.call(CmdHandoff(), "2", caller=self.sleeper)
        self.assertIn("你接手了清醒同伴的身體。", output)
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(self.candidate.pk)
        )
        self.assertEqual(self.session.puppet, self.candidate)
        self.assertIsNone(self.sleeper.db.possessed_by)
        self.assertIs(read_fatigue_state(self.sleeper).posture, SleepPosture.VOLUNTARY)
        self.assertEqual(int(get_world_clock().tick), before)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_handoff_cancel_keeps_control_and_passes_no_time(self):
        self._listing()
        before = int(get_world_clock().tick)
        output = self.call(CmdHandoff(), "cancel", caller=self.sleeper)
        self.assertIn("你取消了交接，控制權沒有改變。", output)
        self.assertIn("取消", self.call(CmdHandoff(), "取消", caller=self.sleeper))
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(self.sleeper.pk)
        )
        self.assertEqual(self.session.puppet, self.sleeper)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertIsNone(self.session.ndb.sleep_handoff_listing)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_handoff_without_a_fresh_listing_rejects_stale_choices(self):
        before = int(get_world_clock().tick)
        output = self.call(CmdHandoff(), "1", caller=self.sleeper)
        self.assertIn("交接選項已經失效", output)
        self.assertIn("回到自己的身體", output)
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(self.sleeper.pk)
        )
        self.assertEqual(int(get_world_clock().tick), before)

    @covers_requirement(
        "companion-possession-core::the-possess-command-surface-is-localized-and-documented"
    )
    @covers_requirement(
        "companion-possession-core::handoff-confirmation-revalidates-the-exact-candidate"
    )
    def test_handoff_candidate_that_left_is_relisted_not_substituted(self):
        self._listing()
        self.candidate.location = self.room2
        before = int(get_world_clock().tick)
        output = self.call(CmdHandoff(), "2", caller=self.sleeper)
        self.assertIn("交接選項已經失效", output)
        self.assertIn("回到自己的身體", output)
        # The complete roster stays visible; the vanished candidate is listed
        # with its committed disabled reason instead of being substituted.
        self.assertIn("接手 清醒同伴（精力 100%）（不在同一地點）", output)
        self.assertEqual(
            current_possession(self.player)["npc_dbid"], int(self.sleeper.pk)
        )
        self.assertEqual(int(get_world_clock().tick), before)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    @covers_requirement(
        "party-system::any-present-sleeper-makes-party-travel-stationary"
    )
    def test_sleeping_body_still_cannot_cast_use_items_or_travel(self):
        from world.rules.field_cast import cast_as_member
        from world.rules.party_inventory import use_member_item

        for operation in (
            lambda: cast_as_member(
                self.sleeper, int(self.sleeper.pk), "t_synthetic_skill"
            ),
            lambda: use_member_item(
                self.sleeper, int(self.sleeper.pk), "t_synthetic_item"
            ),
        ):
            with self.assertRaises(PartyScopeError) as ctx:
                operation()
            self.assertEqual(ctx.exception.reason, REASON_MEMBER_ASLEEP)
        # The stationary rule is a real traversal boundary, not a pure speed
        # assertion: the awake owner's party still contains the sleeper.
        from typeclasses.exits import Exit

        door = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )
        before = int(get_world_clock().tick)
        self.assertIsNone(door.at_traverse(self.player, self.room2))
        self.assertIs(self.player.location, self.room1)
        self.assertIs(self.sleeper.location, self.room1)
        self.assertEqual(int(get_world_clock().tick), before)

    @covers_requirement(
        "companion-possession-core::entry-gates-are-deterministic-stable-coded-and-precede-all-generative-work"
    )
    def test_a_sleeping_body_forbids_foot_travel_by_policy(self):
        """Pure-policy unit assertion, separate from the consumer boundary."""
        with self.assertRaises(FatigueStateError) as ctx:
            foot_speed_scale(read_fatigue_state(self.sleeper))
        self.assertIs(ctx.exception.reason, FatigueRejectReason.TRAVEL_FORBIDDEN)
