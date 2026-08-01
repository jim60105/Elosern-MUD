"""Regression tests for the wilderness_move clock constant (map-wilderness D-5)."""

import unittest

from world.rules.clock import CLOCK_YAML


class WildernessClockCostTests(unittest.TestCase):
    def test_wilderness_move_is_declared_and_distinct_from_move(self):
        defaults = CLOCK_YAML["command_defaults"]
        self.assertEqual(defaults["wilderness_move"], 9000)
        self.assertEqual(defaults["move"], 30)

    def test_continent_crossing_stays_a_sane_travel_time(self):
        # Full 224-step crossing at 10 km/step: the D-5 arithmetic, asserted as
        # a closed-form regression so a future balance edit is caught.
        seconds_per_hour = CLOCK_YAML["seconds_per_hour"]
        hours_per_day = CLOCK_YAML["hours_per_day"]
        days_per_season = CLOCK_YAML["days_per_season"]
        wilderness_move = CLOCK_YAML["command_defaults"]["wilderness_move"]

        total_seconds = 224 * wilderness_move
        total_days = total_seconds / (seconds_per_hour * hours_per_day)
        season_fraction = total_days / days_per_season
        self.assertAlmostEqual(total_days, 23.33, delta=0.01)
        self.assertAlmostEqual(season_fraction, 0.26, delta=0.005)
