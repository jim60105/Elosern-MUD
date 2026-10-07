"""Data-contract test: authored registry index coverage and shipped reference integrity contract

The CI contract of gm-portal-s4-world-data §3.4 over shipped data: the index
represents every startup-synchronised registry plus the named additional
categories with valid display metadata and lazy loaders of frozen dataclass
entries; every declared reference names an indexed registry with a unique
inverse and resolves to an existing key; importing the index (or the leaf
reference module) pulls in no rules, skills or quest package. Startup
synchronisation is untouched: none of this runs at server start.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import re
import subprocess
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path

from tools.spec_traceability import covers_requirement
from world.lore import registry_index
from world.lore.registry_index import (
    GROUPS,
    REGISTRY_INDEX,
    build_reference_index,
    check_references,
    declaration_errors,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The additional categories S4 §3.2 names beyond the startup-sync registries.
ADDITIONAL_CATEGORIES = frozenset(
    {
        "items",
        "npc_profiles",
        "dialogue",
        "assortments",
        "player_presets",
        "starting_kits",
        "npc_tiers",
        "scene_archetypes",
        "skills",
        "sexual_acts",
        "quest_definitions",
        "professions",
        "guild_exam_profiles",
        "shop_configs",
        "service_hosts",
        "monster_behaviour_profiles",
    }
)

#: The first-batch declaring dataclasses, by module, with their declared fields.
FIRST_BATCH = {
    "world.lore.monster_species": {
        "MonsterSpecies": {"default_variant_key"},
        "MonsterVariant": {"species_key", "threat_tier"},
    },
    "world.lore.monster_placement": {
        "AmbientPlacementRule": {"region_key", "variant_keys"},
        "MonsterSite": {"region_key", "variant_keys"},
    },
    "world.quests.definitions": {
        "QuestDefinition": {"rank"},
        "QuestObjective": {
            "monster_tier",
            "item_key",
            "region_key",
            "species_key",
            "countable_variant_keys",
            "site_key",
        },
        "RoomLocator": {"anchor_key"},
    },
    "world.lore.items.vocab": {"ItemDefinition": {"price_table_key"}},
    "world.lore.settlements.places": {
        "PlaceDefinition": {
            "settlement_key",
            "host_race",
            "host_subrace",
            "profession",
            "assortment_keys",
            "extra_item_keys",
            "excluded_item_keys",
            "host_profile_key",
        }
    },
    "world.lore.settlements.shops": {"ShopDefinition": {"assortment_keys"}},
    "world.lore.settlements.assortments": {"AssortmentDefinition": {"item_keys"}},
}

#: Field defaults the declarations had to keep exactly (``MISSING`` = required).
EXPECTED_DEFAULTS = {
    ("MonsterVariant", "species_key"): dataclasses.MISSING,
    ("QuestDefinition", "rank"): dataclasses.MISSING,
    ("QuestObjective", "item_key"): None,
    ("QuestObjective", "countable_variant_keys"): (),
    ("RoomLocator", "anchor_key"): None,
    ("PlaceDefinition", "host_profile_key"): None,
    ("PlaceDefinition", "assortment_keys"): (),
    ("ShopDefinition", "assortment_keys"): dataclasses.MISSING,
}


def _loaded() -> dict[str, Mapping]:
    return {spec.name: spec.loader() for spec in REGISTRY_INDEX}


class RegistryInventoryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loaded = _loaded()

    @covers_requirement("authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_names_are_unique_snake_case_and_never_reserved(self):
        names = [spec.name for spec in REGISTRY_INDEX]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertRegex(name, r"^[a-z][a-z0-9_]*$")
        # ``/gm/world/sources/...`` is the source viewer route.
        self.assertNotIn("sources", names)

    @covers_requirement("authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_display_metadata_and_source_paths(self):
        for spec in REGISTRY_INDEX:
            with self.subTest(registry=spec.name):
                self.assertIn(spec.group, GROUPS)
                self.assertRegex(spec.label, r"[一-鿿]")
                self.assertTrue((REPO_ROOT / spec.source_path).exists(), spec.source_path)
                self.assertFalse(spec.source_path.startswith("/"))
        self.assertEqual(len(GROUPS), 8)
        self.assertEqual({spec.group for spec in REGISTRY_INDEX}, set(GROUPS))

    @covers_requirement("authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_every_startup_sync_registry_and_named_category_is_indexed(self):
        from world.lore.sync import _ALL_REGISTRIES

        names = {spec.name for spec in REGISTRY_INDEX}
        self.assertEqual(len(_ALL_REGISTRIES), 21)
        self.assertLessEqual(set(_ALL_REGISTRIES), names)
        self.assertLessEqual(ADDITIONAL_CATEGORIES, names)
        for category, registry in _ALL_REGISTRIES.items():
            with self.subTest(registry=category):
                self.assertEqual(dict(self.loaded[category]), dict(registry))

    @covers_requirement("authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_loaders_return_mappings_of_frozen_dataclass_entries(self):
        for name, entries in self.loaded.items():
            with self.subTest(registry=name):
                self.assertIsInstance(entries, Mapping)
                self.assertTrue(entries, "an indexed registry ships at least one entry")
                for key, entry in entries.items():
                    self.assertIsInstance(key, str)
                    self.assertTrue(dataclasses.is_dataclass(entry) and not isinstance(entry, type))
                    self.assertTrue(type(entry).__dataclass_params__.frozen, f"{name}:{key}")
                    self.assertNotIn("/", key)

    def test_mapping_keys_keep_field_paths_unambiguous(self):
        # Reference field paths join mapping keys with ``.`` and positions with
        # ``[n]``; a key containing either would make a path ambiguous.
        def walk(value, where):
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                for field in dataclasses.fields(value):
                    walk(getattr(value, field.name), f"{where}.{field.name}")
            elif isinstance(value, Mapping):
                for key, item in value.items():
                    self.assertIsInstance(key, str, where)
                    self.assertIsNone(re.search(r"[.\[\]]", key), f"{where}: {key!r}")
                    walk(item, f"{where}.{key}")
            elif isinstance(value, (list, tuple, set, frozenset)):
                for item in value:
                    walk(item, where)

        for name, entries in self.loaded.items():
            for key, entry in entries.items():
                walk(entry, f"{name}:{key}")

    def test_summary_fields_resolve_on_every_entry(self):
        for spec in REGISTRY_INDEX:
            for path in spec.summary_fields:
                head = path.split(".")[0]
                for key, entry in self.loaded[spec.name].items():
                    with self.subTest(registry=spec.name, field=path, key=key):
                        self.assertTrue(hasattr(entry, head))


class ReferenceIntegrityContractTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_shipped_references_resolve(self):
        self.assertEqual(check_references(), [])

    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model")
    def test_declarations_name_indexed_registries_with_unique_inverses(self):
        self.assertEqual(declaration_errors(), [])

    @covers_requirement("authored-registry-references::declarative-reference-traversal")
    def test_first_batch_declarations_are_present_and_preserve_defaults(self):
        import importlib

        index = build_reference_index()
        declared = {(item.owner.rsplit(".", 1)[-1], item.field) for item in index.declarations}
        for module_name, classes in FIRST_BATCH.items():
            module = importlib.import_module(module_name)
            for class_name, fields in classes.items():
                cls = getattr(module, class_name)
                found = {name for name, _spec in registry_index.iter_declared_fields(cls)}
                with self.subTest(owner=class_name):
                    self.assertEqual(found, fields)
                    self.assertLessEqual({(class_name, name) for name in fields}, declared)
                for field in dataclasses.fields(cls):
                    expected = EXPECTED_DEFAULTS.get((class_name, field.name), "unchecked")
                    if expected != "unchecked":
                        self.assertEqual(field.default, expected, f"{class_name}.{field.name}")

    def test_reference_index_is_cached_for_the_process(self):
        self.assertIs(build_reference_index(), build_reference_index())

    @covers_requirement("authored-registry-references::cached-bidirectional-integrity-model", "authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_startup_sync_adds_no_reference_enforcement(self):
        source = (REPO_ROOT / "world" / "lore" / "sync.py").read_text(encoding="utf-8")
        self.assertNotIn("registry_index", source)
        self.assertNotIn("check_references", source)


class LazyImportContractTest(unittest.TestCase):
    @covers_requirement("authored-registry-references::explicit-complete-lazy-registry-inventory")
    def test_index_import_adds_no_rules_skills_or_quest_module(self):
        script = (
            "import json, sys\n"
            "import world.lore\n"
            "before = set(sys.modules)\n"
            "import world.lore.registry_index\n"
            "added = sorted(set(sys.modules) - before)\n"
            "print(json.dumps(added))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        added = json.loads(result.stdout.strip().splitlines()[-1])
        offending = [
            name
            for name in added
            if re.match(r"^world\.(rules|skills|quests)(\.|$)", name)
        ]
        self.assertEqual(offending, [], added)

    def test_reference_module_is_a_stdlib_only_leaf(self):
        tree = ast.parse((REPO_ROOT / "world" / "lore" / "registry_refs.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported, {"__future__", "dataclasses", "types", "typing"})


if __name__ == "__main__":
    unittest.main()
