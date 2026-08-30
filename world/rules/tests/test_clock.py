"""Focused deterministic tests for player-driven world time."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.clock import (
    AdvanceSource,
    ClockAdvanceBoundError,
    DaypartError,
    MAX_ADVANCE_SECONDS,
    ScheduledEvent,
    SurfaceSnapshot,
    WorldClock,
    WorldDateTime,
    _STAGE_ORDER,
    _EVENT_SOURCES,
    _has_settlement_work,
    _restore_advance_registry,
    _restore_clock_tick,
    _settle_buffs_and_decay,
    _settle_gauge_regen,
    _snapshot_clock_tick,
    _practice_settlement,
    build_advance_snapshot_registry,
    settle_combat_result,
    register_event_source,
    seconds_until_daypart,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter


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

    @covers_requirement("settlement-stage-order::buff-ticks-sexual-decay-and-practice-settlement-are-skipped-for-combat-sourced-advances", "settlement-stage-order::hourly-and-daily-boundary-stages-fire-by-tick-boundary-arithmetic-never-by-iterating")
    def test_command_runs_per_quantum_stages(self):
        entity = Entity()
        clock = WorldClock()
        with patch("world.rules.clock._settle_buffs_and_decay") as settle:
            clock.advance(10, AdvanceSource.COMMAND, [entity])
        settle.assert_called_once_with((entity,), 10)

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

    @covers_requirement("settlement-stage-order::settlement-stages-run-in-the-fixed-order-regen-buffs-sexual-decay-practice-settlement")
    def test_stage_order_is_fixed(self):
        self.assertEqual(
            _STAGE_ORDER,
            (
                "gauge_regen",
                "buff_ticks",
                "sexual_decay",
                "practice_settlement",
                "daily_resets",
                "caravan_arrivals",
                "shop_hours",
                "quest_deadlines",
                "npc_schedules",
                "instance_reclamation",
            ),
        )
        self.assertLess(_STAGE_ORDER.index("gauge_regen"), _STAGE_ORDER.index("buff_ticks"))
        self.assertLess(_STAGE_ORDER.index("buff_ticks"), _STAGE_ORDER.index("sexual_decay"))
        self.assertLess(_STAGE_ORDER.index("sexual_decay"), _STAGE_ORDER.index("practice_settlement"))
        self.assertLess(_STAGE_ORDER.index("practice_settlement"), _STAGE_ORDER.index("daily_resets"))

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

    @covers_requirement("settlement-stage-order::buff-ticks-sexual-decay-and-practice-settlement-are-skipped-for-combat-sourced-advances")
    def test_practice_settlement_runs_outside_combat_and_writes_nothing_without_booking(self):
        # The runner never calls the stage on a COMBAT advance; the stage body
        # itself is inert for an entity without a db and writes no state for
        # an entity that never booked practice.
        entity = Entity()
        clock = WorldClock()
        with patch("world.rules.clock._practice_settlement") as settle:
            clock.advance(10, AdvanceSource.COMBAT, [entity])
        settle.assert_not_called()
        clock = WorldClock()
        with patch("world.rules.clock._practice_settlement") as settle:
            clock.advance(10, AdvanceSource.SKIP, [entity])
        settle.assert_called_once_with((entity,), 10, AdvanceSource.SKIP)
        _practice_settlement((entity,), 3600, AdvanceSource.SKIP)
        self.assertFalse(hasattr(entity, "skill_proficiency"))
        self.assertFalse(hasattr(entity, "db"))

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


class BookingEntity(Entity):
    """Fake settlement entity carrying one declared-practice booking."""

    def __init__(self, booking: str | None = "fire_arrow"):
        super().__init__()
        self.db = SimpleNamespace(
            practice_booking=booking, skill_proficiency={}
        )


class DeclaredPracticeSettlementTests(unittest.TestCase):
    """Closed-form stage consumption: SKIP-only, once per advance, whole hours."""

    @covers_requirement("settlement-stage-order::buff-ticks-sexual-decay-and-practice-settlement-are-skipped-for-combat-sourced-advances")
    def test_booking_survives_combat_and_command_advances_untouched(self):
        entity = BookingEntity()
        clock = WorldClock()
        with patch("world.rules.clock.grant_study_practice_xp") as grant:
            clock.advance(7200, AdvanceSource.COMBAT, [entity])
            clock.advance(7200, AdvanceSource.COMMAND, [entity])
        grant.assert_not_called()
        self.assertEqual(entity.db.practice_booking, "fire_arrow")

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_skip_advance_consumes_the_booking_with_whole_hour_math(self):
        entity = BookingEntity()
        clock = WorldClock()
        with patch("world.rules.clock.grant_study_practice_xp") as grant:
            clock.advance(9000, AdvanceSource.SKIP, [entity])
        # 9000 seconds = 2 completed hours; the 300-second remainder is
        # ignored and the value is passed closed-form, never quantum-looped.
        grant.assert_called_once_with(entity, "fire_arrow", 2)
        self.assertIsNone(entity.db.practice_booking)

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_sub_hour_skip_consumes_the_booking_and_grows_nothing(self):
        entity = BookingEntity()
        with patch("world.rules.clock.grant_study_practice_xp") as grant:
            WorldClock().advance(1800, AdvanceSource.SKIP, [entity])
        grant.assert_not_called()
        self.assertIsNone(entity.db.practice_booking)

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_advance_without_a_booking_writes_nothing(self):
        entity = BookingEntity(booking=None)
        with patch("world.rules.clock.grant_study_practice_xp") as grant:
            WorldClock().advance(28800, AdvanceSource.SKIP, [entity])
        grant.assert_not_called()
        self.assertEqual(entity.db.skill_proficiency, {})


class WorldClockPersistenceTests(EvenniaTestCase):
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

    @covers_requirement("settlement-stage-order::buff-ticks-sexual-decay-and-practice-settlement-are-skipped-for-combat-sourced-advances")
    def test_booking_survives_combat_and_settles_on_next_skip_advance(self):
        from world.rules.clock import get_world_clock
        from world.rules.progression import practice_xp_amount
        from world.skills.registry import SKILL_REGISTRY

        self.player.db.skill_proficiency = {"fire_arrow": 20.0}
        self.player.db.practice_booking = "fire_arrow"
        clock = get_world_clock()
        clock.advance(7200, AdvanceSource.COMBAT, [self.player])
        self.assertEqual(self.player.db.practice_booking, "fire_arrow")
        self.assertEqual(self.player.db.skill_proficiency["fire_arrow"], 20.0)
        clock.advance(7200, AdvanceSource.SKIP, [self.player])
        self.assertIsNone(self.player.db.practice_booking)
        # One formula, two entry points: two booked hours award ten times
        # the per-use composite amount.
        per_use = practice_xp_amount(self.player, SKILL_REGISTRY["fire_arrow"])
        self.assertAlmostEqual(
            self.player.db.skill_proficiency["fire_arrow"],
            20.0 + 2 * 10.0 * per_use,
        )

    @covers_requirement("settlement-stage-order::gauge-and-buff-elapsed-time-is-deterministic")
    def test_failed_advance_restores_consumed_booking_and_awarded_proficiency(self):
        from world.rules.clock import get_world_clock

        self.player.db.skill_proficiency = {"fire_arrow": 20.0}
        self.player.db.practice_booking = "fire_arrow"
        clock = get_world_clock()
        with (
            patch(
                "world.rules.clock._settle_boundary_stages",
                side_effect=RuntimeError("simulated post-practice failure"),
            ),
            self.assertRaises(RuntimeError),
        ):
            clock.advance(28800, AdvanceSource.SKIP, [self.player])
        # The stage consumed the booking and awarded XP before the boundary
        # failed; the rollback restores both registered surfaces to their
        # pre-advance values, leaving the declared intent retryable.
        self.assertEqual(self.player.db.skill_proficiency["fire_arrow"], 20.0)
        self.assertEqual(self.player.db.practice_booking, "fire_arrow")


class _FakeAttributeStore:
    """Minimal in-memory attribute handler for pure registry unit tests."""

    def __init__(self, values):
        self._values = dict(values)

    def has(self, key, category=None):
        return (key, category) in self._values

    def get(self, key, category=None):
        return self._values.get((key, category))


class AdvanceSurfaceContractUnitTests(unittest.TestCase):
    """Pure unit tests for the merged snapshot-registry builder (D2)."""

    def setUp(self):
        self._sources = dict(_EVENT_SOURCES)

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)

    def _entity(self, marker):
        return SimpleNamespace(
            attributes=_FakeAttributeStore(
                {("traits", "traits"): {"hp": marker}, ("buffs", None): [marker]}
            )
        )

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_registry_merges_caller_and_contract_surfaces_by_identity(self):
        caller = self._entity(1)
        discovered = self._entity(2)
        register_event_source(
            "quest_deadlines",
            lambda start, end: [],
            lambda start, end: {
                id(caller): SurfaceSnapshot(
                    attributes={("quest_log", None): (True, ["due"])}
                ),
                id(discovered): SurfaceSnapshot(
                    attributes={("mark", None): (True, "x")}
                ),
            },
        )
        registry = build_advance_snapshot_registry(
            WorldClock(), 60, AdvanceSource.SKIP, [caller]
        )
        # The caller entity appears once, with the union of both surfaces.
        self.assertEqual(len(registry), 2)
        caller_snapshot = registry[id(caller)]
        self.assertIn(("traits", "traits"), caller_snapshot.attributes)
        self.assertIn(("quest_log", None), caller_snapshot.attributes)
        self.assertEqual(caller_snapshot.attributes[("quest_log", None)], (True, ["due"]))
        # The contract-only object carries only its declared surface.
        self.assertEqual(
            registry[id(discovered)].attributes,
            {("mark", None): (True, "x")},
        )

    def test_kinds_without_a_contract_are_skipped_by_the_builder(self):
        called = []
        register_event_source(
            "caravan_arrivals",
            lambda start, end: called.append("settle") or [],
        )
        registry = build_advance_snapshot_registry(
            WorldClock(), 60, AdvanceSource.SKIP, []
        )
        self.assertEqual(registry, {})
        self.assertEqual(called, [])

    def test_contracts_run_in_stage_order(self):
        order = []
        for kind in ("caravan_arrivals", "shop_hours", "quest_deadlines"):
            register_event_source(
                kind,
                lambda start, end: [],
                lambda start, end, kind=kind: order.append(kind) or {},
            )
        build_advance_snapshot_registry(WorldClock(), 60, AdvanceSource.SKIP, [])
        self.assertEqual(order, ["caravan_arrivals", "shop_hours", "quest_deadlines"])

    def test_a_raising_contract_fails_the_advance_before_any_write(self):
        register_event_source(
            "npc_schedules",
            lambda start, end: [],
            lambda start, end: (_ for _ in ()).throw(RuntimeError("contract failed")),
        )
        with self.assertRaises(RuntimeError):
            build_advance_snapshot_registry(WorldClock(), 60, AdvanceSource.SKIP, [])

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_stage_sequence_and_day_bound_are_unchanged(self):
        self.assertEqual(
            _STAGE_ORDER,
            (
                "gauge_regen",
                "buff_ticks",
                "sexual_decay",
                "practice_settlement",
                "daily_resets",
                "caravan_arrivals",
                "shop_hours",
                "quest_deadlines",
                "npc_schedules",
                "instance_reclamation",
            ),
        )
        self.assertEqual(MAX_ADVANCE_SECONDS, 86400)


class AdvanceSurfaceContractTests(EvenniaTest):
    """Completeness guard and pure-read contract behavior (D4/D5)."""

    def setUp(self):
        super().setUp()
        self._sources = dict(_EVENT_SOURCES)

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        super().tearDown()

    @covers_requirement("world-clock::every-registered-boundary-stage-source-declares-the-durable-surfaces-it-may-write")
    def test_completeness_guard_writing_sources_declare_contracts(self):
        from world.maps.instance import register_instance_reclamation
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.caravan_arrivals import register_caravan_arrivals
        from world.rules.npc_schedules import register_npc_schedules
        from world.rules.shop_hours import register_shop_hours

        sync_quest_runtime()
        register_caravan_arrivals()
        register_npc_schedules()
        register_instance_reclamation()
        register_shop_hours()
        for kind in (
            "caravan_arrivals",
            "quest_deadlines",
            "npc_schedules",
            "instance_reclamation",
        ):
            registration = _EVENT_SOURCES[kind]
            self.assertIsNotNone(
                registration.surfaces,
                f"{kind} writes durable state and must declare a contract",
            )
        self.assertIsNone(
            _EVENT_SOURCES["shop_hours"].surfaces,
            "shop_hours is a read-only seam and must not declare a contract",
        )

    def test_synthetic_two_argument_source_still_runs_without_a_contract(self):
        entity = Entity()
        clock = WorldClock(86399)
        register_event_source(
            "caravan_arrivals",
            lambda start, end: [ScheduledEvent("caravan", end, {"key": "x"})],
        )
        events = clock.advance(2, AdvanceSource.COMBAT, [entity])
        self.assertEqual([event.kind for event in events], ["daily_reset", "caravan"])

    @covers_requirement("world-clock::every-registered-boundary-stage-source-declares-the-durable-surfaces-it-may-write")
    def test_contract_is_a_pure_read_that_never_mutates_state(self):
        from typeclasses.npcs import NPC
        from world.rules.npc_schedules import (
            SCHEDULE_TAG,
            set_npc_schedule,
            snapshot_npc_schedule_surfaces,
        )

        npc = create_object(NPC, key="pure-read-npc", location=self.room1)
        set_npc_schedule(
            npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "state", "state": "resting"}
                ],
            },
        )
        npc.db.schedule_state = "duty"
        before_state = npc.db.schedule_state
        before_location = npc.location
        snapshot_npc_schedule_surfaces(0, 86400)
        self.assertEqual(npc.db.schedule_state, before_state)
        self.assertIs(npc.location, before_location)
        self.assertTrue(npc.tags.has(SCHEDULE_TAG))

    def test_contracts_run_before_any_stage_write(self):
        order = []
        from world.rules.clock import _settle_boundary_stages

        register_event_source(
            "quest_deadlines",
            lambda start, end: order.append("settle") or [],
            lambda start, end: order.append("contract") or {},
        )
        with patch("world.rules.clock._settle_boundary_stages", wraps=_settle_boundary_stages):
            WorldClock().advance(60, AdvanceSource.COMBAT, [Entity()])
        self.assertEqual(order, ["contract", "settle"])

    @covers_requirement("world-clock::advance-has-a-bounded-settlement-budget-per-call")
    def test_oversized_advance_raises_before_contracts_run(self):
        called = []
        register_event_source(
            "quest_deadlines",
            lambda start, end: [],
            lambda start, end: called.append(True) or {},
        )
        with self.assertRaises(ClockAdvanceBoundError):
            WorldClock().advance(MAX_ADVANCE_SECONDS + 1, AdvanceSource.SKIP, [Entity()])
        self.assertEqual(called, [])


class OuterOwnerSeamTests(EvenniaTestCase):
    """The outer-owner seam: registry plus tick snapshot/restore around an
    outer transaction (D6, consumed by the movement/cast settlement changes)."""

    def setUp(self):
        super().setUp()
        from world.quests.runtime import QUEST_DEFINITION_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._sources = dict(_EVENT_SOURCES)
        self.player = create_object(PlayerCharacter, key="outer-seam-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.hours = 3600

    def tearDown(self):
        from world.quests.runtime import QUEST_DEFINITION_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _accept_due(self):
        from world.quests.tests._fixtures import quest, register

        self.due = register(quest("outer_seam_due", deadline_hours=1))
        with patch("world.quests.runtime._current_tick", return_value=0):
            from world.quests.runtime import accept_quest

            return accept_quest(self.player, self.due.key)

    def _raw_attribute(self, obj, key):
        """The raw stored Attribute row value for ``key``, read via SQL only.

        Reads through the ``db_attributes`` M2M join without instantiating any
        idmapper-cached Attribute model, so the value proves the database row
        (after rollback) rather than any in-process cache.
        """
        row = (
            obj.db_attributes.through.objects.filter(
                objectdb_id=obj.pk, attribute__db_key=key
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_outer_commit_failure_restores_registry_and_tick(self):
        from django.db import transaction
        from evennia.utils.search import search_script
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.clock import get_world_clock

        self._accept_due()
        sync_quest_runtime()
        clock = get_world_clock()
        script = search_script("world_clock")[0]
        before_tick = clock.tick
        before_log = list(self.player.db.quest_log)

        registry = build_advance_snapshot_registry(
            clock, 2 * self.hours, AdvanceSource.SKIP, [self.player]
        )
        tick_snapshot = _snapshot_clock_tick(clock)
        with transaction.atomic():
            clock.advance(2 * self.hours, AdvanceSource.SKIP, [self.player])
            # Simulate an outer-commit failure: the block exits rolled back
            # with no exception, leaving every cache advanced.
            transaction.set_rollback(True)
        _restore_clock_tick(clock, tick_snapshot)
        _restore_advance_registry(registry, [self.player])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(self._raw_attribute(self.player, "quest_log"), before_log)
