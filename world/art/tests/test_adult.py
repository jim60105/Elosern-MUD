"""Tests for the adult portrait gate (design D3).

The "never reaches the worker" regression is asserted on the full lifecycle
path in ``world/art/tests/test_service.py`` using the counting fixture; here we
cover the pure gate contract against real ``PlayerCharacter`` attributes.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.art.adult import ADULT_MINIMUM, PortraitRejected, portrait_eligibility

from tools.spec_traceability import covers_requirement


class AdultGateTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.character = create_object(PlayerCharacter, key="gate-test")
        self.character.age = 22
        self.character.apparent_age = 22

    @covers_requirement("adult-portrait-gate::every-character-portrait-enqueue-re-checks-both-adult-age-fields-immediately-before-enqueue")
    def test_valid_adult_passes(self):
        age, apparent_age = portrait_eligibility(self.character)
        self.assertEqual((age, apparent_age), (22, 22))

    @covers_requirement("adult-portrait-gate::every-character-portrait-enqueue-re-checks-both-adult-age-fields-immediately-before-enqueue")
    def test_age_17_is_rejected_with_the_named_field(self):
        self.character.age = ADULT_MINIMUM - 1
        with self.assertRaises(PortraitRejected) as ctx:
            portrait_eligibility(self.character)
        self.assertEqual(ctx.exception.field, "age")

    @covers_requirement("adult-portrait-gate::every-character-portrait-enqueue-re-checks-both-adult-age-fields-immediately-before-enqueue")
    def test_apparent_age_17_is_rejected_with_the_named_field(self):
        self.character.apparent_age = ADULT_MINIMUM - 1
        with self.assertRaises(PortraitRejected) as ctx:
            portrait_eligibility(self.character)
        self.assertEqual(ctx.exception.field, "apparent_age")

    @covers_requirement("adult-portrait-gate::every-character-portrait-enqueue-re-checks-both-adult-age-fields-immediately-before-enqueue")
    def test_missing_or_malformed_values_reject_with_a_named_diagnostic(self):
        for field in ("age", "apparent_age"):
            self.character.attributes.remove(field)
            with self.assertRaises(PortraitRejected) as ctx:
                portrait_eligibility(self.character)
            self.assertEqual(ctx.exception.field, field)
            self.assertIn(field, str(ctx.exception))
            self.character.age = 22
            self.character.apparent_age = 22

    def test_string_age_value_is_rejected(self):
        self.character.age = "22"
        with self.assertRaises(PortraitRejected) as ctx:
            portrait_eligibility(self.character)
        self.assertEqual(ctx.exception.field, "age")


if __name__ == "__main__":
    import unittest

    unittest.main()
