"""Self-consistency checks for nations and capital anchors."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.anchors import ANCHOR_REGISTRY, AnchorKind
from world.lore.nations import NATION_REGISTRY


class NationRegistryTests(unittest.TestCase):
    def test_three_nations_and_capitals(self):
        self.assertEqual(set(NATION_REGISTRY), {"grandia", "altoria", "valhalla"})
        for nation in NATION_REGISTRY.values():
            anchor = ANCHOR_REGISTRY[nation.capital_anchor_key]
            self.assertEqual(anchor.kind, AnchorKind.CAPITAL)
            self.assertEqual(anchor.nation_key, nation.key)

    @covers_requirement("lore-registries::nation-registry-covers-the-three-states")
    def test_territory_shares_leave_neutral_land(self):
        total = sum(nation.territory_share for nation in NATION_REGISTRY.values())
        self.assertGreaterEqual(total, 0.85)
        self.assertLessEqual(total, 1.0)
