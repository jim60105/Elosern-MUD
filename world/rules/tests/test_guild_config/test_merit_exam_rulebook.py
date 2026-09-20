"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: MeritThresholdTests, ExamProfileTests.
"""
import unittest
from world.rules.guild_config import EXAM_RANKS
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import validate_exam_profiles
from world.rules.guild_config import validate_merit_thresholds
from world.skills.registry import SKILL_REGISTRY
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

class ExamProfileTests(unittest.TestCase):
    def test_every_profile_stays_inside_its_lore_band(self):
        from world.lore.races import STATIC_TIER_REGISTRY

        raw = raw_rulebook()["exam_profiles"]
        profiles = validate_exam_profiles(raw)
        self.assertEqual(list(profiles), ["E", "D", "C", "B", "A", "S"])
        for rank, profile in profiles.items():
            band = STATIC_TIER_REGISTRY[profile.static_tier_key].band
            self.assertTrue(band[0] <= profile.atk_phys <= band[1])
            self.assertTrue(band[0] <= profile.agility <= band[1])
            self.assertTrue(band[0] <= profile.defense <= band[1])

    def test_every_exam_skill_key_exists(self):
        raw = raw_rulebook()["exam_profiles"]
        profiles = validate_exam_profiles(raw)
        for profile in profiles.values():
            for skill_key in profile.skills:
                self.assertIn(skill_key, SKILL_REGISTRY)

    def test_out_of_band_stat_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {"E": {**raw["E"], "atk_phys": 100}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_wrong_tier_mapping_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {"E": {**raw["E"], "static_tier": "human_elite"}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_unknown_skill_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {
            "E": {**raw["E"], "skills": ["basic_attack", "no_such_skill"]},
            **{k: v for k, v in raw.items() if k != "E"},
        }
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_missing_profile_rank_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {k: v for k, v in raw.items() if k != "E"}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_unknown_profile_rank_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {**raw, "X": raw["E"]}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_non_mapping_profile_entry_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {**raw, "E": "nope"}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_empty_profile_skills_are_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {"E": {**raw["E"], "skills": []}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)


if __name__ == "__main__":
    unittest.main()
