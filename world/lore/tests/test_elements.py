"""Self-consistency checks for the element registry."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.elements import ELEMENT_REGISTRY


class ElementRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::element-registry-covers-the-eight-documented-elements")
    def test_exactly_eight_distinct_elements(self):
        self.assertEqual(len(ELEMENT_REGISTRY), 8)
        self.assertEqual(
            {element.display_name_zh for element in ELEMENT_REGISTRY.values()},
            {"火", "水", "風", "土", "雷", "冰", "光", "暗"},
        )
        self.assertEqual(
            {element.key for element in ELEMENT_REGISTRY.values()},
            set(ELEMENT_REGISTRY),
        )
