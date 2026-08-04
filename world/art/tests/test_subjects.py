"""Tests for the art subject model (pure, no database)."""

from unittest.mock import Mock
import unittest

from evennia.utils.test_resources import EvenniaTest

from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_description,
    character_subject_for,
    description_for,
    monster_description,
    monster_subject_for,
    parse_subject,
    scene_description,
    scene_subject_for,
)

from tools.spec_traceability import covers_requirement


class SubjectParsingTests(unittest.TestCase):
    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_known_kinds_parse_into_typed_subjects(self):
        cases = (
            ("scene:forest_path", ArtSubjectKind.SCENE, "forest_path"),
            ("portrait:character:42", ArtSubjectKind.CHARACTER, "42"),
            ("portrait:monster:gray_wolf", ArtSubjectKind.MONSTER, "gray_wolf"),
        )
        for full, kind, key in cases:
            subject = parse_subject(full)
            self.assertIs(subject.kind, kind)
            self.assertEqual(subject.key, key)
            self.assertEqual(subject.full(), full)

    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_malformed_keys_are_rejected(self):
        for bad in (
            "scene:",
            "scene:a:b",
            "scene:bad\x00key",
            "portrait:character:",
            "portrait:character:a:b",
            "unknown:key",
            "scene",
            "",
        ):
            with self.subTest(full_key=bad):
                with self.assertRaises(ArtSubjectError):
                    parse_subject(bad)

    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_kind_cannot_change_while_keeping_the_same_full_key(self):
        scene = ArtSubject(ArtSubjectKind.SCENE, "k")
        character = ArtSubject(ArtSubjectKind.CHARACTER, "k")
        monster = ArtSubject(ArtSubjectKind.MONSTER, "k")
        self.assertNotEqual(scene.full(), character.full())
        self.assertNotEqual(scene.full(), monster.full())
        self.assertNotEqual(character.full(), monster.full())


class RegistryResolutionTests(unittest.TestCase):
    @covers_requirement("art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries")
    def test_registered_archetypes_resolve(self):
        subject = scene_subject_for("tavern_interior")
        self.assertEqual(subject.full(), "scene:tavern_interior")
        monster = monster_subject_for("low")
        self.assertEqual(monster.full(), "portrait:monster:low")

    @covers_requirement("art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries")
    def test_unknown_archetypes_are_rejected(self):
        for bad in ("not_a_scene", "", "unknown_monster"):
            with self.subTest(bad=bad):
                with self.assertRaises(ArtSubjectError):
                    scene_subject_for(bad)
                with self.assertRaises(ArtSubjectError):
                    monster_subject_for(bad)


class PortraitPolicyTests(EvenniaTest):
    def _character(self, policy):
        character = Mock()
        character.db.portrait_policy = policy
        return character

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_explicit_named_policy_yields_a_unique_subject(self):
        subject = character_subject_for(self._character(
            {"mode": "named", "stable_key": "42"}
        ))
        self.assertEqual(subject.full(), "portrait:character:42")

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_no_named_policy_produces_no_unique_portrait(self):
        self.assertIsNone(character_subject_for(self._character(None)))
        self.assertIsNone(character_subject_for(self._character({"mode": "generic"})))

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_eligibility_is_not_inferred_from_display_name_uniqueness(self):
        named = self._character({"mode": "named", "stable_key": "42"})
        unnamed = self._character(None)
        named.key = "共同名字"
        unnamed.key = "共同名字"
        self.assertIsNotNone(character_subject_for(named))
        self.assertIsNone(character_subject_for(unnamed))

    def test_malformed_policy_raises(self):
        for bad in (
            {"mode": "named"},
            {"mode": "named", "stable_key": "a:b"},
            {"mode": "weird"},
            {"mode": "named", "stable_key": ""},
        ):
            with self.subTest(policy=bad):
                with self.assertRaises(ArtSubjectError):
                    character_subject_for(self._character(bad))


class DescriptionTests(EvenniaTest):
    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth")
    def test_character_description_contains_only_allowed_stable_data(self):
        character = Mock()
        character.db.display_name = "艾琳"
        character.db.race = "beastfolk"
        character.db.subrace = "catkin"
        character.db.persona = "secret tragic past"
        character.db.disguised_stats = {"atk_phys": 99}
        character.key = "艾琳"
        text = character_description(character, 24)
        self.assertIn("艾琳", text)
        self.assertIn("貓人族", text)
        self.assertIn("24", text)
        self.assertNotIn("secret tragic past", text)
        self.assertNotIn("99", text)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth")
    def test_scene_and_monster_descriptions_are_registry_text(self):
        scene = scene_subject_for("forest_path")
        monster = monster_subject_for("low")
        first = description_for(scene)
        second = description_for(scene)
        self.assertEqual(first, second)
        self.assertIn("林間小徑", first)
        monster_text = description_for(monster)
        self.assertIn("Threats a beginning adventurer", monster_text)
        self.assertEqual(monster_text, monster_description(monster))


if __name__ == "__main__":
    unittest.main()
