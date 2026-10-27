"""Data-contract test: shipped map-district landmarks against the authored continent

The registry's districts and landmarks are shipped content, so this module
names them: the production registry validates against the live terrain,
settlement graphs and gateways; the deep forest is the single region district
with its heart near the north coast; the full authored roster stays within
its 110-130 range with one-to-one identities, declared spacing, resolvable
and reachable landmarks and no landmark on a hidden place (without echoing
every name); every landmark is spelt exactly as the map-knowledge writer
records it; and the walkable-component index the
reachability rule reads agrees with the shared wilderness validity rule.
Mechanism rules are covered with synthetic fixtures in ``test_map_districts``.
"""

import dataclasses
import math
import re
import unittest
from collections import Counter

from tools.spec_traceability import covers_requirement
from world.lore.anchors import (
    ANCHOR_GEOGRAPHY_REGISTRY,
    ANCHOR_REGISTRY,
    AnchorKind,
    world_position_m,
)
from world.lore.map_districts import (
    MAP_DISTRICT_REGISTRY,
    MIN_VORONOI_SPACING_KM,
    MapDistrict,
    MapDistrictError,
    cell_of_position,
    production_terrain,
    validate_map_districts,
)
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from elosern_map_core.geometry import cell_center_m
from elosern_map_core.terrain import ridge_center_x

from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.maps.map_data import settlement_graph
from world.maps.wilderness_provider import (
    TERRAIN,
    WATERWAY_FORDS,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    border_river_row,
    forest_edge_row,
    is_valid_wilderness_cell,
    nominal_nation_for_coordinates,
    region_for_coordinates,
)
from world.maps.wilderness_reachability import walkable_components
from world.rules.map_knowledge import decode_node, encode_grid, encode_wild


class ShippedDistrictContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.terrain = production_terrain()

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_shipped_registry_validates_against_the_live_continent(self):
        self.assertIsNone(validate_map_districts(MAP_DISTRICT_REGISTRY, self.terrain))

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_live_terrain_rejects_sea_river_footprint_and_absent_nodes(self):
        river_cell = (900, 1042)  # capital river water, not a ford
        footprint_cell = next(iter(WILDERNESS_ENTRY_REGISTRY["capital_altoria"].footprint_cells))
        faulty = {
            "sea_probe": MapDistrict("sea_probe", "海測區", "海測碑", "wild:elosern:20:20", "voronoi"),
            "river_probe": MapDistrict(
                "river_probe", "河測區", "河測碑", encode_wild("elosern", *river_cell), "voronoi"
            ),
            "wall_probe": MapDistrict(
                "wall_probe", "城測區", "城測碑", encode_wild("elosern", *footprint_cell), "voronoi"
            ),
            "ghost_probe": MapDistrict(
                "ghost_probe", "幽測區", "幽測碑", "grid:capital_altoria:1:1", "voronoi"
            ),
        }
        with self.assertRaises(MapDistrictError) as caught:
            validate_map_districts(faulty, self.terrain)
        problems = "\n".join(caught.exception.problems)
        self.assertIn("sea_probe: landmark 'wild:elosern:20:20' lies in the sea", problems)
        self.assertIn("river_probe: landmark", problems)
        self.assertIn("lies on blocked terrain", problems.split("river_probe:")[1])
        self.assertIn("wall_probe: landmark", problems)
        self.assertIn("lies on blocked terrain", problems.split("wall_probe:")[1])
        self.assertIn("ghost_probe: landmark 'grid:capital_altoria:1:1' is not an existing grid node", problems)

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_deep_forest_is_one_region_district_lit_at_its_heart(self):
        regions = [d for d in MAP_DISTRICT_REGISTRY.values() if d.kind == "region"]
        self.assertEqual([d.region_key for d in regions], ["north_deep_forest"])
        forest = regions[0]
        self.assertEqual(forest.landmark_node, encode_wild("elosern", 1250, 2420))
        # One district covers both nominal claims: no per-nation duplicate.
        self.assertEqual(
            WILDERNESS_REGION_REGISTRY["north_deep_forest"].nominal_nation_keys,
            ("grandia", "valhalla"),
        )
        self.assertEqual(region_for_coordinates(1250, 2420), "north_deep_forest")
        # Roughly 500 km north of the meandering forest edge.
        self.assertTrue(450 <= 2420 - forest_edge_row(1250) <= 550, forest_edge_row(1250))
        # Every other district is a Voronoi seed outside the forest.
        for district in MAP_DISTRICT_REGISTRY.values():
            if district is not forest:
                self.assertEqual(district.kind, "voronoi", district.key)
                self.assertIsNone(district.region_key, district.key)

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_landmarks_are_spelt_as_the_knowledge_writer_records_them(self):
        for district in MAP_DISTRICT_REGISTRY.values():
            with self.subTest(district=district.key):
                parts = decode_node(district.landmark_node)
                if parts["prefix"] == "wild":
                    rebuilt = encode_wild(parts["name"], parts["x"], parts["y"])
                else:
                    self.assertEqual(parts["prefix"], "grid")
                    graph = settlement_graph(parts["z_map_key"])
                    self.assertIsNotNone(graph.node_at((parts["x"], parts["y"])))
                    rebuilt = encode_grid(parts["z_map_key"], parts["x"], parts["y"])
                self.assertEqual(rebuilt, district.landmark_node)

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_seeds_cover_every_nation_outside_the_forest_in_one_metre_frame(self):
        nations = set()
        for district in MAP_DISTRICT_REGISTRY.values():
            if district.kind != "voronoi":
                continue
            parts = decode_node(district.landmark_node)
            if parts["prefix"] == "wild":
                cell = (parts["x"], parts["y"])
            else:
                cell = cell_of_position(
                    self.terrain.grid_site(parts["z_map_key"], (parts["x"], parts["y"])).position_m
                )
            nations.add(nominal_nation_for_coordinates(*cell))
        self.assertEqual(nations, {"altoria", "grandia", "valhalla"})
        # A grid landmark and a wilderness cell share the absolute metre frame:
        # Altoria's plaza is the centre of its anchor cell.
        plaza = self.terrain.grid_site("capital_altoria", (3500, 2850))
        anchor_cell = ANCHOR_GEOGRAPHY_REGISTRY["capital_altoria"].cell
        self.assertEqual(plaza.position_m, cell_center_m(anchor_cell))
        self.assertEqual(plaza.position_m, world_position_m("capital_altoria", (3500, 2850)))
        self.assertTrue(plaza.reachable)

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_grid_landmark_reachability_needs_a_routed_gateway(self):
        from unittest import mock

        from world.lore import wilderness_entry

        plaza = ("capital_altoria", (3500, 2850))
        self.assertTrue(self.terrain.grid_site(*plaza).reachable)
        # Without the capital's gates no gateway routes to the plaza: the same
        # node still resolves, but it is no longer reachable.
        others = {
            key: entry
            for key, entry in WILDERNESS_ENTRY_REGISTRY.items()
            if all(gate.z_map_key != "capital_altoria" for gate in entry.gates)
        }
        with mock.patch.object(wilderness_entry, "WILDERNESS_ENTRY_REGISTRY", others):
            site = production_terrain().grid_site(*plaza)
        self.assertIsNotNone(site)
        self.assertFalse(site.reachable)

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_wilderness_landmarks_share_the_gateway_component(self):
        components = walkable_components()
        gateway = {
            components.component(entry.approach_cell(gate))
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
        for district in MAP_DISTRICT_REGISTRY.values():
            parts = decode_node(district.landmark_node)
            if parts["prefix"] == "wild":
                with self.subTest(district=district.key):
                    self.assertIn(components.component((parts["x"], parts["y"])), gateway)
        # A cell across the summit ridge away from any pass is valid ground of
        # the same component (joined through the passes), while the ridge wall
        # cell itself belongs to none.
        wall = (ridge_center_x(TERRAIN, 1200), 1200)
        self.assertIsNone(components.component(wall))
        self.assertEqual(
            components.component((wall[0] - 3, 1200)), components.component((wall[0] + 3, 1200))
        )

    def _continental_position(self, district):
        parts = decode_node(district.landmark_node)
        if parts["prefix"] == "wild":
            return cell_center_m((parts["x"], parts["y"]))
        return self.terrain.grid_site(parts["z_map_key"], (parts["x"], parts["y"])).position_m

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_roster_is_complete_and_one_to_one(self):
        districts = list(MAP_DISTRICT_REGISTRY.values())
        self.assertTrue(110 <= len(districts) <= 130, len(districts))
        # One landmark per district, and no node, district name or landmark
        # name shared between two districts.
        for field in ("key", "landmark_node", "district_name_zh", "landmark_name_zh"):
            values = [getattr(district, field) for district in districts]
            self.assertEqual(len(set(values)), len(values), field)
        for district in districts:
            with self.subTest(district=district.key):
                self.assertNotEqual(district.district_name_zh, district.landmark_name_zh)
                for name in (district.district_name_zh, district.landmark_name_zh):
                    # Authored lore, never a Latin-letter or numbered placeholder.
                    self.assertIsNone(re.search(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ]", name), name)
                    self.assertIsNone(re.search(r"第?[一二三四五六七八九十]+[號号区區]$", name), name)
        # The deep forest stays the one region district; every nominal nation
        # carries Voronoi seeds roughly in proportion to its walkable land.
        nations = Counter(
            nominal_nation_for_coordinates(*cell_of_position(self._continental_position(d)))
            for d in districts
            if d.kind == "voronoi"
        )
        self.assertEqual(sum(nations.values()), len(districts) - 1)
        # Lower bounds only: Valhalla holds about a fifth of that land, the
        # other two nations most of the rest.
        self.assertGreaterEqual(nations["valhalla"], 15, nations)
        self.assertGreaterEqual(nations["altoria"], 35, nations)
        self.assertGreaterEqual(nations["grandia"], 35, nations)

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_every_pair_of_voronoi_landmarks_keeps_the_declared_spacing(self):
        positions = [
            (district.key, self._continental_position(district))
            for district in MAP_DISTRICT_REGISTRY.values()
            if district.kind == "voronoi"
        ]
        minimum_m = MIN_VORONOI_SPACING_KM * 1000
        closest = min(
            (math.dist(a, b), first, second)
            for index, (first, a) in enumerate(positions)
            for second, b in positions[index + 1 :]
        )
        self.assertGreaterEqual(closest[0], minimum_m, closest)

    @covers_requirement(
        "map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster"
    )
    def test_every_landmark_resolves_and_is_reachable_on_the_live_continent(self):
        components = walkable_components()
        gateway = {
            components.component(entry.approach_cell(gate))
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
        for district in MAP_DISTRICT_REGISTRY.values():
            parts = decode_node(district.landmark_node)
            with self.subTest(district=district.key):
                if parts["prefix"] == "grid":
                    site = self.terrain.grid_site(parts["z_map_key"], (parts["x"], parts["y"]))
                    self.assertIsNotNone(site)
                    self.assertTrue(site.reachable)
                    continue
                cell = (parts["x"], parts["y"])
                self.assertTrue(is_valid_wilderness_cell(cell))
                self.assertIn(components.component(cell), gateway)

    def test_no_landmark_marks_a_hidden_place(self):
        # Elven villages and dungeons appear only after a visit, so no
        # landmark (whose name a lit district shows) sits on their cell.
        hidden = {
            ANCHOR_GEOGRAPHY_REGISTRY[key].cell
            for key, anchor in ANCHOR_REGISTRY.items()
            if anchor.kind in (AnchorKind.ELVEN_VILLAGE, AnchorKind.DUNGEON)
        }
        self.assertTrue(hidden)
        for district in MAP_DISTRICT_REGISTRY.values():
            with self.subTest(district=district.key):
                position = self._continental_position(district)
                self.assertNotIn(cell_of_position(position), hidden)

    def test_registry_entries_are_frozen(self):
        district = next(iter(MAP_DISTRICT_REGISTRY.values()))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            district.landmark_node = "wild:elosern:0:0"


class WalkableComponentContractTests(unittest.TestCase):
    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_index_membership_matches_the_shared_validity_rule(self):
        components = walkable_components()
        # A 37-cell lattice over the whole frame (about 5,300 cells, sea
        # included) plus every cell around each ford.
        cells = [
            (x, y)
            for y in range(0, WILDERNESS_MAX_Y + 1, 37)
            for x in range(0, WILDERNESS_MAX_X + 1, 37)
        ]
        for fords in WATERWAY_FORDS.values():
            for fx, fy in fords:
                cells += [(fx + dx, fy + dy) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)]
        for cell in cells:
            self.assertEqual(
                components.component(cell) is not None, is_valid_wilderness_cell(cell), cell
            )

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_fords_join_the_banks_and_gateways_share_one_component(self):
        components = walkable_components()
        x = 830  # the principal border-river ford's column
        south = components.component((x, border_river_row(x) - 3))
        north = components.component((x, border_river_row(x) + 3))
        self.assertIsNotNone(south)
        self.assertEqual(south, north)
        approaches = {
            components.component(entry.approach_cell(gate))
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
        self.assertEqual(len(approaches), 1)
        self.assertNotIn(None, approaches)
