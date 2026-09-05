"""Tests for the professions rulebook loader and its component-type contract."""

import ast
import tempfile
import types
import unittest
import yaml
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from tools.spec_traceability import covers_requirement

from world.rules import profession_config
from world.rules.profession_config import (
    PROFESSION_COMPONENT_TYPES,
    ProfessionComponent,
    ProfessionConfigError,
    all_professions,
    get_profession,
    load_professions,
    load_professions_into_cache,
)

COMPONENTS_MODULE = Path(profession_config.__file__).parents[2] / "typeclasses" / "components.py"



def base_row(key: str = "merchant") -> dict:
    return {
        "key": key,
        "components": [{"type": "merchant", "default_binding": "place"}],
        "schedule_template": None,
        "default_tier": None,
    }


def base_file(*rows: dict) -> dict:
    return {"schema_version": 1, "professions": list(rows) or [base_row()]}


class ProfessionCacheIsolation(unittest.TestCase):
    """Every case restores the process-global cache so order never matters."""

    def setUp(self):
        super().setUp()
        self._saved_table = profession_config.TABLE

    def tearDown(self):
        profession_config.TABLE = self._saved_table
        super().tearDown()


class ShippedTableTests(ProfessionCacheIsolation):
    @covers_requirement(
        "profession-registries::professions-are-one-validated-rulebook-table-with-keyed-frozen-reads",
    )
    def test_shipped_table_exposes_the_three_blueprint_professions(self):
        table = load_professions()
        self.assertEqual(set(table), {"merchant", "guild_staff", "guild_examiner"})

        merchant = table["merchant"]
        self.assertEqual([(c.type_key, c.default_binding) for c in merchant.components], [("merchant", "place")])

        staff = table["guild_staff"]
        self.assertEqual(
            [(c.type_key, c.default_binding) for c in staff.components],
            [("guild_staff", "place"), ("guild_examiner", "place"), ("scripted_dialogue", "place")],
        )

        examiner = table["guild_examiner"]
        self.assertEqual(
            [(c.type_key, c.default_binding) for c in examiner.components],
            [("guild_examiner", "place"), ("scripted_dialogue", "place")],
        )

        for profession in table.values():
            with self.subTest(profession=profession.key):
                self.assertIsNone(profession.schedule_template)
                self.assertIsNone(profession.default_tier)

    @covers_requirement(
        "profession-registries::professions-are-one-validated-rulebook-table-with-keyed-frozen-reads",
    )
    def test_keyed_reads_are_equal_frozen_values_over_an_immutable_table(self):
        first = get_profession("merchant")
        second = get_profession("merchant")
        self.assertEqual(first, second)
        self.assertIsNone(get_profession("blacksmith"))
        self.assertEqual([p.key for p in all_professions()], list(load_professions()))

        table = profession_config.TABLE
        self.assertIsInstance(table, types.MappingProxyType)
        with self.assertRaises(TypeError):
            table["merchant"] = None  # type: ignore[index]
        with self.assertRaises(TypeError):
            del table["merchant"]  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            table.update({"fake": None})  # type: ignore[attr-defined]

        with self.assertRaises(FrozenInstanceError):
            first.schedule_template = "guard"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            first.components[0].default_binding = "person"  # type: ignore[misc]

    def test_cache_rebuild_logs_load_event(self):
        profession_config.TABLE = None
        with mock.patch.object(profession_config, "log_info") as logged:
            table = load_professions_into_cache()
        logged.assert_called_once()
        event, kwargs = logged.call_args[0], logged.call_args[1]
        self.assertEqual(event, ("profession_rulebook_loaded",))
        self.assertEqual(kwargs["context"]["count"], 3)
        self.assertEqual(sorted(table), ["guild_examiner", "guild_staff", "merchant"])


class RejectionTests(ProfessionCacheIsolation):
    def assert_rejected(self, mutate, *expected_tokens):
        raw = base_file()
        mutate(raw)
        with tempfile.TemporaryDirectory() as home:
            path = Path(home) / "professions.yaml"
            path.write_text(yaml.safe_dump(raw), encoding="utf-8")
            sentinel = object()
            profession_config.TABLE = sentinel
            with self.assertRaises(ProfessionConfigError) as caught:
                load_professions(path)
            self.assertIs(profession_config.TABLE, sentinel)
        message = str(caught.exception)
        for token in expected_tokens:
            self.assertIn(token, message)

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_root_level_offenses_name_the_field_and_value(self):
        with self.subTest("missing schema_version"):
            self.assert_rejected(lambda raw: raw.pop("schema_version"), "missing top-level fields", "schema_version")
        with self.subTest("wrong schema_version"):
            self.assert_rejected(lambda raw: raw.update(schema_version=2), "schema_version must be 1", "2")
        with self.subTest("missing professions list"):
            self.assert_rejected(lambda raw: raw.pop("professions"), "missing top-level fields", "professions")
        with self.subTest("empty professions list"):
            self.assert_rejected(lambda raw: raw.update(professions=[]), "professions must be a non-empty list")
        with self.subTest("unknown top-level key"):
            self.assert_rejected(lambda raw: raw.update(extra=1), "unknown top-level fields", "extra")

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_row_level_offenses_name_the_row(self):
        with self.subTest("empty key"):
            self.assert_rejected(lambda raw: raw["professions"][0].update(key=""), "empty or non-string key")
        with self.subTest("duplicate key"):
            self.assert_rejected(
                lambda raw: raw.update(professions=[base_row("merchant"), base_row("merchant")]),
                "duplicate profession key",
                "merchant",
            )
        with self.subTest("unknown row field"):
            self.assert_rejected(lambda raw: raw["professions"][0].update(extra=1), "has unknown fields", "extra")
        for field in ("components", "schedule_template", "default_tier"):
            with self.subTest(f"missing {field}"):
                self.assert_rejected(
                    lambda raw, field=field: raw["professions"][0].pop(field),
                    "is missing fields",
                    field,
                )
        with self.subTest("empty components"):
            self.assert_rejected(
                lambda raw: raw["professions"][0].update(components=[]),
                "merchant",
                "components must be a non-empty list",
            )

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_unknown_component_type_names_the_row_and_type(self):
        def mutate(raw):
            raw["professions"][0]["components"][0]["type"] = "blacksmith"

        self.assert_rejected(mutate, "merchant", "unknown component type", "blacksmith")

    @covers_requirement(
        "profession-registries::default-binding-is-a-validated-vocabulary-stored-for-later-consumers",
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_binding_vocabulary_is_enforced_at_load(self):
        def mutate(raw):
            raw["professions"][0]["components"][0]["default_binding"] = "portable"

        self.assert_rejected(mutate, "merchant", "default_binding", "portable")

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_malformed_component_pair_shape_is_rejected(self):
        with self.subTest("component not a mapping"):
            self.assert_rejected(
                lambda raw: raw["professions"][0].update(components=["merchant"]),
                "must be a mapping",
            )
        with self.subTest("component missing default_binding"):
            self.assert_rejected(
                lambda raw: raw["professions"][0]["components"][0].pop("default_binding"),
                "is missing fields",
                "default_binding",
            )
        with self.subTest("component unknown field"):
            self.assert_rejected(
                lambda raw: raw["professions"][0]["components"][0].update(extra=1),
                "has unknown fields",
                "extra",
            )

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_schedule_template_that_does_not_exist_is_rejected(self):
        self.assert_rejected(
            lambda raw: raw["professions"][0].update(schedule_template="night_shift"),
            "merchant",
            "unknown schedule_template",
            "night_shift",
        )

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_tier_outside_the_static_tier_registry_is_rejected(self):
        self.assert_rejected(
            lambda raw: raw["professions"][0].update(default_tier="mythic"),
            "merchant",
            "unknown default_tier",
            "mythic",
        )

    @covers_requirement(
        "profession-registries::every-malformed-profession-file-is-rejected-by-name-before-anything-is-cached",
    )
    def test_non_string_values_fail_closed_with_named_errors(self):
        with self.subTest("unhashable binding"):
            self.assert_rejected(
                lambda raw: raw["professions"][0]["components"][0].update(default_binding=[]),
                "default_binding",
            )
        with self.subTest("unhashable tier"):
            self.assert_rejected(
                lambda raw: raw["professions"][0].update(default_tier=[]),
                "merchant",
                "unknown default_tier",
            )
        with self.subTest("non-string template"):
            self.assert_rejected(
                lambda raw: raw["professions"][0].update(schedule_template=["guard"]),
                "merchant",
                "unknown schedule_template",
            )
        with self.subTest("non-string row key"):
            self.assert_rejected(lambda raw: raw["professions"][0].update(key=7), "empty or non-string key")
        with self.subTest("mixed non-string unknown top-level keys"):
            self.assert_rejected(
                lambda raw: raw.update({"extra": 1, 7: 2}),
                "unknown top-level fields",
            )
        with self.subTest("row not a mapping"):
            self.assert_rejected(lambda raw: raw.update(professions=["merchant"]), "must be a mapping")

    def test_known_template_and_tier_are_accepted(self):
        raw = base_file()
        raw["professions"][0].update(schedule_template="guard", default_tier="human_commoner")
        with tempfile.TemporaryDirectory() as home:
            path = Path(home) / "professions.yaml"
            path.write_text(yaml.safe_dump(raw), encoding="utf-8")
            table = load_professions(path)
        self.assertEqual(table["merchant"].schedule_template, "guard")
        self.assertEqual(table["merchant"].default_tier, "human_commoner")

    @covers_requirement(
        "profession-registries::default-binding-is-a-validated-vocabulary-stored-for-later-consumers",
    )
    def test_binding_is_stored_on_the_frozen_component_row(self):
        component = get_profession("merchant").components[0]
        self.assertIsInstance(component, ProfessionComponent)
        self.assertEqual(component.default_binding, "place")
        self.assertIsInstance(component.type_key, str)


class ComponentVocabularyContractTests(unittest.TestCase):
    def _declared_components(self) -> dict[str, str]:
        """Parse ``typeclasses/components.py`` for Component subclasses' name literals."""
        tree = ast.parse(COMPONENTS_MODULE.read_text(encoding="utf-8"))
        declared: dict[str, str] = {}
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {ast.unparse(base) for base in node.bases}
            if "Component" not in bases:
                continue
            name = None
            for statement in node.body:
                if (
                    isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "name" for target in statement.targets)
                    and isinstance(statement.value, ast.Constant)
                ):
                    name = statement.value.value
            self.assertIsNotNone(name, f"component class {node.name} declares no literal name")
            declared[node.name] = name
        return declared

    @covers_requirement(
        "profession-registries::the-component-type-vocabulary-is-contract-pinned-to-the-component-classes",
    )
    def test_vocabulary_equals_declared_name_literal_mapping(self):
        expected = {name: class_name for class_name, name in self._declared_components().items()}
        actual = {key: value.__name__ for key, value in PROFESSION_COMPONENT_TYPES.items()}
        self.assertEqual(actual, expected)

    @covers_requirement(
        "profession-registries::the-component-type-vocabulary-is-contract-pinned-to-the-component-classes",
    )
    def test_every_vocabulary_entry_resolves_to_a_component_class(self):
        import typeclasses.components as components

        for type_key, component_class in PROFESSION_COMPONENT_TYPES.items():
            with self.subTest(type_key=type_key):
                self.assertTrue(isinstance(component_class, type))
                self.assertIs(getattr(components, component_class.__name__), component_class)
                self.assertEqual(component_class.name, type_key)


if __name__ == "__main__":
    unittest.main()
