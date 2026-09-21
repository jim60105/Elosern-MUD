"""Data-contract test: commerce rulebook slice loading contract (commerce-rulebook-slices).

Slice of ``test_guild_config``: CommerceRulebookSliceTests.
"""
from tools.spec_traceability import covers_requirement
import tempfile
import unittest
from pathlib import Path

from world.rules.guild_config import GuildConfigError, load_commerce_config

_SHIPPED_DIR = Path(__file__).resolve().parents[3] / "rules" / "rulebook" / "commerce"

_A_ASSORTMENTS = """
assortments:
  - key: t_bundle_a
    offers:
      - item_key: synthetic_item_a
        buy_copper: 10
        sell_copper: 5
        max_stock: 2
        initial_stock: 1
        restock_quantity: 1
"""
_B_ASSORTMENTS = """
assortments:
  - key: t_bundle_b
    offers:
      - item_key: synthetic_item_b
        buy_copper: 20
        sell_copper: 10
        max_stock: 4
        initial_stock: 2
        restock_quantity: 2
"""
_A_SHOPS = """
shops:
  - shop_key: t_shop_a
    open_hour: 8
    close_hour: 20
    restock_hour: 6
"""
_B_SHOPS = """
shops:
  - shop_key: t_shop_b
    open_hour: 7
    close_hour: 19
    restock_hour: 5
"""
_SCALES_A = """
price_scales:
  t_settlement_one: 100
"""
_SCALES_B = """
price_scales:
  t_settlement_two: 120
"""


class CommerceRulebookSliceTests(unittest.TestCase):
    """The rulebook directory merges sorted slices and rejects shared keys."""

    @staticmethod
    def _write(root: Path, name: str, text: str) -> None:
        (root / name).write_text(text.lstrip("\n"), encoding="utf-8")

    @covers_requirement(
        "commerce-assortments::commerce-balance-data-is-a-set-of-files-not-one-file"
    )
    def test_sections_spread_across_files_load_as_one_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "one.yaml", _A_ASSORTMENTS + _A_SHOPS + _SCALES_A)
            self._write(root, "two.yaml", _B_ASSORTMENTS + _B_SHOPS + _SCALES_B)
            merged = load_commerce_config(root)
        # Identical to what one concatenated file would produce, in sorted
        # file order: every section from every file, concatenated/merged.
        self.assertEqual(
            [row["key"] for row in merged["assortments"]],
            ["t_bundle_a", "t_bundle_b"],
        )
        self.assertEqual(
            [row["shop_key"] for row in merged["shops"]],
            ["t_shop_a", "t_shop_b"],
        )
        self.assertEqual(
            merged["price_scales"], {"t_settlement_one": 100, "t_settlement_two": 120}
        )

    @covers_requirement(
        "commerce-assortments::commerce-balance-data-is-a-set-of-files-not-one-file"
    )
    def test_duplicate_key_across_two_files_fails_naming_key_and_both_files(self):
        cases = [
            ("one.yaml", _A_ASSORTMENTS, "two.yaml", _A_ASSORTMENTS, "t_bundle_a"),
            ("one.yaml", _A_SHOPS, "two.yaml", _A_SHOPS, "t_shop_a"),
            ("one.yaml", _SCALES_A, "two.yaml", _SCALES_A, "t_settlement_one"),
        ]
        for name_a, text_a, name_b, text_b, key in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    self._write(root, name_a, text_a)
                    self._write(root, name_b, text_b)
                    with self.assertRaises(GuildConfigError) as caught:
                        load_commerce_config(root)
                    message = str(caught.exception)
                    self.assertIn(key, message)
                    self.assertIn(name_a, message)
                    self.assertIn(name_b, message)

    def test_parse_error_names_the_offending_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "good.yaml", _A_ASSORTMENTS)
            self._write(root, "bad.yaml", "assortments: [unclosed")
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            self.assertIn("commerce/bad.yaml", str(caught.exception))

    def test_shape_error_names_the_offending_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "bad.yaml", "shops: {t_shop_a: {}}\n")
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            self.assertIn("commerce/bad.yaml", str(caught.exception))

    def test_shipped_rulebook_is_a_directory_of_sorted_slices(self):
        files = sorted(_SHIPPED_DIR.glob("*.yaml"))
        self.assertEqual(
            [path.name for path in files],
            ["altoria.yaml", "ciaran.yaml", "scales.yaml"],
        )
        catalog = load_commerce_config(_SHIPPED_DIR)
        self.assertEqual(len(catalog["assortments"]), 8)
        self.assertEqual(len(catalog["shops"]), 8)
        self.assertEqual(
            catalog["price_scales"], {"capital_altoria": 100, "village_ciaran": 100}
        )


if __name__ == "__main__":
    unittest.main()
