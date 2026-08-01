"""Tests for immutable registration presets."""

import unittest

from world.lore.player_presets import PLAYER_PRESET_REGISTRY, PlayerPreset
from world.lore.races import RACE_REGISTRY
from world.rules.character_creation import resolve_starting_profile


class PlayerPresetTests(unittest.TestCase):
    def test_catalog_covers_every_race_with_valid_adult_allocations(self):
        self.assertEqual(
            {preset.race for preset in PLAYER_PRESET_REGISTRY.values()},
            set(RACE_REGISTRY),
        )
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                self.assertIsInstance(preset, PlayerPreset)
                self.assertGreaterEqual(preset.age, 18)
                self.assertGreaterEqual(preset.apparent_age, 18)
                profile = resolve_starting_profile(preset.race, preset.subrace)
                allocations = preset.allocation_dict()
                self.assertEqual(sum(allocations.values()), profile.budget)
                for key, (lower, upper) in profile.bounds:
                    self.assertLessEqual(allocations[key], upper - lower)
