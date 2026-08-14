"""Tests for immutable registration presets."""

import unittest

from tools.spec_traceability import covers_requirement

from world.lore.player_presets import PLAYER_PRESET_REGISTRY, PlayerPreset
from world.lore.races import RACE_REGISTRY
from world.rules.character_creation import resolve_starting_profile
from world.skills.registry import SKILL_REGISTRY, SkillKind


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

    def test_catalog_ships_exactly_eight_template_characters(self):
        self.assertEqual(len(PLAYER_PRESET_REGISTRY), 8)
        self.assertEqual(
            list(PLAYER_PRESET_REGISTRY),
            [
                "human_wanderer",
                "foxkin_scout",
                "elf_guardian",
                "violet_altoria",
                "lidzia_rosenthal",
                "yuka_darknight",
                "yuna_darknight",
                "elosia_shadowmoon",
            ],
        )

    def test_every_preset_skill_resolves_with_matching_kind(self):
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                for key in preset.active_skills:
                    self.assertEqual(SKILL_REGISTRY[key].kind, SkillKind.ACTIVE)
                for key in preset.passive_skills:
                    self.assertEqual(SKILL_REGISTRY[key].kind, SkillKind.PASSIVE)

    def test_divine_arts_skills_only_on_divine_affinity_races(self):
        for preset in PLAYER_PRESET_REGISTRY.values():
            with self.subTest(preset=preset.key):
                race = RACE_REGISTRY[preset.race]
                for key in (*preset.active_skills, *preset.passive_skills):
                    if SKILL_REGISTRY[key].requires_divine_arts:
                        self.assertTrue(race.can_use_divine_arts)

    def test_skill_lists_returns_the_storage_shape_in_declared_order(self):
        preset = PLAYER_PRESET_REGISTRY["yuna_darknight"]
        self.assertEqual(
            preset.skill_lists(),
            {
                "active": list(preset.active_skills),
                "passive": list(preset.passive_skills),
            },
        )
        self.assertEqual(preset.skill_lists()["active"], ["divine_sexual_arts"])

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_kit_validation_rejects_unknown_kind_mismatch_and_divine_gate(self):
        from world.lore.player_presets import _validate_preset_skill_kits

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e", background="b",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (make(active_skills=("not_a_skill",)), "unknown skill"),
            (make(active_skills=("body_enhancement_basic",)), "classifies it as"),
            (make(passive_skills=("light_sword_style",)), "classifies it as"),
            (make(passive_skills=("divine_sexual_mastery",)), "divine-arts"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_skill_kits({"x": preset})
        _validate_preset_skill_kits({"x": make(race="elf", subrace="fionnen", passive_skills=("divine_sexual_mastery",))})

    def test_identity_validation_rejects_unknown_and_incompatible_subraces(self):
        from world.lore.player_presets import _validate_preset_identities

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e", background="b",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        for preset, message in (
            (make(subrace="not_a_subrace"), "unknown subrace"),
            (make(subrace="foxkin"), "belonging to race"),
            (make(race="not_a_race"), "unknown race"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_identities({"x": preset})
        _validate_preset_identities({"x": make()})

    def test_catalog_ships_human_and_beastfolk_affinity_from_lore(self):
        self.assertEqual(
            PLAYER_PRESET_REGISTRY["violet_altoria"].affinity_elements,
            ("fire", "wind"),
        )
        self.assertEqual(
            PLAYER_PRESET_REGISTRY["foxkin_scout"].affinity_elements,
            ("wind",),
        )
        for key in ("human_wanderer", "lidzia_rosenthal"):
            self.assertEqual(PLAYER_PRESET_REGISTRY[key].affinity_elements, ())

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_elf_presets_must_declare_an_empty_affinity_set(self):
        for key in ("elf_guardian", "yuka_darknight", "yuna_darknight", "elosia_shadowmoon"):
            with self.subTest(preset=key):
                self.assertEqual(PLAYER_PRESET_REGISTRY[key].race, "elf")
                self.assertEqual(
                    PLAYER_PRESET_REGISTRY[key].affinity_elements, ()
                )

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_affinity_validation_rejects_unknown_duplicate_and_elf_non_empty(self):
        from world.lore.player_presets import _validate_preset_affinity_elements

        def make(**overrides):
            values = dict(
                key="x", display_name="x", age=18, apparent_age=18, race="human",
                subrace="human_commoner", allocations=(), emphasis="e", background="b",
            )
            values.update(overrides)
            return PlayerPreset(**values)

        cases = (
            (make(affinity_elements=("luck",)), "unknown affinity element"),
            (make(affinity_elements=("fire", "fire")), "duplicate affinity element"),
            (make(race="elf", subrace="fionnen", affinity_elements=("light",)), "elf preset"),
        )
        for preset, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                _validate_preset_affinity_elements({"x": preset})
        _validate_preset_affinity_elements({"x": make(affinity_elements=("fire", "wind"))})
        _validate_preset_affinity_elements(
            {"x": make(race="elf", subrace="fionnen")}
        )
