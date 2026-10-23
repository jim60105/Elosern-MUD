"""Map-district registry validation over a synthetic terrain (map-districts).

The terrain, settlement and districts here are file-local fixtures: a 400 by
400 frame whose western strip is sea, with a blocked wall column, a northern
``fen`` region, an unreachable eastern island and one synthetic settlement.
Shipped geography is covered by ``test_map_district_content``.
"""

import dataclasses
import unittest

from tools.spec_traceability import covers_requirement
from world.lore.map_districts import (
    MIN_VORONOI_SPACING_KM,
    GridSite,
    MapDistrict,
    MapDistrictError,
    cell_of_position,
    validate_map_districts,
)

_WALL_X = 200
_FEN_Y = 300


class _Terrain:
    wilderness_name = "testland"
    max_cell = (399, 399)
    region_keys = frozenset({"plain", "fen"})

    #: Settlement nodes: (map, xy) -> site. The second is cut off from every
    #: gateway; the third sits in the western sea.
    grid_sites = {
        ("testtown", (40, 60)): GridSite(position_m=(150_200, 150_700), reachable=True),
        ("testtown", (41, 60)): GridSite(position_m=(151_000, 150_700), reachable=False),
        ("testtown", (42, 60)): GridSite(position_m=(4_000, 150_700), reachable=True),
    }

    def is_land(self, cell):
        return cell[0] >= 10

    def is_walkable(self, cell):
        return self.is_land(cell) and not (cell[0] == _WALL_X and cell[1] < _FEN_Y)

    def is_reachable(self, cell):
        return self.is_walkable(cell) and cell[0] < 380

    def region_of(self, cell):
        return "fen" if cell[1] >= _FEN_Y else "plain"

    def grid_site(self, map_key, xy):
        return self.grid_sites.get((map_key, tuple(xy)))


def _voronoi(key, x, y, name=None):
    return MapDistrict(key, f"{name or key}區", f"{name or key}碑", f"wild:testland:{x}:{y}", "voronoi")


def _registry(*districts):
    return {district.key: district for district in districts}


def _valid():
    return _registry(
        MapDistrict("fen_heart", "沼心區", "沼心碑", "wild:testland:250:350", "region", "fen"),
        _voronoi("west_seed", 50, 50),
        _voronoi("east_seed", 300, 50),
        MapDistrict("town_seed", "城區", "城碑", "grid:testtown:40:60", "voronoi"),
    )


class MapDistrictValidationTests(unittest.TestCase):
    def assertRejected(self, registry, *fragments):
        with self.assertRaises(MapDistrictError) as caught:
            validate_map_districts(registry, _Terrain())
        joined = "\n".join(caught.exception.problems)
        for fragment in fragments:
            self.assertIn(fragment, joined)
        return caught.exception.problems

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_a_valid_registry_with_every_kind_and_layer_passes(self):
        self.assertIsNone(validate_map_districts(_valid(), _Terrain()))
        fields = [field.name for field in dataclasses.fields(MapDistrict)]
        self.assertEqual(
            fields,
            ["key", "district_name_zh", "landmark_name_zh", "landmark_node", "kind", "region_key"],
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            _valid()["west_seed"].kind = "region"

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_sea_blocked_absent_and_unreachable_landmarks_are_named(self):
        registry = _valid() | _registry(
            _voronoi("sea_seed", 5, 150),
            _voronoi("wall_seed", _WALL_X, 150),
            _voronoi("island_seed", 390, 150),
            MapDistrict("ghost_seed", "幽區", "幽碑", "grid:testtown:9:9", "voronoi"),
            MapDistrict("cut_seed", "斷區", "斷碑", "grid:testtown:41:60", "voronoi"),
            MapDistrict("dock_seed", "港區", "港碑", "grid:testtown:42:60", "voronoi"),
        )
        problems = self.assertRejected(
            registry,
            "sea_seed: landmark 'wild:testland:5:150' lies in the sea",
            f"wall_seed: landmark 'wild:testland:{_WALL_X}:150' lies on blocked terrain",
            "island_seed: landmark 'wild:testland:390:150' is unreachable",
            "ghost_seed: landmark 'grid:testtown:9:9' is not an existing grid node",
            "cut_seed: landmark 'grid:testtown:41:60' is unreachable",
            "dock_seed: landmark 'grid:testtown:42:60' lies in the sea",
        )
        # Exactly the six faulty declarations are reported; the valid ones are not.
        self.assertEqual(len(problems), 6)
        for valid_key in _valid():
            self.assertFalse(any(p.startswith(f"{valid_key}:") for p in problems))

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_non_canonical_landmark_identities_are_rejected(self):
        for node in (
            "wild:testland:050:50",  # leading zero is not the canonical spelling
            "wild:otherland:50:50",  # not the registered wilderness
            "wild:testland:400:50",  # beyond the frame
            "wild:testland:-1:50",
            "room:12",  # interiors have no continental position
            "grid:testtown:40",
            "grid:testtown:40:60:0",
            "WILD:testland:50:50",
        ):
            with self.subTest(node=node):
                registry = {"odd_seed": MapDistrict("odd_seed", "異區", "異碑", node, "voronoi")}
                self.assertRejected(registry, "odd_seed: landmark_node")

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_duplicate_identities_are_rejected(self):
        twin_node = _voronoi("twin_node", 50, 50, name="雙")
        twin_names = MapDistrict("twin_names", "west_seed區", "west_seed碑", "wild:testland:150:150", "voronoi")
        second_fen = MapDistrict("fen_rim", "沼緣區", "沼緣碑", "wild:testland:100:390", "region", "fen")
        misfiled = {"stray_key": _voronoi("other_key", 50, 250)}
        self.assertRejected(
            _valid() | _registry(twin_node, twin_names, second_fen) | misfiled,
            "twin_node: duplicate landmark_node 'wild:testland:50:50' (also 'west_seed')",
            "twin_names: duplicate district_name_zh 'west_seed區' (also 'west_seed')",
            "twin_names: duplicate landmark_name_zh 'west_seed碑' (also 'west_seed')",
            "fen_rim: duplicate region_key 'fen' (also 'fen_heart')",
            "stray_key: registered under a different key than 'other_key'",
        )

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_kind_and_region_constraints(self):
        self.assertRejected(
            _registry(
                MapDistrict("odd_kind", "甲區", "甲碑", "wild:testland:50:50", "square"),
                MapDistrict("no_region", "乙區", "乙碑", "wild:testland:250:50", "region"),
                MapDistrict("bad_region", "丙區", "丙碑", "wild:testland:250:150", "region", "moor"),
                MapDistrict("loose_region", "丁區", "丁碑", "wild:testland:50:150", "voronoi", "plain"),
                MapDistrict("fen_heart", "沼心區", "沼心碑", "wild:testland:150:150", "region", "fen"),
                _voronoi("fen_seed", 50, 350),
            ),
            "odd_kind: kind 'square'",
            "no_region: region_key None is not a terrain region",
            "bad_region: region_key 'moor' is not a terrain region",
            "loose_region: a voronoi district declares no region_key",
            # A region landmark must lie in its own region...
            "fen_heart: landmark lies in region 'plain', not 'fen'",
            # ...and a Voronoi seed may not sit inside region-district land.
            "fen_seed: landmark lies inside region district territory 'fen'",
        )

    @covers_requirement("map-districts::every-map-district-has-one-canonical-reachable-landmark")
    def test_voronoi_spacing_is_the_single_declared_minimum(self):
        self.assertEqual(MIN_VORONOI_SPACING_KM, 100)
        # Cell centres 100 cells apart are exactly 100 km apart: allowed.
        self.assertIsNone(
            validate_map_districts(
                _registry(_voronoi("near_a", 50, 50), _voronoi("near_b", 150, 50)), _Terrain()
            )
        )
        # 99 cells apart is below the minimum, and the pair is named.
        self.assertRejected(
            _registry(_voronoi("near_a", 50, 50), _voronoi("near_b", 149, 50)),
            "near_a: landmark is 99.0 km from 'near_b', below the 100 km minimum spacing",
        )
        # A grid landmark is measured at its continental position: the town
        # node at (150.2 km, 150.7 km) is 0.36 km from the centre of cell (150, 150).
        self.assertRejected(
            _registry(
                MapDistrict("town_seed", "城區", "城碑", "grid:testtown:40:60", "voronoi"),
                _voronoi("by_town", 150, 150),
            ),
            "town_seed: landmark is 0.4 km from 'by_town'",
        )
        # Region districts are exempt: the forest heart may sit next to a seed.
        self.assertIsNone(
            validate_map_districts(
                _registry(
                    MapDistrict("fen_heart", "沼心區", "沼心碑", "wild:testland:150:300", "region", "fen"),
                    _voronoi("by_fen", 150, 299),
                ),
                _Terrain(),
            )
        )

    def test_cell_of_position_floors_metres_into_kilometre_cells(self):
        self.assertEqual(cell_of_position((150_999, 150_000)), (150, 150))
        self.assertEqual(cell_of_position((151_000, 149_999)), (151, 149))
