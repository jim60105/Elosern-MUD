"""Data-contract test: commerce rulebook slice loading contract

Slice of ``test_guild_config``: CommerceRulebookSliceTests.
"""
from tools.spec_traceability import covers_requirement
import tempfile
import unittest
from pathlib import Path

import yaml

from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.shops import SHOP_REGISTRY
from world.rules.guild_config import (
    GuildConfigError,
    load_commerce_config,
    validate_assortment_configs,
    validate_price_scales,
    validate_shop_configs,
)

_SHIPPED_DIR = Path(__file__).resolve().parents[3] / "rules" / "rulebook" / "commerce"


def _place_by_shop() -> dict:
    """The place that authors each derived shop identity."""
    return {
        dict(place.authored_kwargs)["shop_key"]: place
        for place in PLACE_REGISTRY.values()
        if dict(place.authored_kwargs).get("shop_key")
    }

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
            # Written in reverse lexical order: the loader MUST sort by
            # filename, so the merged order is a-file-rows then z-file-rows
            # regardless of creation order or platform listing order.
            self._write(root, "z_later.yaml", _B_ASSORTMENTS + _B_SHOPS + _SCALES_B)
            self._write(root, "a_earlier.yaml", _A_ASSORTMENTS + _A_SHOPS + _SCALES_A)
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

    def test_duplicate_mapping_key_within_one_slice_fails_load(self):
        # PyYAML's default loader keeps the LAST duplicate silently, which
        # would let one settlement's scale be repriced by an invisible second
        # row. The slice loader must refuse the document instead.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "scales.yaml",
                "price_scales:\n  t_settlement_one: 100\n  t_settlement_one: 900\n",
            )
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            self.assertIn("commerce/scales.yaml", str(caught.exception))
            self.assertIn("t_settlement_one", str(caught.exception))

    def test_duplicate_row_key_within_one_slice_fails_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {
                "key": "t_bundle_a",
                "offers": [
                    {
                        "item_key": "synthetic_item_a",
                        "buy_copper": 10,
                        "sell_copper": 5,
                        "max_stock": 2,
                        "initial_stock": 1,
                        "restock_quantity": 1,
                    }
                ],
            }
            self._write(
                root,
                "one.yaml",
                yaml.dump({"assortments": [row, dict(row)]}, sort_keys=False),
            )
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            self.assertIn("commerce/one.yaml", str(caught.exception))
            self.assertIn("t_bundle_a", str(caught.exception))

    def test_unknown_section_is_rejected_naming_the_file(self):
        # A typo'd section would load as a silent no-op slice.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "typo.yaml", "shop:\n  - shop_key: t_shop_a\n")
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            message = str(caught.exception)
            self.assertIn("commerce/typo.yaml", message)
            self.assertIn("shop", message)

    def test_empty_slice_is_rejected_naming_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "one.yaml", _A_ASSORTMENTS)
            self._write(root, "empty.yaml", "# nothing here\n")
            with self.assertRaises(GuildConfigError) as caught:
                load_commerce_config(root)
            self.assertIn("commerce/empty.yaml", str(caught.exception))

    def test_semantically_empty_slice_is_rejected_naming_the_file(self):
        # A declared-but-empty section is an ownership failure, not a
        # legitimate partial slice: an accidentally emptied settlement would
        # silently vanish from the world.
        empties = ["assortments: []\n", "shops: []\n", "price_scales: {}\n"]
        for text in empties:
            with self.subTest(text=text):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    self._write(root, "one.yaml", _A_ASSORTMENTS)
                    self._write(root, "hollow.yaml", text)
                    with self.assertRaises(GuildConfigError) as caught:
                        load_commerce_config(root)
                    self.assertIn("commerce/hollow.yaml", str(caught.exception))

    def test_non_string_row_key_is_a_named_rulebook_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "bad.yaml",
                "assortments:\n  - key: [not, a, string]\n    offers: []\n",
            )
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

    @covers_requirement(
        "commerce-assortments::commerce-balance-data-is-a-set-of-files-not-one-file"
    )
    def test_shipped_rulebook_is_a_directory_of_sorted_slices(self):
        files = sorted(_SHIPPED_DIR.glob("*.yaml"))
        # The directory is the contract: names stay sorted and unique (the
        # loader merges in filename order), but the roster itself is data --
        # a new settlement slice must not need a test edit.
        names = [path.name for path in files]
        self.assertTrue(names)
        self.assertEqual(names, sorted(set(names)))
        self.assertTrue(all(name.endswith(".yaml") for name in names))
        catalog = load_commerce_config(_SHIPPED_DIR)
        # Structural, not counted: every declared row resolves through the
        # sorted merge and every section is non-empty, so adding a settlement
        # slice is a data edit while an emptied one still fails loudly.
        self.assertTrue(catalog["assortments"])
        self.assertTrue(catalog["shops"])
        for row in catalog["assortments"]:
            self.assertIn(row["key"], ASSORTMENT_REGISTRY)
        self.assertEqual(
            {row["shop_key"] for row in catalog["shops"]}, set(SHOP_REGISTRY)
        )
        scales = validate_price_scales(catalog["price_scales"])
        self.assertTrue(scales)
        for scale in scales.values():
            self.assertIs(type(scale), int)
            self.assertGreaterEqual(scale, 1)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_at_par_slice_offers_travel_field_for_field(self):
        # "Moving a good between shelves does not change its price": where a
        # shop's settlement is at par and the shop declares neither its own
        # price_scale nor an override, every resolved offer must equal the
        # authored assortment row verbatim -- all five fields. A hand-moved
        # row that lost or repriced a field on its way from the slice to the
        # counter fails here, and no pre-split snapshot is needed to see it.
        # Attached to sample-city-altoria because that is the requirement
        # whose merchandise scenarios (a shop exposing precisely its current
        # authored union, goods moving between shelves without repricing)
        # this asserts; the grid/interior half of it stays in
        # world/maps/tests/test_service_interiors.py.
        commerce = load_commerce_config(_SHIPPED_DIR)
        scales = validate_price_scales(commerce["price_scales"])
        assortment_offers = validate_assortment_configs(commerce["assortments"])
        configs = validate_shop_configs(commerce["shops"], assortment_offers, scales)
        places = _place_by_shop()
        rows = {row["shop_key"]: row for row in commerce["shops"]}
        checked = 0
        for shop_key, config in configs.items():
            row = rows[shop_key]
            place = places[shop_key]
            if (
                scales[place.settlement_key] != 100
                or "price_scale" in row
                or "overrides" in row
            ):
                continue
            shop = SHOP_REGISTRY[shop_key]
            excluded = set(place.excluded_item_keys)
            resolved = {offer.item_key: offer for offer in config.offers}
            for assortment_key in shop.assortment_keys:
                for base in assortment_offers[assortment_key].values():
                    if base.item_key in excluded:
                        continue
                    offer = resolved[base.item_key]
                    with self.subTest(shop=shop_key, item=base.item_key):
                        self.assertEqual(
                            (
                                offer.buy_copper,
                                offer.sell_copper,
                                offer.max_stock,
                                offer.initial_stock,
                                offer.restock_quantity,
                            ),
                            (
                                base.buy_copper,
                                base.sell_copper,
                                base.max_stock,
                                base.initial_stock,
                                base.restock_quantity,
                            ),
                        )
                    checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
