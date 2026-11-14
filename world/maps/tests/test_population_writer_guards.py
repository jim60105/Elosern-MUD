"""Behaviour tests: population writers refuse a unit behind the world tick.

Every scenario is built from the synthetic two-zone world of
:func:`build_two_zone_world`; no shipped zone, site, composition or individual is
named, and no test asserts wall-clock time or hardware speed. The proof is
equality of state: a refused write leaves the world exactly as it was, the same
write succeeds for a current unit and for a lagging unit inside a settlement
pass, and a group or a registration that reaches a lagging unit through its own
binding refuses before anything is stored.

The two synthetic zones are two settlement units. A unit lags by advancing the
world clock while its cursor stays at the scenario start; a unit is made current
by naming it in the cursor record at the advanced tick.

The requirements this module proves are ADDED by the change and carry no
canonical identifier before the archive sync, so no test here is annotated. The
test-to-requirement-and-scenario hand-off is recorded in the change's apply
report.
"""

from __future__ import annotations

from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from typeclasses.monsters import Monster

from world.maps import monster_activity, population_units, regional_population
from world.maps.monster_activity import (
    commit_monster_departure,
    create_group,
    read_monster_activity,
)
from world.maps.regional_population import (
    PopulationPosition,
    PopulationPresence,
    PopulationTransition,
    read_population_timeline,
    record_population_protection,
    record_population_transition,
    register_explicit_group,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    GROUP_ACTIVITY,
    SEED,
    SOLO_ACTIVITY,
    STATIONARY_ACTIVITY,
    ActivityFixture,
)
from world.maps.tests.test_scoped_population_settlement import (
    ACTIVITY_B_WANDER,
    BOUNDARY_A,
    EAST_OF_BOUNDARY,
    START,
    TRAVEL_A,
    WANDER_A,
    WANDER_B,
    ZONE_A,
    ZONE_B,
    build_two_zone_world,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import world_escape
from world.rules.clock import get_world_clock
from world.rules.movement_edges import LocationRef

#: The tick every cursor record reports after a fix for a unit that lags.
LAG = 700


def _wilderness_ref(cell: tuple[int, int]) -> LocationRef:
    return LocationRef.wilderness(WILDERNESS_NAME, *cell)


class _Unseeded:
    """The attribute handler of a world that never received the population seed."""

    def has(self, key: str) -> bool:
        return False

    def get(self, key: str, default: object = None) -> object:
        return default


class WriterGuardFixture(ActivityFixture):
    """The two-zone world, its two units and the writer inputs every test rebuilds."""

    def setUp(self):
        super().setUp()
        self.world = build_two_zone_world(self)
        self.unit_a = self.world.unit(WANDER_A)
        self.unit_b = self.world.unit(WANDER_B)
        self.assertNotEqual(self.unit_a, self.unit_b)
        self._scenario()

    # -- scenario -----------------------------------------------------------

    def _scenario(self) -> None:
        """One group in each unit at the start tick, plus the travel group."""
        self._reset_activity(tick=START)
        group_a, bodies_a = self._group(
            cell=WANDER_A,
            members=1,
            activity=GROUP_ACTIVITY,
            owner_key=ZONE_A,
        )
        group_b, bodies_b = self._group(
            cell=WANDER_B,
            members=1,
            activity=ACTIVITY_B_WANDER,
            owner_key=ZONE_B,
        )
        group_t, bodies_t = self._group(
            cell=TRAVEL_A,
            members=1,
            activity=SOLO_ACTIVITY,
            owner_key=ZONE_A,
        )
        self.groups = {ZONE_A: group_a, ZONE_B: group_b, "travel": group_t}
        self.bodies = {ZONE_A: bodies_a, ZONE_B: bodies_b, "travel": bodies_t}
        self.assertNotEqual(self.groups[ZONE_A], self.groups["travel"])

    # -- clock and cursor state ---------------------------------------------

    def lag(self, tick: int = LAG) -> None:
        """Advance the world tick while every unit cursor stays at the start."""
        clock = get_world_clock()
        clock.tick = tick
        clock._persist(tick)

    def make_current(self, *units: str, tick: int = LAG) -> None:
        """Keep the record's default at the start and raise only ``units``."""
        population_units.write_unit_cursors(
            self.wilderness,
            population_units.UnitCursors(
                START, MappingProxyType({unit: tick for unit in units})
            ),
        )

    # -- writers ------------------------------------------------------------

    def write_registration(
        self,
        cell: tuple[int, int],
        *,
        activity: str = STATIONARY_ACTIVITY,
        owner_kind: str = "explicit",
        owner_key: str = "t_guard_owner",
    ) -> Monster:
        individual = self._monster(cell)
        operation_id = f"guard:register:{individual.pk}"
        register_explicit_group(
            self.wilderness,
            [individual],
            cell,
            tick=START,
            owner_kind=owner_kind,
            owner_key=owner_key,
            activity_key=activity,
            operation_id=operation_id,
            transition_source_id=operation_id,
        )
        return individual

    def write_group(
        self,
        cell: tuple[int, int],
        *,
        activity: str = GROUP_ACTIVITY,
        owner_key: str = ZONE_A,
    ) -> str:
        individual = self._monster(cell)
        return create_group(
            self.wilderness,
            operation_id=f"guard:group:{individual.pk}",
            owner_kind="zone",
            owner_key=owner_key,
            activity_key=activity,
            home=_wilderness_ref(cell),
            position=_wilderness_ref(cell),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=START,
        )

    def write_transition(
        self,
        before_cell: tuple[int, int],
        after_cell: tuple[int, int] | None = None,
        *,
        individual: Monster | None = None,
    ) -> str:
        if individual is None:
            individual = self.bodies[ZONE_A][0]
        source_id = f"guard:transition:{before_cell[0]}:{before_cell[1]}:{individual.pk}"
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=source_id,
                individual_id=int(individual.pk),
                occurred_tick=START,
                before=PopulationPresence(
                    True, PopulationPosition(WILDERNESS_NAME, *before_cell), None, None
                ),
                after=(
                    PopulationPresence(False, None, None, None)
                    if after_cell is None
                    else PopulationPresence(
                        True,
                        PopulationPosition(WILDERNESS_NAME, *after_cell),
                        None,
                        None,
                    )
                ),
            ),
        )
        return source_id

    def write_protection(self, cell: tuple[int, int]) -> str:
        engagement_id = f"guard:engagement:{cell[0]}:{cell[1]}"
        record_population_protection(
            self.wilderness,
            engagement_id=engagement_id,
            cell=cell,
            start_tick=START,
            end_tick=None,
        )
        return engagement_id

    def plan_departure(self, cell: tuple[int, int] = TRAVEL_A):
        individual = self.bodies["travel"][0]
        return world_escape.plan_individual_escape(
            individual,
            None,
            world_escape.WorldEscapeContext(
                session_id="guard:battle:1",
                occurred_tick=START + 12,
                source=_wilderness_ref(cell),
                operation_id=f"guard:escape:{individual.pk}",
            ),
        )

    def write_departure(self) -> str:
        plan = self.plan_departure()
        self.assertIsNotNone(plan, "the travel group must have one lawful edge")
        return commit_monster_departure(self.wilderness, plan)

    # -- observations -------------------------------------------------------

    def group_ids(self) -> set[str]:
        return set(read_monster_activity(self.wilderness).groups)

    def timeline(self):
        return read_population_timeline(self.wilderness)

    def assert_nothing_written(self, before: dict, coordinates: dict) -> None:
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), coordinates)


class RequireUnitsCurrentTests(WriterGuardFixture):
    """The guard itself: the refusal, its silence, and the owner's own error."""

    def test_a_lagging_unit_refuses_by_name_with_both_ticks(self):
        self.lag()
        units = {self.unit_b, self.unit_a}
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            population_units.require_units_current(self.wilderness, units)
        message = str(caught.exception)
        self.assertIn(population_units.POPULATION_UNIT_NOT_CURRENT, message)
        # The first offending unit in sorted order names itself with its own
        # cursor and the world tick.
        self.assertIn(min(units), message)
        self.assertIn(str(START), message)
        self.assertIn(str(LAG), message)
        self.assertNotIsInstance(caught.exception, population_units.PopulationScopeViolation)

    def test_a_current_unit_passes_beside_a_lagging_one(self):
        self.lag()
        self.make_current(self.unit_a)
        population_units.require_units_current(self.wilderness, {self.unit_a})
        with self.assertRaises(population_units.PopulationUnitNotCurrent):
            population_units.require_units_current(self.wilderness, {self.unit_b})

    def test_a_running_pass_answers_without_reading_the_record(self):
        self.lag()
        with self.assertRaises(population_units.PopulationUnitNotCurrent):
            population_units.require_units_current(self.wilderness, {self.unit_b})
        with (
            population_units.running_pass(),
            patch.object(
                population_units,
                "read_unit_cursors",
                side_effect=AssertionError("a pass must answer before the record"),
            ),
        ):
            population_units.require_units_current(self.wilderness, {self.unit_b})
            population_units.require_current(
                self.wilderness, [_wilderness_ref(WANDER_B)]
            )

    def test_an_unprovisioned_world_answers_without_reading_the_record(self):
        unprovisioned = SimpleNamespace(
            attributes=_Unseeded(), db_key="t_guard_unprovisioned"
        )
        with patch.object(
            population_units,
            "read_unit_cursors",
            side_effect=AssertionError("an unseeded world must answer before the record"),
        ):
            population_units.require_units_current(unprovisioned, {self.unit_a})
            population_units.require_current(
                unprovisioned, [_wilderness_ref(WANDER_A)]
            )
            # No wilderness at all is the same answer.
            population_units.require_units_current(None, {self.unit_a})
            population_units.require_current(None, [_wilderness_ref(WANDER_A)])

    def test_an_empty_answer_reads_no_record(self):
        self.wilderness.attributes.remove(
            population_units.POPULATION_UNIT_CURSORS_ATTRIBUTE
        )
        population_units.require_units_current(self.wilderness, set())
        population_units.require_current(self.wilderness, [None])

    def test_a_missing_record_refuses_through_the_owner(self):
        self.wilderness.attributes.remove(
            population_units.POPULATION_UNIT_CURSORS_ATTRIBUTE
        )
        with self.assertRaises(regional_population.MalformedPopulationState):
            population_units.require_units_current(self.wilderness, {self.unit_a})


class WriterRefusalTests(WriterGuardFixture):
    """Each writer refuses a lagging unit and leaves every surface untouched."""

    def test_an_explicit_registration_into_a_lagging_unit_writes_nothing(self):
        self.lag()
        individual = self._monster(WANDER_B)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        groups = self.group_ids()
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            register_explicit_group(
                self.wilderness,
                [individual],
                WANDER_B,
                tick=START,
                owner_kind="explicit",
                owner_key="t_guard_owner",
                activity_key=STATIONARY_ACTIVITY,
                operation_id=f"guard:register:{individual.pk}",
            )
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)
        self.assertEqual(self.group_ids(), groups)
        self.assertEqual(self.timeline().transitions, ())

    def test_a_registration_reaching_a_lagging_area_writes_nothing(self):
        # The cell itself is current; the group's activity area is in unit B.
        self.lag()
        self.make_current(self.unit_a)
        individual = self._monster(WANDER_A)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        groups = self.group_ids()
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            register_explicit_group(
                self.wilderness,
                [individual],
                WANDER_A,
                tick=START,
                owner_kind="zone",
                owner_key=ZONE_B,
                activity_key=ACTIVITY_B_WANDER,
                operation_id=f"guard:register:{individual.pk}",
            )
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)
        self.assertEqual(self.group_ids(), groups)

    def test_a_group_creation_in_a_lagging_unit_writes_nothing(self):
        self.lag()
        individual = self._monster(WANDER_B)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        groups = self.group_ids()
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            create_group(
                self.wilderness,
                operation_id=f"guard:group:{individual.pk}",
                owner_kind="zone",
                owner_key=ZONE_B,
                activity_key=ACTIVITY_B_WANDER,
                home=_wilderness_ref(WANDER_B),
                position=_wilderness_ref(WANDER_B),
                member_ids=(individual.pk,),
                seed=SEED,
                tick=START,
            )
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)
        self.assertEqual(self.group_ids(), groups)

    def test_a_group_reaching_a_lagging_unit_writes_nothing(self):
        # The home cell is in the current unit; the activity area is not.
        self.lag()
        self.make_current(self.unit_a)
        individual = self._monster(WANDER_A)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        groups = self.group_ids()
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            create_group(
                self.wilderness,
                operation_id=f"guard:group:{individual.pk}",
                owner_kind="zone",
                owner_key=ZONE_B,
                activity_key=ACTIVITY_B_WANDER,
                home=_wilderness_ref(WANDER_A),
                position=_wilderness_ref(WANDER_A),
                member_ids=(individual.pk,),
                seed=SEED,
                tick=START,
            )
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)
        self.assertEqual(self.group_ids(), groups)

    def test_a_transition_from_a_lagging_unit_writes_nothing(self):
        self.lag()
        individual = self.bodies[ZONE_B][0]
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            self.write_transition(WANDER_B, individual=individual)
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)

    def test_a_transition_into_a_lagging_unit_writes_nothing(self):
        self.lag()
        self.make_current(self.unit_a)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            self.write_transition(WANDER_A, WANDER_B)
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)

    def test_a_protection_of_a_lagging_cell_writes_nothing(self):
        self.lag()
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            self.write_protection(WANDER_B)
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)

    def test_a_departure_from_a_lagging_unit_writes_nothing(self):
        self.lag()
        plan = self.plan_departure()
        self.assertIsNotNone(plan)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            commit_monster_departure(self.wilderness, plan)
        self.assertIn(self.unit_a, str(caught.exception))
        self.assert_nothing_written(before, coordinates)

    def test_a_departure_into_a_lagging_unit_writes_nothing(self):
        # The departure cell is current; the selected destination is not.
        self.lag()
        self.make_current(self.unit_a)
        individual = self._monster(BOUNDARY_A)
        group_id = create_group(
            self.wilderness,
            operation_id=f"guard:boundary:{individual.pk}",
            owner_kind="zone",
            owner_key=ZONE_A,
            activity_key=GROUP_ACTIVITY,
            home=_wilderness_ref(BOUNDARY_A),
            position=_wilderness_ref(BOUNDARY_A),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=START,
        )
        self.assertIn(group_id, self.group_ids())
        east = _wilderness_ref(EAST_OF_BOUNDARY)

        def select_east(candidates, _seed):
            return next(item for item in candidates if item[0].destination == east)

        with patch.object(world_escape, "_commitment", select_east):
            plan = world_escape.plan_individual_escape(
                individual,
                None,
                world_escape.WorldEscapeContext(
                    session_id="guard:battle:2",
                    occurred_tick=START + 12,
                    source=_wilderness_ref(BOUNDARY_A),
                    operation_id=f"guard:escape:{individual.pk}",
                ),
            )
        self.assertIsNotNone(plan, "the eastern edge must be a lawful candidate")
        self.assertEqual(plan.edge.destination, east)
        before = settlement_projection(self.wilderness)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(population_units.PopulationUnitNotCurrent) as caught:
            commit_monster_departure(self.wilderness, plan)
        self.assertIn(self.unit_b, str(caught.exception))
        self.assert_nothing_written(before, coordinates)


class WriterSuccessTests(WriterGuardFixture):
    """The same writers write for a current unit and inside a settlement pass."""

    def assert_every_writer_wrote(self) -> None:
        state = read_monster_activity(self.wilderness)
        timeline = self.timeline()
        self.assertTrue(
            any(
                transition.source_id.startswith("guard:transition")
                for transition in timeline.transitions
            )
        )
        self.assertTrue(
            any(
                protection.engagement_id.startswith("guard:engagement")
                for protection in timeline.protection
            )
        )
        self.assertTrue(
            any(group_id.startswith("guard:group:") for group_id in state.groups)
        )
        self.assertTrue(
            any(group_id.startswith("guard:register:") for group_id in state.groups)
        )
        self.assertTrue(state.journeys)

    def test_every_writer_writes_for_a_current_unit(self):
        registered = self.write_registration(WANDER_A)
        group_id = self.write_group(WANDER_A)
        self.write_transition(WANDER_A)
        self.write_protection(WANDER_A)
        journey_id = self.write_departure()
        self.assertIn(registered, self.wilderness.db.itemcoordinates)
        self.assertIn(group_id, self.group_ids())
        self.assertIn(journey_id, read_monster_activity(self.wilderness).journeys)
        self.assert_every_writer_wrote()

    def test_every_writer_writes_for_a_lagging_unit_inside_a_pass(self):
        self.lag()
        plan = self.plan_departure()
        self.assertIsNotNone(plan)
        with population_units.running_pass():
            registered = self.write_registration(WANDER_A)
            group_id = self.write_group(WANDER_A)
            self.write_transition(WANDER_A)
            self.write_protection(WANDER_A)
            journey_id = commit_monster_departure(self.wilderness, plan)
        self.assertIn(registered, self.wilderness.db.itemcoordinates)
        self.assertIn(group_id, self.group_ids())
        self.assertIn(journey_id, read_monster_activity(self.wilderness).journeys)
        self.assert_every_writer_wrote()
        # The pass answered for the lagging unit; the record itself is untouched.
        self.assertEqual(self.timeline().settled_through_tick, START)
        self.assertEqual(
            population_units.read_unit_cursors(self.wilderness).default, START
        )