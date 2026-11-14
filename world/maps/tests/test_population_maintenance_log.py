"""One aggregated maintenance line per population settlement pass.

A pass moves many bodies; the per-entity events it commits are debug detail and
one info summary carries their counts. The same events committed outside a pass
keep their info level.
"""

from __future__ import annotations

from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement

from world.maps import population_lifecycle, regional_population
from world.maps import monster_activity as activity_owner
from world.maps.monster_activity import (
    commit_group_decision,
    plan_group_decision,
    read_monster_activity,
)
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.tests.test_monster_activity import ActivityFixture, STATIONARY_ACTIVITY
from world.rules.fatigue import (
    FatigueActivity,
    FatigueInterval,
    read_fatigue_state,
    settle_fatigue_intervals,
)

#: The five events a settlement pass counts instead of emitting one info each.
MAINTENANCE_EVENTS = (
    "fatigue_transition",
    "monster_activity_decided",
    "monster_departed",
    "monster_arrived",
    "monster_arrival_deferred",
)

#: The tick the departing group's seed commits its departure at.
DEPARTURE_TICK = 90


def _events(logged) -> list[str]:
    return [call.args[0] for call in logged.call_args_list if call.args]


def _stationary_tick(arrival: int) -> int:
    """The creation tick that gives each stationary group one pass decision."""
    return max(0, arrival - activity_owner.RESTING_DECISION_INTERVAL)


def _stationary_due(arrival: int) -> int:
    return _stationary_tick(arrival) + activity_owner.activity_decision_interval(
        STATIONARY_ACTIVITY
    )


class PopulationMaintenanceLogTests(ActivityFixture):
    """Summary counts, debug detail, and the info level outside a pass."""

    def _scenario_groups(
        self, seed: int, arrival: int
    ) -> tuple[str, tuple[object, ...]]:
        """One two-member departing group and two late stationary groups.

        The stationary groups are created so their single decision in the pass
        falls after the departure and before the arrival, and their slower
        resting cadence keeps the next decision beyond the arrival.
        """
        self._reset_activity(tick=0)
        group_id, bodies = self._group(seed=seed, tick=0, members=2)
        stationary_tick = _stationary_tick(arrival)
        self.assertGreater(
            _stationary_due(arrival),
            DEPARTURE_TICK,
            "the stationary cadence must fall after the departure and before "
            "the arrival for exactly one decision per group",
        )
        self._group(activity=STATIONARY_ACTIVITY, tick=stationary_tick, members=1)
        self._group(activity=STATIONARY_ACTIVITY, tick=stationary_tick, members=1)
        return group_id, bodies

    def _arrival_tick(self, seed: int) -> int:
        """The departing group's arrival tick, read after the departure pass."""
        self._reset_activity(tick=0)
        group_id, _bodies = self._group(seed=seed, tick=0, members=2)
        with self.captureOnCommitCallbacks(execute=False):
            settle_population_lifecycle(0, DEPARTURE_TICK)
        state = read_monster_activity(self.wilderness)
        journey_id = state.groups[group_id].journey_id
        if journey_id is None:
            return DEPARTURE_TICK
        return state.journeys[journey_id].arrival_tick

    @covers_requirement(
        "observability-logging::world-maintenance-settlement-reports-one-aggregated-event-per-pass"
    )
    def test_many_groups_emit_one_info_summary_and_debug_detail(self) -> None:
        self._register_lifecycle()
        seed = self._departure_seed(tick=DEPARTURE_TICK, members=2)
        arrival = self._arrival_tick(seed)
        _group_id, bodies = self._scenario_groups(seed, arrival)
        end_tick = max(arrival, _stationary_due(arrival))
        with (
            patch.object(activity_owner, "log_info") as activity_info,
            patch.object(activity_owner, "log_debug") as activity_debug,
            patch("world.rules.fatigue.log_info") as fatigue_info,
            patch("world.rules.fatigue.log_debug") as fatigue_debug,
            patch.object(population_lifecycle, "log_info") as lifecycle_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settle_population_lifecycle(0, end_tick)
        summaries = [
            call
            for call in lifecycle_info.call_args_list
            if call.args and call.args[0] == "population_maintenance_settled"
        ]
        self.assertEqual(len(summaries), 1)
        context = summaries[0].kwargs["context"]
        self.assertEqual(context["tick_from"], 0)
        self.assertEqual(context["tick_to"], end_tick)
        self.assertEqual(context["monster_activity_decided"], 3)
        self.assertEqual(context["monster_departed"], len(bodies))
        self.assertEqual(context["monster_arrived"], len(bodies))
        info_events = _events(activity_info) + _events(fatigue_info)
        self.assertEqual(
            [event for event in info_events if event in MAINTENANCE_EVENTS], []
        )
        debug_events = _events(activity_debug) + _events(fatigue_debug)
        self.assertEqual(debug_events.count("monster_activity_decided"), 3)
        self.assertEqual(debug_events.count("monster_departed"), len(bodies))
        self.assertEqual(debug_events.count("monster_arrived"), len(bodies))

    @covers_requirement(
        "observability-logging::world-maintenance-settlement-reports-one-aggregated-event-per-pass"
    )
    def test_a_quiet_pass_emits_no_summary(self) -> None:
        self.assertTrue(regional_population.population_provisioned(self.wilderness))
        with (
            patch.object(population_lifecycle, "log_info") as lifecycle_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settle_population_lifecycle(0, 0)
        lifecycle_info.assert_not_called()

    @covers_requirement(
        "observability-logging::world-maintenance-settlement-reports-one-aggregated-event-per-pass"
    )
    def test_a_rolled_back_advance_emits_neither_summary_nor_detail(self) -> None:
        self._register_lifecycle()
        seed = self._departure_seed(tick=DEPARTURE_TICK, members=2)
        arrival = self._arrival_tick(seed)
        self._scenario_groups(seed, arrival)
        end_tick = max(arrival, _stationary_due(arrival))
        with (
            patch.object(activity_owner, "log_info") as activity_info,
            patch.object(activity_owner, "log_debug") as activity_debug,
            patch("world.rules.fatigue.log_info") as fatigue_info,
            patch("world.rules.fatigue.log_debug") as fatigue_debug,
            patch.object(population_lifecycle, "log_info") as lifecycle_info,
        ):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    with self.captureOnCommitCallbacks(execute=False) as callbacks:
                        settle_population_lifecycle(0, end_tick)
                        settled = read_monster_activity(self.wilderness)
                        self.assertGreater(
                            max(group.sequence for group in settled.groups.values()),
                            0,
                        )
                    self.assertTrue(callbacks)
                    raise RuntimeError("late clock stage")
        for logged in (
            activity_info,
            activity_debug,
            fatigue_info,
            fatigue_debug,
            lifecycle_info,
        ):
            logged.assert_not_called()

    @covers_requirement(
        "observability-logging::maintenance-events-outside-a-settlement-pass-keep-info-level"
    )
    def test_a_direct_owner_decision_stays_at_info(self) -> None:
        group_id, _bodies = self._group(tick=0, members=1)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        with (
            patch.object(activity_owner, "log_info") as activity_info,
            patch.object(activity_owner, "log_debug") as activity_debug,
            self.captureOnCommitCallbacks(execute=True),
        ):
            commit_group_decision(self.wilderness, decision)
        decided = [
            call
            for call in activity_info.call_args_list
            if call.args and call.args[0] == "monster_activity_decided"
        ]
        self.assertEqual(len(decided), 1)
        self.assertEqual(
            set(decided[0].kwargs["context"]),
            {"group", "sequence", "tick", "reason"},
        )
        activity_debug.assert_not_called()

    @covers_requirement(
        "observability-logging::maintenance-events-outside-a-settlement-pass-keep-info-level"
    )
    def test_fatigue_settled_outside_a_pass_stays_at_info(self) -> None:
        body = self._monster()
        interval = FatigueInterval(
            body, FatigueActivity.AWAKE, 600, read_fatigue_state(body)
        )
        with (
            patch("world.rules.fatigue.log_info") as fatigue_info,
            patch("world.rules.fatigue.log_debug") as fatigue_debug,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settle_fatigue_intervals((interval,))
        self.assertEqual(_events(fatigue_info), ["fatigue_transition"])
        fatigue_debug.assert_not_called()

    @covers_requirement(
        "observability-logging::maintenance-events-outside-a-settlement-pass-keep-info-level"
    )
    def test_a_contact_inside_a_pass_stays_at_info_and_is_not_counted(self) -> None:
        body = self._monster()
        interval = FatigueInterval(
            body, FatigueActivity.AWAKE, 600, read_fatigue_state(body)
        )

        def contact(_wilderness, _tick, _contact_tick):
            settle_fatigue_intervals((interval,))
            return []

        with (
            patch(
                "world.rules.field_contact.settle_population_contact_at",
                side_effect=contact,
            ),
            patch("world.rules.fatigue.log_info") as fatigue_info,
            patch("world.rules.fatigue.log_debug") as fatigue_debug,
            patch.object(population_lifecycle, "log_info") as lifecycle_info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settle_population_lifecycle(0, 0)
        self.assertEqual(_events(fatigue_info), ["fatigue_transition"])
        fatigue_debug.assert_not_called()
        lifecycle_info.assert_not_called()
