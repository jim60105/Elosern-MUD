"""Behavior tests for authored monster field-activity declarations.

Every row here is a file-local synthetic fixture with invented keys. The tests
prove declared geometry, closed vocabularies, count-compatible bindings and
candidate-world checks without pinning a shipped coordinate, name or count.
"""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from elosern_map_core.terrain import (
    REGION_KEYS,
    TerrainDefinition,
    is_land_cell,
    region_for_coordinates,
)

from world.lore import monster_activity as registry
from world.lore.monster_activity import (
    ACTIVITY_AREA_REGISTRY,
    AGGRESSION_KINDS,
    MONSTER_ACTIVITY_POLICIES,
    MONSTER_ACTIVITY_REGISTRY,
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
    MonsterActivityRegistryError,
    activity_area_problems,
    build_activity_area_registry,
    build_monster_activity_registry,
    resolve_activity_area,
    validate_activity_binding,
    validate_activity_registries,
)
from world.lore.monster_placement import (
    ENCOUNTER_COMPOSITION_REGISTRY,
    MONSTER_SITE_REGISTRY,
    composition_bounds,
)
from world.lore.wilderness_regions import WildernessRegion

AREA = "t_fixture_area"
OTHER_AREA = "t_fixture_other_area"
ACTIVITY = "t_fixture_activity"
REGION = "t_fixture_region"
MAP = "t_fixture_map"
DAY = "t_fixture_dawn"


def _terrain() -> TerrainDefinition:
    """One invented continent: a ridge, a river row and a northern forest."""
    return TerrainDefinition(
        frame_cells=40,
        mainland_boundary_km=((0, 0), (30, 0), (30, 30), (0, 30)),
        forest_edge=((0, 20), (39, 20)),
        waterway_routes={"t_river": ((20, 15), (0, 15))},
        waterway_fords={},
        border_river_key="t_river",
        ridge_stem=((30, 0), (28, 20), (30, 39)),
        ridge_passes=((3, 4),),
        coastal_y_max=3,
        mountain_corridor_half_width=1,
        region_flavors={key: ("合成地形敘述。",) for key in REGION_KEYS},
    )


TERRAIN = _terrain()


@dataclass(frozen=True)
class _Candidate:
    terrain: TerrainDefinition
    regions: Mapping[str, Any]
    settlements: object | None = None


def _candidate(regions=REGION_KEYS, settlements=None) -> _Candidate:
    rows = {
        key: WildernessRegion(key, "合成區域", None, ("合成荒野敘述。",))
        for key in regions
    }
    return _Candidate(
        terrain=TERRAIN,
        regions=MappingProxyType(rows),
        settlements=settlements,
    )


def _land_block() -> tuple[int, int, str]:
    """One in-frame cell whose full 3x3 neighbourhood is land, plus its region."""
    for y in range(2, 38):
        for x in range(2, 38):
            cells = ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if all(is_land_cell(TERRAIN, cell) for cell in cells):
                return x, y, region_for_coordinates(TERRAIN, x, y)
    raise AssertionError("the fixture terrain has no open land block")


def _area(**overrides) -> ActivityArea:
    fields = {"key": AREA, "home_radius": 0}
    fields.update(overrides)
    return ActivityArea(**fields)


def _activity(**overrides) -> MonsterActivity:
    fields = {
        "key": ACTIVITY,
        "policy": "stationary",
        "area_key": AREA,
        "decision_interval": 60,
        "aggression": AggressionCondition("passive"),
    }
    fields.update(overrides)
    return MonsterActivity(**fields)


def _wilderness_home(x: int, y: int) -> dict[str, object]:
    return {"kind": "wilderness", "map": MAP, "x": x, "y": y}


class GeometryResolutionTests(unittest.TestCase):
    """Region and home geometry resolve to deterministic legal-cell locators."""

    def test_region_extent_enumerates_only_its_region_and_sorts_canonically(self):
        x, y, region_key = _land_block()
        rectangle = (x - 1, x + 1, y - 1, y + 1)
        area = _area(region_key=region_key, rectangles=(rectangle,), home_radius=None)
        first = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=_candidate()
        )
        second = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=_candidate()
        )
        self.assertEqual(first, second)
        self.assertTrue(first)
        for locator in first:
            self.assertEqual(locator["kind"], "wilderness")
            self.assertEqual(locator["map"], MAP)
            self.assertTrue(
                rectangle[0] <= locator["x"] <= rectangle[1]
                and rectangle[2] <= locator["y"] <= rectangle[3]
            )
            self.assertEqual(
                region_for_coordinates(TERRAIN, locator["x"], locator["y"]),
                region_key,
            )
            self.assertTrue(is_land_cell(TERRAIN, (locator["x"], locator["y"])))
        self.assertEqual(
            list(first),
            sorted(
                first,
                key=lambda locator: json.dumps(
                    locator, sort_keys=True, separators=(",", ":")
                ),
            ),
        )

    def test_duplicate_rectangles_do_not_duplicate_cells(self):
        x, y, region_key = _land_block()
        rectangle = (x, x, y, y)
        area = _area(
            region_key=region_key,
            rectangles=(rectangle, rectangle),
            home_radius=None,
        )
        resolved = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=_candidate()
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0], _wilderness_home(x, y))

    def test_home_radius_is_inclusive_chebyshev_distance(self):
        x, y, _region = _land_block()
        area = _area(home_radius=1)
        resolved = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=_candidate()
        )
        # The whole 3x3 neighbourhood is land, so every cell at distance <= 1
        # is a legal activity cell.
        self.assertEqual(len(resolved), 9)
        self.assertIn(_wilderness_home(x, y), resolved)
        for locator in resolved:
            self.assertLessEqual(abs(locator["x"] - x), 1)
            self.assertLessEqual(abs(locator["y"] - y), 1)

    def test_zero_radius_contains_only_the_home_cell(self):
        x, y, _region = _land_block()
        resolved = resolve_activity_area(
            _area(home_radius=0),
            home=_wilderness_home(x, y),
            candidate_world=_candidate(),
        )
        self.assertEqual(resolved, (_wilderness_home(x, y),))

    def test_room_home_zero_contains_that_room_only(self):
        home = {"kind": "room", "id": 7}
        resolved = resolve_activity_area(
            _area(home_radius=0), home=home, candidate_world=_candidate()
        )
        self.assertEqual(resolved, (home,))

    def test_nonzero_room_radius_and_region_geometry_reject_room_homes(self):
        with self.assertRaises(MonsterActivityRegistryError):
            resolve_activity_area(
                _area(home_radius=1),
                home={"kind": "room", "id": 7},
                candidate_world=_candidate(),
            )
        with self.assertRaises(MonsterActivityRegistryError):
            resolve_activity_area(
                _area(
                    region_key=REGION,
                    rectangles=((1, 2, 1, 2),),
                    home_radius=None,
                ),
                home={"kind": "room", "id": 7},
                candidate_world=_candidate(),
            )

    def test_malformed_home_locators_are_rejected(self):
        homes = (
            None,
            {"kind": "wilderness"},
            {"kind": "wilderness", "map": "", "x": 1, "y": 2},
            {"kind": "wilderness", "map": MAP, "x": True, "y": 2},
            {"kind": "wilderness", "map": MAP, "x": 1, "y": 2, "extra": 3},
            {"kind": "room", "id": True},
            {"kind": "room", "id": 7, "extra": 1},
            {"kind": "elsewhere", "id": 7},
        )
        for home in homes:
            with self.subTest(home=home):
                with self.assertRaises(MonsterActivityRegistryError):
                    resolve_activity_area(
                        _area(home_radius=0),
                        home=home,
                        candidate_world=_candidate(),
                    )

    def test_settlement_buffers_never_participate_in_activity_geometry(self):
        x, y, region_key = _land_block()
        area = _area(
            region_key=region_key,
            rectangles=((x, x, y, y),),
            home_radius=None,
        )
        without = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=_candidate()
        )
        masked = _candidate(
            settlements={"t_settlement": {"footprint_cells": ((x, y),)}}
        )
        with_buffers = resolve_activity_area(
            area, home=_wilderness_home(x, y), candidate_world=masked
        )
        self.assertEqual(without, with_buffers)


class DeclarationValidationTests(unittest.TestCase):
    """Declarations reject unknown references and malformed forms atomically."""

    def _reject(self, areas=None, activities=None, **kwargs) -> None:
        with self.assertRaises(MonsterActivityRegistryError):
            validate_activity_registries(
                {AREA: _area()} if areas is None else areas,
                {ACTIVITY: _activity()} if activities is None else activities,
                **kwargs,
            )

    def test_invalid_area_forms_are_rejected(self):
        cases = (
            _area(region_key=REGION, rectangles=(), home_radius=None),
            _area(region_key=None, rectangles=((1, 2, 1, 2),), home_radius=1),
            _area(region_key=REGION, rectangles=((1, 2, 1, 2),), home_radius=0),
            _area(region_key=REGION, rectangles=(), home_radius=0),
            _area(home_radius=-1),
            _area(home_radius=True),
            _area(region_key=REGION, rectangles=((2, 1, 1, 2),), home_radius=None),
            _area(region_key=REGION, rectangles=((1, 2, 1),), home_radius=None),
            _area(region_key=REGION, rectangles=((1, True, 1, 2),), home_radius=None),
            _area(
                region_key=REGION,
                rectangles=((1, 2, 1, 2), ((1, 2, 1, 2),)),
                home_radius=None,
            ),
        )
        for area in cases:
            with self.subTest(area=area):
                self._reject(areas={AREA: area})

    def test_area_region_face_rejects_an_unknown_region(self):
        area = _area(region_key="t_absent_region", rectangles=((1, 2, 1, 2),))
        self._reject(areas={AREA: area}, region_face=(REGION,))

    def test_activity_key_identity_and_closed_vocabularies_are_enforced(self):
        cases = (
            _activity(policy="wander"),
            _activity(area_key="t_absent_area"),
            _activity(decision_interval=0),
            _activity(decision_interval=-1),
            _activity(decision_interval=True),
            _activity(decision_interval=1.0),
            _activity(aggression=AggressionCondition("hostile")),
            _activity(aggression=AggressionCondition("defended_area")),
            _activity(
                aggression=AggressionCondition("defended_area", "t_absent_area")
            ),
            _activity(
                aggression=AggressionCondition("passive", AREA)
            ),
            _activity(aggression=AggressionCondition("contact", dayparts=("night",))),
            _activity(
                aggression=AggressionCondition("contact", dayparts=(DAY, DAY))
            ),
            _activity(aggression=AggressionCondition("contact", dayparts=DAY)),
        )
        for activity in cases:
            with self.subTest(activity=activity):
                self._reject(activities={ACTIVITY: activity})

    def test_keyed_builders_reject_duplicate_keys(self):
        with self.assertRaises(MonsterActivityRegistryError):
            build_activity_area_registry((_area(), _area()))
        with self.assertRaises(MonsterActivityRegistryError):
            build_monster_activity_registry((_activity(), _activity()))

    def test_a_mapping_key_must_match_the_row_key(self):
        self._reject(areas={OTHER_AREA: _area()})
        self._reject(activities={OTHER_AREA: _activity()})

    def test_validation_publishes_nothing_on_failure(self):
        areas = {AREA: _area()}
        activities = {ACTIVITY: _activity()}
        before = (dict(areas), dict(activities))
        with self.assertRaises(MonsterActivityRegistryError):
            validate_activity_registries(
                areas,
                {OTHER_AREA: _activity()},
            )
        self.assertEqual((dict(areas), dict(activities)), before)


class BindingValidationTests(unittest.TestCase):
    """A solitary binding requires every legal composition outcome to be one."""

    def test_solitary_binding_rejects_any_multi_individual_outcome(self):
        activity = _activity(policy="solitary_roaming")
        validate_activity_binding(activity, 1, "t_fixture")
        for largest in (2, 3):
            with self.subTest(largest=largest):
                with self.assertRaises(MonsterActivityRegistryError):
                    validate_activity_binding(activity, largest, "t_fixture")

    def test_other_policies_accept_complete_groups_but_need_an_integer(self):
        for policy in ("stationary", "cohesive_group"):
            with self.subTest(policy=policy):
                validate_activity_binding(_activity(policy=policy), 3, "t_fixture")
                with self.assertRaises(MonsterActivityRegistryError):
                    validate_activity_binding(
                        _activity(policy=policy), True, "t_fixture"
                    )

    def test_unknown_policies_and_kinds_stay_closed(self):
        self.assertEqual(
            MONSTER_ACTIVITY_POLICIES,
            ("stationary", "solitary_roaming", "cohesive_group"),
        )
        self.assertEqual(AGGRESSION_KINDS, ("passive", "contact", "defended_area"))


class CandidateAreaValidationTests(unittest.TestCase):
    """Candidate-world geometry rejects unknown regions and impossible bounds."""

    def test_unknown_region_outside_frame_and_no_land_are_reported(self):
        unknown = activity_area_problems(
            _area(region_key="t_absent_region", rectangles=((1, 2, 1, 2),)),
            _candidate(),
        )
        self.assertTrue(any("unknown candidate region" in item for item in unknown))
        outside = activity_area_problems(
            _area(region_key=REGION, rectangles=((39, 41, 0, 0),)),
            _candidate(),
        )
        self.assertTrue(any("outside the candidate frame" in item for item in outside))
        # Outside the fixture mainland polygon, inside its frame.
        offshore = activity_area_problems(
            _area(
                region_key=next(iter(REGION_KEYS)),
                rectangles=((35, 35, 35, 35),),
            ),
            _candidate(),
        )
        self.assertTrue(
            any("intersects no legal cell" in item for item in offshore)
        )

    def test_a_lawful_region_extent_reports_no_problem(self):
        x, y, region_key = _land_block()
        self.assertEqual(
            activity_area_problems(
                _area(region_key=region_key, rectangles=((x, x, y, y),)),
                _candidate(),
            ),
            [],
        )

    def test_home_distance_geometry_needs_no_candidate_cells(self):
        self.assertEqual(
            activity_area_problems(_area(home_radius=3), _candidate()), []
        )


class PublishedActivityRegistryTests(unittest.TestCase):
    """Shipped declarations are frozen and every reference resolves."""

    def test_published_registries_are_read_only_proxies(self):
        for published in (ACTIVITY_AREA_REGISTRY, MONSTER_ACTIVITY_REGISTRY):
            self.assertIsInstance(published, MappingProxyType)
            self.assertTrue(published)
            with self.assertRaises(TypeError):
                published["t_fixture_intruder"] = None

    def test_every_shipped_reference_resolves(self):
        for key, activity in MONSTER_ACTIVITY_REGISTRY.items():
            with self.subTest(activity=key):
                self.assertIn(activity.area_key, ACTIVITY_AREA_REGISTRY)
                if activity.aggression.kind == "defended_area":
                    self.assertIn(
                        activity.aggression.area_key, ACTIVITY_AREA_REGISTRY
                    )
        for key, composition in ENCOUNTER_COMPOSITION_REGISTRY.items():
            with self.subTest(composition=key):
                activity = MONSTER_ACTIVITY_REGISTRY[composition.activity_key]
                validate_activity_binding(
                    activity, composition_bounds(composition)[1], key
                )
        for key, site in MONSTER_SITE_REGISTRY.items():
            with self.subTest(site=key):
                activity = MONSTER_ACTIVITY_REGISTRY[site.activity_key]
                composition = ENCOUNTER_COMPOSITION_REGISTRY[
                    site.composition_key
                ]
                validate_activity_binding(
                    activity, composition_bounds(composition)[1], key
                )

    def test_the_module_offers_no_execution_callable(self):
        public = {
            name
            for name in dir(registry)
            if not name.startswith("_") and callable(getattr(registry, name))
        }
        for fragment in ("spawn", "move", "populate", "reconcile", "schedule"):
            offending = [name for name in public if fragment in name.lower()]
            self.assertEqual(offending, [], f"{fragment} appears in {offending}")


if __name__ == "__main__":
    unittest.main()
