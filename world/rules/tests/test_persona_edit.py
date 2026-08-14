"""Deterministic tests for the post-activation persona background writer."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH
from world.rules.persona_edit import update_background


class PersonaEditTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "editor", "editor@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="editor-shell")
        self.account.at_post_create_character(self.character)

    @covers_requirement("creation-persona-persistence::the-owner-can-freely-update-the-background-after-activation")
    def test_sets_background_and_preserves_every_existing_key(self):
        record = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
            "appearance": {},
            "social_connection": {},
            "custom_key": "kept",
        }
        self.character.db.persona = record
        update_background(self.character, " 在公會登記的新人冒險者 ")
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "在公會登記的新人冒險者")
        for key, value in record.items():
            self.assertEqual(stored[key], value, key)

    @covers_requirement("creation-persona-persistence::the-owner-can-freely-update-the-background-after-activation")
    def test_clearing_removes_the_key_and_touches_nothing_else(self):
        self.character.db.persona = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "故事",
            "habit": "習慣",
            "appearance": {},
            "social_connection": {},
            "background": "舊背景",
        }
        update_background(self.character, "  ")
        stored = self.character.db.persona
        self.assertNotIn("background", stored)
        self.assertEqual(stored["personality"], "沉穩")

    @covers_requirement("creation-persona-persistence::the-owner-can-freely-update-the-background-after-activation")
    def test_creates_the_import_card_when_no_record_exists(self):
        result = update_background(self.character, "新背景")
        self.assertEqual(result, "新背景")
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "新背景")
        for key in ("identity", "personality", "life_story", "habit",
                    "appearance", "social_connection"):
            self.assertIn(key, stored)

    def test_clear_without_a_record_is_a_no_op(self):
        self.assertIsNone(update_background(self.character, None))
        self.assertIsNone(self.character.db.persona)

    def test_over_bound_input_is_rejected(self):
        with self.assertRaises(ValueError):
            update_background(self.character, "x" * (MAX_PERSONA_FIELD_LENGTH + 1))
        self.assertIsNone(self.character.db.persona)

    def test_non_string_input_is_rejected(self):
        with self.assertRaises(ValueError):
            update_background(self.character, 42)

    def test_never_touches_traits_identity_or_clock(self):
        from world.rules.clock import read_world_clock

        clock_before = read_world_clock()
        tick_before = int(clock_before.tick) if clock_before is not None else None
        self.character.attributes.add("age", 20)
        update_background(self.character, "背景")
        self.assertEqual(self.character.age, 20)
        self.assertEqual(self.character.traits.all(), [])
        clock_after = read_world_clock()
        if tick_before is not None:
            self.assertEqual(int(clock_after.tick), tick_before)

    def test_uses_the_attribute_store_not_an_instance_attribute(self):
        update_background(self.character, "背景")
        self.assertTrue(self.character.attributes.has("persona"))
        self.assertEqual(self.character.db.persona["background"], "背景")
        # A plain instance attribute would not survive a cache reset; the
        # persona must live in the persistent attribute store.
        self.character.attributes.reset_cache()
        self.assertEqual(self.character.db.persona["background"], "背景")


if __name__ == "__main__":
    unittest.main()
