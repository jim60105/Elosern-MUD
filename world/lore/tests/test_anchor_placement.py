"""Data-contract test: anchor placement data contract
Self-consistency checks for anchor grid placements (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields, replace
from types import MappingProxyType

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY, AnchorPlacement
from world.maps.static_references import anchor_entrance_xyz
from world.lore.anchors import (
    LOCAL_FRAME_ANCHOR_REGISTRY,
    Anchor,
    GeographicAnchor,
    LocalFrameAnchor,
    anchor_geography,
    anchors,
    world_position_m,
)
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()


class AnchorPlacementRegistryTests(unittest.TestCase):
    @covers_requirement("anchor-placement::anchor-placement-registry-is-intentionally-partial")
    def test_registry_has_one_entry_per_built_settlement(self):
        from world.maps.map_data import current

        documents = current().settlements
        self.assertEqual(
            set(ANCHOR_PLACEMENT_REGISTRY),
            {document.location_ref for document in documents.values()},
        )
        for map_id, document in documents.items():
            with self.subTest(map_id=map_id):
                placement = ANCHOR_PLACEMENT_REGISTRY[document.location_ref]
                self.assertEqual(placement.anchor_key, document.location_ref)
                self.assertEqual(placement.zcoord, map_id)
                self.assertEqual(placement.node.object_id, document.anchor_node.node_id)
                self.assertEqual(
                    anchor_entrance_xyz(placement),
                    (*document.anchor_node.coordinate, map_id),
                )

    @covers_requirement("anchor-placement::every-placement-s-anchor-key-resolves-against-anchor-registry")
    def test_every_entrys_anchor_key_exists_in_anchor_registry(self):
        for placement in ANCHOR_PLACEMENT_REGISTRY.values():
            self.assertIn(placement.anchor_key, anchors())

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

    @covers_requirement(
        "continental-geography::known-continent-geographic-declarations-are-frozen"
    )
    def test_geographic_declarations_do_not_extend_grid_placement(self):
        self.assertTrue(anchor_geography())
        from world.maps.map_data import current

        self.assertEqual(
            set(ANCHOR_PLACEMENT_REGISTRY),
            {document.location_ref for document in current().settlements.values()},
        )
        self.assertLessEqual(set(ANCHOR_PLACEMENT_REGISTRY), set(anchor_geography()))
        self.assertEqual(
            {field.name for field in fields(AnchorPlacement)},
            {"anchor_key", "node"},
        )
        self.assertEqual(
            {field.name for field in fields(GeographicAnchor)},
            {"anchor_key", "cell", "geographic_constraint"},
        )
        from world.rules.lore_knowledge import CODE_CATEGORIES

        self.assertIs(CODE_CATEGORIES["anchor"].registry, anchors())
        self.assertFalse(
            any(
                spec.registry is anchor_geography()
                for spec in CODE_CATEGORIES.values()
            )
        )

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    def test_local_anchor_bindings_transform_to_absolute_metre_positions(self):
        from world.maps.map_data import current

        self.assertEqual(
            {
                key: frame.local_anchor_m
                for key, frame in LOCAL_FRAME_ANCHOR_REGISTRY.items()
            },
            {
                document.location_ref: document.local_anchor_m
                for document in current().settlements.values()
            },
        )
        self.assertTrue(LocalFrameAnchor.__dataclass_params__.frozen)
        from world.maps import geography

        for document in current().settlements.values():
            cell_x, cell_y = geography.current().locations.locations[document.location_ref].cell
            anchor_x, anchor_y = document.local_anchor_m
            for node in document.nodes.values():
                with self.subTest(map=document.location_ref, node=node.node_id):
                    x, y = node.coordinate
                    self.assertEqual(
                        world_position_m(document.location_ref, (x, y)),
                        (1000 * cell_x + 500 + x - anchor_x, 1000 * cell_y + 500 + y - anchor_y),
                    )

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    @covers_requirement(
        "map-geometry-model::geometry-is-explicit-and-snapshot-scoped"
    )
    def test_world_position_transform_adds_the_cell_center_not_the_cell_index(self):
        from world.maps import geography as geography_module
        from world.maps import map_data as map_data_module
        from world.maps import runtime
        from world.tests.geography_fixture import publish_geography, publish_settlements

        synthetic = {
            "t_frame_anchor": GeographicAnchor("t_frame_anchor", (2, 3), "synthetic")
        }
        frames = {"t_frame_anchor": LocalFrameAnchor("t_frame_anchor", (100, 200))}
        previous = geography_module.current()
        previous_settlements = map_data_module.current()
        publish_geography(
            replace(previous, anchor_geography=MappingProxyType(synthetic))
        )
        publish_settlements(
            replace(previous_settlements, local_frame_anchors=MappingProxyType(frames))
        )
        try:
            self.assertEqual(
                world_position_m("t_frame_anchor", (150, 260)),
                (2 * 1000 + 500 + 50, 3 * 1000 + 500 + 60),
            )
        finally:
            publish_settlements(previous_settlements)
            publish_geography(previous)
