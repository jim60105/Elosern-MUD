"""Parsing and topology checks for the capital_altoria sample city."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.contrib.grid.xyzgrid.xymap import XYMap

from world.maps.altoria_capital import MAPSTR, PROTOTYPES, XYMAP_DATA

EXPECTED_COORDS = {
    (2, 0),
    (1, 1),
    (2, 1),
    (3, 1),
    (0, 2),
    (1, 2),
    (2, 2),
    (3, 2),
    (4, 2),
    (1, 3),
    (2, 3),
    (3, 3),
    (2, 4),
}

GRID_KEYS = {
    (2, 0): "南門",
    (2, 1): "南大道",
    (1, 1): "旅店外",
    (3, 1): "冒險者公會外",
    (0, 2): "鐵匠鋪外",
    (1, 2): "市場街",
    (3, 2): "神殿街",
    (4, 2): "光明神殿外",
    (2, 3): "北大道",
    (1, 3): "貴族區門口",
    (3, 3): "城牆哨塔",
    (2, 4): "北門",
}


class AltoriaCapitalMapTests(unittest.TestCase):
    def setUp(self):
        self.map = XYMap(dict(XYMAP_DATA), Z="capital_altoria", xyzgrid=None)
        self.map.parse()

    def test_parse_yields_exactly_the_thirteen_coordinates(self):
        parsed = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertEqual(parsed, EXPECTED_COORDS)

    def test_path_matrix_exists_between_every_pair_of_coordinates(self):
        self.map.calculate_path_matrix(force=True)
        self.assertEqual(self.map.dist_matrix.shape, (13, 13))
        matrix = self.map.dist_matrix
        self.assertFalse((matrix == float("inf")).any())

    def test_twelve_links_form_a_tree(self):
        nodes = self.map.node_index_map
        edges = set()
        for node in nodes.values():
            for neighbor in node.links.values():
                edge = frozenset(((node.X, node.Y), (neighbor.X, neighbor.Y)))
                edges.add(edge)
        self.assertEqual(len(nodes), 13)
        self.assertEqual(len(edges), 12)

    @covers_requirement("sample-city-altoria::exactly-one-room-is-the-anchorroom-at-the-central-plaza")
    def test_only_central_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                if coordinate == (2, 2):
                    self.assertEqual(prototype["prototype_parent"], "anchor_room")
                    self.assertEqual(prototype["anchor_key"], "capital_altoria")
                else:
                    self.assertEqual(prototype["prototype_parent"], "grid_room")
                    self.assertEqual(prototype["key"], GRID_KEYS[coordinate])

    @covers_requirement("sample-city-altoria::the-sample-city-has-exactly-thirteen-rooms-in-a-fixed-connected-topology")
    def test_options_declare_bounded_visual_range(self):
        options = XYMAP_DATA.get("options", {})
        self.assertIn("map_visual_range", options)
        self.assertIn("map_mode", options)
        visual_range = options["map_visual_range"]
        self.assertIsInstance(visual_range, int)
        self.assertIsNot(visual_range, True)
        self.assertGreaterEqual(visual_range, 1)
        self.assertLessEqual(visual_range, 8)
        self.assertIn(options["map_mode"], ("nodes", "scan"))
        # Adding options SHALL NOT change topology.
        self.assertEqual(len(self.map.node_index_map), 13)
        self.assertEqual(len(self._links()), 12)

    def _links(self):
        edges = set()
        for node in self.map.node_index_map.values():
            for neighbor in node.links.values():
                edges.add(frozenset(((node.X, node.Y), (neighbor.X, neighbor.Y))))
        return edges

    def test_no_building_interiors_in_descriptions(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                self.assertNotIn("interior", prototype["desc"].lower())
                self.assertNotIn("inside", prototype["desc"].lower())
