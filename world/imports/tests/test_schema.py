from unittest import TestCase

from jsonschema import Draft202012Validator

from world.imports.schema import CHARACTER_SCHEMA_V1, WORLD_SCHEMA_V1
from world.imports.tests.helpers import example_record


class SchemaTests(TestCase):
    def assert_character_invalid(self, mutate):
        record = example_record()
        mutate(record)
        self.assertTrue(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )

    def test_schema_documents_hard_gates_and_base_values(self):
        properties = CHARACTER_SCHEMA_V1["properties"]
        for key in ("age", "apparent_age"):
            text = properties[key]["description"].lower()
            self.assertIn("hard gate", text)
            self.assertIn("never a warning", text)
        stats = properties["stats"]["description"]
        for phrase in ("BASE", "88*1000", "88000"):
            self.assertIn(phrase, stats)

    def test_stats_reject_unknown_negative_and_zero_hp(self):
        self.assert_character_invalid(lambda r: r["stats"].update(luck=10))
        self.assert_character_invalid(lambda r: r["stats"].update(atk_phys=-1))
        self.assert_character_invalid(lambda r: r["stats"].update(hp=0))

    def test_disguised_stats_values_must_be_integers_but_keys_are_open(self):
        self.assert_character_invalid(
            lambda r: r.update(disguised_stats={"atk_phys": "sixty"})
        )
        record = example_record()
        record["disguised_stats"] = {"charisma": 5}
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )

    def test_persona_is_opaque_but_must_be_an_object(self):
        record = example_record()
        record["persona"] = {"anything": [1, {"nested": None}]}
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )
        self.assert_character_invalid(lambda r: r.update(persona="not an object"))
        self.assertIn("opaque", CHARACTER_SCHEMA_V1["properties"]["persona"]["description"].lower())

    def test_sexual_baseline_requires_and_constrains_vocabulary(self):
        for key in ("arousal", "virgin", "sensitivity"):
            self.assert_character_invalid(lambda r, key=key: r["sexual_baseline"].pop(key))
        for key in ("arousal", "wetness", "shame", "exposure", "climax_phase"):
            self.assert_character_invalid(
                lambda r, key=key: r["sexual_baseline"].update({key: "invalid"})
            )
        self.assert_character_invalid(
            lambda r: r["sexual_baseline"].update(sensitivity={"skin": "invalid"})
        )

    def test_discriminators_are_const_constrained(self):
        self.assertEqual(
            CHARACTER_SCHEMA_V1["properties"]["record_type"]["const"], "character"
        )
        self.assertEqual(
            WORLD_SCHEMA_V1["properties"]["record_type"]["const"], "world_entry"
        )
        self.assert_character_invalid(lambda r: r.update(record_type="world_entry"))

    def test_minimal_world_entry_and_required_content(self):
        record = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "tavern",
            "content": "...",
        }
        validator = Draft202012Validator(WORLD_SCHEMA_V1)
        self.assertFalse(list(validator.iter_errors(record)))
        del record["content"]
        self.assertTrue(list(validator.iter_errors(record)))
