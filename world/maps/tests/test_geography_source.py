"""Data-contract test: geography publication, composition and snapshot-isolation mechanism contract

These exercise the game adapter directly: explicitly loaded candidates, the
immutable composed views, cross-domain join rejection, atomic publication, and
the guarantee that two worlds or a reload never leak derived terrain state.
"""

from __future__ import annotations

import copy
import unittest
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType
from unittest import mock

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from elosern_map_core.codec import document_from_data
from elosern_map_core.terrain import region_for_coordinates as core_region_for

import world.maps.geography as geography
from world.lore.anchors import AnchorKind, anchor_geography, anchors
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
from world.lore import monster_placement as placement
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    WeightedComposition,
)
from world.lore.monster_species import MonsterSpecies, MonsterVariant
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY, WildernessEntryPoint
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


def _synthetic_composition(key: str) -> EncounterComposition:
    return EncounterComposition(
        key, (CompositionMember("t_fixture_variant", 1, 1),)
    )


def _synthetic_zone(
    key: str, region_key: str, rectangle: tuple[int, int, int, int]
) -> tuple[EcologyZone, EncounterComposition]:
    composition = _synthetic_composition(f"{key}_group")
    zone = EcologyZone(
        key,
        region_key,
        (rectangle,),
        (WeightedComposition(composition.key, 1),),
        1,
        50,
        1,
        3600,
        600,
        1,
    )
    return zone, composition


def _synthetic_variants():
    return {
        "t_fixture_variant": MonsterVariant(
            "t_fixture_variant",
            "t_fixture_species",
            "合成變體",
            "合成變體敘述。",
            "t_fixture_tier",
            True,
            None,
            None,
            False,
        )
    }


def _synthetic_species(region_key: str):
    return {
        "t_fixture_species": MonsterSpecies(
            "t_fixture_species",
            "合成物種",
            "合成描述",
            "合成外觀",
            "合成生態",
            (region_key,),
            "合成私有真相",
            "合成私有解釋",
            "合成私有猜想",
            "t_fixture_variant",
            True,
        )
    }


def _ecology_patches(zones, compositions, region_key: str = "t_fixture_region"):
    """Patch the authored ecology registries for one candidate publication.

    The species/variant faces carry a synthetic pair whose habitat is the
    tested region, so candidate publication runs the same complete declaration
    validation the shipped module runs at import.
    """
    return (
        mock.patch.object(
            placement,
            "ECOLOGY_ZONE" + "_REGISTRY",
            MappingProxyType(dict(zones)),
        ),
        mock.patch.object(
            placement,
            "ENCOUNTER_COMPOSITION" + "_REGISTRY",
            MappingProxyType(dict(compositions)),
        ),
        mock.patch.object(
            placement,
            "MONSTER_VARIANT" + "_REGISTRY",
            MappingProxyType(_synthetic_variants()),
        ),
        mock.patch.object(
            placement,
            "MONSTER_SPECIES" + "_REGISTRY",
            MappingProxyType(_synthetic_species(region_key)),
        ),
    )


def _clear_of_settlements(cells) -> bool:
    """Whether no inhabited settlement buffer reaches any of ``cells``."""
    for entry in _settlements().wilderness_entries.values():
        footprint = entry.footprint_cells or {entry.anchor_cell}
        for cell in cells:
            if any(
                max(abs(cell[0] - source[0]), abs(cell[1] - source[1])) <= 1
                for source in footprint
            ):
                return False
    for key, anchor in anchors().items():
        if anchor.kind is AnchorKind.DUNGEON:
            continue
        source = anchor_geography()[key].cell
        if any(
            max(abs(cell[0] - source[0]), abs(cell[1] - source[1])) <= 1
            for cell in cells
        ):
            return False
    return True


def _birth_block() -> tuple[int, int, str]:
    """One walkable 2x2 block in a single region, clear of every settlement.

    The block is selected from the published terrain at test time; no shipped
    coordinate is pinned, and the selection only proves the fixture is lawful
    before the candidate assertions run.
    """
    for region_key, box in sorted(geography.current().region_search_boxes.items()):
        x_min, x_max, y_min, y_max = box
        for y in range(max(y_min, 0), min(y_max, geography.current().max_y) - 1, 4):
            for x in range(max(x_min, 0), min(x_max, geography.current().max_x) - 1, 4):
                cells = ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))
                if not all(wilderness_provider.is_walkable_cell(cell) for cell in cells):
                    continue
                if len(
                    {
                        wilderness_provider.region_for_coordinates(*cell)
                        for cell in cells
                    }
                ) != 1:
                    continue
                if not _clear_of_settlements(cells):
                    continue
                return x, y, wilderness_provider.region_for_coordinates(x, y)
    raise AssertionError("no settlement-clear walkable block exists in this world")


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
        entry = _settlements().wilderness_entries["capital_altoria"]
        gate = entry.gate_for("w")
        self.assertIsNotNone(gate)
        approach = entry.approach_cell(gate)
        self.assertIsNotNone(approach)
        data = _plain(before.continent.data)
        data["terrain"]["waterways"]["t_approach_water"] = {
            "route": [
                {"cell_x": approach[0], "cell_y": approach[1]},
                {"cell_x": approach[0], "cell_y": approach[1] - 1},
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
            f"gate 'w' approach {approach} is not walkable wilderness",
            str(captured.exception),
        )
        self.assertIs(geography.current(), before)
        self.assertEqual(geography.current().identity, identities)


class EcologyCandidatePublicationTests(EvenniaTest):
    """Bounded ecology zones are validated against the same candidate world."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        publish_shipped_geography()

    def setUp(self):
        self._shipped = geography.current()

    def tearDown(self):
        publish_geography(self._shipped)

    def _build(self, settlements=None):
        return geography.build_geography(
            self._shipped.continent,
            self._shipped.locations,
            _settlements() if settlements is None else settlements,
            fingerprints=dict(self._shipped.fingerprints),
        )

    def test_a_rejected_ecology_candidate_keeps_the_published_snapshot(self):
        before = geography.current()
        identity = before.identity
        x, y, region_key = _birth_block()
        zone, composition = _synthetic_zone(
            "t_fixture_tight_zone", region_key, (x, x, y, y)
        )
        with ExitStack() as stack:
            for patcher in _ecology_patches(
                {zone.key: zone}, {composition.key: composition}, region_key
            ):
                stack.enter_context(patcher)
            with self.assertRaises(geography.GeographyError) as captured:
                self._build()
        self.assertIn(zone.key, str(captured.exception))
        self.assertIs(geography.current(), before)
        self.assertEqual(geography.current().identity, identity)

    def test_overlapping_synthetic_zones_are_rejected(self):
        x, y, region_key = _birth_block()
        rectangle = (x, x + 1, y, y + 1)
        first, first_composition = _synthetic_zone(
            "t_fixture_zone_a", region_key, rectangle
        )
        second, second_composition = _synthetic_zone(
            "t_fixture_zone_b", region_key, rectangle
        )
        with ExitStack() as stack:
            for patcher in _ecology_patches(
                {first.key: first, second.key: second},
                {
                    first_composition.key: first_composition,
                    second_composition.key: second_composition,
                },
                region_key,
            ):
                stack.enter_context(patcher)
            with self.assertRaises(geography.GeographyError) as captured:
                self._build()
        self.assertIn(first.key, str(captured.exception))
        self.assertIn(second.key, str(captured.exception))

    def test_eligibility_reads_the_candidate_settlement_geometry(self):
        x, y, region_key = _birth_block()
        zone, composition = _synthetic_zone(
            "t_fixture_candidate_zone", region_key, (x, x + 1, y, y + 1)
        )
        with ExitStack() as stack:
            for patcher in _ecology_patches(
                {zone.key: zone}, {composition.key: composition}, region_key
            ):
                stack.enter_context(patcher)
            # The published settlements leave the block clear: the candidate
            # publishes.
            accepted = self._build()
            self.assertTrue(accepted.identity)
            before = geography.current()
            # A candidate world whose own footprint masks the whole block
            # changes the verdict for the very same zone, so eligibility read
            # the candidate entries rather than stale published geometry.
            entries = dict(_settlements().wilderness_entries)
            anchor_key = next(iter(sorted(entries)))
            entries[anchor_key] = WildernessEntryPoint(
                anchor_key=anchor_key,
                shape=("##", "##"),
                origin_xy=(x, y),
                gates=(),
            )
            masked = replace(
                _settlements(),
                wilderness_entries=MappingProxyType(entries),
            )
            with self.assertRaises(geography.GeographyError) as captured:
                self._build(masked)
        self.assertIn(zone.key, str(captured.exception))
        self.assertIs(geography.current(), before)


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
        # These candidates exist to prove derived terrain tables are
        # snapshot-scoped. A deliberately different coastline re-partitions the
        # regions, which lawfully invalidates the shipped ecology geometry, so
        # the isolation worlds author no zones.
        with ExitStack() as stack:
            for patcher in _ecology_patches({}, {}):
                stack.enter_context(patcher)
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
        from elosern_map_core.authoring import is_walkable_cell, terrain_definition
        from world.lore.map_districts import _ProductionTerrain

        settlement = map_data.current().settlements["capital_altoria"]
        anchor_xy = settlement.local_anchor_m
        first = geography.current()
        retained = _ProductionTerrain(first)
        before = retained.grid_site("capital_altoria", anchor_xy)
        self.assertIsNotNone(before)
        data = _plain(first.locations.data)
        cell = data["locations"]["capital_altoria"]["cell"]
        base = (int(cell["cell_x"]), int(cell["cell_y"]))
        terrain = terrain_definition(first.continent)
        # Move the anchor one cell along the first cardinal direction whose
        # shifted footprint is still walkable land. The approved north-bank
        # cell sits against the river, so the legal direction is read from the
        # authored terrain instead of a copied offset.
        dx, dy = next(
            (dx, dy)
            for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1))
            if all(
                is_walkable_cell(terrain, point)
                for point in settlement.wilderness_geometry(
                    (base[0] + dx, base[1] + dy)
                ).footprint_cells
            )
        )
        cell["cell_x"] = base[0] + dx
        cell["cell_y"] = base[1] + dy
        moved = document_from_data(geography.LOCATIONS_PATH, data)
        second = geography.build_geography(
            first.continent,
            moved,
            _settlements(),
            fingerprints=dict(first.fingerprints),
        )
        publish_geography(second)
        after = retained.grid_site("capital_altoria", anchor_xy)
        self.assertEqual(after.position_m, before.position_m)
        fresh = _ProductionTerrain(second).grid_site("capital_altoria", anchor_xy)
        self.assertEqual(
            (
                fresh.position_m[0] - before.position_m[0],
                fresh.position_m[1] - before.position_m[1],
            ),
            (dx * 1000, dy * 1000),
        )

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
