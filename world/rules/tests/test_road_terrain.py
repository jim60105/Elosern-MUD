"""Road terrain: one wilderness step is a road step at both ends, in either direction."""

from __future__ import annotations

import unittest
from unittest import mock

from elosern_map_core.roads_codec import RoadNetwork
from world.maps import road_network
from world.rules import travel_cost
from world.rules.fatigue import get_policy
from world.rules.tests.test_travel_plan import (
    _OPEN,
    PlannerTestCase,
    _box,
    _snapshot,
    _traveller,
)
from world.rules.travel_cost import (
    ROAD_TERRAIN,
    distance_traversal_cost,
    wilderness_distance_m,
    wilderness_step_cost,
    wilderness_terrain,
)
from world.rules.travel_plan import plan_travel

#: The production region→terrain join, captured before ``PlannerTestCase``
#: replaces it in ``setUp``; the planner case must exercise the real function.
_PRODUCTION_TERRAIN = travel_cost.wilderness_terrain

_SYNTHETIC_TERRAIN = {"t_open": "open_ground", "t_woodland": "woodland"}


def _network(cells) -> RoadNetwork:
    """One synthetic network: never a shipped road cell."""
    return RoadNetwork(
        fingerprint="t_road_terrain",
        nodes=(),
        roads=(),
        cells=frozenset(tuple(cell) for cell in cells),
    )


class _RoadTerrainCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._previous_network = road_network.current()
        self.addCleanup(road_network._install, self._previous_network)
        self.regions = {}
        patches = (
            mock.patch.object(
                travel_cost,
                "region_for_coordinates",
                side_effect=lambda x, y: self.regions[(x, y)],
            ),
            mock.patch.dict(
                travel_cost.WILDERNESS_TERRAIN, dict(_SYNTHETIC_TERRAIN)
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def fill(self, cells, region: str) -> None:
        for cell in cells:
            self.regions[tuple(cell)] = region


class RoadTerrainTests(_RoadTerrainCase):
    def test_a_step_between_two_road_cells_is_a_road_step(self):
        self.fill([(0, 0), (1, 0), (1, 1)], "t_open")
        road_network._install(_network({(0, 0), (1, 0), (1, 1)}))
        member = _traveller(get_policy().max_units).detached()

        for source, destination in (((0, 0), (1, 0)), ((0, 0), (1, 1))):
            with self.subTest(source=source, destination=destination):
                self.assertEqual(
                    wilderness_terrain(source, destination), ROAD_TERRAIN
                )
                cost = wilderness_step_cost(source, destination, (member,))
                expected = distance_traversal_cost(
                    wilderness_distance_m(source, destination),
                    ROAD_TERRAIN,
                    (member,),
                )
                self.assertEqual(cost.seconds, expected.seconds)

    def test_a_partial_step_keeps_the_slower_region_in_both_directions(self):
        self.fill([(0, 0), (1, 0), (2, 0)], "t_open")
        self.regions[(1, 0)] = "t_woodland"
        road_network._install(_network({(0, 0)}))

        for source, destination in (((0, 0), (1, 0)), ((1, 0), (0, 0))):
            with self.subTest(source=source, destination=destination):
                self.assertEqual(
                    wilderness_terrain(source, destination), "woodland"
                )

    def test_a_road_cell_queried_with_itself_answers_road(self):
        self.fill([(0, 0), (5, 5)], "t_woodland")
        road_network._install(_network({(0, 0)}))

        self.assertEqual(wilderness_terrain((0, 0), (0, 0)), ROAD_TERRAIN)
        self.assertEqual(wilderness_terrain((5, 5), (5, 5)), "woodland")

    def test_no_published_network_keeps_the_regional_terrain(self):
        self.fill([(0, 0), (1, 0)], "t_open")
        self.regions[(1, 0)] = "t_woodland"
        road_network._install(None)

        self.assertEqual(wilderness_terrain((0, 0), (1, 0)), "woodland")


class PlannerRoadTerrainTests(PlannerTestCase):
    """Two cardinal-only routes of equal length: only one runs on a road."""

    def setUp(self):
        super().setUp()
        self._previous_network = road_network.current()
        self.addCleanup(road_network._install, self._previous_network)
        patches = (
            mock.patch.object(
                travel_cost,
                "region_for_coordinates",
                side_effect=lambda x, y: self.terrain[(x, y)],
            ),
            mock.patch.dict(
                travel_cost.WILDERNESS_TERRAIN, {"open_ground": "open_ground"}
            ),
            # This case must run the production join, not the regional pick the
            # shared planner fixture installs.
            mock.patch.object(
                travel_cost, "wilderness_terrain", new=_PRODUCTION_TERRAIN
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_planner_takes_the_road_at_equal_distance(self):
        self.fill(_box(5, 5, 7, 7), _OPEN)
        del self.terrain[(6, 6)]  # the impassable centre forces cardinal routes
        road_route = [(5, 5), (5, 6), (5, 7), (6, 7)]
        road_network._install(_network(road_route))
        traveller = _traveller(get_policy().max_units)

        plan = plan_travel(
            _snapshot((5, 5), _box(5, 5, 7, 7), [traveller]), (7, 7), "forced", False
        )

        self.assertEqual(
            [step.cell for step in plan.steps],
            [(5, 6), (5, 7), (6, 7), (7, 7)],
        )
        self.assertEqual(plan.stop_reason, "destination_reached")
        seconds, _ = self.replay(
            (5, 5),
            [step.cell for step in plan.steps],
            [(traveller.reserve_units, traveller.posture)],
        )
        self.assertEqual([step.seconds for step in plan.steps], seconds)
        self.assertEqual(plan.total_seconds, sum(seconds))


if __name__ == "__main__":
    unittest.main()
