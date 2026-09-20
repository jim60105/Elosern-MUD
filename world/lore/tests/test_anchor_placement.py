"""Data-contract test: anchor placement data contract
Self-consistency checks for anchor grid placements (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_REGISTRY, Anchor


class AnchorPlacementRegistryTests(unittest.TestCase):
    @covers_requirement("anchor-placement::anchor-placement-registry-is-intentionally-partial")
    def test_registry_has_one_entry_per_built_settlement(self):
        self.assertEqual(
            list(ANCHOR_PLACEMENT_REGISTRY),
            ["capital_altoria", "village_ciaran"],
        )
        capital = ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]
        self.assertEqual(capital.anchor_key, "capital_altoria")
        self.assertEqual(capital.zcoord, "capital_altoria")
        self.assertEqual(capital.entrance_xy, (2, 2))
        village = ANCHOR_PLACEMENT_REGISTRY["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertEqual(village.zcoord, "village_ciaran")
        self.assertEqual(village.entrance_xy, (1, 1))

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
