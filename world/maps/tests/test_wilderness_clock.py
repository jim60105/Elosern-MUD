"""Regression tests for the wilderness travel context (map-wilderness D-5)."""

from tools.spec_traceability import covers_requirement

import types
import unittest

from world.rules.clock import CLOCK_YAML
from world.rules.travel_cost import distance_traversal_cost, wilderness_distance_m

#: ``wilderness_move`` remains the distinct wilderness flight-waiver context
#: key; its seconds value is an authored connector default, never the duration
#: authority for a distance-bearing step.
CONNECTOR = types.SimpleNamespace()


class WildernessClockCostTests(unittest.TestCase):
    @covers_requirement("wilderness-gateway::wilderness-move-is-a-new-distinct-clock-cost-not-a-reuse-of-the-grid-s-move-constant")
    def test_wilderness_move_is_declared_and_distinct_from_move(self):
        defaults = CLOCK_YAML["command_defaults"]
        self.assertEqual(defaults["wilderness_move"], 9000)
        self.assertEqual(defaults["move"], 30)

    @covers_requirement("wilderness-gateway::wilderness-move-is-a-new-distinct-clock-cost-not-a-reuse-of-the-grid-s-move-constant")
    def test_no_fixed_wilderness_seconds_authority_remains(self):
        # The declared cell span and terrain speed decide the duration: a
        # cardinal 1 km step is 800 s on a good road and 2,400 s on a rough
        # mountain trail, neither equal to the retained connector constant.
        cardinal = wilderness_distance_m((0, 0), (1, 0))
        road = distance_traversal_cost(cardinal, "road", [CONNECTOR])
        mountain = distance_traversal_cost(cardinal, "mountain_trail", [CONNECTOR])
        self.assertEqual(road.seconds, 800)
        self.assertEqual(mountain.seconds, 2400)
        self.assertNotEqual(road.seconds, CLOCK_YAML["command_defaults"]["wilderness_move"])
        self.assertNotEqual(
            mountain.seconds, CLOCK_YAML["command_defaults"]["wilderness_move"]
        )

    @covers_requirement("wilderness-gateway::wilderness-move-is-a-new-distinct-clock-cost-not-a-reuse-of-the-grid-s-move-constant")
    def test_continent_crossing_stays_a_sane_travel_time(self):
        # Full 2700-step crossing at the one-kilometre cell span: a good-road
        # crossing is about 25 days and the slowest terrain about 75 days,
        # the latter inside the authored season bounds; the exact numbers are
        # arithmetic here, not a single clock advance.
        seconds_per_hour = CLOCK_YAML["seconds_per_hour"]
        hours_per_day = CLOCK_YAML["hours_per_day"]
        days_per_season = CLOCK_YAML["days_per_season"]
        cardinal = wilderness_distance_m((0, 0), (1, 0))

        road_days = (
            2700 * distance_traversal_cost(cardinal, "road", [CONNECTOR]).seconds
        ) / (seconds_per_hour * hours_per_day)
        mountain_days = (
            2700
            * distance_traversal_cost(cardinal, "mountain_trail", [CONNECTOR]).seconds
        ) / (seconds_per_hour * hours_per_day)

        self.assertAlmostEqual(road_days, 25.0, delta=0.01)
        self.assertAlmostEqual(mountain_days, 75.0, delta=0.01)
        self.assertLess(mountain_days / days_per_season, 1.0)
