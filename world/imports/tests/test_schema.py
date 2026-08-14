from tools.spec_traceability import covers_requirement

from unittest import TestCase

from jsonschema import Draft202012Validator

from world.art.subjects import (
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_LENGTH,
)
from world.imports.schema import (
    CHARACTER_SCHEMA_V1,
    MAX_ENTITY_KEY_LENGTH,
    WORLD_SCHEMA_V1,
)
from world.imports.tests.helpers import example_record


class SchemaTests(TestCase):
    def assert_character_invalid(self, mutate):
        record = example_record()
        mutate(record)
        self.assertTrue(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )

    @covers_requirement("import-schema::stats-values-are-documented-as-base-pre-skill-multiplier-values", "import-schema::the-age-gate-is-documented-in-the-schema-s-own-description-text")
    def test_schema_documents_hard_gates_and_base_values(self):
        properties = CHARACTER_SCHEMA_V1["properties"]
        for key in ("age", "apparent_age"):
            text = properties[key]["description"].lower()
            self.assertIn("hard gate", text)
            self.assertIn("never a warning", text)
        stats = properties["stats"]["description"]
        for phrase in ("BASE", "88*1000", "88000"):
            self.assertIn(phrase, stats)

    @covers_requirement("import-schema::stats-only-accepts-the-eight-documented-trait-keys")
    def test_stats_reject_unknown_negative_and_zero_hp(self):
        self.assert_character_invalid(lambda r: r["stats"].update(luck=10))
        self.assert_character_invalid(lambda r: r["stats"].update(atk_phys=-1))
        self.assert_character_invalid(lambda r: r["stats"].update(hp=0))

    @covers_requirement("import-schema::disguised-stats-is-typed-as-an-integer-valued-mapping-with-no-key-constraint-at-the-schema-layer")
    def test_disguised_stats_values_must_be_integers_but_keys_are_open(self):
        self.assert_character_invalid(
            lambda r: r.update(disguised_stats={"atk_phys": "sixty"})
        )
        record = example_record()
        record["disguised_stats"] = {"charisma": 5}
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )

    @covers_requirement("import-reference-example::the-reference-example-exercises-every-major-schema-branch", "import-schema::persona-is-validated-as-an-object-and-nothing-more")
    def test_persona_is_opaque_but_must_be_an_object(self):
        record = example_record()
        record["persona"] = {"anything": [1, {"nested": None}]}
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )
        self.assert_character_invalid(lambda r: r.update(persona="not an object"))
        self.assertIn("opaque", CHARACTER_SCHEMA_V1["properties"]["persona"]["description"].lower())

    @covers_requirement("import-schema::sexual-baseline-requires-arousal-virgin-and-sensitivity-with-level-fields-constrained-to-the-sexual-vocabulary-registry")
    @covers_requirement("import-validation::sexual-baseline-shape-violations-are-rejections")
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

    @covers_requirement("import-schema::imported-entity-keys-use-a-safe-character-set")
    def test_entity_keys_reject_separators_and_control_characters(self):
        for bad in (
            "orc|alpha",
            "orc/alpha",
            "orc:alpha",
            "orc{alpha",
            "orc}alpha",
            "orc\x00alpha",
            "orc\x1falpha",
            "orc\x7falpha",
            "orc\x85alpha",
            "trailing newline\n",
        ):
            with self.subTest(key=bad):
                self.assert_character_invalid(lambda r, bad=bad: r.update(key=bad))

    @covers_requirement("import-schema::imported-entity-keys-use-a-safe-character-set")
    def test_entity_key_length_bound_is_64_characters(self):
        self.assert_character_invalid(lambda r: r.update(key="x" * 65))
        record = example_record()
        record["key"] = "x" * 64
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )

    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_schema_pattern_derives_from_the_shared_art_contract(self):
        # The schema mirrors the art-side subject-key contract literally: same
        # length bound, and every reserved separator rejected by the pattern.
        self.assertEqual(MAX_ENTITY_KEY_LENGTH, MAX_SUBJECT_KEY_LENGTH)
        for char in sorted(FORBIDDEN_SUBJECT_KEY_CHARACTERS):
            with self.subTest(char=char):
                self.assert_character_invalid(
                    lambda r, char=char: r.update(key=f"a{char}b")
                )

    def test_world_entry_keys_share_the_entity_key_rules(self):
        validator = Draft202012Validator(WORLD_SCHEMA_V1)
        for bad in ("a|b", "a/b", "a:b", "a{b", "a}b", "a\x01b", "a\x7fb", "a\n"):
            record = {
                "record_type": "world_entry",
                "schema_version": 1,
                "key": bad,
                "content": "...",
            }
            with self.subTest(key=bad):
                self.assertTrue(list(validator.iter_errors(record)))
        record = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "x" * 64,
            "content": "...",
        }
        self.assertFalse(list(validator.iter_errors(record)))

    @covers_requirement("import-schema::world-schema-v1-validates-a-minimal-opaque-world-info-entry")
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

    @covers_requirement("import-schema::character-schema-v1-accepts-an-optional-affinity-elements-array")
    def test_affinity_elements_structural_bounds(self):
        schema = CHARACTER_SCHEMA_V1["properties"]["affinity_elements"]
        self.assertEqual(schema["uniqueItems"], True)
        self.assertEqual(schema["maxItems"], 8)
        self.assertEqual(
            set(schema["items"]["enum"]),
            {"fire", "water", "wind", "earth", "lightning", "ice", "light", "dark"},
        )
        self.assertIn("neutral", schema["description"].lower())

        record = example_record()
        record["affinity_elements"] = ["fire", "wind"]
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )
        self.assert_character_invalid(
            lambda r: r.update(affinity_elements=["luck"])
        )
        self.assert_character_invalid(
            lambda r: r.update(affinity_elements=["fire", "fire"])
        )
        self.assert_character_invalid(
            lambda r: r.update(
                affinity_elements=[
                    "fire", "water", "wind", "earth",
                    "lightning", "ice", "light", "dark", "fire",
                ]
            )
        )
        del record["affinity_elements"]
        self.assertFalse(
            list(Draft202012Validator(CHARACTER_SCHEMA_V1).iter_errors(record))
        )
