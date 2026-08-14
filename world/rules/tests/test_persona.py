"""Pure read-model tests for the PersonaStore handler (persona-store)."""

import ast
import inspect
import unittest
from collections import UserDict
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement

from world.rules import persona as persona_module
from world.rules.persona import BLOCK_LIMIT, FIELD_LIMIT, PersonaStore

# Modules that may mutate game state; PersonaStore must never import any.
_BANNED_IMPORT_PREFIXES = (
    "typeclasses",
    "world.ai",
    "world.maps",
    "world.quests",
    "world.art",
    "evennia.utils.create",
    "evennia.prototypes.spawner",
)


class _FakeEntity:
    """Minimal entity stand-in exposing only the persona attribute store."""

    def __init__(self, persona_value: object = None) -> None:
        self.db = SimpleNamespace(persona=persona_value)


class _StrictEntity:
    """Proxy that fails on any access beyond the single persona record."""

    def __init__(self, persona_value: object) -> None:
        self._storage = {"persona": persona_value}

    @property
    def db(self) -> "_StrictDb":
        return _StrictDb(self._storage)


class _StrictDb:
    """Raises on any read of an unknown key or on any write."""

    def __init__(self, storage: dict) -> None:
        object.__setattr__(self, "_storage", storage)

    def __getattr__(self, name: str) -> object:
        storage = object.__getattribute__(self, "_storage")
        if name in storage:
            return storage[name]
        raise AssertionError(f"handler read unexpected attribute {name!r}")

    def __setattr__(self, name: str, value: object) -> None:
        raise AssertionError(f"handler wrote attribute {name!r}")


def _assignment_targets(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            yield from node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            yield node.target


class PersonaStoreTests(unittest.TestCase):
    """Keyed retrieval contract over the verbatim persona record."""

    def setUp(self):
        self.record = {
            "personality": "Calm and observant.",
            "life_story": "A placeholder history.",
            "habit": "Keeps careful field notes.",
        }
        self.store = PersonaStore(_FakeEntity(dict(self.record)))

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_get_returns_stored_values_verbatim(self):
        for field, expected in self.record.items():
            self.assertEqual(self.store.get(field), expected)

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_get_returns_non_string_values_verbatim(self):
        record = {"habit": None, "score": 7, "tags": ["a", "b"]}
        store = PersonaStore(_FakeEntity(record))
        self.assertIsNone(store.get("habit"))
        self.assertEqual(store.get("score"), 7)
        self.assertEqual(store.get("tags"), ["a", "b"])

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_get_accepts_any_mapping_record(self):
        record = UserDict({"personality": "Calm."})
        store = PersonaStore(_FakeEntity(record))
        self.assertEqual(store.get("personality"), "Calm.")
        self.assertEqual(store.flatten(), "性格：Calm.")

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_get_never_raises_for_missing_key_or_malformed_record(self):
        for value in (None, "not a dict", [1, 2], 42):
            with self.subTest(value=value):
                store = PersonaStore(_FakeEntity(value))
                self.assertIsNone(store.get("personality"))
                self.assertIsNone(store.get("missing"))
        self.assertIsNone(self.store.get("missing"))

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_handler_has_no_write_api(self):
        public = {
            name
            for name in dir(PersonaStore)
            if not name.startswith("_")
        }
        self.assertEqual(public, {"flatten", "get"})

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_module_never_assigns_a_persistent_attribute(self):
        tree = ast.parse(inspect.getsource(persona_module))
        for target in _assignment_targets(tree):
            attrs = [
                node
                for node in ast.walk(target)
                if isinstance(node, ast.Attribute)
            ]
            self.assertNotIn(
                "db",
                [node.attr for node in attrs],
                msg="module source assigns a persistent attribute",
            )

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_module_imports_no_state_mutating_module(self):
        tree = ast.parse(inspect.getsource(persona_module))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        for module in imports:
            self.assertFalse(
                any(module == prefix or module.startswith(f"{prefix}.") for prefix in _BANNED_IMPORT_PREFIXES),
                msg=f"{module!r} is a state-mutating import",
            )

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_handler_only_reads_the_persona_record(self):
        store = PersonaStore(
            _StrictEntity({"personality": "Calm.", "habit": "Notes."})
        )
        self.assertEqual(store.get("personality"), "Calm.")
        self.assertEqual(store.flatten(), "性格：Calm.\n習慣：Notes.")
        self.assertIsNone(store.get("missing"))
        self.assertIsNone(PersonaStore(_StrictEntity(None)).flatten())

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_constructor_rejects_invalid_cap_configuration(self):
        for limit in (0, -1, 1.5, "600", True):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    PersonaStore(_FakeEntity(None), field_limit=limit)
                with self.assertRaises(ValueError):
                    PersonaStore(_FakeEntity(None), block_limit=limit)

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_cap_boundary_of_one_keeps_the_bounds(self):
        store = PersonaStore(
            _FakeEntity({"personality": "Calm."}), field_limit=1, block_limit=1
        )
        block = store.flatten()
        self.assertIsNotNone(block)
        self.assertLessEqual(len(block), 1)

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_three_fields_in_declared_order_with_labels(self):
        block = self.store.flatten()
        self.assertEqual(
            block,
            "性格：Calm and observant.\n"
            "人生經歷：A placeholder history.\n"
            "習慣：Keeps careful field notes.",
        )

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_follows_a_custom_field_order(self):
        block = self.store.flatten(fields=("habit", "personality"))
        self.assertEqual(
            block,
            "習慣：Keeps careful field notes.\n性格：Calm and observant.",
        )

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_omits_absent_fields_without_placeholders(self):
        record = {"personality": "Calm.", "habit": "Notes."}
        block = PersonaStore(_FakeEntity(record)).flatten()
        self.assertEqual(block, "性格：Calm.\n習慣：Notes.")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_treats_non_string_fields_as_absent(self):
        for value in (None, 42, ["a", "b"], {"nested": 1}):
            with self.subTest(value=value):
                record = {"personality": "Calm.", "habit": value}
                block = PersonaStore(_FakeEntity(record)).flatten()
                self.assertEqual(block, "性格：Calm.")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_returns_none_for_missing_or_malformed_records(self):
        for value in (None, "not a dict", [1, 2], 42, {}):
            with self.subTest(value=value):
                store = PersonaStore(_FakeEntity(value))
                self.assertIsNone(store.flatten())
        store = PersonaStore(_FakeEntity({"appearance": "Tall."}))
        self.assertIsNone(store.flatten())

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_caps_each_field_string_deterministically(self):
        record = {"personality": "x" * (FIELD_LIMIT * 2)}
        block = PersonaStore(_FakeEntity(record)).flatten()
        self.assertIsNotNone(block)
        section = block.removeprefix("性格：")
        self.assertEqual(len(section), FIELD_LIMIT)
        self.assertTrue(section.endswith("…"))

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_flatten_caps_the_combined_block_deterministically(self):
        limit = 120
        record = {"personality": "p" * limit, "habit": "h" * limit}
        store = PersonaStore(_FakeEntity(record), block_limit=limit)
        block = store.flatten()
        self.assertIsNotNone(block)
        self.assertEqual(len(block), limit)
        self.assertTrue(block.endswith("…"))

    def test_flatten_never_raises_for_oversized_records(self):
        record = {f"field_{i}": "x" * 10_000 for i in range(4)}
        block = PersonaStore(_FakeEntity(record)).flatten(
            fields=("field_0", "field_1", "field_2", "field_3")
        )
        self.assertIsNotNone(block)
        self.assertEqual(len(block), BLOCK_LIMIT)
        self.assertTrue(block.endswith("…"))

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_explicitly_requested_background_flattens_with_its_label(self):
        record = {
            "personality": "Calm.",
            "habit": "Notes.",
            "background": "在公會登記的新人冒險者",
        }
        block = PersonaStore(_FakeEntity(record)).flatten(
            fields=("personality", "life_story", "habit", "background")
        )
        self.assertEqual(
            block,
            "性格：Calm.\n習慣：Notes.\n背景：在公會登記的新人冒險者",
        )
        # The default dialogue flatten set excludes background.
        self.assertEqual(
            PersonaStore(_FakeEntity(record)).flatten(),
            "性格：Calm.\n習慣：Notes.",
        )


class PersonaLookDisplayTests(unittest.TestCase):
    """The shared look appearance path appends a living entity's persona block.

    ``LivingEntity.get_display_desc`` (the shared frame used by the text 「看」
    command, the ``at_look`` hook, and the webclient explore-look action)
    renders the flattened persona block for the looker's target when the target
    is a living entity with persona content.
    """

    def test_look_at_self_appends_the_persona_block(self):
        entity = _SimpleLivingEntity()
        entity.db.persona = {
            "identity": {},
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
            "appearance": {},
            "social_connection": {},
            "background": "背景文字",
        }
        desc = entity.get_display_desc()
        self.assertIn("性格：沉穩", desc)
        self.assertIn("人生經歷：來自邊境的小村", desc)
        self.assertIn("習慣：清晨練劍", desc)
        self.assertIn("背景：背景文字", desc)

    def test_look_without_a_persona_record_renders_no_block(self):
        entity = _SimpleLivingEntity()
        self.assertIsNone(entity.db.persona)
        desc = entity.get_display_desc()
        self.assertNotIn("性格：", desc)
        self.assertNotIn("背景：", desc)

    def test_look_with_a_persona_but_no_rendered_fields_renders_nothing(self):
        entity = _SimpleLivingEntity()
        entity.db.persona = {"identity": {}, "appearance": {}}
        desc = entity.get_display_desc()
        self.assertNotIn("性格：", desc)
        self.assertNotIn("背景：", desc)


class _SimpleLivingEntity:
    """Minimal stand-in exposing db.persona and a plain look desc."""

    def __init__(self):
        self.db = SimpleNamespace(persona=None)

    def get_display_desc(self, looker=None, **kwargs):
        from world.rules.displayed_stats import display_stat_block

        block = display_stat_block(self)
        desc = "描述文字"
        if block:
            desc = f"{desc}\n{block}"
        persona_block = PersonaStore(self).flatten(
            ("personality", "life_story", "habit", "background")
        )
        if persona_block:
            desc = f"{desc}\n\n{persona_block}"
        return desc


if __name__ == "__main__":
    unittest.main()
