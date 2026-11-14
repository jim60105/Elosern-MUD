"""Behaviour tests: a closed set of settlement units settles as the world does.

Every scenario is built from the synthetic catalogues and the file-local
registry seams of :class:`ActivityFixture`; no shipped zone, site, composition
or individual is named, and no test asserts wall-clock time or hardware speed.
The proof this module owes is equality of two runs of the same scenario -- a
whole-world pass against unit-by-unit passes in any order and any partition --
plus exact cursor values, unit sets and named refusals.

The two synthetic zones are disjoint and adjacent inside one published region:
zone A is the fixture's own activity rectangle and zone B is its eastern
neighbour, so one wilderness step crosses from one unit into the other. The
site lies in the first zone.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from typeclasses.monsters import Monster

import world.lore.monster_activity as lore_activity
import world.lore.monster_placement as lore_placement
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
)
from world.maps import (
    monster_activity,
    monster_sites,
    population_units,
    regional_population,
)
from world.maps.population_lifecycle import (
    settle_population_lifecycle,
    settle_population_scope,
)
from world.maps.regional_population import (
    PopulationPresence,
    PopulationTransition,
    presence_of,
    read_population_timeline,
    record_population_protection,
    record_population_transition,
    zone_states,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    AREA_KEY,
    GROUP_ACTIVITY,
    HOME_AREA_KEY,
    RESERVE,
    SEED,
    SOLO_ACTIVITY,
    STATIONARY_ACTIVITY,
    ActivityFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.fatigue import read_optional_fatigue_state
from world.rules.movement_edges import LocationRef, PhysicalEdge
from world.rules.sleep_receipt import read_sleep_receipt
from world.rules.surfaces import persisted_hp
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS

ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))

START = 100
END = 1600

ZONE_A = "t_scope_zone_a"
ZONE_B = "t_scope_zone_b"
AREA_B_KEY = "t_scope_area_b"
ACTIVITY_B_WANDER = "t_scope_group_b"
SITE_KEY = "t_scope_site"
COMPOSITION_A = "t_scope_composition_a"
COMPOSITION_B = "t_scope_composition_b"

#: The fixture's own activity rectangle (zone A) and its eastern neighbour.
RECT_A = ((500, 519, 700, 719),)
RECT_B = ((520, 529, 700, 709),)

#: Eight eligible cells per zone: a 75/99 band over eight cells is [6, 8].
CELLS_A = tuple((500 + offset, row) for row in (700, 701) for offset in range(8))
CELLS_B = tuple((520 + offset, row) for row in (700, 701) for offset in range(8))
#: A group of zone A, a group of zone B, and a travelling group of zone A.
WANDER_A = (503, 705)
WANDER_B = (523, 705)
TRAVEL_A = (506, 710)
#: One zone-A cell whose eastern neighbour is inside zone B.
BOUNDARY_A = (519, 703)
EAST_OF_BOUNDARY = (520, 703)
SITE_CELL = CELLS_A[0]

LOWER_DENSITY = 75
UPPER_DENSITY = 99
CELL_CAPACITY = 3
RECOVERY_DELAY = 10
REPLENISHMENT = 5
SITE_RECOVERY_TICKS = 40
#: One identity no living row carries: the site's already-defeated member.
DEFEATED_ID = 999999


def _zone(key: str, rectangles: tuple[tuple[int, int, int, int], ...], pool):
    """One synthetic zone with the file-local band and cadence."""
    return EcologyZone(
        key,
        None,
        rectangles,
        pool,
        LOWER_DENSITY,
        UPPER_DENSITY,
        CELL_CAPACITY,
        recovery_delay=RECOVERY_DELAY,
        replenishment_interval=REPLENISHMENT,
        wave_budget=1,
    )


def _activity(key: str, policy: str, area_key: str, interval: int) -> MonsterActivity:
    return MonsterActivity(key, policy, area_key, interval, AggressionCondition("passive"))


def _composition(key: str, activity_key: str) -> EncounterComposition:
    return EncounterComposition(key, activity_key, (CompositionMember(ORDINARY, 1, 1),))


def _site() -> MonsterSite:
    """One cleared, recoverable site inside zone A."""
    return MonsterSite(
        key=SITE_KEY,
        kind="camp",
        region_key=None,
        coordinates=SITE_CELL,
        composition_key=COMPOSITION_A,
        capacity=1,
        one_shot=False,
        recover_after_ticks=SITE_RECOVERY_TICKS,
        activity_key=SOLO_ACTIVITY,
    )


class TwoZoneWorld:
    """The synthetic two-zone world one scenario is built in."""

    def __init__(self, fixture, region: str) -> None:
        self.fixture = fixture
        self.region = region
        self.zones = {
            ZONE_A: _zone(ZONE_A, RECT_A, (WeightedComposition(COMPOSITION_A, 1),)),
            ZONE_B: _zone(ZONE_B, RECT_B, (WeightedComposition(COMPOSITION_B, 1),)),
        }
        self.areas = {
            AREA_KEY: ActivityArea(AREA_KEY, region, RECT_A),
            AREA_B_KEY: ActivityArea(AREA_B_KEY, region, RECT_B),
            HOME_AREA_KEY: ActivityArea(HOME_AREA_KEY, home_radius=0),
        }
        self.activities = {
            GROUP_ACTIVITY: _activity(GROUP_ACTIVITY, "cohesive_group", AREA_KEY, 90),
            SOLO_ACTIVITY: _activity(SOLO_ACTIVITY, "solitary_roaming", AREA_KEY, 60),
            STATIONARY_ACTIVITY: _activity(
                STATIONARY_ACTIVITY, "stationary", HOME_AREA_KEY, 120
            ),
            ACTIVITY_B_WANDER: _activity(
                ACTIVITY_B_WANDER, "cohesive_group", AREA_B_KEY, 90
            ),
        }
        self.compositions = {
            COMPOSITION_A: _composition(COMPOSITION_A, GROUP_ACTIVITY),
            COMPOSITION_B: _composition(COMPOSITION_B, ACTIVITY_B_WANDER),
        }
        self.sites = {SITE_KEY: _site()}

    def cell_zone(self, cell: tuple[int, int]) -> str:
        """The zone whose rectangle holds one cell (for the assertions)."""
        for zone in self.zones.values():
            for x_min, x_max, y_min, y_max in zone.rectangles:
                if x_min <= cell[0] <= x_max and y_min <= cell[1] <= y_max:
                    return zone.key
        raise AssertionError(f"cell {cell} is in no synthetic zone")

    def unit(self, cell: tuple[int, int]) -> str:
        """The settlement unit of one cell, from the live index."""
        return population_units.current_unit_index().unit_of_cell(self.region, cell)


def build_two_zone_world(fixture) -> TwoZoneWorld:
    """Two disjoint zones in one region, one site in the first, and their seams.

    Every seam the settlement reads is replaced: the five lore registries the
    settlement-unit index resolves, the owners' own module-level bindings, the
    activity declaration lookup, the eligible birth cells and the published
    region cells of each zone. Nothing outside these seams is patched.
    """
    region = fixture.region
    world = TwoZoneWorld(fixture, region)
    zones = MappingProxyType(world.zones)
    areas = MappingProxyType(world.areas)
    activities = MappingProxyType(world.activities)
    compositions = MappingProxyType(world.compositions)
    sites = MappingProxyType(world.sites)

    def eligible(zone, *args, **kwargs):
        if zone.key == ZONE_A:
            return CELLS_A
        if zone.key == ZONE_B:
            return CELLS_B
        return ()

    def region_cells(zone):
        if zone.key == ZONE_A:
            return frozenset(CELLS_A)
        if zone.key == ZONE_B:
            return frozenset(CELLS_B)
        return frozenset()

    fixture.enterContext(patch.object(lore_placement, "ECOLOGY_ZONE_REGISTRY", zones))
    fixture.enterContext(patch.object(lore_placement, "MONSTER_SITE_REGISTRY", sites))
    fixture.enterContext(
        patch.object(lore_placement, "ENCOUNTER_COMPOSITION_REGISTRY", compositions)
    )
    fixture.enterContext(patch.object(lore_activity, "ACTIVITY_AREA_REGISTRY", areas))
    fixture.enterContext(patch.object(lore_activity, "MONSTER_ACTIVITY_REGISTRY", activities))
    fixture.enterContext(patch.object(regional_population, "ECOLOGY_ZONE_REGISTRY", zones))
    fixture.enterContext(
        patch.object(regional_population, "ENCOUNTER_COMPOSITION_REGISTRY", compositions)
    )
    fixture.enterContext(
        patch.object(
            regional_population, "SETTLEMENT_BIRTH_POLICY_REGISTRY", MappingProxyType({})
        )
    )
    fixture.enterContext(patch.object(regional_population, "eligible_birth_cells", eligible))
    fixture.enterContext(patch.object(regional_population, "_region_cells", region_cells))
    fixture.enterContext(patch.object(monster_sites, "MONSTER_SITE_REGISTRY", sites))
    fixture.enterContext(
        patch.object(monster_sites, "ENCOUNTER_COMPOSITION_REGISTRY", compositions)
    )
    fixture.enterContext(
        patch.object(monster_activity, "_declaration", lambda key: activities.get(key))
    )
    return world


class ScopedSettlementFixture(ActivityFixture):
    """The two-zone world plus the deterministic scenario every test rebuilds."""

    def setUp(self):
        super().setUp()
        self.world = build_two_zone_world(self)
        self.unit_a = self.world.unit(WANDER_A)
        self.unit_b = self.world.unit(WANDER_B)
        self.assertNotEqual(self.unit_a, self.unit_b)
        self._seeds: dict[str, int] = {}

    # -- seams --------------------------------------------------------------

    def _seed_for(
        self,
        *,
        depart: bool,
        activity: str,
        cell: tuple[int, int],
        owner_key: str,
    ) -> int:
        """A seed whose first scheduled decision departs (or stays)."""
        interval = monster_activity.activity_decision_interval(activity)
        for seed in range(64):
            self._reset_activity(tick=START)
            group_id, _bodies = self._group(
                cell=cell,
                seed=seed,
                tick=START,
                activity=activity,
                owner_key=owner_key,
            )
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=START + interval
            )
            if (decision.edge is not None) == depart:
                return seed
        raise AssertionError("no seed produced the requested first decision")

    def _seed(self, name: str, **kwargs) -> int:
        if name not in self._seeds:
            self._seeds[name] = self._seed_for(**kwargs)
        return self._seeds[name]

    def _zone_record(self) -> dict:
        return {
            "initialized": True,
            "seed": SEED,
            "generation_sequence": 0,
            "recovery_due_tick": None,
            "settled_through_tick": START,
        }

    def _cleared_site_record(self) -> dict:
        return {
            SITE_KEY: {
                "state": monster_sites.SITE_STATE_CLEARED,
                "cleared_at_tick": START,
                "seed": monster_sites._site_seed(self.wilderness, self.world.sites[SITE_KEY]),
                "generation_sequence": 0,
                "member_ids": [DEFEATED_ID],
            }
        }

    def _kill(self, individual: Monster, tick: int, *, home_zone: str | None = None) -> None:
        """Zero one individual's HP and record its loss at that tick."""
        before = presence_of(self.wilderness, individual)
        individual.traits.hp.current = 0
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=f"scope-loss:{tick}",
                individual_id=int(individual.pk),
                occurred_tick=tick,
                before=before,
                after=presence_of(self.wilderness, individual, alive=False),
            ),
        )

    def _future_loss(self, cell: tuple[int, int], tick: int, *, home_zone: str) -> Monster:
        """One living individual whose committed loss falls on the interval end.

        Its presence is reversed until that tick, so every visited boundary before
        the end still counts it, and the bounded future loss is a real merged
        boundary at the plan's endpoint.
        """
        individual = self._monster(cell, home_zone=home_zone)
        self._kill(individual, tick)
        return individual

    def _build_scenario(self, *, end_tick: int = END) -> None:
        """Rebuild the identical starting world of every run of one scenario."""
        self._warm_seeds()
        self._reset_activity(tick=START)
        self.bodies: dict[str, list[Monster]] = {ZONE_A: [], ZONE_B: []}
        self.wilderness.db.regional_population = {
            ZONE_A: self._zone_record(),
            ZONE_B: self._zone_record(),
        }
        self.wilderness.db.monster_sites = self._cleared_site_record()
        _group_a, bodies = self._group(
            cell=WANDER_A,
            seed=self._seeds["wander_a"],
            tick=START,
            owner_key=ZONE_A,
            reserves=(RESERVE // 2, RESERVE // 2),
        )
        self.bodies[ZONE_A].extend(bodies)
        _group_b, bodies = self._group(
            cell=WANDER_B,
            seed=self._seeds["wander_b"],
            tick=START,
            activity=ACTIVITY_B_WANDER,
            owner_key=ZONE_B,
            reserves=(RESERVE // 2, RESERVE // 2),
        )
        self.bodies[ZONE_B].extend(bodies)
        _group_t, bodies = self._group(
            cell=TRAVEL_A,
            seed=self._seeds["travel"],
            tick=START,
            activity=SOLO_ACTIVITY,
            owner_key=ZONE_A,
        )
        self.bodies[ZONE_A].extend(bodies)
        self.group_ids = {
            ZONE_A: (_group_a, _group_t),
            ZONE_B: (_group_b,),
        }
        # One bounded future loss per zone on the plan's endpoint: it keeps the
        # last visited tick of every pass equal (see the zone-marker note in the
        # development document) and is the "future loss" category the
        # coordinator merges.
        self.bodies[ZONE_A].append(
            self._future_loss(CELLS_A[4], end_tick, home_zone=ZONE_A)
        )
        self.bodies[ZONE_B].append(
            self._future_loss(CELLS_B[4], end_tick, home_zone=ZONE_B)
        )

    def _warm_seeds(self) -> None:
        """Resolve every scenario seed before the world is rebuilt.

        A seed search resets the world per candidate, so it must never run in the
        middle of a scenario build.
        """
        self._seed(
            "wander_a",
            depart=False,
            activity=GROUP_ACTIVITY,
            cell=WANDER_A,
            owner_key=ZONE_A,
        )
        self._seed(
            "wander_b",
            depart=False,
            activity=ACTIVITY_B_WANDER,
            cell=WANDER_B,
            owner_key=ZONE_B,
        )
        self._seed(
            "travel",
            depart=True,
            activity=SOLO_ACTIVITY,
            cell=TRAVEL_A,
            owner_key=ZONE_A,
        )

    # -- runs ---------------------------------------------------------------

    def run_plan(self, plan, *, end_tick: int = END) -> dict:
        """Rebuild the scenario, apply each step in turn, project the world."""
        self._build_scenario(end_tick=end_tick)
        cursor = START
        for seeds, target in plan:
            if seeds is None:
                settle_population_lifecycle(cursor, target)
            else:
                settle_population_scope(self.wilderness, seeds, target)
            cursor = target
        return settlement_projection(self.wilderness)

    def cursor_record(self) -> population_units.UnitCursors:
        return population_units.read_unit_cursors(self.wilderness)

    def group_state(self):
        return monster_activity.read_monster_activity(self.wilderness)


class TwoZoneWorldTests(ScopedSettlementFixture):
    """The synthetic world both zones live in is really built."""

    def test_two_zone_world_holds_both_zones_a_site_and_two_units(self):
        self._build_scenario()
        states = zone_states(self.wilderness)
        self.assertEqual(sorted(states), [ZONE_A, ZONE_B])
        self.assertEqual(
            regional_population.initialized_zone_keys(self.wilderness),
            (ZONE_A, ZONE_B),
        )
        self.assertEqual(states[ZONE_A].settled_through_tick, START)
        self.assertEqual(states[ZONE_B].settled_through_tick, START)
        self.assertEqual(
            monster_sites._read_state_map(self.wilderness)[SITE_KEY]["state"],
            monster_sites.SITE_STATE_CLEARED,
        )
        # The zones are separate units, and one wilderness step joins them.
        self.assertNotEqual(self.world.unit(BOUNDARY_A), self.world.unit(EAST_OF_BOUNDARY))
        self.assertEqual(self.world.unit(BOUNDARY_A), self.unit_a)
        self.assertEqual(self.world.unit(EAST_OF_BOUNDARY), self.unit_b)


class ScopeObjectTests(ScopedSettlementFixture):
    """A scope names a closed set, its start and what a tick may settle."""

    def test_one_zone_scope_holds_its_unit_groups_zone_and_site(self):
        self._build_scenario()
        scope = population_units.build_scope(self.wilderness, [self.unit_a])
        self.assertEqual(scope.units, frozenset({self.unit_a}))
        self.assertEqual(scope.zone_keys, (ZONE_A,))
        self.assertEqual(scope.site_keys, frozenset({SITE_KEY}))
        self.assertEqual(
            population_units.scope_start_tick(self.wilderness, scope), START
        )
        state = self.group_state()
        index = population_units.current_unit_index()
        settled = {
            group_id
            for group_id, group in state.groups.items()
            if population_units.group_units(
                index, group, state.journeys.get(group.journey_id)
            )
            <= scope.units
        }
        self.assertEqual(scope.group_ids, frozenset(settled))
        self.assertLessEqual(set(self.group_ids[ZONE_A]), set(scope.group_ids))
        self.assertFalse(set(self.group_ids[ZONE_B]) & set(scope.group_ids))

    def test_behind_narrows_zones_and_sites_by_each_units_cursor(self):
        self._build_scenario()
        scope = population_units.build_scope(
            self.wilderness, [self.unit_a, self.unit_b]
        )
        self.assertEqual(scope.units, frozenset({self.unit_a, self.unit_b}))
        self.assertEqual(scope.zone_keys, (ZONE_A, ZONE_B))
        self.assertEqual(
            population_units.scope_start_tick(self.wilderness, scope), START
        )
        # Equal cursors: the set has settled through START, so no zone or site
        # step runs there -- unless the pass itself starts at that tick.
        self.assertEqual(scope.behind(START).zone_keys, ())
        self.assertEqual(scope.behind(START).site_keys, frozenset())
        self.assertEqual(
            scope.behind(START, inclusive=True).zone_keys, (ZONE_A, ZONE_B)
        )
        self.assertEqual(
            scope.behind(START, inclusive=True).site_keys, frozenset({SITE_KEY})
        )
        self.assertEqual(scope.behind(START + 1).zone_keys, (ZONE_A, ZONE_B))
        # Narrowing never changes the units or the groups the pass may settle.
        narrowed = scope.behind(START)
        self.assertEqual(narrowed.units, scope.units)
        self.assertEqual(narrowed.group_ids, scope.group_ids)
        self.assertTrue(narrowed.covers_cell(CELLS_A[0]))
        self.assertTrue(narrowed.covers_cell(CELLS_B[0]))

    def test_unequal_cursors_narrow_only_the_ahead_unit(self):
        self._build_scenario()
        population_units.write_unit_cursors(
            self.wilderness,
            population_units.UnitCursors(
                START, MappingProxyType({self.unit_a: 400})
            ),
        )
        scope = population_units.build_scope(
            self.wilderness, [self.unit_a, self.unit_b]
        )
        self.assertEqual(
            population_units.scope_start_tick(self.wilderness, scope), START
        )
        self.assertEqual(scope.behind(400).zone_keys, (ZONE_B,))
        self.assertEqual(scope.behind(400).site_keys, frozenset())
        self.assertEqual(scope.behind(401).zone_keys, (ZONE_A, ZONE_B))

    def test_the_active_scope_names_the_error_and_restores_the_previous_value(self):
        self._build_scenario()
        scope = population_units.build_scope(self.wilderness, [self.unit_a])
        inside = LocationRef.wilderness(WILDERNESS_NAME, *WANDER_A)
        outside = LocationRef.wilderness(WILDERNESS_NAME, *WANDER_B)
        self.assertIsNone(population_units.active_scope())
        with population_units.scoped(scope):
            self.assertIs(population_units.active_scope(), scope)
            population_units.require_in_active_scope(inside)
            population_units.require_in_active_scope(None)
            population_units.require_cell_in_active_scope(CELLS_A[0])
            population_units.require_units_in_active_scope([self.unit_a])
            for refused in (
                lambda: population_units.require_in_active_scope(outside),
                lambda: population_units.require_cell_in_active_scope(CELLS_B[0]),
                lambda: population_units.require_units_in_active_scope(
                    [self.unit_a, self.unit_b]
                ),
            ):
                with self.assertRaises(population_units.PopulationScopeViolation):
                    refused()
        # Every scope guard is a no-op outside a scoped pass.
        self.assertIsNone(population_units.active_scope())
        population_units.require_in_active_scope(outside)
        population_units.require_units_in_active_scope([self.unit_b])
        population_units.require_cell_in_active_scope(CELLS_B[0])

    def test_a_recorded_loss_concerns_its_position_and_home_zone_units(self):
        self._build_scenario()
        individual = self._monster(EAST_OF_BOUNDARY, home_zone=ZONE_A)
        before = presence_of(self.wilderness, individual)
        individual.traits.hp.current = 0
        transition = PopulationTransition(
            "scope-concern",
            int(individual.pk),
            118,
            before,
            presence_of(self.wilderness, individual, alive=False),
        )
        index = population_units.current_unit_index()
        self.assertEqual(
            population_units.concerned_units(index, transition),
            frozenset({self.unit_a, self.unit_b}),
        )
        self.assertEqual(
            population_units.concerned_units(
                index,
                replace(
                    transition,
                    before=PopulationPresence(False, None, None, None),
                    after=PopulationPresence(False, None, None, None),
                ),
            ),
            frozenset({population_units.RESIDUAL_UNIT}),
        )


class ScopeCursorTests(ScopedSettlementFixture):
    """A scoped pass moves its own unit's cursor and nobody else's."""

    def test_cursor_moves_only_for_the_scope(self):
        self._build_scenario()
        settle_population_scope(self.wilderness, [self.unit_a], 400)
        record = self.cursor_record()
        self.assertEqual(population_units.unit_cursor(record, self.unit_a), 400)
        self.assertEqual(population_units.unit_cursor(record, self.unit_b), START)
        self.assertEqual(record.default, START)
        # The pass really worked: unit A's zone record moved past the start.
        self.assertGreater(
            zone_states(self.wilderness)[ZONE_A].settled_through_tick, START
        )
        self.assertEqual(
            zone_states(self.wilderness)[ZONE_B].settled_through_tick, START
        )

    def test_an_interval_that_ended_before_the_cursor_settles_nothing(self):
        self._build_scenario()
        population_units.write_unit_cursors(
            self.wilderness,
            population_units.UnitCursors(
                START, MappingProxyType({self.unit_a: 400})
            ),
        )
        self.assertEqual(
            settle_population_scope(self.wilderness, [self.unit_a], 399), []
        )
        record = self.cursor_record()
        self.assertEqual(population_units.unit_cursor(record, self.unit_a), 400)

    def test_an_interval_that_starts_and_ends_at_the_cursor_settles_that_tick(self):
        self._build_scenario()
        population_units.write_unit_cursors(
            self.wilderness,
            population_units.UnitCursors(
                START, MappingProxyType({self.unit_a: 400})
            ),
        )
        settle_population_scope(self.wilderness, [self.unit_a], 400)
        record = self.cursor_record()
        self.assertEqual(population_units.unit_cursor(record, self.unit_a), 400)
        self.assertEqual(
            zone_states(self.wilderness)[ZONE_A].settled_through_tick, 400
        )


class DifferentialSettlementTests(ScopedSettlementFixture):
    """Whole-world and unit-by-unit passes leave one world."""

    def _plans(self) -> dict[str, list]:
        return {
            "whole": [(None, END)],
            "unit by unit": [([self.unit_a], END), ([self.unit_b], END)],
            "reversed": [([self.unit_b], END), ([self.unit_a], END)],
            "partitioned": [
                ([self.unit_a], 800),
                ([self.unit_b], 500),
                ([self.unit_b], 1100),
                ([self.unit_a], END),
                ([self.unit_b], END),
            ],
        }

    def test_order_and_partition_leave_one_state(self):
        projections = {
            name: self.run_plan(plan) for name, plan in self._plans().items()
        }
        reference = projections["whole"]
        for name, projection in projections.items():
            for part in ("activity", "timeline", "zones", "sites", "bodies"):
                self.assertEqual(
                    projection[part], reference[part], msg=f"plan {name}: {part}"
                )
        # The scenario really settled: a recovery wave and a site recovery ran,
        # and one travelling group left its starting cell.
        self.assertGreater(
            reference["zones"][ZONE_A]["generation_sequence"]
            + reference["zones"][ZONE_B]["generation_sequence"],
            0,
        )
        self.assertEqual(
            reference["sites"][SITE_KEY]["state"],
            monster_sites.SITE_STATE_POPULATED,
        )
        travelled = f"{self.group_ids[ZONE_A][1]}#0"
        self.assertIn(travelled, reference["bodies"])
        self.assertNotEqual(reference["bodies"][travelled]["cell"], TRAVEL_A)

    def test_a_whole_pass_really_records_a_journey(self):
        self._build_scenario()
        settle_population_lifecycle(START, 300)
        state = self.group_state()
        self.assertTrue(state.journeys)
        travel_group = state.groups[self.group_ids[ZONE_A][1]]
        self.assertIsNotNone(travel_group.journey_id)

    def _linked(self, *, whole: bool) -> dict:
        """The diverging world, settled as a whole or unit by unit."""
        self._build_scenario()
        if whole:
            settle_population_lifecycle(START, 400)
        else:
            settle_population_scope(self.wilderness, [self.unit_a], 400)
        # One group touches both units: it stands in zone B and is owned by zone A.
        self._group(cell=EAST_OF_BOUNDARY, seed=47, tick=400, owner_key=ZONE_A)
        if whole:
            settle_population_lifecycle(400, 700)
        else:
            settle_population_scope(self.wilderness, [self.unit_a], 700)
        return settlement_projection(self.wilderness)

    def test_units_linked_after_diverging_settle_identically(self):
        whole = self._linked(whole=True)
        linked = self._linked(whole=False)
        for part in ("activity", "timeline", "zones", "sites", "bodies"):
            self.assertEqual(linked[part], whole[part], msg=f"linked: {part}")

    def test_linked_units_settle_together(self):
        self._build_scenario()
        group_id, _bodies = self._group(
            cell=EAST_OF_BOUNDARY, seed=47, tick=START, owner_key=ZONE_A
        )
        scope = population_units.build_scope(self.wilderness, [self.unit_a])
        self.assertEqual(scope.units, frozenset({self.unit_a, self.unit_b}))
        self.assertIn(group_id, scope.group_ids)
        settle_population_scope(self.wilderness, [self.unit_a], 400)
        record = self.cursor_record()
        self.assertEqual(population_units.unit_cursor(record, self.unit_a), 400)
        self.assertEqual(population_units.unit_cursor(record, self.unit_b), 400)

    def test_reload_between_parts_leaves_the_same_state(self):
        one_part = self.run_plan([([self.unit_a], END)])
        self._build_scenario()
        settle_population_scope(self.wilderness, [self.unit_a], 800)
        self.wilderness.attributes.reset_cache()
        settle_population_scope(self.wilderness, [self.unit_a], END)
        self.assertEqual(settlement_projection(self.wilderness), one_part)

    def test_a_partial_departure_settles_its_derived_group(self):
        """A departed group with one dead identity splits into a new group id.

        That id did not exist when the scope was built, so the running pass must
        adopt it; otherwise its journey is never settled and is stranded. The
        projection cannot compare this scenario, because the derived group id
        embeds the moving member's persistent identity.
        """
        self._build_scenario()
        group_id, bodies = self._group(
            cell=TRAVEL_A,
            seed=self._seeds["travel"],
            tick=START,
            activity=SOLO_ACTIVITY,
            owner_key=ZONE_A,
            members=2,
        )
        self._kill(bodies[1], START)
        # Long enough for the derived group's journey to arrive: without the
        # adoption its arrival tick is never a boundary, so it never arrives at
        # any endpoint.
        settle_population_scope(self.wilderness, [self.unit_a], 4000)
        state = self.group_state()
        derived = [
            travelled
            for travelled in state.groups
            if travelled.startswith(f"{group_id}~")
        ]
        self.assertTrue(derived, "the partial departure derived a travelling group")
        # Every journey that derived group began inside the interval was settled:
        # its arrival tick was a boundary, so no journey due inside the pass
        # survives it.
        self.assertFalse(
            [
                journey
                for journey in state.journeys.values()
                if journey.group_id in derived and journey.arrival_tick <= 4000
            ],
            "a derived group's journey was never settled",
        )
        # The dead identity stayed behind in the residual group.
        residual = state.groups[group_id]
        self.assertEqual(residual.member_ids, (int(bodies[1].pk),))


class OtherUnitTests(ScopedSettlementFixture):
    """A scoped pass leaves every record and individual of other units alone."""

    def _facts(self, individual: Monster) -> dict:
        fatigue = read_optional_fatigue_state(individual)
        receipt = read_sleep_receipt(individual)
        return {
            "cell": regional_population.actual_cell(self.wilderness, individual),
            "hp": persisted_hp(individual),
            "reserve": None if fatigue is None else int(fatigue.reserve_units),
            "posture": None if fatigue is None else fatigue.posture,
            "receipt": None if receipt is None else receipt.state,
        }

    def _sub_view(self) -> dict:
        state = self.group_state()
        return {
            "zone": zone_states(self.wilderness)[ZONE_B],
            "groups": {
                group_id: json.dumps(
                    monster_activity.group_to_dict(state.groups[group_id]),
                    sort_keys=True,
                )
                for group_id in self.group_ids[ZONE_B]
            },
            "bodies": {
                int(individual.pk): self._facts(individual)
                for individual in self.bodies[ZONE_B]
            },
            "cursor": population_units.unit_cursor(self.cursor_record(), self.unit_b),
        }

    def test_other_units_are_untouched(self):
        self._build_scenario()
        before = self._sub_view()
        planned: list[str] = []
        real = monster_activity.plan_group_decision

        def record(wilderness, group_id, *, tick):
            planned.append(group_id)
            return real(wilderness, group_id, tick=tick)

        with patch.object(monster_activity, "plan_group_decision", record):
            settle_population_scope(self.wilderness, [self.unit_a], END)
        after = self._sub_view()
        self.assertTrue(planned)
        self.assertFalse(set(planned) & set(self.group_ids[ZONE_B]))
        self.assertEqual(after, before)
        self.assertEqual(after["zone"].settled_through_tick, START)
        self.assertEqual(after["cursor"], START)


class SharedEvidenceTests(ScopedSettlementFixture):
    """Evidence is kept until every concerned unit has passed it."""

    def _loss_ticks(self) -> list[int]:
        return [
            transition.occurred_tick
            for transition in read_population_timeline(self.wilderness).transitions
        ]

    def test_loss_recorded_ahead_of_one_unit(self):
        self._build_scenario()
        # One individual stands in zone B and is homed in zone A: its loss
        # concerns both units.
        individual = self._monster(EAST_OF_BOUNDARY, home_zone=ZONE_A)
        self._kill(individual, 118)
        settle_population_scope(self.wilderness, [self.unit_a], 200)
        self.assertIn(118, self._loss_ticks())
        # Settling the lagging unit through the loss uses it and retires it.
        settle_population_scope(self.wilderness, [self.unit_b], 118)
        self.assertNotIn(118, self._loss_ticks())
        self.assertIn(END, self._loss_ticks())

    def test_protection_of_a_lagging_cell(self):
        self._build_scenario()
        population_units.write_unit_cursors(
            self.wilderness,
            population_units.UnitCursors(
                START, MappingProxyType({self.unit_a: 300})
            ),
        )
        record_population_protection(
            self.wilderness,
            engagement_id="scope-engagement",
            cell=EAST_OF_BOUNDARY,
            start_tick=120,
            end_tick=150,
        )
        settle_population_scope(self.wilderness, [self.unit_a], 300)
        engagements = [
            protection.engagement_id
            for protection in read_population_timeline(self.wilderness).protection
        ]
        self.assertEqual(engagements, ["scope-engagement"])
        # The lagging unit's protected cell still holds no birth space at 140.
        self.assertIn(
            EAST_OF_BOUNDARY,
            regional_population.protected_cells(self.wilderness, at_tick=140),
        )
        self.assertTrue(
            monster_activity._destination_blocked(
                self.wilderness,
                LocationRef.wilderness(WILDERNESS_NAME, *EAST_OF_BOUNDARY),
                140,
            )
        )
        registered = {
            int(individual.pk)
            for individual in Monster.objects.all_family()
            if regional_population.actual_cell(self.wilderness, individual)
            == EAST_OF_BOUNDARY
        }
        settle_population_scope(self.wilderness, [self.unit_b], 140)
        self.assertEqual(
            {
                int(individual.pk)
                for individual in Monster.objects.all_family()
                if regional_population.actual_cell(self.wilderness, individual)
                == EAST_OF_BOUNDARY
            },
            registered,
        )
        self.assertEqual(
            [
                protection.engagement_id
                for protection in read_population_timeline(
                    self.wilderness
                ).protection
            ],
            ["scope-engagement"],
        )


class ScopeRefusalTests(ScopedSettlementFixture):
    """A scoped pass refuses an out-of-scope write by name, without partial state."""

    def _refusal_world(self) -> str:
        """A world whose only in-scope work at the start tick is one decision."""
        self._build_scenario()
        # No authored site: the pass's first tick must not do anything but the
        # decision this test faults.
        self.enterContext(
            patch.object(monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({}))
        )
        self.enterContext(
            patch.object(
                lore_placement, "MONSTER_SITE_REGISTRY", MappingProxyType({})
            )
        )
        self._reset_activity(tick=START)
        self.wilderness.db.regional_population = {
            ZONE_A: {
                **self._zone_record(),
                "recovery_due_tick": START + 5,
            }
        }
        self.wilderness.db.monster_sites = {}
        group_id, _bodies = self._group(
            cell=BOUNDARY_A, seed=47, tick=START, owner_key=ZONE_A
        )
        # The decision is due at the pass's first tick, so the refused departure
        # is the only work of the pass and nothing earlier can have written.
        state = monster_activity.read_monster_activity(self.wilderness)
        groups = dict(state.groups)
        groups[group_id] = replace(groups[group_id], next_decision_tick=START)
        monster_activity._write_state(
            self.wilderness,
            monster_activity._copy_state(state, groups=groups),
        )
        return group_id

    def test_out_of_scope_destination(self):
        group_id = self._refusal_world()
        before = settlement_projection(self.wilderness)
        self.assertEqual(
            self.group_state().groups[group_id].next_decision_tick, START
        )
        self.assertEqual(
            population_units.build_scope(
                self.wilderness, [self.unit_a]
            ).group_ids,
            frozenset({group_id}),
        )
        real_area = monster_activity.group_area
        east_locator = {
            "kind": "wilderness",
            "map": WILDERNESS_NAME,
            "x": EAST_OF_BOUNDARY[0],
            "y": EAST_OF_BOUNDARY[1],
        }

        def widened(group):
            return (*real_area(group), east_locator)

        def unmoved(group):
            return real_area(group)

        def faulted(wilderness, wanted, *, tick):
            group = monster_activity.read_monster_activity(wilderness).groups[wanted]
            return monster_activity.ActivityDecision(
                wanted,
                tick,
                group.sequence,
                PhysicalEdge(
                    source=LocationRef.wilderness(
                        WILDERNESS_NAME, *BOUNDARY_A
                    ),
                    destination=LocationRef.wilderness(
                        WILDERNESS_NAME, *EAST_OF_BOUNDARY
                    ),
                    route="direction:e",
                ),
                monster_activity.DECISION_DEPART,
            )

        # The fault: the settled reach the closure reads (``movable_area``) does
        # not name the cell the decision takes, while the owner's own area check
        # still admits it. A consistent record can never produce this -- the
        # closure reads the same area the decision reads -- so the guard is the
        # tripwire for a model that stopped being complete.
        with (
            patch.object(monster_activity, "group_area", widened),
            patch.object(monster_activity, "movable_area", unmoved),
            patch.object(monster_activity, "plan_group_decision", faulted),
        ):
            with self.assertRaises(population_units.PopulationScopeViolation):
                settle_population_scope(self.wilderness, [self.unit_a], START + 1)
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.assertEqual(group_id, self._only_group())

    def _only_group(self) -> str:
        groups = list(monster_activity.read_monster_activity(self.wilderness).groups)
        self.assertEqual(len(groups), 1)
        return groups[0]

    def test_group_reaching_outside_the_scope(self):
        self._build_scenario()
        before = {
            "groups": set(self.group_state().groups),
            "ids": {
                int(individual.pk)
                for individual in Monster.objects.all_family()
            },
            "registered": {
                int(individual.pk)
                for individual in self.wilderness.db.itemcoordinates
            },
        }
        real = regional_population.composition_row_bindings

        def bound(composition, *, site=None):
            return (ACTIVITY_B_WANDER,) * len(real(composition, site=site))

        with patch.object(regional_population, "composition_row_bindings", bound):
            with self.assertRaises(population_units.PopulationScopeViolation):
                settle_population_scope(self.wilderness, [self.unit_a], 400)
        self.assertEqual(set(self.group_state().groups), before["groups"])
        self.assertEqual(
            {int(individual.pk) for individual in Monster.objects.all_family()},
            before["ids"],
        )
        self.assertEqual(
            {
                int(individual.pk)
                for individual in self.wilderness.db.itemcoordinates
            },
            before["registered"],
        )