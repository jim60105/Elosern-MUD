"""Focused deterministic tests for player-driven world time."""

from tools.spec_traceability import covers_requirement

import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.clock import (
    AdvanceSource,
    ClockAdvanceBoundError,
    DaypartError,
    MAX_ADVANCE_SECONDS,
    ScheduledEvent,
    WorldClock,
    WorldDateTime,
    _STAGE_ORDER,
    _has_settlement_work,
    _settle_buffs_and_decay,
    _settle_gauge_regen,
    _try_accrue_magic_study,
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

    def test_fractional_regen_is_floored_to_integer_storage(self):
        entity = Entity()
        entity.traits.hp = Gauge(10, 100, 0.5)
        _settle_gauge_regen([entity], 45)
        self.assertIsInstance(entity.traits.hp.current, int)
        self.assertEqual(entity.traits.hp.current, 32)
        self.assertEqual(entity.traits.hp.regen_remainder, 0.5)

    def test_segmented_regen_matches_one_equal_length_advance(self):
        segment = Entity()
        segment.traits.hp = Gauge(10, 125, 1.25)
        single = Entity()
        single.traits.hp = Gauge(10, 125, 1.25)
        _settle_gauge_regen([segment], 30)
        _settle_gauge_regen([segment], 30)
        _settle_gauge_regen([single], 60)
        self.assertEqual(segment.traits.hp.current, single.traits.hp.current)
        self.assertEqual(segment.traits.hp.current, 85)
        self.assertEqual(segment.traits.hp.regen_remainder, 0.0)
        self.assertEqual(single.traits.hp.regen_remainder, 0.0)

    def test_regen_remainder_resets_when_a_gauge_clamps_at_full(self):
        entity = Entity()
        entity.traits.hp = Gauge(99, 125, 1.25)
        _settle_gauge_regen([entity], 30)
        self.assertEqual(entity.traits.hp.current, 125)
        self.assertEqual(entity.traits.hp.regen_remainder, 0.0)

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
        with (
            patch("world.rules.clock.reset_daily_counters") as reset,
            patch("world.rules.clock.MAX_ADVANCE_SECONDS", 86400 * 3),
        ):
            WorldClock(1).advance(86400 * 3, AdvanceSource.COMBAT, [entity])
        self.assertEqual(reset.call_count, 3)

    @covers_requirement("world-clock::advance-has-a-bounded-settlement-budget-per-call")
    def test_advance_exactly_at_the_one_day_bound_is_accepted(self):
        # `wait until` can legally request a full-day wait; the bound is
        # exclusive so the worst case stays a valid advance.
        entity = Entity()
        clock = WorldClock()
        events = clock.advance(MAX_ADVANCE_SECONDS, AdvanceSource.COMBAT, [entity])
        self.assertEqual(clock.tick, MAX_ADVANCE_SECONDS)
        self.assertIsInstance(events, list)

    @covers_requirement("world-clock::advance-has-a-bounded-settlement-budget-per-call")
    def test_oversized_advance_raises_before_any_stage(self):
        entity = Entity()
        clock = WorldClock(10)
        with (
            patch("world.rules.clock._run_stages") as stages,
            self.assertRaises(ClockAdvanceBoundError),
        ):
            clock.advance(MAX_ADVANCE_SECONDS + 1, AdvanceSource.SKIP, [entity])
        stages.assert_not_called()
        self.assertEqual(clock.tick, 10)
        self.assertEqual(entity.traits.hp.current, 10)

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

    def test_negative_tick_and_negative_advance_fail_closed(self):
        with self.assertRaises(ValueError):
            WorldDateTime.from_tick(-1)
        with self.assertRaises(ValueError):
            WorldClock().advance(-1, AdvanceSource.SKIP, [])

    def test_buffed_actor_is_detected_as_settlement_work(self):
        buff = SimpleNamespace(
            paused=False, stacks=1, remaining_seconds=300, tick_interval=None
        )
        entity = Entity()
        entity.buffs = SimpleNamespace(all={"poisoned": buff})
        self.assertTrue(_has_settlement_work(entity))
        idle = Entity()
        self.assertFalse(_has_settlement_work(idle))

    def test_magic_study_import_failure_degrades_gracefully(self):
        with patch.dict(sys.modules, {"world.rules.progression": None}):
            _try_accrue_magic_study((), 60, AdvanceSource.SKIP)

    def test_invalid_settlement_interval_fails_module_validation(self):
        import world.rules.clock as clock_module
        import world.rules.sexual_state as sexual_state

        original = dict(sexual_state.DECAY_CONFIG)
        sexual_state.DECAY_CONFIG["fake_bad"] = {"interval_seconds": 0}
        try:
            with self.assertRaises(ValueError):
                clock_module._validate_settlement_intervals(
                    clock_module.BUFF_DEFINITIONS, sexual_state.DECAY_CONFIG
                )
        finally:
            sexual_state.DECAY_CONFIG.clear()
            sexual_state.DECAY_CONFIG.update(original)


class WorldClockPersistenceTests(EvenniaTest):
    @covers_requirement("settlement-stage-order::scheduledevent-is-a-plain-json-compatible-record-with-no-live-entity-references", "world-clock::tick-is-persisted-via-a-non-repeating-script-used-purely-as-an-attribute-container")
    def test_singleton_persists_only_tick(self):
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        clock.advance(7, AdvanceSource.COMBAT, [])
        self.assertEqual(get_world_clock().tick, 7)

    def test_gauge_persistence_stays_integral_with_regen_remainder(self):
        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object
        from world.rules.clock import _settle_gauge_regen

        entity = create_object(PlayerCharacter, key="regen gauge keeper")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.traits.hp.current = 10
        entity.traits.hp.base = 125
        entity.traits.hp.rate = 1.25

        _settle_gauge_regen([entity], 30)
        stored_after = entity.attributes.get("traits", category="traits")["hp"]
        self.assertIsInstance(stored_after["current"], int)
        self.assertEqual(stored_after["current"], 47)
        self.assertEqual(stored_after["regen_remainder"], 0.5)


class WorldClockAtomicityTests(EvenniaTest):
    """The advance is all-or-nothing for entity state and the persisted tick."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.traits.hp.current = 10
        self.player.traits.hp.base = 100
        self.player.traits.hp.rate = 1
        self.player.traits.sp.current = 3
        self.player.traits.sp.base = 100
        self.player.traits.sp.rate = 2

    def _stored_hp(self):
        return self.player.attributes.get("traits", category="traits")["hp"]["current"]

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_failed_advance_restores_entity_state_and_leaves_tick_unchanged(self):
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        before_tick = clock.tick
        with (
            patch(
                "world.rules.clock._settle_buffs_and_decay",
                side_effect=RuntimeError("simulated mid-advance failure"),
            ),
            self.assertRaises(RuntimeError),
        ):
            clock.advance(3600, AdvanceSource.SKIP, [self.player])
        # No partial save: the tick and both entity surfaces are unchanged.
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self.player.traits.hp.current, 10)
        self.assertEqual(self._stored_hp(), 10)
        self.assertEqual(self.player.traits.sp.current, 3)

    def test_persist_failure_restores_tick_in_memory_and_on_the_script(self):
        from evennia.utils.search import search_script
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        script = search_script("world_clock")[0]
        clock.advance(60, AdvanceSource.SKIP, [self.player])
        before_tick = clock.tick

        def failing_persist(tick):
            script.db.tick = tick
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(60, AdvanceSource.SKIP, [self.player])
        # The in-memory clock, a fresh read of the singleton, the persisted
        # script attribute, and the entity surface all keep their old values.
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        self.assertEqual(self.player.traits.hp.current, 70)
        self.assertEqual(self._stored_hp(), 70)

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_successful_advance_persists_entity_state_and_tick_together(self):
        from evennia.utils.search import search_object, search_script
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        before_tick = clock.tick
        clock.advance(3600, AdvanceSource.SKIP, [self.player])
        # Simulate a restart: drop both idmapper instances and re-fetch.
        self.player.flush_cached_instance(self.player)
        script = search_script("world_clock")[0]
        script.flush_cached_instance(script)
        fresh_player = search_object(self.player.key)[0]
        self.assertEqual(fresh_player.traits.hp.current, 100)
        self.assertEqual(fresh_player.traits.sp.current, 100)
        self.assertEqual(get_world_clock().tick, before_tick + 3600)

    @covers_requirement("world-clock::advance-has-a-bounded-settlement-budget-per-call")
    def test_oversized_advance_raises_before_any_write(self):
        from world.rules.clock import get_world_clock

        clock = get_world_clock()
        before_tick = clock.tick
        with (
            patch("world.rules.clock._run_stages") as stages,
            self.assertRaises(ClockAdvanceBoundError),
        ):
            clock.advance(MAX_ADVANCE_SECONDS + 1, AdvanceSource.SKIP, [self.player])
        stages.assert_not_called()
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self.player.traits.hp.current, 10)
        self.assertEqual(self._stored_hp(), 10)
