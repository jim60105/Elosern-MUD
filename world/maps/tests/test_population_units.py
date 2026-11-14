"""Behaviour tests: authored geometry resolves to independently settled units.

A settlement unit is a part of the monster population whose settlement never
reads another part's state, and each unit records how far it has been settled.
The geometry scenarios use hand-built ``t_`` registries only; the live-state
and cursor scenarios use the file-local synthetic activity rows of
``test_monster_activity``. No test asserts wall-clock time or hardware speed:
the assertions are unit identifiers, exact cursor values and state equality.

Each test claims the canonical identifier of the requirement and scenario its
assertions establish.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from types import MappingProxyType
from unittest import TestCase
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

import world.lore.monster_activity as lore_activity
import world.lore.monster_placement as lore_placement
from world.lore.monster_activity import ActivityArea, AggressionCondition, MonsterActivity
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
)
from world.maps import population_units, regional_population
from world.maps.monster_activity import (
    JourneyPlan,
    MonsterJourney,
    read_monster_activity,
    state_to_dict,
)
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.population_units import (
    POPULATION_UNIT_CURSORS_ATTRIBUTE,
    RESIDUAL_UNIT,
    UnitCursors,
    advance_unit_cursors,
    build_unit_index,
    current_unit_index,
    group_units,
    read_unit_cursors,
    site_area_links,
    site_unit,
    unit_closure,
    unit_cursor,
    unit_of_location,
    write_unit_cursors,
    zone_bound_areas,
)
from world.maps.regional_population import (
    MalformedPopulationState,
    initialize_population_seed,
    read_population_timeline,
)
from world.maps.tests.test_monster_activity import (
    AREA_KEY,
    PROBE,
    SEED,
    ActivityFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.movement_edges import LocationRef, PhysicalEdge

REGION = "t_units_region"
OTHER_REGION = "t_units_other_region"


def _zone(
    key: str,
    region_key: str = REGION,
    rectangles: tuple[tuple[int, int, int, int], ...] = (),
    pool: tuple[WeightedComposition, ...] = (),
) -> EcologyZone:
    """One synthetic zone; ``test_population_zone_pass`` uses placeholders too."""
    return EcologyZone(
        key,
        region_key,
        rectangles,
        pool,
        lower_density=1,
        upper_density=100,
        cell_capacity=1,
        recovery_delay=60,
        replenishment_interval=60,
        wave_budget=1,
    )


def _area(
    key: str,
    region_key: str = REGION,
    rectangles: tuple[tuple[int, int, int, int], ...] = (),
) -> ActivityArea:
    """One synthetic region-bound activity area."""
    return ActivityArea(key, region_key, rectangles)


class AuthoredGeometryTests(TestCase):
    """Authored zones and areas resolve to units without reading the database."""

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_disjoint_zones_resolve_to_two_units(self):
        index = build_unit_index(
            {
                "t_zone_west": _zone("t_zone_west", rectangles=((0, 9, 0, 9),)),
                "t_zone_east": _zone("t_zone_east", rectangles=((20, 29, 0, 9),)),
            },
            {},
            {},
        )
        west = index.unit_of_zone["t_zone_west"]
        east = index.unit_of_zone["t_zone_east"]
        self.assertNotEqual(west, east)
        self.assertEqual(west, "zone:t_zone_west")
        self.assertEqual(east, "zone:t_zone_east")
        self.assertEqual(index.unit_of_cell(REGION, (5, 5)), west)
        self.assertEqual(index.unit_of_cell(REGION, (25, 5)), east)

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_an_area_that_overlaps_two_zones_bridges_them(self):
        index = build_unit_index(
            {
                "t_zone_west": _zone("t_zone_west", rectangles=((0, 9, 0, 9),)),
                "t_zone_east": _zone("t_zone_east", rectangles=((20, 29, 0, 9),)),
            },
            {"t_bridge": _area("t_bridge", rectangles=((9, 20, 0, 9),))},
            {},
        )
        unit = index.unit_of_zone["t_zone_west"]
        self.assertEqual(index.unit_of_zone["t_zone_east"], unit)
        self.assertEqual(index.unit_of_area["t_bridge"], unit)
        self.assertEqual(index.unit_of_cell(REGION, (5, 5)), unit)
        self.assertEqual(index.unit_of_cell(REGION, (25, 5)), unit)

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_birth_binding_links_a_zone_to_a_distant_area(self):
        zone = _zone(
            "t_zone",
            rectangles=((0, 9, 0, 9),),
            pool=(WeightedComposition("t_composition", 1),),
        )
        distant = _area("t_distant_area", rectangles=((100, 109, 100, 109),))
        index = build_unit_index(
            {"t_zone": zone},
            {"t_distant_area": distant},
            {"t_zone": frozenset({"t_distant_area"})},
        )
        self.assertEqual(index.unit_of_zone["t_zone"], "zone:t_zone")
        self.assertEqual(index.unit_of_area["t_distant_area"], "zone:t_zone")
        self.assertEqual(
            index.unit_of_cell(REGION, (5, 5)),
            index.unit_of_cell(REGION, (105, 105)),
        )

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_equal_rectangles_in_different_regions_are_two_units(self):
        index = build_unit_index(
            {
                "t_zone_here": _zone(
                    "t_zone_here", REGION, rectangles=((0, 9, 0, 9),)
                ),
                "t_zone_there": _zone(
                    "t_zone_there", OTHER_REGION, rectangles=((0, 9, 0, 9),)
                ),
            },
            {},
            {},
        )
        self.assertNotEqual(
            index.unit_of_zone["t_zone_here"],
            index.unit_of_zone["t_zone_there"],
        )
        self.assertEqual(index.unit_of_cell(REGION, (5, 5)), "zone:t_zone_here")
        self.assertEqual(
            index.unit_of_cell(OTHER_REGION, (5, 5)), "zone:t_zone_there"
        )

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_resolution_is_stable_when_the_registries_are_reversed(self):
        zones = {
            "t_zone_a": _zone("t_zone_a", rectangles=((0, 9, 0, 9),)),
            "t_zone_b": _zone("t_zone_b", rectangles=((20, 29, 0, 9),)),
            "t_zone_c": _zone("t_zone_c", rectangles=((0, 9, 20, 29),)),
        }
        areas = {
            "t_area_ab": _area("t_area_ab", rectangles=((9, 20, 0, 9),)),
            "t_area_c": _area("t_area_c", rectangles=((0, 9, 20, 29),)),
            "t_area_far": _area("t_area_far", rectangles=((200, 209, 200, 209),)),
        }
        forward = build_unit_index(zones, areas, {})
        backward = build_unit_index(
            dict(reversed(list(zones.items()))),
            dict(reversed(list(areas.items()))),
            {},
        )
        self.assertEqual(dict(forward.unit_of_zone), dict(backward.unit_of_zone))
        self.assertEqual(dict(forward.unit_of_area), dict(backward.unit_of_area))
        self.assertEqual(dict(forward.rectangles), dict(backward.rectangles))
        for cell in ((5, 5), (25, 5), (5, 25), (205, 205), (500, 500)):
            self.assertEqual(
                forward.unit_of_cell(REGION, cell),
                backward.unit_of_cell(REGION, cell),
            )

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_a_room_and_an_uncovered_cell_are_the_residual_unit(self):
        index = build_unit_index(
            {"t_zone": _zone("t_zone", rectangles=((0, 9, 0, 9),))}, {}, {}
        )
        self.assertIsNone(unit_of_location(index, None))
        self.assertEqual(unit_of_location(index, LocationRef.room(1)), RESIDUAL_UNIT)
        self.assertEqual(index.unit_of_cell(None, (0, 0)), RESIDUAL_UNIT)
        self.assertEqual(index.unit_of_cell(REGION, (500, 500)), RESIDUAL_UNIT)
        self.assertEqual(index.unit_of_cell(OTHER_REGION, (5, 5)), RESIDUAL_UNIT)

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_zone_bound_areas_read_birth_bindings_from_the_registries(self):
        zone = _zone(
            "t_zone",
            rectangles=((0, 9, 0, 9),),
            pool=(WeightedComposition("t_composition", 1),),
        )
        composition = EncounterComposition(
            "t_composition",
            "t_activity",
            (CompositionMember("t_variant", 1, 1),),
        )
        activity = MonsterActivity(
            "t_activity",
            "cohesive_group",
            "t_zone_grounds",
            60,
            AggressionCondition("passive"),
        )
        site_composition = EncounterComposition(
            "t_site_composition",
            "t_site_activity",
            (CompositionMember("t_variant", 1, 1),),
        )
        site_activity = MonsterActivity(
            "t_site_activity",
            "solitary_roaming",
            "t_site_grounds",
            60,
            AggressionCondition("passive"),
        )
        site = MonsterSite(
            "t_site",
            "camp",
            REGION,
            (5, 5),
            "t_site_composition",
            None,
            1,
            False,
        )
        areas = {
            "t_zone_grounds": _area("t_zone_grounds", rectangles=((0, 9, 0, 9),)),
            "t_site_grounds": _area("t_site_grounds", rectangles=((0, 9, 0, 9),)),
            "t_site_home": ActivityArea("t_site_home", home_radius=0),
        }
        with (
            patch.object(
                lore_placement,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({"t_zone": zone}),
            ),
            patch.object(
                lore_placement,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(
                    {
                        "t_composition": composition,
                        "t_site_composition": site_composition,
                    }
                ),
            ),
            patch.object(
                lore_placement,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({"t_site": site}),
            ),
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(
                    {"t_activity": activity, "t_site_activity": site_activity}
                ),
            ),
            patch.object(
                lore_activity,
                "ACTIVITY_AREA_REGISTRY",
                MappingProxyType(areas),
            ),
        ):
            bound = zone_bound_areas()
            self.assertEqual(
                bound["t_zone"],
                frozenset({"t_zone_grounds", "t_site_grounds"}),
            )
            # A site whose cell lies inside the zone joins through the zone.
            self.assertEqual(site_area_links(), ())

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_a_site_outside_every_zone_joins_its_own_areas(self):
        composition = EncounterComposition(
            "t_site_composition",
            "t_site_activity_a",
            (
                CompositionMember("t_variant", 1, 1),
                CompositionMember("t_variant", 1, 1, "t_site_activity_b"),
            ),
        )
        site = MonsterSite(
            "t_site",
            "camp",
            REGION,
            (500, 500),
            "t_site_composition",
            None,
            1,
            False,
        )
        areas = {
            "t_area_a": _area("t_area_a", rectangles=((500, 509, 500, 509),)),
            "t_area_b": _area("t_area_b", rectangles=((520, 529, 520, 529),)),
        }
        activities = {
            "t_site_activity_a": MonsterActivity(
                "t_site_activity_a",
                "cohesive_group",
                "t_area_a",
                60,
                AggressionCondition("passive"),
            ),
            "t_site_activity_b": MonsterActivity(
                "t_site_activity_b",
                "solitary_roaming",
                "t_area_b",
                60,
                AggressionCondition("passive"),
            ),
        }
        with (
            patch.object(
                lore_placement,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({}),
            ),
            patch.object(
                lore_placement,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType({"t_site_composition": composition}),
            ),
            patch.object(
                lore_placement,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({"t_site": site}),
            ),
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(activities),
            ),
            patch.object(
                lore_activity,
                "ACTIVITY_AREA_REGISTRY",
                MappingProxyType(areas),
            ),
        ):
            self.assertEqual(zone_bound_areas(), {})
            links = site_area_links()
            self.assertEqual(links, (frozenset({"t_area_a", "t_area_b"}),))
            index = build_unit_index({}, areas, {}, links)
            self.assertEqual(
                index.unit_of_area["t_area_a"],
                index.unit_of_area["t_area_b"],
            )
            self.assertEqual(index.unit_of_area["t_area_a"], "area:t_area_a")


class UnitResolutionTests(ActivityFixture):
    """Two disjoint synthetic zones inside the real published probe region."""

    def setUp(self):
        super().setUp()
        # A runtime lookup by attribute string: the sanctioned seam for reading
        # one authored row of a shipped registry from a behaviour test.
        self.probe_area = getattr(lore_activity, "ACTIVITY_AREA_REGISTRY")[
            AREA_KEY
        ].rectangles[0]
        self.second_cell = self._outside_cell(PROBE, self.region)
        self.enterContext(
            patch.object(
                lore_placement,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType(
                    {
                        "t_units_zone_a": _zone(
                            "t_units_zone_a",
                            self.region,
                            ((PROBE[0], PROBE[0], PROBE[1], PROBE[1]),),
                        ),
                        "t_units_zone_b": _zone(
                            "t_units_zone_b",
                            self.region,
                            (
                                (
                                    self.second_cell[0],
                                    self.second_cell[0],
                                    self.second_cell[1],
                                    self.second_cell[1],
                                ),
                            ),
                        ),
                    }
                ),
            )
        )
        self.enterContext(
            patch.object(
                lore_placement,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType({}),
            )
        )
        self.enterContext(
            patch.object(
                lore_placement,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({}),
            )
        )
        self.index = current_unit_index()
        self.unit_a = self.index.unit_of_zone["t_units_zone_a"]
        self.unit_b = self.index.unit_of_zone["t_units_zone_b"]

    def _outside_cell(
        self, cell: tuple[int, int], region_key: str
    ) -> tuple[int, int]:
        """One published cell of the region outside the probe activity area."""
        for offset in range(20, 120):
            candidate = (cell[0] + offset, cell[1])
            if (
                regional_population.cell_region(candidate) == region_key
                and not self._in_probe_area(candidate)
            ):
                return candidate
        raise AssertionError("no second cell of the probe region")

    def _in_probe_area(self, candidate: tuple[int, int]) -> bool:
        """Whether a cell lies inside the fixture's authored activity extent."""
        x_min, x_max, y_min, y_max = self.probe_area
        x, y = candidate
        return x_min <= x <= x_max and y_min <= y <= y_max

    @covers_requirement(
        "population-settlement-units::a-group-s-units-and-unit-closures-are-derived-from-live-state"
    )
    def test_a_group_inside_its_zone_touches_exactly_that_unit(self):
        group_id, _bodies = self._group(cell=PROBE, owner_key="t_units_zone_a")
        state = read_monster_activity(self.wilderness)
        self.assertEqual(
            group_units(self.index, state.groups[group_id], None),
            frozenset({self.unit_a}),
        )
        self.assertEqual(
            unit_closure(self.index, state, {self.unit_a}),
            frozenset({self.unit_a}),
        )

    @covers_requirement(
        "population-settlement-units::a-group-s-units-and-unit-closures-are-derived-from-live-state"
    )
    def test_an_escaped_member_links_two_units(self):
        group_id, _bodies = self._group(cell=PROBE, owner_key="t_units_zone_a")
        state = read_monster_activity(self.wilderness)
        escaped = replace(
            state.groups[group_id],
            position=LocationRef.wilderness(WILDERNESS_NAME, *self.second_cell),
        )
        self.wilderness.db.monster_activity = state_to_dict(
            replace(state, groups={**state.groups, group_id: escaped})
        )
        state = read_monster_activity(self.wilderness)
        self.assertEqual(
            group_units(self.index, state.groups[group_id], None),
            frozenset({self.unit_a, self.unit_b}),
        )
        self.assertEqual(
            unit_closure(self.index, state, {self.unit_b}),
            frozenset({self.unit_a, self.unit_b}),
        )
        self.assertEqual(
            unit_closure(self.index, state, {self.unit_a}),
            frozenset({self.unit_a, self.unit_b}),
        )

    @covers_requirement(
        "population-settlement-units::a-group-s-units-and-unit-closures-are-derived-from-live-state"
    )
    def test_journey_endpoints_touch_both_units_until_arrival(self):
        group_id, bodies = self._group(cell=PROBE, owner_key="t_units_zone_a")
        state = read_monster_activity(self.wilderness)
        journey = MonsterJourney(
            "t_journey",
            group_id,
            tuple(body.pk for body in bodies),
            LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            LocationRef.wilderness(WILDERNESS_NAME, *self.second_cell),
            0,
            600,
            0,
            None,
            PhysicalEdge(
                LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
                LocationRef.wilderness(WILDERNESS_NAME, *self.second_cell),
                "direction:n",
            ),
            JourneyPlan(0, Fraction(0), (), (), ()),
        )
        travelling = replace(
            state,
            groups={
                **state.groups,
                group_id: replace(
                    state.groups[group_id], position=None, journey_id="t_journey"
                ),
            },
            journeys={"t_journey": journey},
        )
        self.assertEqual(
            group_units(self.index, travelling.groups[group_id], journey),
            frozenset({self.unit_a, self.unit_b}),
        )
        self.assertEqual(
            unit_closure(self.index, travelling, {self.unit_b}),
            frozenset({self.unit_a, self.unit_b}),
        )

    @covers_requirement(
        "population-settlement-units::authored-geometry-resolves-to-settlement-units"
    )
    def test_a_room_and_an_uncovered_cell_are_the_residual_unit(self):
        self.assertEqual(
            unit_of_location(self.index, LocationRef.room(1)), RESIDUAL_UNIT
        )
        outside = self._uncovered_cell()
        self.assertEqual(
            unit_of_location(
                self.index, LocationRef.wilderness(WILDERNESS_NAME, *outside)
            ),
            RESIDUAL_UNIT,
        )

    def test_an_unknown_site_is_the_residual_unit(self):
        self.assertEqual(site_unit(self.index, "t_unknown_site"), RESIDUAL_UNIT)

    def _uncovered_cell(self) -> tuple[int, int]:
        """One published cell of no authored zone or activity area."""
        for offset in range(20, 120):
            for candidate in (
                (self.second_cell[0] + offset, self.second_cell[1] + 60),
                (self.second_cell[0] + 60, self.second_cell[1] + offset),
            ):
                region_key = regional_population.cell_region(candidate)
                if (
                    region_key is not None
                    and self.index.unit_of_cell(region_key, candidate)
                    == RESIDUAL_UNIT
                ):
                    return candidate
        raise AssertionError("no uncovered published cell")


class UnitCursorTests(ActivityFixture):
    """Each unit records its settled-through tick and refuses a bad record."""

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_fresh_provisioning_records_the_provisioning_tick(self):
        for attribute in (
            regional_population.POPULATION_SEED_ATTRIBUTE,
            regional_population.POPULATION_TIMELINE_ATTRIBUTE,
            POPULATION_UNIT_CURSORS_ATTRIBUTE,
        ):
            self.wilderness.attributes.remove(attribute)
        initialize_population_seed(self.wilderness, seed=SEED, tick=100)
        cursors = read_unit_cursors(self.wilderness)
        self.assertEqual(cursors.default, 100)
        self.assertEqual(cursors.units, {})
        for unit_id in ("zone:t_any_zone", "area:t_any_area", RESIDUAL_UNIT):
            self.assertEqual(unit_cursor(cursors, unit_id), 100)

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_a_pass_records_its_endpoint_for_every_unit(self):
        self.assertEqual(read_unit_cursors(self.wilderness).default, 0)
        settle_population_lifecycle(100, 260)
        cursors = read_unit_cursors(self.wilderness)
        self.assertEqual(cursors.default, 260)
        self.assertEqual(unit_cursor(cursors, "zone:t_any_zone"), 260)
        self.assertEqual(unit_cursor(cursors, RESIDUAL_UNIT), 260)

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_explicit_units_advance_without_moving_the_default(self):
        write_unit_cursors(self.wilderness, UnitCursors(50, {}))
        advance_unit_cursors(self.wilderness, ("zone:t_one",), 80)
        cursors = read_unit_cursors(self.wilderness)
        self.assertEqual(cursors.default, 50)
        self.assertEqual(unit_cursor(cursors, "zone:t_one"), 80)
        self.assertEqual(unit_cursor(cursors, "zone:t_two"), 50)
        # A cursor never decreases.
        advance_unit_cursors(self.wilderness, ("zone:t_one",), 40)
        self.assertEqual(
            unit_cursor(read_unit_cursors(self.wilderness), "zone:t_one"), 80
        )
        # A whole-world advance raises every listed unit with the default.
        write_unit_cursors(
            self.wilderness, UnitCursors(50, MappingProxyType({"zone:t_one": 90}))
        )
        advance_unit_cursors(self.wilderness, None, 70)
        cursors = read_unit_cursors(self.wilderness)
        self.assertEqual(cursors.default, 70)
        self.assertEqual(unit_cursor(cursors, "zone:t_one"), 90)
        self.assertEqual(unit_cursor(cursors, "zone:t_two"), 70)

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_a_later_stage_failure_restores_the_record(self):
        self._register_lifecycle()
        settle_population_lifecycle(0, 100)
        self.assertEqual(read_unit_cursors(self.wilderness).default, 100)
        clock = get_world_clock()
        clock.tick = 100
        clock._persist(100)
        before = read_unit_cursors(self.wilderness)
        recorded: list[int] = []
        advance = population_units.advance_unit_cursors

        def recording(wilderness, unit_ids, tick):
            advance(wilderness, unit_ids, tick)
            # The clock stage settles the observed units, and this world has no
            # party: the residual unit is the one that really advanced.
            recorded.append(
                unit_cursor(read_unit_cursors(wilderness), RESIDUAL_UNIT)
            )

        from world.rules import clock as clock_module

        def late_stage(start: int, end: int) -> list:
            raise RuntimeError("late stage fault")

        with patch.object(population_units, "advance_unit_cursors", recording):
            clock_module.register_event_source("field_contact", late_stage)
            self.addCleanup(
                clock_module._EVENT_SOURCES.pop, "field_contact", None
            )
            with self.assertRaises(RuntimeError):
                clock.advance(160, AdvanceSource.SKIP, [])
        self.assertEqual(recorded, [260])
        self.assertEqual(read_unit_cursors(self.wilderness), before)
        self.wilderness.attributes.reset_cache()
        self.assertEqual(read_unit_cursors(self.wilderness), before)

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_a_missing_or_malformed_record_refuses_and_rewrites_nothing(self):
        cases = (
            [],
            {"default": 0},
            {"default": 0, "units": {}, "extra": 1},
            {"default": True, "units": {}},
            {"default": -1, "units": {}},
            {"default": 0, "units": []},
            {"default": 0, "units": {"zone:t_one": "5"}},
            {"default": 0, "units": {"": 5}},
            {"default": 0, "units": {5: 5}},
        )
        self.wilderness.attributes.remove(POPULATION_UNIT_CURSORS_ATTRIBUTE)
        self.assertFalse(
            self.wilderness.attributes.has(POPULATION_UNIT_CURSORS_ATTRIBUTE)
        )
        with self.assertRaises(MalformedPopulationState):
            read_unit_cursors(self.wilderness)
        self.assertFalse(
            self.wilderness.attributes.has(POPULATION_UNIT_CURSORS_ATTRIBUTE)
        )
        for case in cases:
            with self.subTest(case=case):
                self.wilderness.db.population_unit_cursors = case
                with self.assertRaises(MalformedPopulationState):
                    read_unit_cursors(self.wilderness)
                self.assertEqual(
                    self.wilderness.attributes.get(POPULATION_UNIT_CURSORS_ATTRIBUTE),
                    case,
                )

    @covers_requirement(
        "population-settlement-units::each-unit-records-its-settlement-progress"
    )
    def test_a_pass_over_a_missing_or_malformed_record_refuses_before_settling(self):
        timeline_tick = read_population_timeline(self.wilderness).settled_through_tick
        activity_tick = read_monster_activity(self.wilderness).settled_through_tick
        cases = (None, {"default": "5", "units": {}}, {"default": 0})
        for case in cases:
            with self.subTest(case=case):
                self.wilderness.attributes.remove(POPULATION_UNIT_CURSORS_ATTRIBUTE)
                if case is not None:
                    self.wilderness.db.population_unit_cursors = case
                with self.assertRaises(MalformedPopulationState):
                    settle_population_lifecycle(100, 260)
                # No settlement was committed, so a direct caller outside a
                # clock advance cannot leave an advanced world behind a raise.
                self.assertEqual(
                    read_population_timeline(self.wilderness).settled_through_tick,
                    timeline_tick,
                )
                self.assertEqual(
                    read_monster_activity(self.wilderness).settled_through_tick,
                    activity_tick,
                )
                if case is None:
                    self.assertFalse(
                        self.wilderness.attributes.has(
                            POPULATION_UNIT_CURSORS_ATTRIBUTE
                        )
                    )
                else:
                    self.assertEqual(
                        self.wilderness.attributes.get(
                            POPULATION_UNIT_CURSORS_ATTRIBUTE
                        ),
                        case,
                    )

    def _stored_cursor_bytes(self) -> object:
        """The serialized stored cursor value, for a byte-level comparison."""
        attribute = self.wilderness.attributes.get(
            POPULATION_UNIT_CURSORS_ATTRIBUTE, return_obj=True
        )
        return None if attribute is None else repr(attribute.db_value)

    def test_a_refused_advance_leaves_the_stored_mapping_untouched(self):
        write_unit_cursors(self.wilderness, UnitCursors(50, {"zone:t_one": 60}))
        before = self._stored_cursor_bytes()
        # The invalid unit identifier is reached before the one write, so
        # neither its own unit nor the earlier one is raised.
        with self.assertRaises(ValueError):
            advance_unit_cursors(self.wilderness, ("zone:t_one", ""), 80)
        self.assertEqual(self._stored_cursor_bytes(), before)
        # An invalid tick refuses before the read that could store anything.
        with self.assertRaises(ValueError):
            advance_unit_cursors(self.wilderness, None, -1)
        self.assertEqual(self._stored_cursor_bytes(), before)
        self.assertEqual(
            read_unit_cursors(self.wilderness),
            UnitCursors(50, {"zone:t_one": 60}),
        )