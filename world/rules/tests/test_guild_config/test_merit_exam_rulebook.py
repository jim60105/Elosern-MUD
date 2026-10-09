"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: MeritThresholdTests.
"""
import unittest
from world.rules.guild_config import EXAM_RANKS
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import validate_merit_thresholds
from ._support import (
    raw_rulebook,
)


class MeritThresholdTests(unittest.TestCase):
    def test_loaded_thresholds_are_strictly_increasing(self):
        raw = raw_rulebook()["merit_thresholds"]
        values = validate_merit_thresholds(raw)
        self.assertEqual(list(values), ["E", "D", "C", "B", "A", "S"])
        for lower, upper in zip(EXAM_RANKS, EXAM_RANKS[1:]):
            self.assertLess(values[lower], values[upper])

    def test_non_strict_sequence_is_rejected(self):
        bad = {"E": 5, "D": 5, "C": 40, "B": 90, "A": 200, "S": 500}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_negative_threshold_is_rejected(self):
        bad = {"E": -1, "D": 5, "C": 40, "B": 90, "A": 200, "S": 500}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_missing_threshold_rank_is_rejected(self):
        raw = raw_rulebook()["merit_thresholds"]
        bad = {k: v for k, v in raw.items() if k != "E"}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_unknown_threshold_rank_is_rejected(self):
        bad = {**raw_rulebook()["merit_thresholds"], "X": 1}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_non_integer_threshold_is_rejected(self):
        bad = {**raw_rulebook()["merit_thresholds"], "E": True}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

if __name__ == "__main__":
    unittest.main()
