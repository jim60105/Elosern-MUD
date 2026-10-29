"""Data-contract test: geography publication, composition and snapshot-isolation mechanism contract

These exercise the game adapter directly: explicitly loaded candidates, the
immutable composed views, cross-domain join rejection, atomic publication, and
the guarantee that two worlds or a reload never leak derived terrain state.
"""

from __future__ import annotations

import copy
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from elosern_map_core.codec import document_from_data
from elosern_map_core.terrain import region_for_coordinates as core_region_for

import world.maps.geography as geography
from world.lore.anchors import AnchorKind, anchor_geography, anchors
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.lore.wilderness_regions import harbor_sites, regions
from world.maps import map_data, wilderness_provider
from world.tests.geography_fixture import (
    publish_geography,
    publish_shipped_geography,
)

publish_shipped_geography()


def _settlements():
    """The candidate settlement world every geography candidate is joined against."""

    return map_data.current()


def _plain(value):
    if isinstance(value, MappingProxyType):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return copy.deepcopy(value)


def _continent_variant(**terrain_overrides):
    """A schema-valid continent candidate derived from the published one."""

    data = _plain(geography.current().continent.data)
    data["terrain"].update(terrain_overrides)
    return document_from_data(geography.CONTINENT_PATH, data)


class ShippedGeographyPublicationTests(EvenniaTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        publish_shipped_geography()

    def setUp(self):
        self._shipped = geography.current()

    def tearDown(self):
        publish_geography(self._shipped)

    def test_the_published_views_are_immutable(self):
        with self.assertRaises(TypeError):
            regions()["eastern_plains"] = regions()["central_mountains"]
        with self.assertRaises(FrozenInstanceError):
            anchors()["capital_altoria"].display_name_zh = "changed"
        self.assertIsInstance(geography.current().terrain.region_search_boxes, MappingProxyType)

    @covers_requirement(
        "map-geographic-sources::geographic-yaml-is-the-sole-map-facing-authority"
    )
    def test_an_unbuilt_location_is_displayable_without_local_content(self):
        key = "dungeon_arcane_ruins"
        rooms = ObjectDB.objects.count()
        anchor = anchors()[key]
        cell = anchor_geography()[key].cell
        self.assertTrue(anchor.display_name_zh)
        self.assertIs(anchor.kind, AnchorKind.DUNGEON)
        self.assertEqual(wilderness_provider.region_for_coordinates(*cell),
                         core_region_for(geography.current().terrain, *cell))
        self.assertNotIn(key, SETTLEMENT_REGISTRY)
        self.assertNotIn(key, WILDERNESS_ENTRY_REGISTRY)
        publish_shipped_geography()
        self.assertEqual(ObjectDB.objects.count(), rooms)
        self.assertIn(key, anchors())

    def test_publication_is_atomic_and_keeps_the_previous_baseline(self):
        before = geography.current()
        identities = before.identity
        data = _plain(before.continent.data)
        data["regions"]["eastern_plains"]["scene_archetype"] = "no_such_scene"
        broken = document_from_data(geography.CONTINENT_PATH, data)
        with self.assertRaises(geography.GeographyError) as captured:
            geography.build_geography(
                broken,
                before.locations,
                _settlements(),
                fingerprints=dict(before.fingerprints),
            )
        self.assertIn("eastern_plains", str(captured.exception))
        self.assertIs(geography.current(), before)
        self.assertEqual(geography.current().identity, identities)

    def test_unknown_lore_joins_are_diagnosed(self):
        before = geography.current()
        data = _plain(before.locations.data)
        data["locations"].pop("dungeon_dragon_nest")
        locations = document_from_data(geography.LOCATIONS_PATH, data)
        with self.assertRaises(geography.GeographyError) as captured:
            geography.build_geography(
                before.continent,
                locations,
                _settlements(),
                fingerprints=dict(before.fingerprints),
            )
        self.assertIn("dungeon_dragon_nest", str(captured.exception))

    def test_unsupported_cell_scale_is_rejected(self):
        before = geography.current()
        data = _plain(before.continent.data)
        data["cell_size_km"] = 2
        candidate = document_from_data(geography.CONTINENT_PATH, data)
        with self.assertRaises(geography.GeographyError) as captured:
            geography.build_geography(
                candidate,
                before.locations,
                _settlements(),
                fingerprints=dict(before.fingerprints),
            )
        self.assertIn("cell_size_km", str(captured.exception))

    def test_gateway_approach_is_validated_before_publication(self):
        before = geography.current()
        identities = before.identity
        data = _plain(before.continent.data)
        data["terrain"]["waterways"]["t_approach_water"] = {
            "route": [
                {"cell_x": 864, "cell_y": 1080},
                {"cell_x": 864, "cell_y": 1079},
            ],
            "fords": [],
        }
        candidate = document_from_data(geography.CONTINENT_PATH, data)
        with self.assertRaises(geography.GeographyError) as captured:
            geography.build_geography(
                candidate,
                before.locations,
                _settlements(),
                fingerprints=dict(before.fingerprints),
            )
        self.assertIn(
            "gate 'w' approach (864, 1080) is not walkable wilderness",
            str(captured.exception),
        )
        self.assertIs(geography.current(), before)
        self.assertEqual(geography.current().identity, identities)


class SnapshotIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publish_shipped_geography()

    def setUp(self):
        self._shipped = geography.current()
        self._locations = self._shipped.locations
        self._fingerprints = dict(self._shipped.fingerprints)

    def tearDown(self):
        publish_geography(self._shipped)
        from web.webclient.presentation.map_quest_destinations import clear_search_memo

        clear_search_memo()

    def _world(self, coastal_y_max: int):
        continent = _continent_variant(coastal_y_max=coastal_y_max)
        return geography.build_geography(
            continent,
            self._locations,
            _settlements(),
            fingerprints=self._fingerprints,
        )

    def test_two_worlds_keep_independent_derived_tables(self):
        first = self._world(500)
        second = self._world(400)
        self.assertIsNot(first.terrain, second.terrain)
        self.assertNotEqual(first.identity, second.identity)
        publish_geography(first)
        first_box = wilderness_provider.region_search_boxes()["eastern_plains"]
        publish_geography(second)
        second_box = wilderness_provider.region_search_boxes()["eastern_plains"]
        self.assertNotEqual(first_box, second_box)
        self.assertEqual(second_box[2], 401)
        publish_geography(first)
        self.assertEqual(wilderness_provider.region_search_boxes()["eastern_plains"], first_box)

    def test_reachability_and_search_memos_are_snapshot_scoped(self):
        from world.maps.wilderness_reachability import walkable_components
        from web.webclient.presentation.map_quest_destinations import nearest_region_cell

        first = self._world(500)
        second = self._world(400)
        publish_geography(first)
        first_components = walkable_components()
        first_cell = nearest_region_cell(
            (0, 0),
            "southeast_coast",
            classify=wilderness_provider.region_for_coordinates,
            is_legal=lambda cell: wilderness_provider.is_valid_wilderness_cell(cell),
            bounds=wilderness_provider.region_search_boxes()["southeast_coast"],
        )
        publish_geography(second)
        second_components = walkable_components()
        self.assertIsNot(first_components, second_components)
        second_cell = nearest_region_cell(
            (0, 0),
            "southeast_coast",
            classify=wilderness_provider.region_for_coordinates,
            is_legal=lambda cell: wilderness_provider.is_valid_wilderness_cell(cell),
            bounds=wilderness_provider.region_search_boxes()["southeast_coast"],
        )
        self.assertEqual(
            wilderness_provider.region_for_coordinates(*second_cell),
            "southeast_coast",
        )
        self.assertEqual(
            wilderness_provider.region_for_coordinates(*first_cell),
            "southeast_coast",
        )
        # The stale world's index still answers for its own snapshot.
        self.assertIsNotNone(first_components.component((500, 700)))
        # The occupancy memo is keyed by the authored world, so both searches
        # leave their own entries instead of sharing one.
        from web.webclient.presentation import map_quest_destinations

        identities = {key[0] for key in map_quest_destinations._OCCUPANCY}
        self.assertIn(first.identity, identities)
        self.assertIn(second.identity, identities)

    def test_local_lookup_does_not_build_a_world_scan(self):
        from world.maps import wilderness_reachability

        original = wilderness_reachability.walkable_components

        def _forbid(snapshot=None):
            raise AssertionError("local lookup built a whole-frame index")

        wilderness_reachability.walkable_components = _forbid
        try:
            wilderness_provider.region_for_coordinates(1250, 2420)
            wilderness_provider.is_valid_wilderness_cell((500, 700))
            wilderness_provider.terrain_description(860, 1080)
            wilderness_provider.is_land_cell((1000, 1000))
        finally:
            wilderness_reachability.walkable_components = original

    def test_retained_adapter_keeps_its_snapshot_coordinates(self):
        from world.lore.map_districts import _ProductionTerrain

        first = geography.current()
        retained = _ProductionTerrain(first)
        before = retained.grid_site("capital_altoria", (3500, 2850))
        self.assertIsNotNone(before)
        data = _plain(first.locations.data)
        data["locations"]["capital_altoria"]["cell"] = {
            "cell_x": 861,
            "cell_y": 1080,
        }
        moved = document_from_data(geography.LOCATIONS_PATH, data)
        second = geography.build_geography(
            first.continent,
            moved,
            _settlements(),
            fingerprints=dict(first.fingerprints),
        )
        publish_geography(second)
        after = retained.grid_site("capital_altoria", (3500, 2850))
        self.assertEqual(after.position_m, before.position_m)
        fresh = _ProductionTerrain(second).grid_site("capital_altoria", (3500, 2850))
        self.assertEqual(fresh.position_m[0] - before.position_m[0], 1000)

    def test_candidate_without_a_classifier_region_is_rejected(self):
        data = _plain(self._shipped.continent.data)
        data["regions"].pop("central_mountains")
        candidate = document_from_data(geography.CONTINENT_PATH, data)
        with self.assertRaises(geography.GeographyError) as captured:
            geography.build_geography(
                candidate,
                self._locations,
                _settlements(),
                fingerprints=self._fingerprints,
            )
        self.assertIn("central_mountains", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
