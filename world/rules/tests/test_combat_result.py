"""Unit tests for the shared combat-result rendering (task 3.5)."""

import unittest

from world.rules.action import RejectReason
from world.rules.combat_result import (
    settle_to_messages,
    settle_to_oob_result,
)
from world.rules.event_log import EventEntry, EventLog


class CombatResultRenderingTests(unittest.TestCase):
    def _log(self):
        entry = EventEntry(
            kind="damage",
            actor="hero",
            target="goblin",
            data={"amount": 5},
            text_template="{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
        )
        return EventLog("hero", "fire_ball", ("goblin",), (entry,), 6)

    def test_round_settlement_renders_logs_and_continue_message(self):
        lines, message = settle_to_messages(
            {"outcome": "round", "logs": [self._log()]}
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("造成了 5 點傷害", lines[0])
        self.assertEqual(message, "行動完成，繼續戰鬥。")

    def test_terminal_settlement_uses_stable_message(self):
        lines, message = settle_to_messages(
            {"outcome": "victory", "logs": [self._log()]}
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(message, "戰鬥結束，你取得了勝利。")

    def test_rejected_settlement_emits_no_prose(self):
        lines, message = settle_to_messages(
            {
                "outcome": "rejected",
                "reason": RejectReason.INSUFFICIENT_RESOURCE,
                "detail": "mp",
            }
        )
        self.assertEqual(lines, ())
        self.assertEqual(message, "你的資源不足。")

    def test_rejected_without_reason_uses_fallback(self):
        lines, message = settle_to_messages({"outcome": "rejected"})
        self.assertEqual(lines, ())
        self.assertEqual(message, "這項行動無法完成。")

    def test_oob_round_result_declares_affected_panels(self):
        result = settle_to_oob_result({"outcome": "round"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "round")
        self.assertEqual(
            result["affected_panels"], ("status", "context_actions", "art")
        )
        self.assertNotIn("logs", result)

    def test_oob_terminal_result_declares_no_affected_panels(self):
        result = settle_to_oob_result({"outcome": "fled"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "fled")
        self.assertEqual(result["message"], "你脫離了戰鬥。")
        # A terminal outcome must publish a full snapshot, not a partial
        # update: the mode flips back to exploration.
        self.assertEqual(result["affected_panels"], ())

    def test_oob_rejected_result_maps_reason(self):
        result = settle_to_oob_result(
            {"outcome": "rejected", "reason": RejectReason.TARGET_DEAD}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "target_dead")
        self.assertEqual(result["message"], "目標已失去行動能力。")

    def test_oob_rejected_without_reason_uses_fallback(self):
        result = settle_to_oob_result({"outcome": "rejected"})
        self.assertEqual(result["code"], "rejected")
        self.assertEqual(result["message"], "這項行動無法完成。")


if __name__ == "__main__":
    unittest.main()
