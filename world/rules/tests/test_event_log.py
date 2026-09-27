"""Tests for the no-LLM event-log seam."""

from tools.spec_traceability import covers_requirement

from dataclasses import asdict
import json
import unittest

from world.rules.event_log import (
    EventEntry,
    EventLog,
    render_entry_text,
    render_plain_text,
)


class EventLogTests(unittest.TestCase):
    @covers_requirement("event-log::eventlog-and-evententry-are-frozen-serializable-entity-key-only-records")
    @covers_requirement("event-log::eventlog-is-structured-for-combat-compression-and-pure-function-narration")
    def test_json_round_trip_contains_only_plain_data(self):
        log = EventLog(
            actor="elosia",
            # EventLog is a plain record: the skill key is carried data, not
            # a registry read — an invented key keeps the seam data-free.
            skill_key="t_duskward_confer",
            targets=("violet",),
            entries=(
                EventEntry(
                    "skill_granted",
                    "elosia",
                    "violet",
                    {"scale": 0.1},
                    "{actor} 對 {target} 施展了暮授術。",
                ),
            ),
            time_cost_seconds=6,
        )
        self.assertEqual(json.loads(json.dumps(asdict(log)))["actor"], "elosia")
        self.assertEqual(
            render_plain_text(log),
            "elosia 對 violet 施展了暮授術。",
        )

    @covers_requirement("event-log::render-plain-text-renders-an-eventlog-to-prose-with-no-llm-involvement")
    def test_multiple_entries_render_in_order(self):
        entries = tuple(
            EventEntry("test", "a", None, {}, text)
            for text in ("第一行", "第二行")
        )
        log = EventLog("a", "test", (), entries, 0)
        self.assertEqual(render_plain_text(log), "第一行\n第二行")

    @covers_requirement("event-log::render-plain-text-renders-an-eventlog-to-prose-with-no-llm-involvement")
    def test_entry_text_join_keeps_plain_text_byte_identical(self):
        # The beats panel renders one entry at a time through
        # ``render_entry_text``; ``render_plain_text`` must stay the same
        # newline join over it, empty templates included (those lines are
        # empty strings, never dropped).
        entries = (
            EventEntry(
                "roll",
                "a",
                "b",
                {"raw_roll": 42, "hit": True},
                "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
            ),
            EventEntry("combat_kill_xp", "a", None, {}, ""),
            EventEntry("damage", "a", "b", {"amount": 7}, "{target} 受到了 {data[amount]} 點傷害。"),
        )
        log = EventLog("a", "test", ("b",), entries, 0)
        self.assertEqual(
            [render_entry_text(entry) for entry in entries],
            ["a 對 b 的攻擊擲出了 42。", "", "b 受到了 7 點傷害。"],
        )
        self.assertEqual(
            render_plain_text(log),
            "a 對 b 的攻擊擲出了 42。\n\nb 受到了 7 點傷害。",
        )

    @covers_requirement("event-log::evententry-kind-is-an-open-convention-not-a-closed-enum")
    def test_trait_delta_is_an_open_renderable_kind(self):
        entry = EventEntry(
            "trait_delta",
            "actor",
            "actor",
            {"trait_key": "mp", "delta": -20},
            "{target} 的 {data[trait_key]} 改變了。",
        )
        log = EventLog("actor", "cast", ("actor",), (entry,), 6)
        self.assertEqual(render_plain_text(log), "actor 的 mp 改變了。")
