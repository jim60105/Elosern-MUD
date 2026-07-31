"""Command-level tests for the resolver's out-of-combat caller."""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.action import CmdCast, REJECTION_MESSAGES
from world.rules.action import RejectReason
from world.rules.combat import Battlefield, BattlefieldActionContext


class CmdCastTests(EvenniaCommandTestMixin, EvenniaTest):
    def test_successful_stock_disguise_cast_renders_event(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {
            "active": ["status_disguise"],
            "passive": [],
        }
        self.char1.db.disguised_stats = {"atk_phys": 1}
        self.call(CmdCast(), "status_disguise", f"{self.char1.key} 改變了")

    def test_unknown_skill_renders_named_rejection(self):
        self.char1.db.skills = {"active": [], "passive": []}
        self.call(
            CmdCast(),
            "definitely_missing",
            REJECTION_MESSAGES[RejectReason.UNKNOWN_SKILL],
        )

    def test_missing_skill_argument_renders_usage(self):
        self.call(CmdCast(), "", "用法：cast")

    def test_rejection_message_table_covers_every_reason(self):
        self.assertEqual(set(REJECTION_MESSAGES), set(RejectReason))

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
