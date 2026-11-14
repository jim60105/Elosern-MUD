"""Behaviour tests: a clock advance settles the observed units only.

The registered population stage settles the closed set a player character
observes -- plus every unit linked to it by a group -- through the advance's end
tick, and leaves every other unit's records, individuals and settled-through
tick alone. The proof is equality of state: a world advanced that way and then
caught up everywhere is the world equal whole-world passes leave, and one
advance's decisions, snapshots and rollback do not depend on how much the
unobserved units hold.

Every scenario is built from the synthetic two-zone world of
:func:`world.maps.tests.test_scoped_population_settlement.build_two_zone_world`
and a player placed by
:func:`world.maps.tests.test_population_catch_up.place_player`; no shipped zone,
site, composition or individual is named, and no test asserts wall-clock time or
hardware speed. The delta's requirements are ADDED, so their canonical
identifiers exist only after the archive sync and these tests carry no
``covers_requirement`` annotation yet.
"""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import patch

from django.test import override_settings
from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

import world.lore.monster_activity as lore_activity
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.maps import (
    monster_activity,
    population_forecast,
    population_lifecycle,
    population_units,
)
from world.maps.population_lifecycle import (
    settle_population_lifecycle,
    settle_population_scope,
)
from world.maps.regional_population import read_population_timeline, zone_state
from world.maps.tests._settlement_projection import (
    catch_up_world,
    settlement_projection,
)
from world.maps.tests.test_population_catch_up import (
    _drop_attribute_caches,
    place_player,
)
from world.maps.tests.test_scoped_population_settlement import (
    ACTIVITY_B_WANDER,
    AREA_KEY,
    ScopedSettlementFixture,
    WANDER_A,
    WANDER_B,
    ZONE_A,
    ZONE_B,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import field_contact
from world.rules.clock import AdvanceSource, advance_scope, get_world_clock
from world.rules.combat_session import forfeit
from world.rules.fatigue import (
    SleepPosture,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.field_contact import forecast_observers
from world.rules.movement_edges import quote_edge
from world.rules.surfaces import persisted_hp
from world.rules.tests._combat_session_helpers import _race_key
from world.rules.world_escape import build_journey_plan
from typeclasses.monsters import Monster

START = 100
END = 1600

#: One contact-admitting walking binding and one stationary one, both inside
#: the fixture's first zone. They are file-local activity rows, never shipped.
CONTACT_ACTIVITY = "t_observed_contact_walker"
CONTACT_STATIONARY = "t_observed_contact_stationary"

#: A zone-A cell that is no site, no scenario group and no zone-B neighbour.
OBSERVER_CELL = (505, 705)


class ObservedAdvanceFixture(ScopedSettlementFixture):
    """The two-zone world with the observed clock stage installed."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    # -- runs ---------------------------------------------------------------

    def advance(self, seconds: int) -> list:
        """One command advance with no party in the advance's own scope."""
        return get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])

    def set_world_tick(self, tick: int) -> None:
        clock = get_world_clock()
        clock.tick = tick
        clock._persist(tick)

    # -- reads --------------------------------------------------------------

    def cursors(self) -> population_units.UnitCursors:
        return population_units.read_unit_cursors(self.wilderness)

    def settled_through(self, unit: str) -> int:
        return population_units.unit_cursor(self.cursors(), unit)

    def far_zone_state(self) -> dict:
        """Every durable and live fact of the unobserved zone's unit."""
        state = monster_activity.read_monster_activity(self.wilderness)
        group_id = self.group_ids[ZONE_B][0]
        group = state.groups[group_id]
        return {
            "zone": zone_state(self.wilderness, ZONE_B),
            "group": group,
            "journey": state.journeys.get(group.journey_id),
            "bodies": tuple(
                (
                    self.wilderness.db.itemcoordinates.get(body),
                    getattr(body.location, "pk", None),
                    persisted_hp(body),
                    read_optional_fatigue_state(body),
                )
                for body in self.bodies[ZONE_B]
            ),
        }

    def drop_caches(self) -> None:
        _drop_attribute_caches(self.wilderness, *Monster.objects.all_family())

    def place_party(self, cell: tuple[int, int]):
        """A placed player with the physiology an authored contact reads."""
        player = place_player(self, cell)
        player.race = _race_key()
        player.apply_race_baseline()
        player.traits.hp.base = 5000
        player.traits.hp.current = 5000
        write_fatigue_state(player, 360000, SleepPosture.AWAKE)
        return player


class ObservedScopeTests(ObservedAdvanceFixture):
    """A clock advance settles the observed units and nothing else."""

    def test_the_far_unit_keeps_its_records_individuals_and_tick(self):
        self._build_scenario()
        place_player(self, WANDER_A)
        before = self.far_zone_state()
        self.advance(600)
        self.assertEqual(self.settled_through(self.unit_a), 700)
        self.assertEqual(self.settled_through(self.unit_b), START)
        self.assertEqual(self.far_zone_state(), before)

    def test_an_observed_unit_behind_the_start_settles_from_its_cursor(self):
        self._build_scenario()
        place_player(self, WANDER_A)
        self.set_world_tick(400)
        self.advance(300)
        self.assertEqual(self.settled_through(self.unit_a), 700)
        observed = settlement_projection(self.wilderness)
        # The same rebuilt world, settled by one scoped pass over the interval.
        self._build_scenario()
        self.set_world_tick(400)
        settle_population_scope(self.wilderness, {self.unit_a}, 700)
        self.set_world_tick(700)
        self.assertEqual(observed, settlement_projection(self.wilderness))

    def test_a_world_without_a_player_moves_only_the_residual_unit(self):
        self._build_scenario()
        self.advance(600)
        cursors = self.cursors()
        self.assertEqual(cursors.default, START)
        self.assertEqual(cursors.units, {population_units.RESIDUAL_UNIT: 700})
        self.assertEqual(self.settled_through(self.unit_a), START)
        self.assertEqual(self.settled_through(self.unit_b), START)

    def test_a_later_stage_failure_restores_every_unit_and_the_state(self):
        self._build_scenario()
        place_player(self, WANDER_A)
        self.set_world_tick(400)
        cursors_before = self.cursors()
        before = settlement_projection(self.wilderness)
        advance_real = population_units.advance_unit_cursors

        def late_stage(start: int, end: int) -> list:
            raise RuntimeError("late stage fault")

        from world.rules import clock as clock_module

        with patch.object(
            population_units, "advance_unit_cursors", wraps=advance_real
        ) as advanced:
            clock_module.register_event_source("field_contact", late_stage)
            self.addCleanup(clock_module._EVENT_SOURCES.pop, "field_contact", None)
            with self.assertRaises(RuntimeError):
                self.advance(300)
        # The inline catch-up from the lowered cursor really wrote before the
        # later stage failed, so the restore is not an untouched world.
        self.assertTrue(advanced.called)
        self.assertEqual(self.cursors(), cursors_before)
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.drop_caches()
        self.assertEqual(self.cursors(), cursors_before)
        self.assertEqual(settlement_projection(self.wilderness), before)


class DeferredOutcomeTests(ObservedAdvanceFixture):
    """Deferred settlement gives the whole-world result."""

    #: 100 -> 400 -> 1000 -> 1600, the scenario's own endpoint.
    INTERVALS = (300, 600, 600)

    def observed_run(self, *, reload: bool) -> dict:
        self._build_scenario()
        place_player(self, WANDER_A)
        for seconds in self.INTERVALS:
            self.advance(seconds)
        if reload:
            self.drop_caches()
        catch_up_world(self.wilderness)
        return settlement_projection(self.wilderness)

    def reference_run(self) -> dict:
        self._build_scenario()
        for seconds in self.INTERVALS:
            start = int(get_world_clock().tick)
            settle_population_lifecycle(start, start + seconds)
            self.set_world_tick(start + seconds)
        return settlement_projection(self.wilderness)

    def test_advancing_then_catching_up_equals_whole_world_passes(self):
        observed = self.observed_run(reload=False)
        # The far zone really settled at the catch-up: its group took the
        # decision its own cursor owed, so the comparison is not an untouched
        # world on either side.
        group_id = self.group_ids[ZONE_B][0]
        state = monster_activity.read_monster_activity(self.wilderness)
        self.assertGreater(state.groups[group_id].sequence, 0)
        self.assertEqual(observed, self.reference_run())

    def test_reloading_while_a_unit_is_behind_keeps_the_catch_up_result(self):
        self.assertEqual(
            self.observed_run(reload=True), self.observed_run(reload=False)
        )


class UnobservedIndependenceTests(ObservedAdvanceFixture):
    """Decisions and snapshots do not depend on the unobserved units."""

    def _advance_over(self, extra_groups: int):
        self._build_scenario()
        place_player(self, WANDER_A)
        for _ in range(extra_groups):
            self._group(
                cell=WANDER_B,
                activity=ACTIVITY_B_WANDER,
                owner_key=ZONE_B,
            )
        scope = population_units.build_scope(
            self.wilderness, population_units.observed_units(self.wilderness)
        )
        state = monster_activity.read_monster_activity(self.wilderness)
        expected_order = tuple(
            sorted(
                {
                    member
                    for group_id in scope.group_ids
                    for member in state.groups[group_id].member_ids
                }
            )
        )
        real_plan = monster_activity.plan_group_decision
        real_snapshot = monster_activity.snapshot_activity_surfaces
        with (
            patch.object(
                monster_activity, "plan_group_decision", wraps=real_plan
            ) as planned,
            patch.object(
                monster_activity, "snapshot_activity_surfaces", wraps=real_snapshot
            ) as snapshotted,
        ):
            self.advance(600)
        group_ids = [call.args[1] for call in planned.call_args_list]
        members = [call.kwargs["member_ids"] for call in snapshotted.call_args_list]
        return group_ids, members, expected_order, set(scope.group_ids)

    def test_growing_the_far_zone_changes_neither_decisions_nor_snapshots(self):
        one_planned, one_members, expected, scope_groups = self._advance_over(0)
        many_planned, many_members, expected_many, _ = self._advance_over(5)
        self.assertTrue(one_planned)
        # The same groups decide, and the same individuals are snapshotted.
        self.assertEqual(one_planned, many_planned)
        self.assertEqual(len(one_members), len(many_members))
        self.assertEqual(
            [len(members) for members in one_members],
            [len(members) for members in many_members],
        )
        # Every planned group belongs to the observed closed set, and the
        # rollback snapshot is exactly its members -- no far-zone individual.
        self.assertLessEqual(scope_groups, set(one_planned))
        self.assertEqual(one_members[0], expected)
        self.assertEqual(many_members[0], expected_many)
        self.assertEqual(len(expected), len(expected_many))
        self.assertTrue(expected)


class ContactForecastTests(ObservedAdvanceFixture):
    """The interruptible-skip boundary query projects the observed units only."""

    def _contact_activities(self) -> None:
        """Publish a walking and a stationary contact-admitting binding."""
        areas = dict(self.world.areas)
        activities = dict(self.world.activities)
        activities[CONTACT_ACTIVITY] = MonsterActivity(
            CONTACT_ACTIVITY,
            "solitary_roaming",
            AREA_KEY,
            30,
            AggressionCondition("contact"),
        )
        activities[CONTACT_STATIONARY] = MonsterActivity(
            CONTACT_STATIONARY,
            "stationary",
            AREA_KEY,
            120,
            AggressionCondition("contact"),
        )
        self.enterContext(
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(activities),
            )
        )
        self.enterContext(
            patch.object(
                lore_activity,
                "ACTIVITY_AREA_REGISTRY",
                MappingProxyType(areas),
            )
        )
        self.enterContext(
            patch.object(
                monster_activity, "_declaration", lambda key: activities.get(key)
            )
        )

    def _arriving_contact(self) -> tuple[tuple[int, int], int]:
        """A contact group due to arrive, its destination cell and arrival tick."""
        interval = monster_activity.activity_decision_interval(CONTACT_ACTIVITY)
        for seed in range(1, 64):
            group_id, bodies = self._group(
                cell=WANDER_A,
                activity=CONTACT_ACTIVITY,
                owner_key=ZONE_A,
                seed=seed,
                tick=START,
                members=1,
            )
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=START + interval
            )
            if decision.edge is None:
                monster_activity.release_group(self.wilderness, group_id)
                for body in bodies:
                    body.delete()
                continue
            destination = decision.edge.destination
            cell = (destination.x, destination.y)
            states = monster_activity.projected_member_states(
                self.wilderness, group_id, tick=START + interval
            )
            resolution = quote_edge(bodies[0], decision.edge, bodies, states=states)
            plan = build_journey_plan(bodies, resolution, states)
            return cell, START + interval + int(plan["seconds"])
        raise AssertionError("no seed produced a contact group that departs")

    def _stationary_contact(self, cell: tuple[int, int]):
        """A stationary contact group and a party standing in its cell."""
        self._group(
            cell=cell,
            activity=CONTACT_STATIONARY,
            owner_key=ZONE_A,
            tick=START,
            members=1,
        )
        return self.place_party(cell)

    def _query(self, player, *, start: int = START, end: int = END):
        """The registered boundary query, its answer and its captured snapshot."""
        with (
            advance_scope((player,)),
            patch.object(
                population_forecast,
                "project_activity_window",
                wraps=population_forecast.project_activity_window,
            ) as projected,
        ):
            answer = population_lifecycle.next_population_lifecycle_boundary(
                start, end
            )
        self.assertTrue(projected.called)
        return answer, projected.call_args.args[0]

    def _whole_world_answer(self, player, *, start: int = START, end: int = END):
        snapshot = population_forecast.capture_activity_snapshot(start_tick=start)
        with advance_scope((player,)):
            return population_forecast.project_activity_window(
                snapshot,
                start_tick=start,
                end_tick=end,
                observers=forecast_observers(),
                wilderness=WILDERNESS_NAME,
            )

    def test_the_query_projects_only_observed_inputs_and_answers_the_contact(self):
        self._build_scenario()
        self._contact_activities()
        cell, arrival = self._arriving_contact()
        player = place_player(self, cell)
        answer, snapshot = self._query(player)
        whole = self._whole_world_answer(player)
        self.assertIsNotNone(whole.first_tick)
        self.assertEqual(answer, whole.first_tick)
        self.assertEqual(answer, arrival)
        self.assertEqual(
            whole.contact_sources, (population_forecast.FORECAST_SOURCE_BIRTH,)
        )
        scope = population_units.build_scope(
            self.wilderness, population_units.observed_units(self.wilderness)
        )
        self.assertTrue(snapshot.groups)
        self.assertLessEqual(
            {group.group_id for group in snapshot.groups}, set(scope.group_ids)
        )
        self.assertLessEqual(
            {zone.key for zone in snapshot.zones}, set(scope.zone_keys)
        )
        self.assertLessEqual(
            {site.key for site in snapshot.sites}, set(scope.site_keys)
        )
        self.assertNotIn(
            self.group_ids[ZONE_B][0], {group.group_id for group in snapshot.groups}
        )
        # The whole-world capture really holds the unobserved planning input,
        # so dropping it is what makes the two answers equal.
        world_snapshot = population_forecast.capture_activity_snapshot(
            start_tick=START
        )
        self.assertIn(
            self.group_ids[ZONE_B][0],
            {group.group_id for group in world_snapshot.groups},
        )

    def test_a_lagging_far_zone_answers_the_same_tick(self):
        self._build_scenario()
        self._contact_activities()
        player = self._stationary_contact(OBSERVER_CELL)
        # The advance settles the observed unit to 700 and leaves the far zone
        # at its own cursor, so the two runs differ only in that lag.
        self.advance(600)
        behind, _snapshot = self._query(player, start=700)
        catch_up_world(self.wilderness)
        current, _snapshot = self._query(player, start=700)
        self.assertIsNotNone(behind)
        self.assertEqual(current, behind)


class EndpointContactTests(ObservedAdvanceFixture):
    """The observed pass admits authored contact at the advance's endpoint."""

    def setUp(self):
        super().setUp()
        # The subject is the population pass's own contact block, not the
        # separate clock source that also admits at an interval endpoint.
        from world.rules import clock as clock_module

        clock_module._EVENT_SOURCES.pop("field_contact", None)
        self._build_scenario()
        self._publish_contact_activity()
        self.player = self.place_party(OBSERVER_CELL)
        enter_wilderness(
            self.player, coordinates=OBSERVER_CELL, name=WILDERNESS_NAME
        )
        # One contact-admitting body sharing the party's room, whose own
        # scheduled decision falls on the advance's endpoint.
        self._group(
            cell=OBSERVER_CELL,
            activity=CONTACT_STATIONARY,
            owner_key=ZONE_A,
            tick=START,
            members=1,
        )

    def _publish_contact_activity(self) -> None:
        activities = dict(self.world.activities)
        activities[CONTACT_STATIONARY] = MonsterActivity(
            CONTACT_STATIONARY,
            "stationary",
            AREA_KEY,
            120,
            AggressionCondition("contact"),
        )
        self.enterContext(
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(activities),
            )
        )
        self.enterContext(
            patch.object(
                monster_activity, "_declaration", lambda key: activities.get(key)
            )
        )

    def test_the_contact_runs_after_arrivals_and_before_idle_departures(self):
        order: list[tuple[int, str]] = []
        real_contact = field_contact.settle_population_contact_at
        real_decisions = monster_activity.settle_group_decisions_at
        contact_calls: list[int] = []

        def contact_probe(wilderness, tick, contact_tick):
            order.append((int(tick), "contact"))
            contact_calls.append(int(contact_tick))
            return real_contact(wilderness, tick, contact_tick)

        def decisions_probe(wilderness, tick, *, scope=None):
            order.append((int(tick), "decisions"))
            return real_decisions(wilderness, tick, scope=scope)

        clock = get_world_clock()
        with (
            patch.object(field_contact, "settle_population_contact_at", contact_probe),
            patch.object(
                monster_activity, "settle_group_decisions_at", decisions_probe
            ),
        ):
            events = clock.advance(600, AdvanceSource.COMMAND, [self.player])
        # Only the advance's endpoint is an admitted contact, and the pass
        # reaches it after the same tick's arrivals and before its departures.
        self.assertEqual(contact_calls, [700])
        self.assertEqual(
            [name for tick, name in order if name == "contact"], ["contact"]
        )
        self.assertEqual(
            [name for tick, name in order if tick == 700],
            ["contact", "decisions"],
        )
        admitted = [
            event for event in events if event.kind == field_contact.CONTACT_EVENT
        ]
        self.assertEqual(len(admitted), 1)
        self.assertEqual(int(admitted[0].due_tick), 700)
        self.assertEqual(clock.tick, 700)

    def test_a_scoped_pass_still_refuses_the_authored_contact_by_name(self):
        with self.assertRaises(ValueError) as raised:
            settle_population_scope(
                self.wilderness, {self.unit_a}, 700, contact=True
            )
        self.assertIn(
            "a scoped settlement pass cannot run the authored field contact",
            str(raised.exception),
        )


class DefeatProtectionTests(ObservedAdvanceFixture):
    """A defeat settlement catches its own fight cell up before writing."""

    def _publish_contact(self) -> None:
        activities = dict(self.world.activities)
        activities[CONTACT_STATIONARY] = MonsterActivity(
            CONTACT_STATIONARY,
            "stationary",
            AREA_KEY,
            120,
            AggressionCondition("contact"),
        )
        self.enterContext(
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(activities),
            )
        )
        self.enterContext(
            patch.object(
                monster_activity, "_declaration", lambda key: activities.get(key)
            )
        )

    def test_a_defeat_writes_protection_for_a_cell_whose_unit_is_behind(self):
        self._build_scenario()
        self._publish_contact()
        battlefield = WANDER_B
        player = self.place_party(battlefield)
        enter_wilderness(player, coordinates=battlefield, name=WILDERNESS_NAME)
        self._group(
            cell=battlefield,
            activity=CONTACT_STATIONARY,
            owner_key=ZONE_B,
            tick=START,
            members=1,
        )
        admitted = field_contact.admit_field_contact_at(
            player, source_id=field_contact.SOURCE_FIELD, tick=START
        )
        self.assertIsNotNone(admitted)
        cell = admitted["record"].population_cell
        self.assertEqual((int(cell["x"]), int(cell["y"])), battlefield)
        # The party leaves the battlefield, so the far unit is no longer
        # observed and the advance leaves it at its own cursor.
        enter_wilderness(player, coordinates=WANDER_A, name=WILDERNESS_NAME)
        self.advance(600)
        self.assertEqual(self.settled_through(self.unit_b), START)
        # The defeat settlement writes the fight cell's protection evidence; the
        # writer refuses a lagging unit by name, so the settlement catches the
        # cell up before its own transaction.
        forfeit(player)
        now = int(get_world_clock().tick)
        self.assertGreater(now, 700, "the settlement advanced the clock")
        self.assertEqual(self.settled_through(self.unit_b), now)
        protection = read_population_timeline(self.wilderness).protection
        self.assertTrue(
            [
                entry
                for entry in protection
                if (int(entry.cell.x), int(entry.cell.y)) == battlefield
            ]
        )

    @override_settings(POPULATION_CATCH_UP_REFUSES_NESTED=True)
    def test_the_settlement_announces_its_cell_for_the_aftermath_advance(self):
        self._build_scenario()
        self._publish_contact()
        battlefield = WANDER_B
        player = self.place_party(battlefield)
        enter_wilderness(player, coordinates=battlefield, name=WILDERNESS_NAME)
        self._group(
            cell=battlefield,
            activity=CONTACT_STATIONARY,
            owner_key=ZONE_B,
            tick=START,
            members=1,
        )
        admitted = field_contact.admit_field_contact_at(
            player, source_id=field_contact.SOURCE_FIELD, tick=START
        )
        self.assertIsNotNone(admitted)
        # The party still stands on the battlefield, so the observed advance
        # settles the fight cell's unit to the world tick...
        self.advance(600)
        self.assertEqual(self.settled_through(self.unit_b), 700)
        # ...and the party then leaves it. The settlement's own entry catch-up
        # is inert (the unit is current) and the production nested refusal is
        # on, so only the announced cell can keep the unit current through the
        # defeat aftermath's advance.
        enter_wilderness(player, coordinates=WANDER_A, name=WILDERNESS_NAME)
        forfeit(player)
        now = int(get_world_clock().tick)
        self.assertGreater(now, 700, "the settlement advanced the clock")
        self.assertEqual(self.settled_through(self.unit_b), now)
        protection = read_population_timeline(self.wilderness).protection
        self.assertTrue(
            [
                entry
                for entry in protection
                if (int(entry.cell.x), int(entry.cell.y)) == battlefield
            ]
        )