"""Data-contract test: anchor data contract

Every map-facing field comes from ``content/maps/locations.yaml``; political
affiliation, population and dungeon floor counts come from the separate Python
lore joined by identity. These checks prove the composition and its identity
joins, never a copied row table.
"""

from tools.spec_traceability import covers_requirement

import unittest

import world.maps.geography as geography
from world.lore.anchors import (
    ANCHOR_LORE,
    AnchorKind,
    GeographicAnchor,
    anchor_geography,
    anchors,
)


def setUpModule():
    from world.tests.geography_fixture import publish_shipped_geography

    publish_shipped_geography()


class AnchorRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons")
    def test_every_declared_location_composes_with_its_non_map_lore(self):
        composed = anchors()
        self.assertTrue(composed)
        self.assertEqual(set(composed), set(anchor_geography()))
        for key, anchor in composed.items():
            with self.subTest(anchor=key):
                self.assertEqual(anchor.key, key)
                self.assertTrue(anchor.display_name_zh)
                self.assertTrue(anchor.description)
                lore = ANCHOR_LORE.get(key)
                self.assertIsNotNone(lore, "authored lore joins every shipped location")
                self.assertEqual(anchor.nation_key, lore.nation_key)
                self.assertEqual(anchor.population, lore.population)
                self.assertEqual(anchor.floors, lore.floors)

    def test_every_supported_kind_appears_without_a_fixed_roster_count(self):
        kinds = {anchor.kind for anchor in anchors().values()}
        self.assertEqual(
            kinds,
            {AnchorKind.CAPITAL, AnchorKind.ELVEN_VILLAGE, AnchorKind.DUNGEON},
        )

    @covers_requirement("lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons")
    def test_dungeon_floor_counts_follow_their_own_lore_owner(self):
        dungeons = {
            key: anchor
            for key, anchor in anchors().items()
            if anchor.kind is AnchorKind.DUNGEON
        }
        self.assertTrue(dungeons)
        for key, anchor in dungeons.items():
            with self.subTest(anchor=key):
                self.assertEqual(anchor.floors, ANCHOR_LORE[key].floors)
                self.assertIsNotNone(anchor.floors)

    def test_elven_villages_are_neutral(self):
        for anchor in anchors().values():
            if anchor.kind == AnchorKind.ELVEN_VILLAGE:
                self.assertIsNone(anchor.nation_key)

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_every_location_cell_is_available_without_a_fixed_roster_count(self):
        self.assertTrue(GeographicAnchor.__dataclass_params__.frozen)
        for key, entry in anchor_geography().items():
            with self.subTest(anchor=key):
                self.assertEqual(entry.anchor_key, key)
                self.assertTrue(entry.geographic_constraint)
                self.assertTrue(geography.current().locations.locations[key].cell == entry.cell)

    @covers_requirement(
        "map-geographic-sources::geographic-yaml-is-the-sole-map-facing-authority"
    )
    def test_composition_distinguishes_a_new_location_from_absent_lore(self):
        from elosern_map_core.codec import document_from_data
        from world.maps.geography import build_geography, current

        data = dict(current().locations.data)
        data["locations"] = {
            **data["locations"],
            "t_unbuilt_location": {
                "kind": "dungeon",
                "display_name_zh": "合成未建遺跡",
                "description": "A synthetic geographic location with no local map.",
                "cell": {"cell_x": 1000, "cell_y": 1000},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            },
        }
        added = document_from_data(
            "content/maps/locations.yaml", data
        )
        from world.maps import map_data

        snapshot = build_geography(
            current().continent,
            added,
            map_data.current(),
            fingerprints=dict(current().fingerprints),
        )
        view = snapshot.anchors["t_unbuilt_location"]
        self.assertEqual(view.kind, AnchorKind.DUNGEON)
        self.assertEqual(view.display_name_zh, "合成未建遺跡")
        self.assertIsNone(view.nation_key)
        self.assertIsNone(view.population)
        self.assertIsNone(view.floors)


if __name__ == "__main__":
    unittest.main()
