"""Tests for loss-aware overwhelm EventLog compression."""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.overwhelm import compress_event_logs


def entry(kind, *, actor="elf", target="human", hit=None, amount=None):
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
    return EventEntry(kind, actor, target, data, template)


class CompressionTests(unittest.TestCase):
    @covers_requirement("event-log-compression::compress-event-logs-preserves-every-attack-record-without-kind-based-filtering")
    @covers_requirement("event-log-compression::a-full-record-of-who-hit-whom-for-how-much-is-preserved-alongside-the-summary")
    @covers_requirement("event-log-compression::compress-event-logs-prepends-one-overwhelm-resolution-summary-entry-aggregating-the")
    def test_successful_roll_survives_alongside_its_paired_damage(self):
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
        self.assertEqual(result[1].entries, (hit_roll, damage, miss_roll))
        summary = result[0]
        self.assertEqual(summary.actor, "elves")
        self.assertEqual(summary.targets, ("humans",))
        self.assertEqual(summary.time_cost_seconds, 0)
        self.assertEqual(
            summary.entries[0].data,
            {"rounds": 2, "hits": 1, "total_damage": 30},
        )

    @covers_requirement("event-log-compression::compress-event-logs-preserves-every-attack-record-without-kind-based-filtering")
    def test_miss_roll_survives_unchanged(self):
        miss_roll = entry("roll", hit=False)
        log = EventLog(
            "elf",
            "attack",
            ("human",),
            (miss_roll,),
            6,
        )
        result = compress_event_logs([log], "elves", "humans", 1)
        self.assertEqual(result[1].entries, (miss_roll,))

    def test_empty_input_log_is_dropped(self):
        log = EventLog(
            "elf",
            "attack",
            ("human",),
            (),
            6,
        )
        result = compress_event_logs([log], "elves", "humans", 1)
        self.assertEqual(len(result), 1)

    @covers_requirement("event-log-compression::compress-event-logs-preserves-every-attack-record-without-kind-based-filtering")
    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_output_count_is_input_plus_summary_and_marker(self):
        logs = [
            EventLog(
                "elf",
                "attack",
                ("human",),
                (entry("roll", hit=True), entry("damage", amount=10)),
                6,
            ),
            EventLog(
                "elf",
                "attack",
                ("human",),
                (entry("roll", hit=True), entry("damage", amount=15)),
                6,
            ),
        ]
        plain = compress_event_logs(logs, "elves", "humans", 1)
        self.assertEqual(
            sum(len(log.entries) for log in plain),
            4 + 1,
        )
        marked = compress_event_logs(
            logs,
            "elves",
            "humans",
            1,
            commanded_actor="elf",
            commanded_skill="attack",
            commanded_window=logs,
        )
        self.assertEqual(
            sum(len(log.entries) for log in marked),
            4 + 1 + 1,
        )

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


class MarkerTests(unittest.TestCase):
    def _action_log(self, actor, skill_key, *, target="human", hit=True, amount=30):
        roll = entry("roll", actor=actor, target=target, hit=hit)
        if not hit:
            return EventLog(actor, skill_key, (target,), (roll,), 6)
        return EventLog(
            actor,
            skill_key,
            (target,),
            (roll, entry("damage", actor=actor, target=target, amount=amount)),
            6,
        )

    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_marker_prepends_to_the_first_matching_window_log(self):
        player = "瑟芮雅"
        commanded = self._action_log(player, "basic_attack", target=player, hit=False)
        companion = self._action_log("夥伴", "fire_ball")
        auto = self._action_log(player, "basic_attack", amount=40)
        window = (commanded, companion)
        result = compress_event_logs(
            (commanded, companion, auto),
            "party",
            "foes",
            2,
            commanded_actor=player,
            commanded_skill="basic_attack",
            commanded_window=window,
        )
        marked = result[1]
        self.assertEqual(marked.entries[0].kind, "commanded_action")
        self.assertEqual(marked.entries[0].actor, player)
        self.assertIsNone(marked.entries[0].target)
        self.assertEqual(marked.entries[0].data, {"skill": "基本攻擊"})
        # The later auto basic attack matches actor+skill but lies outside
        # the window, so it is never marked.
        self.assertNotEqual(result[3].entries[0].kind, "commanded_action")
        self.assertEqual(
            [entry.kind for log in result[2:] for entry in log.entries].count(
                "commanded_action"
            ),
            0,
        )

    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_marker_follows_window_order_not_raw_order(self):
        player = "瑟芮雅"
        first = self._action_log("夥伴", "fire_ball")
        second = self._action_log(player, "basic_attack", hit=False)
        # The window lists the player's log first, inverting the raw order;
        # the marker must land on the first match in WINDOW order.
        result = compress_event_logs(
            (first, second),
            "party",
            "foes",
            1,
            commanded_actor=player,
            commanded_skill="basic_attack",
            commanded_window=(second, first),
        )
        self.assertEqual(result[1].entries[0].kind, "roll")
        self.assertEqual(result[2].entries[0].kind, "commanded_action")

    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_invalidated_round1_command_yields_no_marker(self):
        player = "瑟芮雅"
        companion = self._action_log("夥伴", "fire_ball")
        auto = self._action_log(player, "basic_attack", amount=40)
        window = (companion,)
        result = compress_event_logs(
            (companion, auto),
            "party",
            "foes",
            2,
            commanded_actor=player,
            commanded_skill="basic_attack",
            commanded_window=window,
        )
        kinds = [entry.kind for log in result for entry in log.entries]
        self.assertNotIn("commanded_action", kinds)

    def test_default_calls_add_no_marker(self):
        log = self._action_log("elf", "attack")
        result = compress_event_logs([log], "elves", "humans", 1)
        self.assertNotIn(
            "commanded_action",
            [entry.kind for entry in result[1].entries],
        )

    def test_partial_arguments_add_no_marker(self):
        log = self._action_log("elf", "attack")
        result = compress_event_logs(
            [log],
            "elves",
            "humans",
            1,
            commanded_actor="elf",
            commanded_skill="attack",
        )
        self.assertNotIn(
            "commanded_action",
            [entry.kind for entry in result[1].entries],
        )

    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_unknown_commanded_skill_falls_back_to_raw_key(self):
        player = "瑟芮雅"
        log = self._action_log(player, "mystery_art")
        result = compress_event_logs(
            [log],
            "party",
            "foes",
            1,
            commanded_actor=player,
            commanded_skill="mystery_art",
            commanded_window=(log,),
        )
        self.assertEqual(result[1].entries[0].data, {"skill": "mystery_art"})

    @covers_requirement("event-log-compression::compress-event-logs-marks-the-player-s-commanded-action-with-a-commanded-action-entry")
    def test_marked_log_renders_player_perspective_line(self):
        player = "瑟芮雅"
        log = self._action_log(player, "basic_attack", target=player, hit=False)
        result = compress_event_logs(
            [log],
            "party",
            "foes",
            1,
            commanded_actor=player,
            commanded_skill="basic_attack",
            commanded_window=(log,),
        )
        rendered = render_plain_text(result[1])
        self.assertTrue(rendered.startswith("你施展了「基本攻擊」。"))


def _join_renderer(logs):
    return "\n".join(render_plain_text(log) for log in logs)


def _maximum_size_compressed_log() -> tuple[EventLog, ...]:
    """One maximum-size compressed record: 12 rounds, 16 participants, all hits."""
    raw_logs = []
    for round_index in range(12):
        for index in range(16):
            actor = f"戰士{round_index}-{index}"
            target = f"敵人{round_index}-{index}"
            raw_logs.append(
                EventLog(
                    actor,
                    "basic_attack",
                    (target,),
                    (
                        EventEntry(
                            "roll",
                            actor,
                            target,
                            {"raw_roll": 99, "hit": True},
                            "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
                        ),
                        EventEntry(
                            "damage",
                            actor,
                            target,
                            {"amount": 50},
                            "{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
                        ),
                    ),
                    6,
                )
            )
    return compress_event_logs(
        raw_logs,
        "party",
        "foes",
        12,
        commanded_actor="戰士0-0",
        commanded_skill="basic_attack",
        commanded_window=tuple(raw_logs[:16]),
    )


class NarratorBoundaryTests(unittest.TestCase):
    """A maximum-size compressed log exceeds the narrator's prompt bounds and
    degrades through the deterministic template renderer without raising."""

    def setUp(self):
        from world.ai import guardrail
        from world.ai.narrator import register_narrator

        guardrail._semantic_validators.clear()
        guardrail._degrade_fallbacks.clear()
        register_narrator(_join_renderer)

    def tearDown(self):
        from world.ai import guardrail

        guardrail._semantic_validators.clear()
        guardrail._degrade_fallbacks.clear()

    @covers_requirement("event-log-compression::a-compressed-eventlog-renders-through-render-plain-text-with-no-llm-involvement")
    def test_maximum_size_compressed_log_degrades_to_template_renderer(self):
        from types import SimpleNamespace

        from world.ai.narrator import narrate_event_logs

        logs = _maximum_size_compressed_log()
        deferred = narrate_event_logs(logs, SimpleNamespace())
        result = deferred.result
        deferred.addErrback(lambda failure: None)
        self.assertEqual(result, _join_renderer(logs))
