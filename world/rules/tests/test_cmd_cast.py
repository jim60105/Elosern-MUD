"""Command-level tests for the resolver's out-of-combat caller."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.action import CmdCast
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.rules.action import RejectReason
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.clock import WorldClock
from world.rules.party import AUTO_LEAVE_MESSAGE, join_party
from world.rules.player_messages import (
    rejection_message,
    session_reason_message,
    terminal_outcome_message,
)
from world.rules.combat_session import SessionReason


class CmdCastTests(EvenniaCommandTestMixin, EvenniaTest):
    @covers_requirement("action-resolution-pipeline::every-production-skill-path-receives-registered-event-effect-planning-automatically")
    def test_successful_stock_disguise_cast_renders_event(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {
            "active": ["status_disguise"],
            "passive": [],
        }
        self.char1.db.disguised_stats = {"atk_phys": 1}
        clock = WorldClock()
        with patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), "status_disguise", f"{self.char1.key} 改變了")
        self.assertEqual(clock.tick, 6)

    def test_unknown_skill_renders_named_rejection(self):
        self.char1.db.skills = {"active": [], "passive": []}
        clock = WorldClock()
        with patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(
                CmdCast(),
                "definitely_missing",
                rejection_message(RejectReason.UNKNOWN_SKILL),
            )
        self.assertEqual(clock.tick, 0)

    def test_missing_skill_argument_renders_usage(self):
        self.call(CmdCast(), "", "用法：cast")

    def test_rejection_message_table_covers_every_reason(self):
        for reason in RejectReason:
            message = rejection_message(reason)
            self.assertTrue(message.strip())
            self.assertLessEqual(sum(1 for _ in message), 512)

    def test_session_message_table_covers_every_session_reason(self):
        for reason in SessionReason:
            message = session_reason_message(str(reason))
            self.assertTrue(message.strip())

    def test_terminal_outcome_table_covers_every_terminal_outcome(self):
        for outcome in ("victory", "defeat", "fled", "exam_passed", "exam_failed", "cap"):
            message = terminal_outcome_message(outcome)
            self.assertTrue(message.strip())
            self.assertNotEqual(message, "繼續戰鬥。")

    def test_flee_uses_active_battlefield_context(self):
        self.char1.race = "human"
        self.char2.race = "human"
        for entity in (self.char1, self.char2):
            entity.apply_race_baseline()
            entity.db.skills = {"active": [], "passive": []}
        field = Battlefield(
            {
                "party": frozenset({self.char1.key}),
                "foes": frozenset({self.char2.key}),
            },
            {self.char1.key: self.char1, self.char2.key: self.char2},
        )
        self.char1.ndb.action_context = BattlefieldActionContext(field)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            self.call(CmdCast(), "flee", "Char 嘗試脫離戰鬥。")
        self.assertIn(self.char1.key, field.fled)


class CmdCastSexualCoercionTests(EvenniaCommandTestMixin, EvenniaTest):
    """The auto-leave notification of an out-of-combat forced act reaches the
    player after the rendered EventLog (sexual-resist-out-of-combat)."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {"active": [], "passive": []}
        self.clock = WorldClock()

    def _companion(self, key, affinity: int | None = None):
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        npc.traits.hp.base = 100
        npc.traits.hp.current = 100
        if affinity is not None:
            apply_affinity_change(
                npc, self.char1, AffinitySource.QUEST_COMPLETION, affinity
            )
        join_party(npc, self.char1)
        return npc

    def _forced_cast(self, target_key):
        with (
            patch(
                "world.rules.cast_settlement.read_world_clock",
                return_value=self.clock,
            ),
            patch(
                "world.rules.cast_settlement.get_world_clock",
                return_value=self.clock,
            ),
            patch("world.rules.action.roll_d100", return_value=1),
            patch("commands.action.render_plain_text", return_value="RENDERED"),
        ):
            return self.call(
                CmdCast(), f"combat_tease={target_key}", use_assertequal=True
            )

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-act-s-party-auto-leave-notification-reaches-the-player")
    def test_auto_leave_notification_arrives_after_the_event_log(self):
        coerced = self._companion("離隊伴侶", affinity=70)
        returned = self._forced_cast(coerced.key)
        self.assertEqual(returned, "RENDERED\n" + AUTO_LEAVE_MESSAGE)
        self.assertNotIn(int(coerced.pk), self.char1.db.party)

    @covers_requirement("sexual-resist-out-of-combat::an-out-of-combat-forced-act-s-party-auto-leave-notification-reaches-the-player")
    def test_forced_act_without_auto_leave_sends_only_the_event_log(self):
        companion = self._companion("留守伴侶", affinity=73)
        returned = self._forced_cast(companion.key)
        self.assertEqual(returned, "RENDERED")
        self.assertIn(int(companion.pk), self.char1.db.party)
