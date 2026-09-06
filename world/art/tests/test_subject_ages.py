"""Tests for canonical character-age eligibility (design D3).

The "never reaches the worker" regression is asserted on the full lifecycle
path in ``world/art/tests/test_service.py`` using the counting fixture; here we
cover the pure eligibility contract — canonical attribute presence and type —
against real ``PlayerCharacter`` attributes.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.art.subjects import ArtSubjectError, character_ages

from tools.spec_traceability import covers_requirement


class CharacterAgesTests(EvenniaTestCase):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.character = create_object(PlayerCharacter, key="gate-test")
        self.character.age = 22
        self.character.apparent_age = 22

    @covers_requirement("art-asset-lifecycle::portrait-character-enqueue-validates-canonical-age-attributes-immediately-before-enqueue")
    def test_valid_canonical_ages_pass(self):
        age, apparent_age = character_ages(self.character)
        self.assertEqual((age, apparent_age), (22, 22))

    @covers_requirement("art-asset-lifecycle::portrait-character-enqueue-validates-canonical-age-attributes-immediately-before-enqueue")
    def test_zero_ages_pass(self):
        self.character.age = 0
        self.character.apparent_age = 0
        self.assertEqual(character_ages(self.character), (0, 0))

    @covers_requirement("art-asset-lifecycle::portrait-character-enqueue-validates-canonical-age-attributes-immediately-before-enqueue")
    def test_missing_or_malformed_values_reject_with_a_named_diagnostic(self):
        for field in ("age", "apparent_age"):
            self.character.attributes.remove(field)
            with self.assertRaises(ArtSubjectError) as ctx:
                character_ages(self.character)
            self.assertIn(field, str(ctx.exception))
            self.character.age = 22
            self.character.apparent_age = 22

    def test_string_age_value_is_rejected(self):
        self.character.age = "22"
        with self.assertRaises(ArtSubjectError) as ctx:
            character_ages(self.character)
        self.assertIn("age", str(ctx.exception))

    def test_boolean_age_value_is_rejected(self):
        self.character.age = True
        with self.assertRaises(ArtSubjectError) as ctx:
            character_ages(self.character)
        self.assertIn("age", str(ctx.exception))


if __name__ == "__main__":
    import unittest

    unittest.main()
