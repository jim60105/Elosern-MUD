"""Deterministic tests for the post-activation four-field persona writer."""

import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH
from world.rules.persona_edit import (
    PERSONA_EDITABLE_FIELDS,
    update_background,
    update_persona_field,
)


class PersonaEditTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "editor", "editor@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="editor-shell")
        self.account.at_post_create_character(self.character)

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
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

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
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

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
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

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_whitelist_is_exactly_the_four_prose_fields(self):
        self.assertEqual(
            set(PERSONA_EDITABLE_FIELDS),
            {"background", "personality", "life_story", "habit"},
        )

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_each_field_set_changes_only_that_field(self):
        record = {
            "identity": {"public_view": {"name": "甲"}},
            "personality": "",
            "life_story": "",
            "habit": "",
            "appearance": {},
            "social_connection": {},
            "background": "舊背景",
            "custom_key": "kept",
        }
        self.character.db.persona = record
        written: set[str] = set()
        for field in sorted(PERSONA_EDITABLE_FIELDS):
            with self.subTest(field=field):
                update_persona_field(self.character, field, f"  {field}文字  ")
                stored = self.character.db.persona
                self.assertEqual(stored[field], f"{field}文字")
                # Every other key (unknown, structural, and the other prose
                # fields as last written) is untouched by this write.
                self.assertEqual(stored["custom_key"], "kept")
                self.assertEqual(stored["identity"], {"public_view": {"name": "甲"}})
                for other in PERSONA_EDITABLE_FIELDS - {field}:
                    expected = (
                        f"{other}文字"
                        if other in written
                        else record[other]
                    )
                    self.assertEqual(stored[other], expected, other)
                written.add(field)

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_clearing_any_field_removes_only_its_key(self):
        record = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "故事",
            "habit": "習慣",
            "appearance": {},
            "social_connection": {},
            "background": "背景",
        }
        for field in sorted(PERSONA_EDITABLE_FIELDS):
            with self.subTest(field=field):
                self.character.db.persona = dict(record)
                update_persona_field(self.character, field, None)
                stored = self.character.db.persona
                self.assertNotIn(field, stored)
                for other in record:
                    if other != field:
                        self.assertEqual(stored[other], record[other], other)

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_clearing_each_field_touches_no_other_state(self):
        record = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "故事",
            "habit": "習慣",
            "appearance": {},
            "social_connection": {},
            "background": "背景",
        }
        self.character.db.persona = dict(record)
        cleared: set[str] = set()
        for field in sorted(PERSONA_EDITABLE_FIELDS):
            with self.subTest(field=field):
                update_persona_field(self.character, field, None)
                stored = self.character.db.persona
                self.assertNotIn(field, stored)
                # Each clear removes exactly its own key: every field cleared
                # so far is gone and every remaining key is byte-identical.
                cleared.add(field)
                self.assertEqual(set(stored), set(record) - cleared)
                for other in set(record) - cleared:
                    self.assertEqual(stored[other], record[other], other)

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_setting_without_a_record_creates_the_import_card(self):
        result = update_persona_field(self.character, "habit", "清晨練劍")
        self.assertEqual(result, "清晨練劍")
        stored = self.character.db.persona
        self.assertEqual(
            set(stored),
            {
                "identity", "personality", "life_story", "habit",
                "appearance", "social_connection",
            },
        )
        self.assertEqual(stored["habit"], "清晨練劍")
        self.assertEqual(stored["identity"], {})
        self.assertEqual(stored["appearance"], {})

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_over_bound_and_bad_field_reject_without_writing(self):
        self.character.db.persona = {"personality": "沉穩", "custom_key": "kept"}
        with self.assertRaises(ValueError):
            update_persona_field(
                self.character, "habit", "x" * (MAX_PERSONA_FIELD_LENGTH + 1)
            )
        with self.assertRaises(ValueError):
            update_persona_field(self.character, "identity", "結構鍵不可寫")
        with self.assertRaises(ValueError):
            update_persona_field(self.character, 42, "非字串欄位")
        with self.assertRaises(ValueError):
            update_persona_field(self.character, "habit", 42)
        stored = self.character.db.persona
        self.assertEqual(
            stored, {"personality": "沉穩", "custom_key": "kept"}
        )

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_clear_without_a_record_creates_nothing(self):
        for field in sorted(PERSONA_EDITABLE_FIELDS):
            with self.subTest(field=field):
                self.assertIsNone(
                    update_persona_field(self.character, field, None)
                )
        self.assertIsNone(self.character.db.persona)

    @covers_requirement("persona-editing::one-deterministic-service-writes-the-four-editable-persona-fields")
    def test_update_background_wrapper_is_equivalent(self):
        written = update_background(self.character, " 包裝器背景 ")
        self.assertEqual(written, "包裝器背景")
        self.assertEqual(self.character.db.persona["background"], "包裝器背景")
        self.assertIsNone(update_background(self.character, "  "))
        self.assertNotIn("background", self.character.db.persona)
        with self.assertRaises(ValueError):
            update_background(
                self.character, "x" * (MAX_PERSONA_FIELD_LENGTH + 1)
            )


if __name__ == "__main__":
    unittest.main()
