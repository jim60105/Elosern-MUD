"""Self-consistency checks for anchor grid placements (map-anchor-grid)."""

import unittest
from dataclasses import fields

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_REGISTRY, Anchor


class AnchorPlacementRegistryTests(unittest.TestCase):
    def test_registry_has_exactly_one_entry_keyed_capital_altoria(self):
        self.assertEqual(list(ANCHOR_PLACEMENT_REGISTRY), ["capital_altoria"])
        placement = ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]
        self.assertEqual(placement.anchor_key, "capital_altoria")
        self.assertEqual(placement.zcoord, "capital_altoria")
        self.assertEqual(placement.entrance_xy, (2, 2))

    def test_every_entrys_anchor_key_exists_in_anchor_registry(self):
        for placement in ANCHOR_PLACEMENT_REGISTRY.values():
            self.assertIn(placement.anchor_key, ANCHOR_REGISTRY)

    def test_anchor_dataclass_keeps_its_pre_change_field_set(self):
        self.assertEqual(
            {field.name for field in fields(Anchor)},
            {
                "key",
                "kind",
                "display_name_zh",
                "nation_key",
                "population",
                "floors",
                "description",
            },
        )