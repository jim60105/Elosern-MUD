"""Behaviour tests: the periodic drain pays the population backlog in slices.

After the observed-unit clock stage, an unobserved settlement unit keeps its own
settled-through tick until something settles it. The drain pays that debt off
the action path: one run settles the closed set with the lowest settled-through
tick forward by at most one bounded slice of game time, never past the world
tick, and leaves every other unit and the world tick alone.

Every scenario is built from the synthetic two-zone world of
:func:`world.maps.tests.test_scoped_population_settlement.build_two_zone_world`
and the file-local activity rows of ``test_monster_activity``; no shipped zone,
site, composition or individual is named, and no test asserts wall-clock time
or hardware speed. The drain's real-time cadence is exercised by calling the
Script's own functions with deterministic inputs, never by starting a timer or
sleeping. Because ``default`` is also the residual unit's cursor, every scenario
writes the cursor record explicitly so exactly the intended units lag.

The ``covers_requirement`` annotations of this module were added by the archive
workflow, after the delta sync gave the requirements their canonical
identifiers.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import Mock, patch

from django.conf import settings as django_settings
from django.test import override_settings
from evennia.utils.create import create_script

from tools.spec_traceability import covers_requirement
from typeclasses.monsters import Monster

from world.maps import (
    monster_activity,
    population_drain,
    population_lifecycle,
    population_units,
    regional_population,
)
from world.maps.monster_activity import read_monster_activity, state_to_dict
from world.maps.population_drain import (
    MAX_SETS_PER_RUN,
    PopulationDrainScript,
    drain_population_backlog,
)
from world.maps.population_lifecycle import (
    settle_population_lifecycle,
    settle_population_scope,
)
from world.maps.population_units import (
    UnitCursors,
    all_units,
    closed_sets,
    lagging_sets,
    write_unit_cursors,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_population_catch_up import _drop_attribute_caches
from world.maps.tests.test_scoped_population_settlement import (
    ScopedSettlementFixture,
    WANDER_A,
    WANDER_B,
    ZONE_A,
    ZONE_B,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import player_input
from world.rules.clock import get_world_clock
from world.rules.movement_edges import LocationRef

START = 100
#: One slice the design ships; the tests pass their own values where it matters.
SLICE = 600
#: A world tick far enough ahead that a slice never reaches it.
FAR_TICK = 5000
#: The tick the drain-to-completion comparison settles through.
COMPLETION_TICK = 1600
#: One cell no authored rectangle covers: its unit is the residual unit.
RESIDUAL_CELL = (900, 900)


class DrainFixture(ScopedSettlementFixture):
    """The two-zone world plus the explicit clock and cursor record helpers."""

    def setUp(self):
        super().setUp()
        player_input.reset_player_input()
        self.addCleanup(player_input.reset_player_input)
        self._build_scenario(end_tick=COMPLETION_TICK)

    # -- runs ---------------------------------------------------------------

    def drain(self, slice_seconds: int = SLICE) -> bool:
        return drain_population_backlog(slice_seconds)

    def set_world_tick(self, tick: int) -> None:
        clock = get_world_clock()
        clock.tick = tick
        clock._persist(tick)

    def write_cursors(self, default: int, units: dict[str, int]) -> None:
        """Write the whole record; units the dict omits report ``default``."""
        write_unit_cursors(
            self.wilderness, UnitCursors(default, MappingProxyType(dict(units)))
        )

    # -- reads --------------------------------------------------------------

    def cursors(self) -> population_units.UnitCursors:
        return population_units.read_unit_cursors(self.wilderness)

    def settled_through(self, unit: str) -> int:
        return population_units.unit_cursor(self.cursors(), unit)

    def world_tick(self) -> int:
        return get_world_clock().tick

    def index(self) -> population_units.UnitIndex:
        return population_units.current_unit_index()

    def drop_caches(self) -> None:
        _drop_attribute_caches(self.wilderness, *Monster.objects.all_family())

    # -- state --------------------------------------------------------------

    def link_group_home(self, group_id: str, cell: tuple[int, int]) -> None:
        """Rewrite one stored group's home to ``cell``, linking its units.

        A group touching two settlement units is the lawful linked case the
        closure rule covers; no writer needs a new entry point for it.
        """
        state = read_monster_activity(self.wilderness)
        groups = dict(state.groups)
        groups[group_id] = replace(
            groups[group_id], home=LocationRef.wilderness(WILDERNESS_NAME, *cell)
        )
        self.wilderness.db.monster_activity = state_to_dict(
            replace(state, groups=groups)
        )

    def events(self, logged) -> list:
        return [call for call in logged.call_args_list if call.args]


class LaggingSetTests(DrainFixture):
    """The drain picks the lowest closed set and never passes the world tick."""

    @covers_requirement(
        "population-settlement-units::"
        "a-drain-run-settles-the-most-lagging-closed-set-by-one-bounded-slice"
    )
    def test_one_slice_moves_the_most_lagging_set_and_keeps_the_world_tick(self):
        self.set_world_tick(FAR_TICK)
        self.write_cursors(FAR_TICK, {self.unit_a: START, self.unit_b: 400})
        self.assertEqual(
            lagging_sets(self.wilderness, FAR_TICK),
            (
                (START, frozenset({self.unit_a})),
                (400, frozenset({self.unit_b})),
            ),
            "the sets are ordered by cursor, ties by their smallest unit",
        )
        self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)
        self.assertEqual(self.settled_through(self.unit_b), 400)
        self.assertEqual(self.world_tick(), FAR_TICK)

    @covers_requirement(
        "population-settlement-units::"
        "a-drain-run-settles-the-most-lagging-closed-set-by-one-bounded-slice"
    )
    def test_a_slice_ends_at_the_world_tick(self):
        self.set_world_tick(500)
        self.write_cursors(500, {self.unit_a: START})
        self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), 500)
        self.assertEqual(self.world_tick(), 500)

    @covers_requirement(
        "population-settlement-units::"
        "a-drain-run-settles-the-most-lagging-closed-set-by-one-bounded-slice"
    )
    def test_a_current_world_writes_nothing_and_emits_nothing(self):
        before = self.cursors()
        projection = settlement_projection(self.wilderness)
        with patch.object(population_drain, "log_info") as info:
            self.assertFalse(self.drain())
        info.assert_not_called()
        self.assertEqual(self.cursors(), before)
        self.assertEqual(settlement_projection(self.wilderness), projection)

    @covers_requirement(
        "population-settlement-units::"
        "a-drain-run-settles-the-most-lagging-closed-set-by-one-bounded-slice"
    )
    def test_linked_units_move_together(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START, self.unit_b: START})
        self.link_group_home(self.group_ids[ZONE_B][0], WANDER_A)
        self.assertEqual(
            lagging_sets(self.wilderness, 700),
            ((START, frozenset({self.unit_a, self.unit_b})),),
            "one group touching both units closes them into one set",
        )
        self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)
        self.assertEqual(self.settled_through(self.unit_b), START + SLICE)

    def test_closed_sets_partition_every_index_unit(self):
        state = read_monster_activity(self.wilderness)
        index = self.index()
        units = all_units(index)
        sets = closed_sets(index, state, units)
        self.assertEqual(
            set().union(*sets),
            set(units),
            "every unit of the index belongs to one closed set",
        )
        self.assertEqual(
            sum(len(closed) for closed in sets),
            len(set().union(*sets)),
            "distinct closed sets are disjoint",
        )
        self.assertIn(population_units.RESIDUAL_UNIT, units)
        self.assertIn(self.unit_a, units)
        self.assertIn(self.unit_b, units)


class DrainEquivalenceTests(DrainFixture):
    """A drained world is the world a whole-world pass leaves."""

    @covers_requirement(
        "population-settlement-units::draining-gives-the-whole-world-result"
    )
    def test_one_slice_equals_one_scoped_pass_over_the_same_interval(self):
        self.set_world_tick(COMPLETION_TICK)
        self.write_cursors(COMPLETION_TICK, {self.unit_a: START})
        self.assertTrue(self.drain())
        drained = settlement_projection(self.wilderness)

        self._build_scenario(end_tick=COMPLETION_TICK)
        self.set_world_tick(COMPLETION_TICK)
        self.write_cursors(COMPLETION_TICK, {self.unit_a: START})
        settle_population_scope(self.wilderness, {self.unit_a}, START + SLICE)
        self.assertEqual(settlement_projection(self.wilderness), drained)

    @covers_requirement(
        "population-settlement-units::draining-gives-the-whole-world-result"
    )
    def test_drain_to_completion_equals_one_whole_world_pass(self):
        self.set_world_tick(COMPLETION_TICK)
        self.write_cursors(COMPLETION_TICK, {self.unit_a: START, self.unit_b: START})
        runs = 0
        while self.drain():
            runs += 1
            if runs >= 200:
                self.fail("the drain did not converge within 200 runs")
        self.assertEqual(lagging_sets(self.wilderness, COMPLETION_TICK), ())
        drained = settlement_projection(self.wilderness)

        self._build_scenario(end_tick=COMPLETION_TICK)
        settle_population_lifecycle(START, COMPLETION_TICK)
        self.assertEqual(settlement_projection(self.wilderness), drained)


class DrainReportTests(DrainFixture):
    """A settled run reports itself; a failed run keeps every prior value."""

    @covers_requirement(
        "population-settlement-units::a-drain-run-is-atomic-and-reports-itself"
    )
    def test_reported_slice(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START, self.unit_b: 400})
        with (
            patch.object(population_drain, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertTrue(self.drain())
        events = self.events(info)
        self.assertEqual(len(events), 1, "one info event per settled run")
        self.assertEqual(events[0].args[0], "population_backlog_drained")
        self.assertEqual(
            events[0].kwargs["context"],
            {
                "units": 1,
                "tick_from": START,
                "tick_to": START + SLICE,
                "remaining": 1,
            },
            "the event names the settled unit, both ticks and the lagging unit",
        )

    @covers_requirement(
        "population-settlement-units::a-drain-run-is-atomic-and-reports-itself"
    )
    def test_the_reported_remaining_count_is_units_not_sets(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START, self.unit_b: 400})
        self.link_group_home(self.group_ids[ZONE_B][0], RESIDUAL_CELL)
        self.assertEqual(
            lagging_sets(self.wilderness, 700),
            (
                (START, frozenset({self.unit_a})),
                (400, frozenset({self.unit_b, population_units.RESIDUAL_UNIT})),
            ),
        )
        with (
            patch.object(population_drain, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertTrue(self.drain())
        context = self.events(info)[0].kwargs["context"]
        self.assertEqual(context["units"], 1)
        # The linked set still lags through unit B, but the residual unit it
        # also holds already stands at the world tick: one unit lags, not two.
        self.assertEqual(context["remaining"], 1)

    @covers_requirement(
        "population-settlement-units::a-drain-run-is-atomic-and-reports-itself"
    )
    def test_a_linked_set_keeps_its_current_unit_and_reports_only_lagging_units(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: 700, self.unit_b: START})
        self.link_group_home(self.group_ids[ZONE_B][0], WANDER_A)
        self.assertEqual(
            lagging_sets(self.wilderness, 700),
            ((START, frozenset({self.unit_a, self.unit_b})),),
        )
        with (
            patch.object(population_drain, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertTrue(self.drain(300))
        self.assertEqual(self.settled_through(self.unit_b), 400)
        self.assertEqual(
            self.settled_through(self.unit_a),
            700,
            "a settlement never rewinds an already-current unit",
        )
        context = self.events(info)[0].kwargs["context"]
        self.assertEqual(context["units"], 2)
        self.assertEqual(context["tick_to"], 400)
        self.assertEqual(context["remaining"], 1)

    @covers_requirement(
        "population-settlement-units::a-drain-run-is-atomic-and-reports-itself"
    )
    def test_a_failed_run_keeps_the_prior_state_and_the_next_run_settles(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        before = settlement_projection(self.wilderness)
        recorded: dict = {}
        real = regional_population.record_population_transition

        def fail_on_a_departure(wilderness, transition):
            """Fail once the departure's own writes are already in flight."""
            if transition.after.position is None and transition.before.position is not None:
                recorded["individual"] = transition.individual_id
                recorded["coordinates"] = dict(wilderness.db.itemcoordinates)
                raise RuntimeError("injected drain fault")
            return real(wilderness, transition)

        with (
            patch.object(
                regional_population,
                "record_population_transition",
                fail_on_a_departure,
            ),
            patch.object(population_drain, "log_error") as error,
            patch.object(population_drain, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertFalse(self.drain())
        self.assertIn("individual", recorded, "the run reached a departure")
        body = next(
            body
            for body in self.bodies[ZONE_A]
            if int(body.pk) == recorded["individual"]
        )
        self.assertNotIn(
            body,
            recorded["coordinates"],
            "the departure detached the individual before the fault",
        )
        self.assertEqual(self.settled_through(self.unit_a), START)
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.drop_caches()
        self.assertEqual(settlement_projection(self.wilderness), before)
        events = self.events(error)
        self.assertEqual(len(events), 1, "one error event per failed run")
        self.assertEqual(events[0].args[0], "population_backlog_drain_failed")
        self.assertEqual(
            events[0].kwargs["context"],
            {"units": 1, "tick_from": START, "tick_to": 700},
        )
        info.assert_not_called()

        self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)

    @covers_requirement(
        "population-settlement-units::a-drain-run-is-atomic-and-reports-itself"
    )
    def test_a_failing_set_does_not_starve_the_next(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START, self.unit_b: START})
        real = population_lifecycle.settle_population_scope

        def fail_the_first_set(wilderness, seeds, end_tick, *, contact=False):
            if self.unit_a in set(seeds):
                raise RuntimeError("injected set fault")
            return real(wilderness, seeds, end_tick, contact=contact)

        with (
            patch.object(
                population_lifecycle, "settle_population_scope", fail_the_first_set
            ),
            patch.object(population_drain, "log_error") as error,
            patch.object(population_drain, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), START)
        self.assertEqual(self.settled_through(self.unit_b), START + SLICE)
        errors = self.events(error)
        self.assertEqual(len(errors), 1, "one error event for the failing set")
        self.assertEqual(
            errors[0].kwargs["context"],
            {"units": 1, "tick_from": START, "tick_to": 700},
        )
        events = self.events(info)
        self.assertEqual(len(events), 1, "the next set still reports itself")
        self.assertEqual(
            events[0].kwargs["context"],
            {
                "units": 1,
                "tick_from": START,
                "tick_to": START + SLICE,
                "remaining": 1,
            },
        )


class PeriodicCallerTests(DrainFixture):
    """The periodic caller repeats once per interval and honours its switch."""

    @covers_requirement(
        "population-settlement-units::the-periodic-drain-honours-its-switch"
    )
    def test_disabled_repeat_does_not_drain(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with (
            override_settings(POPULATION_DRAIN_ENABLED=False),
            patch.object(
                population_drain,
                "drain_population_backlog",
                wraps=drain_population_backlog,
            ) as drain,
        ):
            PopulationDrainScript.at_repeat(Mock())
        drain.assert_not_called()
        self.assertEqual(self.settled_through(self.unit_a), START)

    @covers_requirement(
        "population-settlement-units::the-periodic-drain-honours-its-switch"
    )
    def test_enabled_repeat_drains_once_with_the_configured_slice(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with (
            override_settings(
                POPULATION_DRAIN_ENABLED=True, POPULATION_DRAIN_SLICE_SECONDS=SLICE
            ),
            patch.object(
                population_drain,
                "drain_population_backlog",
                wraps=drain_population_backlog,
            ) as drain,
            self.captureOnCommitCallbacks(execute=True),
        ):
            PopulationDrainScript.at_repeat(Mock())
        drain.assert_called_once_with(SLICE)
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)

    @covers_requirement(
        "population-settlement-units::the-periodic-drain-yields-to-recent-player-input"
    )
    def test_recent_input_repeat_reads_nothing_and_drains_nothing(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with (
            override_settings(
                POPULATION_DRAIN_ENABLED=True, POPULATION_DRAIN_IDLE_SECONDS=20
            ),
            patch.object(player_input, "_now", side_effect=[100.0, 102.0]),
            patch.object(
                population_drain,
                "drain_population_backlog",
                wraps=drain_population_backlog,
            ) as drain,
            patch.object(population_units, "lagging_sets", wraps=lagging_sets) as lagging,
            patch.object(
                monster_activity,
                "read_monster_activity",
                wraps=read_monster_activity,
            ) as activity,
            patch.object(population_drain, "log_info") as info,
        ):
            player_input.note_player_input()
            PopulationDrainScript.at_repeat(Mock())
        drain.assert_not_called()
        lagging.assert_not_called()
        activity.assert_not_called()
        info.assert_not_called()
        self.assertEqual(self.settled_through(self.unit_a), START)

    @covers_requirement(
        "population-settlement-units::the-periodic-drain-yields-to-recent-player-input"
    )
    def test_a_window_old_input_repeat_drains_once(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with (
            override_settings(
                POPULATION_DRAIN_ENABLED=True, POPULATION_DRAIN_IDLE_SECONDS=20
            ),
            patch.object(player_input, "_now", side_effect=[100.0, 120.0]),
            patch.object(
                population_drain,
                "drain_population_backlog",
                wraps=drain_population_backlog,
            ) as drain,
            self.captureOnCommitCallbacks(execute=True),
        ):
            player_input.note_player_input()
            PopulationDrainScript.at_repeat(Mock())
        drain.assert_called_once_with(SLICE)
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)

    @covers_requirement(
        "population-settlement-units::the-periodic-drain-yields-to-recent-player-input"
    )
    def test_no_recorded_input_repeat_drains_once(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        player_input.reset_player_input()
        with (
            override_settings(
                POPULATION_DRAIN_ENABLED=True, POPULATION_DRAIN_IDLE_SECONDS=20
            ),
            patch.object(
                population_drain,
                "drain_population_backlog",
                wraps=drain_population_backlog,
            ) as drain,
            self.captureOnCommitCallbacks(execute=True),
        ):
            PopulationDrainScript.at_repeat(Mock())
        drain.assert_called_once_with(SLICE)
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)

    def test_script_creation_reads_the_configured_interval(self):
        script = create_script(PopulationDrainScript, obj=None, autostart=False)
        self.assertEqual(script.key, "population_drain")
        self.assertEqual(
            script.interval, django_settings.POPULATION_DRAIN_INTERVAL_SECONDS
        )
        self.assertTrue(script.persistent)
        self.assertGreater(MAX_SETS_PER_RUN, 0)


class IdleWindowBypassTests(DrainFixture):
    """The catch-up and a direct drain ignore the recorded player input."""

    @covers_requirement(
        "population-settlement-units::catch-up-and-direct-drains-ignore-the-idle-window"
    )
    def test_catch_up_during_activity_settles_to_the_world_tick(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with patch.object(player_input, "_now", return_value=100.0):
            player_input.note_player_input()
            self.assertTrue(
                population_lifecycle.ensure_population_current(
                    self.wilderness, {self.unit_a}
                )
            )
        self.assertEqual(self.settled_through(self.unit_a), self.world_tick())

    @covers_requirement(
        "population-settlement-units::catch-up-and-direct-drains-ignore-the-idle-window"
    )
    def test_direct_drain_during_activity_settles_one_slice(self):
        self.set_world_tick(700)
        self.write_cursors(700, {self.unit_a: START})
        with (
            patch.object(player_input, "_now", return_value=100.0),
            self.captureOnCommitCallbacks(execute=True),
        ):
            player_input.note_player_input()
            self.assertTrue(self.drain())
        self.assertEqual(self.settled_through(self.unit_a), START + SLICE)


class QuietRunTests(DrainFixture):
    """An absent world, seed or record settles nothing and reports nothing."""

    def test_slice_must_be_a_positive_integer(self):
        for bad in (0, -1, True, 1.5, "600"):
            with self.subTest(slice_seconds=bad):
                with self.assertRaises(ValueError):
                    drain_population_backlog(bad)

    def test_no_world_settles_nothing_without_an_event(self):
        with (
            patch.object(regional_population, "live_wilderness", return_value=None),
            patch.object(population_drain, "log_error") as error,
        ):
            self.assertFalse(self.drain())
        error.assert_not_called()

    def test_an_unseeded_world_settles_nothing_without_an_event(self):
        with (
            patch.object(
                regional_population, "population_provisioned", return_value=False
            ),
            patch.object(population_drain, "log_error") as error,
        ):
            self.assertFalse(self.drain())
        error.assert_not_called()

    def test_a_missing_cursor_record_settles_nothing_without_an_event(self):
        self.wilderness.attributes.remove(
            population_units.POPULATION_UNIT_CURSORS_ATTRIBUTE
        )
        with patch.object(population_drain, "log_error") as error:
            self.assertFalse(self.drain())
        error.assert_not_called()