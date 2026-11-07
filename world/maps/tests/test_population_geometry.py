"""Behavior tests for the candidate-world ecology birth geometry.

Every fixture here is synthetic: an invented ridge/river world, invented
anchors, and invented settlement footprints, so no shipped coordinate, region
key, or settlement identity is read or pinned. Expected cell sets and density
bounds are enumerated from the fixture's own authored numbers, never obtained
by calling the calculator under test.

The four mechanisms under test are independent of the shipped map:
bounded zone geometry, the settlement birth-exclusion ring, integer density
bounds, and the complete-composition recovery proof.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping
from unittest import mock

from elosern_map_core.terrain import REGION_KEYS, TerrainDefinition, region_for_coordinates

from tools.spec_traceability import covers_requirement

from world.lore.anchors import Anchor, AnchorKind, GeographicAnchor
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    SettlementBirthPolicy,
    WeightedComposition,
)
from world.lore.wilderness_entry import WildernessEntryPoint
from world.lore.wilderness_regions import WildernessRegion
from world.maps import population_geometry
from world.maps.published import SourceMemo
from world.maps.population_geometry import (
    MINIMUM_SETTLEMENT_BUFFER,
    PopulationGeometryError,
    density_bounds,
    eligible_birth_cells,
    validate_ecology_geometry,
)

RECTANGLE = (10, 13, 10, 13)
ZONE = "t_fixture_zone"
TOWN = "t_fixture_town"
CAPITAL = "t_fixture_capital"
DUNGEON = "t_fixture_dungeon"
COMPOSITION = "t_fixture_composition"
ACTIVITY = "t_fixture_activity"


def _terrain() -> TerrainDefinition:
    """A small invented continent: ridge at x~43, river at row 15, forest north."""
    return TerrainDefinition(
        frame_cells=60,
        mainland_boundary_km=((0, 0), (60, 0), (60, 60), (0, 60)),
        forest_edge=((0, 25), (59, 25)),
        waterway_routes={"t_border_river": ((30, 15), (0, 15))},
        waterway_fords={},
        border_river_key="t_border_river",
        ridge_stem=((44, 0), (42, 25), (44, 59)),
        ridge_passes=((3, 4),),
        coastal_y_max=5,
        mountain_corridor_half_width=1,
        region_flavors={key: ("合成地形敘述。",) for key in REGION_KEYS},
    )


TERRAIN = _terrain()
#: The region the fixed test rectangle belongs to, read from the fixture world.
REGION = region_for_coordinates(TERRAIN, RECTANGLE[0], RECTANGLE[2])


@dataclass(frozen=True)
class _Candidate:
    """One candidate geography world, duck-typed to the snapshot's geometry fields."""

    terrain: TerrainDefinition
    regions: Mapping[str, Any]
    anchors: Mapping[str, Anchor]
    anchor_geography: Mapping[str, GeographicAnchor]


def _candidate(anchors=(), *, placed: bool = True) -> _Candidate:
    """A candidate world carrying exactly the given ``(key, kind, cell)`` anchors.

    ``placed`` publishes each anchor's geographic cell; ``False`` models a
    world whose anchor rows exist without any published map geometry.
    """
    anchor_map: dict[str, Anchor] = {}
    geography_map: dict[str, GeographicAnchor] = {}
    for key, kind, cell in anchors:
        anchor_map[key] = Anchor(key, kind, "合成錨點", None, None, None, "合成地點。")
        if placed:
            geography_map[key] = GeographicAnchor(key, cell, "合成地理限制")
    regions = {
        key: WildernessRegion(key, "合成區域", None, ("合成荒野敘述。",))
        for key in REGION_KEYS
    }
    return _Candidate(
        terrain=TERRAIN,
        regions=MappingProxyType(regions),
        anchors=MappingProxyType(anchor_map),
        anchor_geography=MappingProxyType(geography_map),
    )


def _entry(anchor_key: str, shape: tuple[str, ...], origin: tuple[int, int]):
    return WildernessEntryPoint(
        anchor_key=anchor_key, shape=shape, origin_xy=origin, gates=()
    )


def _composition(key: str = COMPOSITION, members=None) -> EncounterComposition:
    return EncounterComposition(
        key,
        ACTIVITY,
        (CompositionMember("t_fixture_variant", 1, 1),)
        if members is None
        else tuple(members),
    )


def _zone(**overrides) -> EcologyZone:
    fields = {
        "key": ZONE,
        "region_key": REGION,
        "rectangles": (RECTANGLE,),
        "pool": (WeightedComposition(COMPOSITION, 1),),
        "lower_density": 1,
        "upper_density": 50,
        "cell_capacity": 3,
        "recovery_delay": 3600,
        "replenishment_interval": 600,
        "wave_budget": 3,
    }
    fields.update(overrides)
    return EcologyZone(**fields)


def _rectangle_cells(rectangle=RECTANGLE) -> set[tuple[int, int]]:
    x_min, x_max, y_min, y_max = rectangle
    return {
        (x, y)
        for x in range(x_min, x_max + 1)
        for y in range(y_min, y_max + 1)
    }


def _eligible(zone=None, *, anchors=(), entries=None, policies=None):
    return eligible_birth_cells(
        _zone() if zone is None else zone,
        geography=_candidate(anchors),
        entries={} if entries is None else entries,
        policies={} if policies is None else policies,
    )


class DensityBoundsTests(unittest.TestCase):
    """Requirement: density intervals permit complete unobstructed recovery."""

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_sparse_densities_round_the_interval_outward(self):
        # Independently known: ceil(25*5/100)=2 and floor(25*12/100)=3.
        self.assertEqual(density_bounds(25, 5, 12), (2, 3))
        # ceil(400*1/100)=4 and floor(400*3/100)=12.
        self.assertEqual(density_bounds(400, 1, 3), (4, 12))
        # ceil(2*50/100)=1 and floor(2*99/100)=1.
        self.assertEqual(density_bounds(2, 50, 99), (1, 1))

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_invalid_densities_and_empty_domains_are_rejected(self):
        cases = (
            (0, 1, 10),
            (25, 0, 10),
            (25, 10, 9),
            (25, 1, 100),
            (25, 1, 1),
            (25, True, 10),
            (25, 1, False),
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(PopulationGeometryError):
                    density_bounds(*case)
        # ceil(1*1/100)=1 but floor(1*99/100)=0: no positive usable interval.
        with self.assertRaises(PopulationGeometryError):
            density_bounds(1, 1, 99)


class BirthGeometryTests(unittest.TestCase):
    """Requirement: eligible birth area excludes inhabited settlement surroundings."""

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings",
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats",
    )
    def test_zone_geometry_is_exactly_its_bounded_rectangle(self):
        cells = _eligible()
        # Every cell of the rectangle is walkable land inside its region, and
        # nothing outside the rectangle is ever returned.
        self.assertEqual(cells, tuple(sorted(_rectangle_cells())))
        self.assertNotIn((RECTANGLE[0] - 1, RECTANGLE[2]), cells)
        self.assertNotIn((RECTANGLE[1] + 1, RECTANGLE[3]), cells)

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_intersecting_rectangles_are_deduplicated_within_a_zone(self):
        overlapping = (11, 12, 11, 12)
        zone = _zone(rectangles=(RECTANGLE, overlapping))
        self.assertEqual(
            _eligible(zone), tuple(sorted(_rectangle_cells(RECTANGLE)))
        )

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_rectangle_crossing_region_and_water_rules_keeps_only_its_region(self):
        # Row 15 is the invented river (water, still western_hills_valleys);
        # rows 16-17 lie in the next region. Only row 14 is both the zone's
        # parent region and valid wilderness ground.
        zone = _zone(rectangles=((10, 13, 14, 17),))
        self.assertEqual(
            _eligible(zone), ((10, 14), (11, 14), (12, 14), (13, 14))
        )

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_footprint_settlement_excludes_its_exterior_ring(self):
        # The town's two-cell footprint is (10,10)-(11,10); the one-cell
        # Chebyshev ring removes the six rectangle cells around it.
        entry = _entry(TOWN, ("##",), (10, 10))
        cells = _eligible(
            anchors=[(TOWN, AnchorKind.TOWN, (10, 10))], entries={TOWN: entry}
        )
        self.assertEqual(
            cells,
            (
                (10, 12),
                (10, 13),
                (11, 12),
                (11, 13),
                (12, 12),
                (12, 13),
                (13, 10),
                (13, 11),
                (13, 12),
                (13, 13),
            ),
        )
        # The footprint itself and its immediate neighbours are all excluded.
        for excluded in ((10, 10), (11, 10), (12, 10), (10, 11), (11, 11), (12, 11)):
            self.assertNotIn(excluded, cells)

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_noncapital_and_a_capital_settlement_exclude_identically(self):
        entry = _entry(TOWN, ("##",), (10, 10))
        noncapital = _eligible(
            anchors=[(TOWN, AnchorKind.TOWN, (10, 10))], entries={TOWN: entry}
        )
        capital_entry = _entry(CAPITAL, ("##",), (10, 10))
        capital = _eligible(
            anchors=[(CAPITAL, AnchorKind.CAPITAL, (10, 10))],
            entries={CAPITAL: capital_entry},
        )
        self.assertEqual(noncapital, capital)
        self.assertNotIn((12, 10), noncapital)

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_point_settlement_uses_its_published_anchor_cell(self):
        # A point-shaped village at (14,12): distance is measured from the
        # anchor cell alone, excluding (13,11)-(13,13) inside the rectangle.
        entry = _entry(TOWN, (".#.",), (13, 12))
        cells = _eligible(
            anchors=[(TOWN, AnchorKind.ELVEN_VILLAGE, (14, 12))],
            entries={TOWN: entry},
        )
        expected = _rectangle_cells() - {(13, 11), (13, 12), (13, 13)}
        self.assertEqual(cells, tuple(sorted(expected)))

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_dungeon_anchor_receives_no_settlement_buffer(self):
        # A point-shaped dungeon straddling the rectangle would still be an
        # anchor-footprint-free point: no exclusion at all.
        entry = _entry(DUNGEON, (".#.",), (11, 12))
        cells = _eligible(
            anchors=[(DUNGEON, AnchorKind.DUNGEON, (12, 12))],
            entries={DUNGEON: entry},
        )
        self.assertEqual(cells, tuple(sorted(_rectangle_cells())))

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_dungeon_footprint_is_removed_by_shared_validity_only(self):
        # An anchor footprint cell is never wilderness ground, so the shared
        # rule removes the two footprint cells; the neighbours stay eligible
        # because a dungeon grants no birth buffer.
        entry = _entry(DUNGEON, ("##",), (10, 10))
        cells = _eligible(
            anchors=[(DUNGEON, AnchorKind.DUNGEON, (59, 59))],
            entries={DUNGEON: entry},
        )
        expected = _rectangle_cells() - {(10, 10), (11, 10)}
        self.assertEqual(cells, tuple(sorted(expected)))

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_an_explicit_policy_enlarges_the_buffer(self):
        entry = _entry(TOWN, ("##",), (10, 10))
        anchors = [(TOWN, AnchorKind.TOWN, (10, 10))]
        minimum_ring = _eligible(anchors=anchors, entries={TOWN: entry})
        self.assertIn((12, 12), minimum_ring)
        cells = _eligible(
            anchors=anchors,
            entries={TOWN: entry},
            policies={TOWN: SettlementBirthPolicy(TOWN, 2)},
        )
        # A two-cell ring leaves only the rectangle's northern row.
        self.assertEqual(
            cells, ((10, 13), (11, 13), (12, 13), (13, 13))
        )
        self.assertNotIn((12, 12), cells)

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_policy_below_the_generic_ring_is_rejected(self):
        entry = _entry(TOWN, ("##",), (10, 10))
        for buffer in (0, -3, True):
            with self.subTest(buffer=buffer):
                with self.assertRaises(PopulationGeometryError):
                    _eligible(
                        anchors=[(TOWN, AnchorKind.TOWN, (10, 10))],
                        entries={TOWN: entry},
                        policies={
                            TOWN: SettlementBirthPolicy(TOWN, buffer)
                        },
                    )

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_the_candidate_entries_decide_the_footprint(self):
        # The same anchor and rectangle: only the candidate's own wilderness
        # entry can turn a distant anchor cell into an overlapping footprint.
        anchors = [(TOWN, AnchorKind.TOWN, (0, 0))]
        without_entry = _eligible(anchors=anchors)
        with_entry = _eligible(
            anchors=anchors, entries={TOWN: _entry(TOWN, ("##",), (10, 10))}
        )
        self.assertEqual(without_entry, tuple(sorted(_rectangle_cells())))
        self.assertNotEqual(with_entry, without_entry)

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_map_less_settlement_uses_its_candidate_anchor_cell(self):
        near = _candidate([(TOWN, AnchorKind.TOWN, (14, 12))])
        far = _candidate([(TOWN, AnchorKind.TOWN, (0, 0))])
        near_cells = eligible_birth_cells(
            _zone(), geography=near, entries={}, policies={}
        )
        far_cells = eligible_birth_cells(
            _zone(), geography=far, entries={}, policies={}
        )
        self.assertEqual(
            near_cells,
            tuple(sorted(_rectangle_cells() - {(13, 11), (13, 12), (13, 13)})),
        )
        self.assertEqual(far_cells, tuple(sorted(_rectangle_cells())))

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_the_live_wilderness_registry_is_never_consulted(self):
        # A footprint over the whole rectangle in the published registry must
        # not change a candidate-denominated answer.
        live = {TOWN: _entry(TOWN, ("####", "####", "####", "####"), (10, 10))}
        with mock.patch(
            "world.lore.wilderness_entry.WILDERNESS_ENTRY" + "_REGISTRY",
            MappingProxyType(live),
        ):
            cells = _eligible()
        self.assertEqual(cells, tuple(sorted(_rectangle_cells())))

    def test_an_inhabited_anchor_without_published_geometry_excludes_nothing(self):
        # A world may carry an inhabited anchor row whose map geometry does not
        # exist (the managed-browser install merges its stand-in anchors into
        # the authored world). Such a settlement has no surroundings to keep
        # free, so its presence must not reject the zone's whole geometry.
        unplaced = _candidate([(TOWN, AnchorKind.TOWN, (14, 12))], placed=False)
        cells = eligible_birth_cells(
            _zone(), geography=unplaced, entries={}, policies={}
        )
        self.assertEqual(cells, tuple(sorted(_rectangle_cells())))

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_a_policy_naming_a_nonsettlement_anchor_is_rejected(self):
        entry = _entry(DUNGEON, (".#.",), (11, 12))
        for anchor_key, kind in ((DUNGEON, AnchorKind.DUNGEON), ("t_unknown", None)):
            with self.subTest(anchor_key=anchor_key):
                anchors = [] if kind is None else [(DUNGEON, kind, (12, 12))]
                with self.assertRaises(PopulationGeometryError):
                    _eligible(
                        anchors=anchors,
                        entries={DUNGEON: entry},
                        policies={
                            anchor_key: SettlementBirthPolicy(anchor_key, 2)
                        },
                    )


class CandidatePublicationTests(unittest.TestCase):
    """Requirement: ecology declarations publish only complete valid habitats."""

    def _problems(self, zones, *, anchors=(), entries=None, compositions=None, policies=None):
        return validate_ecology_geometry(
            geography=_candidate(anchors),
            entries={} if entries is None else entries,
            zones=zones,
            compositions={COMPOSITION: _composition()}
            if compositions is None
            else compositions,
            policies={} if policies is None else policies,
        )

    def test_a_complete_candidate_has_no_problem(self):
        self.assertEqual(self._problems({ZONE: _zone()}), ())

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_overlapping_zones_are_rejected_even_before_exclusions(self):
        first = _zone()
        second = _zone(key="t_fixture_other_zone", rectangles=((12, 15, 12, 15),))
        problems = self._problems({ZONE: first, second.key: second})
        self.assertTrue(problems)
        self.assertIn(ZONE, problems[0])
        self.assertIn(second.key, problems[0])

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_a_zone_outside_its_parent_region_is_rejected(self):
        other_region = next(key for key in REGION_KEYS if key != REGION)
        problems = self._problems({ZONE: _zone(region_key=other_region)})
        self.assertTrue(problems)

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_a_zone_with_no_eligible_cell_is_rejected(self):
        # The whole rectangle lies inside the town's one-cell ring.
        entry = _entry(TOWN, ("##",), (10, 10))
        zone = _zone(rectangles=((10, 11, 10, 11),))
        problems = self._problems(
            {ZONE: zone},
            anchors=[(TOWN, AnchorKind.TOWN, (10, 10))],
            entries={TOWN: entry},
        )
        self.assertTrue(any("no eligible birth cell" in problem for problem in problems))

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_a_pool_with_no_complete_recovery_path_is_rejected(self):
        # E=16, densities 50/60 -> lower 8, upper 9. A three-individual group
        # cannot fit the two remaining headroom from seven living individuals,
        # so no wave can bring that unobstructed population into the band.
        group = _composition(
            COMPOSITION, (CompositionMember("t_fixture_variant", 3, 3),)
        )
        zone = _zone(lower_density=50, upper_density=60, cell_capacity=3, wave_budget=3)
        problems = self._problems({ZONE: zone}, compositions={COMPOSITION: group})
        self.assertTrue(any("no complete recovery path" in problem for problem in problems))
        # One-individual compositions can always climb from seven to nine.
        self.assertEqual(self._problems({ZONE: zone}), ())

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_a_composition_above_the_upper_bound_is_rejected(self):
        # E=16, densities 1/10 -> lower 1, upper 1; a two-individual group can
        # never fit the only allowed total.
        pair = _composition(
            COMPOSITION,
            (
                CompositionMember("t_fixture_variant", 1, 1),
                CompositionMember("t_fixture_variant_b", 1, 1),
            ),
        )
        zone = _zone(lower_density=1, upper_density=10)
        problems = self._problems({ZONE: zone}, compositions={COMPOSITION: pair})
        self.assertTrue(any("above its upper bound" in problem for problem in problems))

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_a_pool_recovers_over_repeated_waves_and_may_overshoot_the_lower_bound(self):
        # E=20, densities 25/35 -> lower 5, upper 7. A three-individual group
        # recovers 0 -> 3 -> 6, which crosses the lower bound without landing
        # on it exactly.
        group = _composition(
            COMPOSITION, (CompositionMember("t_fixture_variant", 3, 3),)
        )
        zone = _zone(
            rectangles=((10, 13, 10, 14),),
            lower_density=25,
            upper_density=35,
        )
        self.assertEqual(
            self._problems({ZONE: zone}, compositions={COMPOSITION: group}), ()
        )

    @covers_requirement(
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery"
    )
    def test_headroom_is_proven_by_fitting_compositions_not_by_one_fixed_size(self):
        # The same E=20 at 25/30 gives lower 5, upper 6. Recovering from four
        # living individuals needs a one-individual increment, which the
        # one-to-three composition can select without truncating a group.
        varied = _composition(
            COMPOSITION, (CompositionMember("t_fixture_variant", 1, 3),)
        )
        group = _composition(
            COMPOSITION, (CompositionMember("t_fixture_variant", 3, 3),)
        )
        zone = _zone(
            rectangles=((10, 13, 10, 14),),
            lower_density=25,
            upper_density=30,
        )
        self.assertEqual(
            self._problems({ZONE: zone}, compositions={COMPOSITION: varied}), ()
        )
        problems = self._problems({ZONE: zone}, compositions={COMPOSITION: group})
        self.assertTrue(
            any("no complete recovery path" in problem for problem in problems)
        )


if __name__ == "__main__":
    unittest.main()


class SourceMemoTests(unittest.TestCase):
    """Derived map values follow the identity of their immutable sources."""

    def test_a_value_is_built_once_per_source_generation(self):
        memo = SourceMemo()
        source = {"a": 1}
        builds = mock.Mock(side_effect=[1, 2, 3])
        self.assertEqual(memo.resolve((source,), "key", builds), 1)
        self.assertEqual(memo.resolve((source,), "key", builds), 1)
        self.assertEqual(memo.resolve((source,), "other", builds), 2)
        self.assertEqual(builds.call_count, 2)

    def test_an_equal_but_distinct_source_drops_every_value(self):
        memo = SourceMemo()
        memo.resolve(({"a": 1},), "key", lambda: "old")
        self.assertEqual(memo.resolve(({"a": 1},), "key", lambda: "new"), "new")
