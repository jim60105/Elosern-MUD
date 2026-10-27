"""Data-contract test: anchor placement data contract
Self-consistency checks for anchor grid placements (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields
from unittest.mock import patch

from world.lore import anchors as anchors_module
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY, AnchorPlacement
from world.maps.static_references import anchor_entrance_xyz
from world.lore.anchors import (
    ANCHOR_GEOGRAPHY_REGISTRY,
    ANCHOR_REGISTRY,
    LOCAL_FRAME_ANCHOR_REGISTRY,
    Anchor,
    GeographicAnchor,
    LocalFrameAnchor,
    world_position_m,
)


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
        self.assertEqual(anchor_entrance_xyz(capital), (3500, 2850, "capital_altoria"))
        self.assertEqual(capital.node.object_id, "central_plaza")
        village = ANCHOR_PLACEMENT_REGISTRY["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertEqual(village.zcoord, "village_ciaran")
        self.assertEqual(anchor_entrance_xyz(village), (220, 305, "village_ciaran"))
        self.assertEqual(village.node.object_id, "village_plaza")

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

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_geographic_declarations_do_not_extend_grid_placement(self):
        self.assertEqual(len(ANCHOR_GEOGRAPHY_REGISTRY), 9)
        self.assertEqual(
            list(ANCHOR_PLACEMENT_REGISTRY),
            ["capital_altoria", "village_ciaran"],
        )
        self.assertLessEqual(set(ANCHOR_PLACEMENT_REGISTRY), set(ANCHOR_GEOGRAPHY_REGISTRY))
        self.assertEqual(
            {field.name for field in fields(AnchorPlacement)},
            {"anchor_key", "node"},
        )
        self.assertEqual(
            {field.name for field in fields(GeographicAnchor)},
            {"anchor_key", "cell", "geographic_constraint"},
        )
        from world.rules.lore_knowledge import CODE_CATEGORIES

        self.assertFalse(
            any(
                spec.registry is ANCHOR_GEOGRAPHY_REGISTRY
                for spec in CODE_CATEGORIES.values()
            )
        )

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    def test_local_anchor_bindings_transform_to_absolute_metre_positions(self):
        self.assertEqual(
            {
                key: frame.local_anchor_m
                for key, frame in LOCAL_FRAME_ANCHOR_REGISTRY.items()
            },
            {
                "capital_altoria": (3500, 2850),
                "village_ciaran": (220, 305),
            },
        )
        self.assertTrue(LocalFrameAnchor.__dataclass_params__.frozen)
        self.assertEqual(
            world_position_m("capital_altoria", (3500, 2850)),
            (860_500, 1_080_500),
        )
        self.assertEqual(
            world_position_m("village_ciaran", (220, 305)),
            (1_340_500, 1_220_500),
        )
        # Altoria's south gate sits 450 m west and 2,700 m south of the plaza.
        self.assertEqual(
            world_position_m("capital_altoria", (3050, 150)),
            (860_500 - 450, 1_080_500 - 2700),
        )

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    @covers_requirement(
        "map-geometry-model::geometry-is-explicit-and-snapshot-scoped"
    )
    def test_world_position_transform_adds_the_cell_center_not_the_cell_index(self):
        geography = {"t_frame_anchor": GeographicAnchor("t_frame_anchor", (2, 3), "synthetic")}
        frames = {"t_frame_anchor": LocalFrameAnchor("t_frame_anchor", (100, 200))}
        with patch.dict(
            anchors_module.ANCHOR_GEOGRAPHY_REGISTRY, geography, clear=True
        ), patch.dict(
            anchors_module.LOCAL_FRAME_ANCHOR_REGISTRY, frames, clear=True
        ):
            self.assertEqual(
                world_position_m("t_frame_anchor", (150, 260)),
                (2500 + 50, 3500 + 60),
            )
