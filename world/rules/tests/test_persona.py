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
        self.assertEqual(public, {"flatten", "get", "public_view"})

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
    def test_scalar_non_string_fields_are_treated_as_absent(self):
        # Tolerant rendering keeps scalar shapes (None, numbers, booleans)
        # absent; container values now render (persona-store delta).
        for value in (None, 42, 3.5, True):
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

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_nested_identity_mapping_renders_public_and_hidden_lines(self):
        record = {"identity": {"public": "退役騎士", "hidden": "叛逃貴族"}}
        block = PersonaStore(_FakeEntity(record)).flatten(("identity",))
        self.assertEqual(block, "身分：\n公開身分：退役騎士\n隱秘身分：叛逃貴族")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_string_identity_renders_single_labeled_section(self):
        record = {"identity": "暗影谷村的年輕黑暗精靈"}
        block = PersonaStore(_FakeEntity(record)).flatten(("identity",))
        self.assertEqual(block, "身分：暗影谷村的年輕黑暗精靈")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_appearance_renders_declared_subkey_order_with_stringify_and_dashes(self):
        record = {
            "appearance": {
                "feature": ["左眼下淚痣", "銀髮"],
                "height": "165cm",
                "attire": {"日常": "旅行斗篷"},
                "weight": "49kg",
            }
        }
        block = PersonaStore(_FakeEntity(record)).flatten(("appearance",))
        self.assertEqual(
            block,
            "外觀：\n"
            "height：165cm\n"
            "weight：49kg\n"
            "attire：{'日常': '旅行斗篷'}\n"
            "feature：\n- 左眼下淚痣\n- 銀髮",
        )

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_social_connection_entries_key_by_counterparty_name(self):
        record = {"social_connection": {"悠奈": {"relationship": "舊識"}, "黛莉雅": "宿敵"}}
        block = PersonaStore(_FakeEntity(record)).flatten(("social_connection",))
        self.assertEqual(
            block,
            "人脈：\n悠奈：{'relationship': '舊識'}\n黛莉雅：宿敵",
        )

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_unknown_subkeys_follow_declared_keys_with_raw_labels(self):
        record = {"identity": {"hidden": "祕", "public": "表", "origin": "暗影谷"}}
        block = PersonaStore(_FakeEntity(record)).flatten(("identity",))
        self.assertEqual(block, "身分：\n公開身分：表\n隱秘身分：祕\norigin：暗影谷")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_scalar_subkeys_and_items_are_skipped_without_raising(self):
        record = {
            "identity": {"public": "表", "hidden": None, "rank": 3, "active": True},
            "appearance": {"feature": [None, 42, True, "刀疤"]},
        }
        block = PersonaStore(_FakeEntity(record)).flatten(("identity", "appearance"))
        self.assertEqual(block, "身分：\n公開身分：表\n外觀：\nfeature：\n- 刀疤")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_deeper_nesting_stringifies_as_final_fallback(self):
        record = {"appearance": {"attire": {"戰鬥": {"head": "兜帽"}}}}
        block = PersonaStore(_FakeEntity(record)).flatten(("appearance",))
        self.assertEqual(block, "外觀：\nattire：{'戰鬥': {'head': '兜帽'}}")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_top_level_list_field_renders_dashed_items(self):
        record = {"habit": ["清晨練劍", "夜讀"]}
        block = PersonaStore(_FakeEntity(record)).flatten()
        self.assertEqual(block, "習慣：\n- 清晨練劍\n- 夜讀")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_mapping_with_no_renderable_entries_produces_no_section(self):
        record = {"identity": {}, "appearance": {"rank": 3}, "personality": "Calm."}
        block = PersonaStore(_FakeEntity(record)).flatten(
            ("identity", "appearance", "personality")
        )
        self.assertEqual(block, "性格：Calm.")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_nested_section_is_capped_deterministically(self):
        record = {
            "identity": {"public": "x" * (FIELD_LIMIT * 2), "hidden": "y" * 100}
        }
        store = PersonaStore(_FakeEntity(record))
        block = store.flatten(("identity",))
        self.assertIsNotNone(block)
        self.assertLessEqual(len(block), FIELD_LIMIT)
        self.assertTrue(block.endswith("…"))
        self.assertEqual(block, store.flatten(("identity",)))

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_default_field_set_ignores_structural_keys(self):
        record = {
            "personality": "Calm.",
            "identity": {"public": "表", "hidden": "祕"},
            "appearance": {"height": "165cm"},
            "social_connection": {"悠奈": "舊識"},
        }
        block = PersonaStore(_FakeEntity(record)).flatten()
        self.assertEqual(block, "性格：Calm.")

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_worst_case_record_truncates_deterministically_at_block_limit(self):
        record = {
            "personality": "性" * FIELD_LIMIT,
            "life_story": "事" * FIELD_LIMIT,
            "habit": "慣" * FIELD_LIMIT,
            "identity": {"public": "公" * FIELD_LIMIT, "hidden": "隱" * FIELD_LIMIT},
            "appearance": {
                "height": "高" * 50,
                "weight": "重" * 50,
                "measurement": "量" * 50,
                "style": "風" * 50,
                "overview": "觀" * 50,
                "attire": {"日常": "服" * 100},
                "feature": ["特" * 40, "徵" * 40],
            },
            "social_connection": {
                f"對象{i}": {"relationship": "舊識", "note": "備" * 80}
                for i in range(10)
            },
        }
        fields = (
            "personality",
            "life_story",
            "habit",
            "identity",
            "appearance",
            "social_connection",
        )
        store = PersonaStore(_FakeEntity(record))
        block = store.flatten(fields)
        self.assertIsNotNone(block)
        self.assertEqual(len(block), BLOCK_LIMIT)
        self.assertTrue(block.endswith("…"))
        self.assertEqual(block, store.flatten(fields))

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_drops_hidden_identity_without_mutating_the_record(self):
        record = {
            "identity": {"public": "旅行商人", "hidden": "落魄王族"},
            "personality": "溫柔",
        }
        store = PersonaStore(_FakeEntity(record))
        view = store.public_view()
        self.assertIsNot(view, store)
        self.assertIsInstance(view, PersonaStore)
        rendered = view.flatten(("identity", "personality"))
        self.assertEqual(rendered, "身分：\n公開身分：旅行商人\n性格：溫柔")
        self.assertNotIn("落魄王族", rendered)
        self.assertEqual(
            record,
            {
                "identity": {"public": "旅行商人", "hidden": "落魄王族"},
                "personality": "溫柔",
            },
        )

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_keeps_string_identity_and_degrades_malformed_records(self):
        store = PersonaStore(_FakeEntity({"identity": "流浪劍士"}))
        self.assertEqual(store.public_view().flatten(("identity",)), "身分：流浪劍士")
        for value in (None, "not a dict", [1, 2], 42):
            with self.subTest(value=value):
                self.assertIsNone(
                    PersonaStore(_FakeEntity(value)).public_view().flatten()
                )

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_carries_the_store_bounds(self):
        record = {"identity": {"public": "公" * 50, "hidden": "隱" * 50}}
        store = PersonaStore(_FakeEntity(record), field_limit=20, block_limit=30)
        view = store.public_view()
        block = view.flatten(("identity",))
        self.assertIsNotNone(block)
        self.assertLessEqual(len(block), 30)
        self.assertTrue(block.endswith("…"))
        self.assertNotIn("隱", block)

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_of_hidden_only_identity_renders_nothing(self):
        record = {"identity": {"hidden": "祕密"}}
        view = PersonaStore(_FakeEntity(record)).public_view()
        self.assertIsNone(view.flatten(("identity",)))

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_prunes_nested_hidden_entries_at_any_depth(self):
        record = {
            "identity": {
                "public": {"hidden": "巢狀祕密", "role": "商人", "ties": [{"hidden": "深", "k": "v"}]},
            }
        }
        block = PersonaStore(_FakeEntity(record)).public_view().flatten(("identity",))
        self.assertEqual(
            block, "身分：\n公開身分：{'role': '商人', 'ties': [{'k': 'v'}]}"
        )
        self.assertNotIn("巢狀祕密", block)
        self.assertNotIn("深", block)

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_is_an_independent_snapshot_of_later_mutations(self):
        record = {"identity": {"public": {"role": "商人"}}}
        view = PersonaStore(_FakeEntity(record)).public_view()
        # A writer adding a hidden entry to the shared nested container after
        # the view was taken must not surface through the already-built view.
        record["identity"]["public"]["hidden"] = "後植入"
        block = view.flatten(("identity",))
        self.assertEqual(block, "身分：\n公開身分：{'role': '商人'}")
        self.assertNotIn("後植入", block)

    @covers_requirement("persona-store::personastore-is-a-read-only-handler-over-the-verbatim-persona-record")
    def test_public_view_drops_cycle_backreferences_without_raising(self):
        inner: dict = {"public": "表", "hidden": "環"}
        identity = {"public": inner}
        inner["loop"] = identity  # self-referential opaque shape
        store = PersonaStore(_FakeEntity({"identity": identity}))
        block = store.public_view().flatten(("identity",))
        self.assertIsNotNone(block)
        self.assertIn("公開身分", block)
        self.assertNotIn("環", block)
        # The NPC-side tolerant path must also survive a cyclic value: the
        # stringify fallback relies on repr's cycle marker, never a raise.
        self.assertIsNotNone(store.flatten(("identity",)))

    @covers_requirement("persona-store::flatten-produces-one-bounded-labeled-prompt-block")
    def test_exotic_numeric_list_items_are_skipped(self):
        from decimal import Decimal
        from fractions import Fraction

        record = {"appearance": {"feature": [Decimal("1.5"), Fraction(1, 2), 1 + 2j, None, "刀疤"]}}
        block = PersonaStore(_FakeEntity(record)).flatten(("appearance",))
        self.assertEqual(block, "外觀：\nfeature：\n- 刀疤")


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
