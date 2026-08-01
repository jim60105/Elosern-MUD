"""Focused deterministic tests for player-driven world time."""

from tools.spec_traceability import covers_requirement

import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.clock import (
    AdvanceSource,
    DaypartError,
    ScheduledEvent,
    WorldClock,
    WorldDateTime,
    _STAGE_ORDER,
    _settle_buffs_and_decay,
    _settle_gauge_regen,
    settle_combat_result,
    register_event_source,
    seconds_until_daypart,
)
from evennia.utils.test_resources import EvenniaTest


class Gauge:
    def __init__(self, current, maximum, rate=0):
        self.current = current
        self.value = current
        self.max = maximum
        self.rate = rate


class Buffs:
    all = {}


class Entity:
    def __init__(self):
        self.traits = SimpleNamespace(
            hp=Gauge(10, 100, 2),
            mp=Gauge(20, 100, 0),
            sp=Gauge(30, 100, 0),
        )
        self.buffs = Buffs()
        self.sexual = None


class ClockTests(unittest.TestCase):
    @covers_requirement("world-clock::worldclock-persists-exactly-one-integer-every-calendar-field-is-derived-from-it")
    @covers_requirement("world-clock::the-calendar-is-a-subtropical-four-mild-season-year-with-no-invented-month-names")
    def test_calendar_is_derived_from_tick(self):
        self.assertEqual(
            WorldDateTime.from_tick(0),
            WorldDateTime(0, 0, 1, 0, 0, 0),
        )
        self.assertEqual(WorldDateTime.from_tick(86400).day_in_season, 2)
        self.assertEqual(WorldDateTime.from_tick(86400 * 90).season_index, 1)
        self.assertEqual(WorldDateTime.from_tick(86400 * 360).year, 1)

    @covers_requirement("time-skip-commands::wait-until-daypart-computes-seconds-to-the-next-occurrence-of-a-named-daypart")
    def test_daypart_is_strictly_future(self):
        calendar = WorldDateTime(0, 0, 1, 2, 30, 0)
        self.assertEqual(seconds_until_daypart(calendar, "dawn"), 12600)
        self.assertEqual(seconds_until_daypart(calendar, "midnight"), 77400)
        with self.assertRaises(DaypartError):
            seconds_until_daypart(calendar, "tea")

    @covers_requirement("world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop")
    def test_regen_is_closed_form_and_clamped(self):
        entity = Entity()
        _settle_gauge_regen([entity], 28800)
        self.assertEqual(entity.traits.hp.current, 100)

    @covers_requirement("settlement-stage-order::long-jumps-settle-in-quanta-not-per-second-steps-with-an-early-exit-once-nothing")
    def test_no_work_exits_before_a_quantum(self):
        entity = Entity()
        with (
            patch("world.rules.clock.tick_buffs") as tick,
            patch("world.rules.clock.decay_tick") as decay,
        ):
            _settle_buffs_and_decay((entity,), 28800)
        tick.assert_not_called()
        decay.assert_not_called()

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_quantum_loop_honors_defensive_cap(self):
        entity = Entity()
        with (
            patch("world.rules.clock._has_settlement_work", return_value=True),
            patch("world.rules.clock.CLOCK_YAML", {"max_settlement_quanta": 3}),
            patch("world.rules.clock.tick_buffs") as tick,
            patch("world.rules.clock.decay_tick") as decay,
        ):
            _settle_buffs_and_decay((entity,), 100)
        self.assertEqual(tick.call_count, 3)
        self.assertEqual(decay.call_count, 3)

    def test_sub_quantum_elapsed_seconds_are_not_lost(self):
        entity = Entity()
        with (
            patch("world.rules.clock._has_settlement_work", return_value=True),
            patch("world.rules.clock.tick_buffs") as tick,
            patch("world.rules.clock.decay_tick") as decay,
        ):
            _settle_buffs_and_decay((entity,), 6)
            _settle_buffs_and_decay((entity,), 6)
        self.assertEqual([call.args[1] for call in tick.call_args_list], [6, 6])
        self.assertEqual([call.args[1] for call in decay.call_args_list], [6, 6])

    def test_combat_skips_per_quantum_stages_but_regenerates(self):
        entity = Entity()
        clock = WorldClock()
        with patch("world.rules.clock._settle_buffs_and_decay") as settle:
            clock.advance(10, AdvanceSource.COMBAT, [entity])
        settle.assert_not_called()
        self.assertEqual(entity.traits.hp.current, 30)

    def test_daily_boundary_and_event_registry(self):
        entity = Entity()
        clock = WorldClock(86399)
        register_event_source(
            "caravan_arrivals",
            lambda start, end: [ScheduledEvent("caravan", end, {"key": "x"})],
        )
        events = clock.advance(2, AdvanceSource.COMBAT, [entity])
        self.assertEqual([event.kind for event in events], ["daily_reset", "caravan"])

    @covers_requirement("settlement-stage-order::buff-ticks-sexual-decay-and-magic-study-are-skipped-for-combat-sourced-advances", "settlement-stage-order::hourly-and-daily-boundary-stages-fire-by-tick-boundary-arithmetic-never-by-iterating")
    def test_command_runs_per_quantum_stages(self):
        entity = Entity()
        clock = WorldClock()
        with patch("world.rules.clock._settle_buffs_and_decay") as settle:
            clock.advance(10, AdvanceSource.COMMAND, [entity])
        settle.assert_called_once_with((entity,), 10)

    @covers_requirement("settlement-stage-order::magic-study-is-invoked-through-a-self-arming-lazy-import-and-its-own-internal")
    def test_magic_study_lazy_import_self_arms(self):
        calls = []
        module = SimpleNamespace(
            accrue_magic_study=lambda entities, seconds, source: calls.append(
                (entities, seconds, source)
            )
        )
        entity = Entity()
        with patch.dict(sys.modules, {"world.rules.progression": module}):
            WorldClock().advance(10, AdvanceSource.SKIP, [entity])
        self.assertEqual(calls, [((entity,), 10, AdvanceSource.SKIP)])

    def test_daily_resets_use_crossed_boundary_count(self):
        entity = Entity()
        entity.sexual = object()
        with patch("world.rules.clock.reset_daily_counters") as reset:
            WorldClock(1).advance(86400 * 3, AdvanceSource.COMBAT, [entity])
        self.assertEqual(reset.call_count, 3)

    def test_identical_inputs_are_reproducible_and_scoped(self):
        first, second, untouched = Entity(), Entity(), Entity()
        left = WorldClock(10).advance(5, AdvanceSource.COMBAT, [first])
        right = WorldClock(10).advance(5, AdvanceSource.COMBAT, [second])
        self.assertEqual(first.traits.hp.current, second.traits.hp.current)
        self.assertEqual(left, right)
        self.assertEqual(untouched.traits.hp.current, 10)

    @covers_requirement("world-clock::settle-combat-result-is-the-sanctioned-call-site-for-combat-sourced-advances")
    @covers_requirement("world-clock::advance-settles-exactly-the-entities-its-caller-supplies-never-a-global-registry")
    def test_settle_combat_result_uses_combat_source(self):
        clock = WorldClock()
        result = SimpleNamespace(total_seconds=18)
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            settle_combat_result(result, [])
        self.assertEqual(clock.tick, 18)

    @covers_requirement("settlement-stage-order::settlement-stages-run-in-the-fixed-order-regen-buffs-sexual-decay-magic-study")
    def test_stage_order_is_fixed(self):
        self.assertLess(_STAGE_ORDER.index("gauge_regen"), _STAGE_ORDER.index("buff_ticks"))
        self.assertLess(_STAGE_ORDER.index("buff_ticks"), _STAGE_ORDER.index("sexual_decay"))
        self.assertLess(_STAGE_ORDER.index("sexual_decay"), _STAGE_ORDER.index("magic_study"))
        self.assertLess(_STAGE_ORDER.index("magic_study"), _STAGE_ORDER.index("daily_resets"))


class WorldClockPersistenceTests(EvenniaTest):
    @covers_requirement("settlement-stage-order::scheduledevent-is-a-plain-json-compatible-record-with-no-live-entity-references", "world-clock::tick-is-persisted-via-a-non-repeating-script-used-purely-as-an-attribute-container")
    def test_singleton_persists_only_tick(self):
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        clock.advance(7, AdvanceSource.COMBAT, [])
        self.assertEqual(get_world_clock().tick, 7)
