"""Data-contract test: shipped map-district landmarks against the authored continent

The district document is shipped content, so this module names the source and
its consumers rather than echoing every authored row: the published district
snapshot validates against the live terrain, settlement graphs and gateways;
every landmark is spelt exactly as the map-knowledge writer records it, is
reachable on walkable ground and follows a moved settlement binding; the deep
forest stays the single cross-claim region district; the frozen partition and
the map presenters read the same loaded identities and authored names.
Mechanism rules are covered with synthetic fixtures in ``test_map_districts``.
"""

import json
import unittest
from collections.abc import Mapping
from unittest import mock

import numpy as np

from elosern_map_core.geometry import cell_center_m
from elosern_map_core.partition import PartitionInput, compute_partition
from elosern_map_core.references import ReferenceIndex
from tools import map_district_partition as generator
from tools.spec_traceability import covers_requirement
from world.lore import map_districts
from world.maps import runtime
from world.lore.anchors import AnchorKind, anchor_geography, anchors
from world.lore.map_districts import (
    DISTRICTS_PATH,
    MIN_VORONOI_SPACING_KM,
    build_districts,
    cell_of_position,
    landmark_node_id,
    landmark_node_ids,
    production_terrain,
)
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.lore.wilderness_regions import regions
from world.maps import district_partition, geography, wilderness_provider
from world.maps.map_data import settlement_graph
from world.maps.static_references import binding_signature, map_reference_index
from world.maps.wilderness_reachability import walkable_components
from world.rules.map_district_lighting import lit_district_keys_from_visits
from world.rules.map_knowledge import NodeVisit, decode_node, encode_grid, encode_wild
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _rows():
    """The authored rows as plain data, for a synthetic candidate document."""

    return _plain(map_districts.current().document.data["districts"])


def _document(rows):
    data = {"version": 1, "kind": "districts", "id": "districts", "districts": rows}
    return map_districts.parse_districts_document(json.dumps(data, ensure_ascii=False))


class ShippedDistrictContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.snapshot = map_districts.current()
        cls.terrain = production_terrain()
        cls.districts = cls.snapshot.districts

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_the_document_is_the_published_authority(self):
        self.assertEqual(self.snapshot.document.relative_path, DISTRICTS_PATH)
        self.assertEqual(tuple(self.snapshot.districts), tuple(self.snapshot.document.districts))
        self.assertTrue(self.districts)
        # Reloading the same source reproduces the same identity and a
        # diagnostic-free candidate: no consumer registration, no Python row.
        again = runtime.compose().districts
        self.assertEqual(again.identity, self.snapshot.identity)
        self.assertEqual(again.diagnostics, ())
        self.assertEqual(tuple(again.districts), tuple(self.districts))

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_landmarks_are_qualified_identities_not_coordinates(self):
        for key, district in self.districts.items():
            with self.subTest(district=key):
                landmark = district.landmark
                if landmark.domain == "wilderness_cell":
                    self.assertIsNotNone(landmark.cell)
                    self.assertIsNone(landmark.map_id)
                    self.assertIsNone(landmark.object_id)
                    continue
                self.assertIsNone(landmark.cell)
                self.assertIsNotNone(landmark.object_id)
                if landmark.domain in ("settlement_node", "interior_room"):
                    self.assertIsNotNone(landmark.map_id)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_landmarks_are_spelt_as_the_knowledge_writer_records_them(self):
        for key, district in self.districts.items():
            with self.subTest(district=key):
                node_id = landmark_node_id(district)
                self.assertIsNotNone(node_id)
                parts = decode_node(node_id)
                if parts["prefix"] == "wild":
                    rebuilt = encode_wild(parts["name"], parts["x"], parts["y"])
                else:
                    self.assertEqual(parts["prefix"], "grid")
                    graph = settlement_graph(parts["z_map_key"])
                    self.assertIsNotNone(graph.node_at((parts["x"], parts["y"])))
                    rebuilt = encode_grid(parts["z_map_key"], parts["x"], parts["y"])
                self.assertEqual(rebuilt, node_id)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_every_landmark_resolves_and_is_reachable_on_the_live_continent(self):
        components = walkable_components()
        gateway = {
            components.component(entry.approach_cell(gate))
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
        for key, district in self.districts.items():
            parts = decode_node(landmark_node_id(district))
            with self.subTest(district=key):
                if parts["prefix"] == "grid":
                    site = self.terrain.grid_site(parts["z_map_key"], (parts["x"], parts["y"]))
                    self.assertIsNotNone(site)
                    self.assertTrue(site.reachable)
                    continue
                cell = (parts["x"], parts["y"])
                self.assertTrue(wilderness_provider.is_valid_wilderness_cell(cell))
                self.assertIn(components.component(cell), gateway)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_a_grid_landmark_is_reachable_only_through_a_routed_gateway(self):
        grid_districts = [
            district
            for district in self.districts.values()
            if district.landmark.domain == "settlement_node"
        ]
        self.assertTrue(grid_districts)
        for district in grid_districts:
            landmark = district.landmark
            parts = decode_node(landmark_node_id(district))
            node = settlement_graph(landmark.map_id).node_at((parts["x"], parts["y"]))
            self.assertTrue(self.terrain.grid_site(landmark.map_id, node.coordinate).reachable)
            # Without that settlement's gates no gateway routes to the node:
            # the same identity still resolves, but it is no longer reachable.
            others = {
                key: entry
                for key, entry in WILDERNESS_ENTRY_REGISTRY.items()
                if all(gate.z_map_key != landmark.map_id for gate in entry.gates)
            }
            from dataclasses import replace
            from types import MappingProxyType

            from world.maps import map_data
            from world.tests.geography_fixture import publish_settlements

            published = map_data.current()
            without_gates = replace(
                published,
                wilderness_entries=MappingProxyType(others),
            )
            publish_settlements(without_gates)
            try:
                site = production_terrain().grid_site(landmark.map_id, node.coordinate)
            finally:
                publish_settlements(published)
            self.assertIsNotNone(site)
            self.assertFalse(site.reachable)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_region_districts_cover_one_region_across_nominal_claims(self):
        region_districts = [
            district for district in self.districts.values() if district.kind == "region"
        ]
        self.assertTrue(region_districts)
        for district in region_districts:
            with self.subTest(district=district.district_id):
                self.assertIn(district.region_key, regions())
                region = regions()[district.region_key]
                self.assertGreaterEqual(len(set(region.nominal_nation_keys)), 2)
                parts = decode_node(landmark_node_id(district))
                position = cell_center_m((parts["x"], parts["y"]))
                self.assertEqual(
                    wilderness_provider.region_for_coordinates(
                        *cell_of_position(position)
                    ),
                    district.region_key,
                )

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_every_pair_of_voronoi_landmarks_keeps_the_declared_spacing(self):
        positions = [
            (key, self._continental_position(district))
            for key, district in self.districts.items()
            if district.kind == "voronoi"
        ]
        minimum_m = MIN_VORONOI_SPACING_KM * 1000
        closest = min(
            (
                ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5,
                first,
                second,
            )
            for index, (first, a) in enumerate(positions)
            for second, b in positions[index + 1 :]
        )
        self.assertGreaterEqual(closest[0], minimum_m, closest)

    def _continental_position(self, district):
        parts = decode_node(landmark_node_id(district))
        if parts["prefix"] == "wild":
            return cell_center_m((parts["x"], parts["y"]))
        return self.terrain.grid_site(parts["z_map_key"], (parts["x"], parts["y"])).position_m

    def test_no_landmark_marks_a_hidden_place(self):
        hidden = {
            anchor_geography()[key].cell
            for key, anchor in anchors().items()
            if anchor.kind in (AnchorKind.ELVEN_VILLAGE, AnchorKind.DUNGEON)
        }
        self.assertTrue(hidden)
        for key, district in self.districts.items():
            with self.subTest(district=key):
                self.assertNotIn(
                    cell_of_position(self._continental_position(district)), hidden
                )


class _SyntheticTerrain:
    """A small all-walkable frame for synthetic district candidates."""

    wilderness_name = "testland"
    max_cell = (399, 399)
    region_keys = frozenset({"plain"})

    def is_land(self, cell):
        return True

    def is_walkable(self, cell):
        return True

    def is_reachable(self, cell):
        return True

    def region_of(self, cell):
        return "plain"

    def grid_site(self, map_key, xy):
        return None


def _synthetic_districts(cells):
    rows = {
        key: {
            "district_name_zh": f"合成{key}區",
            "landmark_name_zh": f"合成{key}碑",
            "landmark": {
                "domain": "wilderness_cell",
                "map_id": None,
                "object_id": None,
                "cell": {"cell_x": x, "cell_y": y},
            },
            "kind": "voronoi",
            "region_key": None,
        }
        for key, (x, y) in cells.items()
    }
    return build_districts(
        _document(rows),
        terrain=_SyntheticTerrain(),
        index=ReferenceIndex.build(),
    )


class SyntheticConsumerEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_a_new_district_is_discovered_and_lights_without_registration(self):
        before = _synthetic_districts({"alpha_seed": (120, 140)})
        after = _synthetic_districts(
            {"alpha_seed": (120, 140), "beta_seed": (300, 200)}
        )
        self.assertEqual(tuple(before.districts), ("alpha_seed",))
        self.assertEqual(tuple(after.districts), ("alpha_seed", "beta_seed"))
        self.assertEqual(after.diagnostics, ())
        beta = after.districts["beta_seed"]
        node_id = landmark_node_id(beta)
        self.assertEqual(
            node_id, encode_wild(wilderness_provider.WILDERNESS_NAME, 300, 200)
        )
        visit = NodeVisit(node_id, 1, 1)
        with mock.patch.object(map_districts, "_PUBLISHED", after):
            # Lighting reads the published snapshot by default: the new
            # declaration needs no code registration.
            self.assertEqual(
                lit_district_keys_from_visits([visit]), frozenset({"beta_seed"})
            )

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_an_authored_name_edit_reaches_presenters_without_changing_identity(self):
        baseline = map_districts.current()
        key = next(
            key
            for key, district in baseline.districts.items()
            if district.landmark.domain == "wilderness_cell"
        )
        cell = decode_node(landmark_node_id(baseline.districts[key]))
        area_cell = (cell["x"], cell["y"])
        self.assertEqual(district_partition.district_at(area_cell), key)
        before_signature = binding_signature()
        before_name = self._area_district_name(area_cell, baseline)

        rows = _rows()
        rows[key]["district_name_zh"] = f"{before_name}改名"
        edited = build_districts(
            _document(rows),
            terrain=production_terrain(),
            index=map_reference_index(),
        )
        self.assertNotEqual(edited.identity, baseline.identity)
        self.assertEqual(
            landmark_node_ids(edited.districts), landmark_node_ids(baseline.districts)
        )
        with mock.patch.object(map_districts, "_PUBLISHED", edited):
            self.assertNotEqual(binding_signature(), before_signature)
            self.assertEqual(
                self._area_district_name(area_cell, edited), f"{before_name}改名"
            )

    @staticmethod
    def _area_district_name(cell, snapshot):
        from web.webclient.presentation.area_map import _district_name

        with mock.patch.object(map_districts, "_PUBLISHED", snapshot):
            return _district_name(cell)

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_discovered_districts_seed_the_existing_partition_algorithm(self):
        # 180 km apart: the declared 100 km minimum holds, so the candidate is
        # diagnostic-free and publishable.
        snapshot = _synthetic_districts({"west_seed": (10, 10), "east_seed": (190, 10)})
        self.assertEqual(snapshot.diagnostics, ())
        size = 205
        with mock.patch.object(map_districts, "_PUBLISHED", snapshot):
            # The production input adapter reads the published district world:
            # no test-side seed construction and no registration.
            seeds = generator.district_seeds()
        self.assertEqual(
            {seed.key for seed in seeds}, set(snapshot.districts)
        )
        land = np.ones((size, size), dtype=bool)
        walkable = np.ones((size, size), dtype=bool)
        nation = np.zeros((size, size), dtype=np.uint8)
        nation[:, :101] = 1
        nation[:, 101:] = 2
        walkable[:, 100] = False
        region = np.full((size, size), 1, dtype=np.uint8)
        inp = PartitionInput(
            size,
            land,
            walkable,
            nation,
            ("altoria", "grandia"),
            region,
            ("plain",),
            seeds,
            source_signature="synthetic",
        )
        partition = compute_partition(inp)
        self.assertEqual(partition.keys, tuple(sorted(snapshot.districts)))
        self.assertTrue(np.all(partition.owner[land] > 0))
        self.assertEqual(partition.owner_at((10, 10)), "west_seed")
        self.assertEqual(partition.owner_at((190, 10)), "east_seed")
        # The blocked border column stays with the nearer same-nation seed and
        # no district owns land in both nations.
        self.assertEqual(partition.owner_at((100, 10)), "west_seed")
        for code, key in enumerate(partition.keys, start=1):
            with self.subTest(district=key):
                nations = np.unique(nation[partition.owner == code])
                self.assertEqual(nations.size, 1)


class WalkableComponentContractTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_index_membership_matches_the_shared_validity_rule(self):
        components = walkable_components()
        # A 37-cell lattice over the whole frame (about 5,300 cells, sea
        # included) plus every cell around each ford.
        cells = [
            (x, y)
            for y in range(0, wilderness_provider.WILDERNESS_MAX_Y + 1, 37)
            for x in range(0, wilderness_provider.WILDERNESS_MAX_X + 1, 37)
        ]
        for fords in geography.current().terrain.waterway_fords.values():
            for fx, fy in fords:
                cells += [
                    (fx + dx, fy + dy)
                    for dx in (-2, -1, 0, 1, 2)
                    for dy in (-2, -1, 0, 1, 2)
                ]
        for cell in cells:
            self.assertEqual(
                components.component(cell) is not None,
                wilderness_provider.is_valid_wilderness_cell(cell),
                cell,
            )

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_fords_join_the_banks_and_gateways_share_one_component(self):
        components = walkable_components()
        x = 830  # the principal border-river ford's column
        south = components.component((x, wilderness_provider.border_river_row(x) - 3))
        north = components.component((x, wilderness_provider.border_river_row(x) + 3))
        self.assertIsNotNone(south)
        self.assertEqual(south, north)
        approaches = {
            components.component(entry.approach_cell(gate))
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
        self.assertEqual(len(approaches), 1)
        self.assertNotIn(None, approaches)
