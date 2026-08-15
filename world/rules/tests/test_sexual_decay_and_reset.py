"""Tests for clock-independent decay and daily reset callables."""

from tools.spec_traceability import covers_requirement

import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules import sexual_state
from world.rules.sexual_state import decay_tick, reset_daily_counters


class SexualDecayAndResetTests(EvenniaTest):
    def test_decay_accumulates_and_moves_at_most_one_level(self):
        entity = create_object(PlayerCharacter, key="decay")
        entity.sexual.pleasure.base = 85
        decay_tick(entity, 1799)
        self.assertEqual(entity.sexual.arousal.level, "極限")
        decay_tick(entity, 1)
        self.assertEqual(entity.sexual.arousal.level, "高度")
        decay_tick(entity, 3600)
        self.assertEqual(entity.sexual.arousal.level, "中等")

    def test_afterglow_decay_routes_through_guard(self):
        entity = create_object(PlayerCharacter, key="afterglow")
        entity.sexual.climax_phase.value = "餘韻"
        original = sexual_state._apply_climax_phase_set
        calls = []

        def recording_guard(target, level):
            calls.append((target, level))
            return original(target, level)

        sexual_state._apply_climax_phase_set = recording_guard
        try:
            decay_tick(entity, 300)
        finally:
            sexual_state._apply_climax_phase_set = original
        self.assertEqual(calls, [(entity, "未達")])
        self.assertEqual(entity.sexual.climax_phase.level, "未達")

    def test_afterglow_does_not_reuse_time_from_another_phase(self):
        entity = create_object(PlayerCharacter, key="fresh afterglow interval")
        decay_tick(entity, 299)
        entity.sexual.climax_phase.value = "餘韻"
        decay_tick(entity, 1)
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")
        decay_tick(entity, 299)
        self.assertEqual(entity.sexual.climax_phase.level, "未達")

    def test_daily_reset_changes_only_counter(self):
        entity = create_object(PlayerCharacter, key="daily reset")
        entity.sexual.pleasure.base = 35
        entity.sexual.record_climax()
        before = entity.sexual.arousal.level
        reset_daily_counters(entity)
        self.assertEqual(entity.sexual.climax_today, 0)
        self.assertEqual(entity.sexual.arousal.level, before)

    @covers_requirement("sexual-state-handler::decay-tick-decays-pleasure-by-crossing-exactly-one-band-per-configured-interval")
    def test_decay_from_the_middle_of_a_band_crosses_to_the_band_below(self):
        entity = create_object(PlayerCharacter, key="mid-band decay")
        entity.sexual.pleasure.base = 72
        decay_tick(entity, 1800)
        self.assertEqual(entity.sexual.pleasure.value, 59)
        self.assertEqual(entity.sexual.arousal.level, "中等")

    @covers_requirement("sexual-state-handler::decay-tick-decays-pleasure-by-crossing-exactly-one-band-per-configured-interval")
    def test_decay_at_the_floor_band_clamps_at_pleasure_zero(self):
        entity = create_object(PlayerCharacter, key="floor-band decay")
        entity.sexual.pleasure.base = 5
        decay_tick(entity, 1800)
        self.assertEqual(entity.sexual.pleasure.value, 0)

    @covers_requirement("sexual-state-handler::decay-tick-decays-pleasure-by-crossing-exactly-one-band-per-configured-interval")
    def test_decay_never_crosses_more_than_one_band_per_interval(self):
        entity = create_object(PlayerCharacter, key="single-band decay")
        entity.sexual.pleasure.base = 85
        decay_tick(entity, 1800)
        self.assertEqual(entity.sexual.pleasure.value, 84)
        self.assertEqual(entity.sexual.arousal.level, "高度")

    @covers_requirement("sexual-state-handler::decay-tick-and-reset-daily-counters-are-exposed-as-plain-callables-with-no-settlement-order-invented")
    def test_module_has_no_clock_or_settlement_policy(self):
        source = inspect.getsource(sexual_state)
        self.assertNotIn("WorldClock", source)
        self.assertNotIn("settlement_order", source)
        self.assertNotIn("trait_regen", source)
        self.assertNotIn("tick_buffs", source)
