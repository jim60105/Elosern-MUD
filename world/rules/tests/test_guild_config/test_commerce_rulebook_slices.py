"""Data-contract test: commerce rulebook slice loading contract

Slice of ``test_guild_config``: CommerceRulebookSliceTests.
"""
from tools.spec_traceability import covers_requirement
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from world.rules.guild_config import (
    GuildConfigError,
    load_commerce_config,
    validate_assortment_configs,
    validate_price_scales,
    validate_shop_configs,
)

_SHIPPED_DIR = Path(__file__).resolve().parents[3] / "rules" / "rulebook" / "commerce"
_BASELINE = Path(__file__).resolve().parent / "commerce_catalog_baseline.json"

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

    def test_shipped_rulebook_is_a_directory_of_sorted_slices(self):
        files = sorted(_SHIPPED_DIR.glob("*.yaml"))
        self.assertEqual(
            [path.name for path in files],
            ["altoria.yaml", "ciaran.yaml", "scales.yaml"],
        )
        catalog = load_commerce_config(_SHIPPED_DIR)
        # ciaran-village-crafts grew the village to six shelves and six
        # homes; altoria-adornments-and-remedies split two more capital
        # bundles out of the sundries, and altoria-sanctum added the
        # sanctum's own bundle and counter: five capital + six elven
        # assortments, thirteen shops.
        self.assertEqual(len(catalog["assortments"]), 13)
        self.assertEqual(len(catalog["shops"]), 13)
        self.assertEqual(
            catalog["price_scales"], {"capital_altoria": 100, "village_ciaran": 100}
        )

    @covers_requirement(
        "commerce-assortments::commerce-balance-data-is-a-set-of-files-not-one-file"
    )
    def test_resolved_shipped_catalog_equals_the_pre_split_baseline(self):
        # The split promised the resolved catalog moved verbatim: every
        # shop's offers, prices, stock and hours. The baseline started as
        # the pre-split resolved catalog (normalized JSON) captured before
        # the directory existed and is the equality guard the slice loader
        # must keep passing — re-baselined whenever a content change
        # deliberately moves the catalog (ciaran-village-crafts added the
        # two village homes' shops, moved the earring offer between
        # shelves, and added the remedy offers). What it must NEVER absorb
        # is drift from the SLICE LOADERS: the offers still have to resolve
        # through the same merge/validation path the split introduced.
        commerce = load_commerce_config(_SHIPPED_DIR)
        configs = validate_shop_configs(
            commerce["shops"],
            validate_assortment_configs(commerce["assortments"]),
            validate_price_scales(commerce["price_scales"]),
        )
        resolved = {
            "price_scales": dict(sorted(validate_price_scales(commerce["price_scales"]).items())),
            "shops": {
                shop_key: {
                    "open_hour": cfg.open_hour,
                    "close_hour": cfg.close_hour,
                    "restock_hour": cfg.restock_hour,
                    "offers": [
                        {
                            "item_key": offer.item_key,
                            "buy_copper": offer.buy_copper,
                            "sell_copper": offer.sell_copper,
                            "max_stock": offer.max_stock,
                            "initial_stock": offer.initial_stock,
                            "restock_quantity": offer.restock_quantity,
                        }
                        for offer in sorted(cfg.offers, key=lambda o: o.item_key)
                    ],
                }
                for shop_key, cfg in sorted(configs.items())
            },
        }
        baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(resolved["price_scales"], baseline["price_scales"])
        self.assertEqual(resolved["shops"], baseline["shops"])

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_the_moved_offers_travel_field_for_field(self):
        # altoria-adornments-and-remedies moved seventeen offer rows out of
        # general_sundries into the two new specialist bundles, and
        # altoria-sanctum moved 受洗聖水 verbatim onto the sanctum's own
        # counter. A hand-moved row where a digit went missing is exactly
        # what this guards: the
        # literal BEFORE table below is the pre-move resolved offer of every
        # moved item (captured from the shipped data at the parent commit and
        # equal, field for field, to the re-baselined commerce_catalog_
        # baseline.json's pre-move general-store rows); after the move, each
        # key resolves — through the real loader and validators, not a
        # re-parse of the YAML — in exactly ONE capital shop, with all five
        # fields identical.
        before = {
            # accessory-slot adornments -> capital_adornments / altoria_jeweller
            "silver_hairpin": (200, 100, 10, 5, 2),
            "wolf_fang_necklace": (800, 400, 5, 2, 1),
            "pilgrim_medallion": (1500, 750, 5, 2, 1),
            "protective_ring": (30000, 15000, 1, 1, 1),
            "storage_pouch": (10000, 5000, 3, 3, 1),
            "gliding_cloak": (80000, 40000, 1, 1, 1),
            "purified_pendant": (15000, 7500, 3, 1, 1),
            "fearless_brooch": (15000, 7500, 3, 1, 1),
            "apothecary_beads": (2500, 1250, 5, 2, 2),
            "passion_silk_choker": (4800, 2400, 3, 1, 1),
            "radiant_holy_emblem": (20000, 10000, 2, 1, 1),
            # remedies -> capital_remedies / altoria_alchemist
            "healing_potion": (100, 50, 5, 3, 2),
            "greater_healing_potion": (250, 125, 5, 3, 2),
            "mana_potion": (120, 60, 10, 4, 2),
            "miners_bracing_broth": (50, 25, 20, 10, 5),
            "beastfolk_herbal_salve": (60, 30, 20, 10, 5),
            "passion_draught": (300, 150, 5, 2, 1),
            # 受洗聖水 -> sanctum_wares / altoria_sanctum_shop
            # (altoria-sanctum)
            "baptismal_holy_water": (120, 60, 10, 4, 2),
        }
        commerce = load_commerce_config(_SHIPPED_DIR)
        configs = validate_shop_configs(
            commerce["shops"],
            validate_assortment_configs(commerce["assortments"]),
            validate_price_scales(commerce["price_scales"]),
        )
        for item_key, fields in before.items():
            with self.subTest(item=item_key):
                homes = [
                    (shop_key, offer)
                    for shop_key, cfg in configs.items()
                    # Capital shops only: the village shelves deliberately
                    # share remedy keys with the capital at village prices
                    # (settlement-shops design §4.1).
                    if shop_key.startswith("altoria_")
                    for offer in cfg.offers
                    if offer.item_key == item_key
                ]
                self.assertEqual(len(homes), 1, f"{item_key} offered by {len(homes)} shops")
                offer = homes[0][1]
                self.assertEqual(
                    (
                        offer.buy_copper,
                        offer.sell_copper,
                        offer.max_stock,
                        offer.initial_stock,
                        offer.restock_quantity,
                    ),
                    fields,
                    f"{item_key} drifted from its pre-move offer",
                )
        # The new shops are where the goods landed, in bundle size: the
        # eleven-plus-six of the adornments split, and altoria-sanctum's
        # thirteen (twelve intimacy goods plus the moved 受洗聖水).
        self.assertEqual(len(configs["altoria_jeweller"].offers), 11)
        self.assertEqual(len(configs["altoria_alchemist"].offers), 6)
        self.assertEqual(len(configs["altoria_sanctum_shop"].offers), 13)


if __name__ == "__main__":
    unittest.main()
