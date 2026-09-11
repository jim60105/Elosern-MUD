"""Data-contract test: element data contract
Self-consistency checks for the element registry."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.elements import ELEMENT_REGISTRY
from world.imports.schema import CHARACTER_SCHEMA_V1


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

    def test_import_affinity_enum_mirrors_the_element_vocabulary(self):
        # Data-contract half (migrated off the behavior-suite gate): the
        # character schema's affinity enum must list EXACTLY the shipped
        # element keys — a content claim about shipped data, so it lives
        # here, not in the mechanics-only import-schema tests.
        affinity = CHARACTER_SCHEMA_V1["properties"]["affinity_elements"]
        self.assertEqual(
            set(affinity["items"]["enum"]),
            set(ELEMENT_REGISTRY),
        )
