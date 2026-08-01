"""Self-consistency checks for anchor grid placements (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_REGISTRY, Anchor


class AnchorPlacementRegistryTests(unittest.TestCase):
    @covers_requirement("anchor-placement::anchor-placement-registry-is-intentionally-partial")
    def test_registry_has_exactly_one_entry_keyed_capital_altoria(self):
        self.assertEqual(list(ANCHOR_PLACEMENT_REGISTRY), ["capital_altoria"])
        placement = ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]
        self.assertEqual(placement.anchor_key, "capital_altoria")
        self.assertEqual(placement.zcoord, "capital_altoria")
        self.assertEqual(placement.entrance_xy, (2, 2))

    @covers_requirement("anchor-placement::every-placement-s-anchor-key-resolves-against-anchor-registry")
    def test_every_entrys_anchor_key_exists_in_anchor_registry(self):
        for placement in ANCHOR_PLACEMENT_REGISTRY.values():
            self.assertIn(placement.anchor_key, ANCHOR_REGISTRY)

    @covers_requirement("anchor-placement::anchorplacement-is-a-frozen-dataclass-separate-from-anchor")
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
