"""Authoring-contract tests for the single ``content/items/`` catalog.

Behavior tests for the ADDED ``lore-item-catalog`` requirement: the manifest
defines the authored order, every slice is typed and closed, and malformed or
escaping documents are rejected with a named source before a candidate is
published. No requirement annotation is attached here until archive sync
creates the canonical requirement ID.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from world.lore.items import ItemCatalogError, load_item_catalog


def _row(key: str, **overrides) -> dict:
    row = {
        "key": key,
        "display_name_zh": f"合成{key}",
        "price_table_key": "t_meal",
        "sellable": True,
        "presentation": {
            "kind": "misc",
            "icon_key": "misc",
            "rarity": "common",
            "summary_zh": f"{key} 的合成摘要。",
        },
    }
    row.update(overrides)
    return row


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self._roots: list[Path] = []

    def tearDown(self):
        import shutil

        for root in self._roots:
            shutil.rmtree(root, ignore_errors=True)

    def catalog(self, files: dict[str, list[dict]], *, declared=None, manifest=None) -> Path:
        root = Path(tempfile.mkdtemp())
        self._roots.append(root)
        if manifest is None:
            manifest = {
                "schema_version": 1,
                "files": list(declared if declared is not None else files),
            }
        (root / "catalog.yaml").write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        for name, rows in files.items():
            (root / name).write_text(
                yaml.safe_dump({"items": rows}, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        return root

    def assert_rejected(self, root: Path, fragment: str) -> None:
        with self.assertRaises(ItemCatalogError) as caught:
            load_item_catalog(root)
        self.assertIn(fragment, str(caught.exception))


class AuthoringOrderTests(CatalogCase):
    def test_declared_file_and_row_order_is_preserved(self):
        root = self.catalog(
            {
                "zeta.yaml": [_row("t_order_b"), _row("t_order_a")],
                "alpha.yaml": [_row("t_order_c")],
            },
            declared=["zeta.yaml", "alpha.yaml"],
        )
        catalog = load_item_catalog(root)
        self.assertEqual(list(catalog.definitions), ["t_order_b", "t_order_a", "t_order_c"])

    def test_sources_name_the_declaring_file(self):
        root = self.catalog(
            {"zeta.yaml": [_row("t_order_d")], "alpha.yaml": [_row("t_order_e")]},
            declared=["zeta.yaml", "alpha.yaml"],
        )
        catalog = load_item_catalog(root)
        self.assertTrue(catalog.sources["t_order_d"].endswith("zeta.yaml"))
        self.assertTrue(catalog.sources["t_order_e"].endswith("alpha.yaml"))


class RejectionTests(CatalogCase):
    def test_duplicate_item_key_across_files_is_rejected(self):
        root = self.catalog(
            {"one.yaml": [_row("t_dup_key")], "two.yaml": [_row("t_dup_key")]}
        )
        self.assert_rejected(root, "repeats the item key")

    def test_duplicate_yaml_mapping_key_is_rejected(self):
        root = self.catalog({"one.yaml": [_row("t_yaml_key")]})
        (root / "one.yaml").write_text(
            "items:\n- key: t_yaml_key\n  display_name_zh: 甲\n"
            "  display_name_zh: 乙\n",
            encoding="utf-8",
        )
        self.assert_rejected(root, "duplicate YAML mapping key")

    def test_undeclared_yaml_file_is_rejected(self):
        root = self.catalog({"one.yaml": [_row("t_declared")]})
        (root / "stray.yaml").write_text("items: []\n", encoding="utf-8")
        self.assert_rejected(root, "undeclared item catalog files")

    def test_unknown_row_field_is_rejected(self):
        self.assert_rejected(
            self.catalog({"one.yaml": [_row("t_unknown", modifier_key="t_unknown")]}),
            "unknown fields",
        )

    def test_colon_in_key_is_rejected(self):
        self.assert_rejected(
            self.catalog({"one.yaml": [_row("t:bad")]}), "must match"
        )

    def test_equipment_effects_without_slot_is_rejected(self):
        self.assert_rejected(
            self.catalog(
                {"one.yaml": [_row("t_no_slot", equipment_effects={})]}
            ),
            "without an equipment slot",
        )

    def test_slot_without_equipment_effects_is_rejected(self):
        self.assert_rejected(
            self.catalog(
                {"one.yaml": [_row("t_no_effects", equipment_slot="armor")]}
            ),
            "without equipment_effects",
        )

    def test_symlink_outside_the_catalog_is_rejected(self):
        root = self.catalog({"one.yaml": [_row("t_symlink")]})
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, outside, True)
        target = outside / "escaped.yaml"
        target.write_text("items: []\n", encoding="utf-8")
        (root / "one.yaml").unlink()
        (root / "one.yaml").symlink_to(target)
        self.assert_rejected(root, "outside the item catalog directory")


if __name__ == "__main__":
    unittest.main()
