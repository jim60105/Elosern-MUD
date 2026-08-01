"""Tests for loss-aware overwhelm EventLog compression."""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.overwhelm import compress_event_logs


def entry(kind, *, hit=None, amount=None):
    data = {}
    if hit is not None:
        data["hit"] = hit
    if amount is not None:
        data["amount"] = amount
    template = (
        "{actor} 對 {target} 造成 {data[amount]} 點傷害。"
        if kind == "damage"
        else "{actor} 的擲骰結果為 {data[raw_roll]}。"
    )
    if kind == "roll":
        data["raw_roll"] = 50
    return EventEntry(kind, "elf", "human", data, template)


class CompressionTests(unittest.TestCase):
    @covers_requirement("event-log-compression::compress-event-logs-drops-redundant-hit-rolls-and-preserves-miss-and-damage-records")
    @covers_requirement("event-log-compression::a-full-record-of-who-hit-whom-for-how-much-is-preserved-alongside-the-summary", "event-log-compression::compress-event-logs-prepends-one-overwhelm-resolution-summary-entry-aggregating-the")
    def test_drops_redundant_hit_roll_but_preserves_miss_and_damage(self):
        hit_roll = entry("roll", hit=True)
        miss_roll = entry("roll", hit=False)
        damage = entry("damage", amount=30)
        log = EventLog(
            "elf",
            "attack",
            ("human",),
            (hit_roll, damage, miss_roll),
            6,
        )
        result = compress_event_logs([log], "elves", "humans", 2)
        self.assertEqual(result[1].entries, (damage, miss_roll))
        summary = result[0]
        self.assertEqual(summary.actor, "elves")
        self.assertEqual(summary.targets, ("humans",))
        self.assertEqual(summary.time_cost_seconds, 0)
        self.assertEqual(
            summary.entries[0].data,
            {"rounds": 2, "hits": 1, "total_damage": 30},
        )

    def test_empty_filtered_log_is_dropped(self):
        log = EventLog(
            "elf",
            "attack",
            ("human",),
            (entry("roll", hit=True),),
            6,
        )
        result = compress_event_logs([log], "elves", "humans", 1)
        self.assertEqual(len(result), 1)

    @covers_requirement("event-log-compression::a-compressed-eventlog-renders-through-render-plain-text-with-no-llm-involvement")
    def test_damage_attribution_and_rendering_are_preserved(self):
        damage_one = entry("damage", amount=10)
        damage_two = entry("damage", amount=15)
        log = EventLog(
            "elf",
            "attack",
            ("human",),
            (damage_one, damage_two),
            6,
        )
        result = compress_event_logs([log], "elves", "humans", 1)
        self.assertEqual(result[1].entries, (damage_one, damage_two))
        rendered = "\n".join(render_plain_text(item) for item in result)
        self.assertTrue(rendered)
        self.assertNotIn("{", rendered)
        self.assertIn("雙方共命中", rendered)
        self.assertNotIn("壓制了", rendered)
        self.assertEqual(
            render_plain_text(result[0]),
            render_plain_text(result[0]),
        )
