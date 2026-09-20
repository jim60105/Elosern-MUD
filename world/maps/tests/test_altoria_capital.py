"""Data-contract test: capital xymap data contract
Parsing and topology checks for the capital_altoria sample city."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.contrib.grid.xyzgrid.xymap import XYMap

from world.maps.altoria_capital import PROTOTYPES, XYMAP_DATA

EXPECTED_COORDS = {
    (3, 0),
    (1, 1),
    (2, 1),
    (3, 1),
    (4, 1),
    (5, 1),
    (2, 2),
    (3, 2),
    (1, 3),
    (2, 3),
    (3, 3),
    (4, 3),
    (5, 3),
    (6, 3),
    (2, 4),
    (3, 4),
    (4, 4),
    (3, 5),
    (4, 5),
    (5, 5),
    (4, 6),
}

GRID_KEYS = {
    (3, 0): "南門",
    (1, 1): "碼頭埠",
    (2, 1): "河岸道",
    (3, 1): "南大道",
    (4, 1): "客棧巷",
    (5, 1): "浴場前",
    (2, 2): "舊城牆遺跡",
    (3, 2): "大道北段",
    (1, 3): "工匠巷",
    (2, 3): "市場街",
    (3, 3): "中央廣場",
    (4, 3): "公會前",
    (5, 3): "東市",
    (6, 3): "東門",
    (2, 4): "校場外",
    (3, 4): "聖階",
    (4, 4): "大神殿前",
    (3, 5): "貴族區前",
    (4, 5): "上城門",
    (5, 5): "學院前",
    (4, 6): "王宮前庭",
}

# The authored undirected edge set. The aggregate invariants (21 nodes, 26
# edges, six cycles, two diagonals) admit many valid graphs; pinning the exact
# edge set is what keeps the teardrop's diagonals and terrace links from being
# silently rewired by a whitespace shift in MAPSTR.
EXPECTED_LINKS = {
    frozenset({(4, 6), (4, 5)}),
    frozenset({(3, 5), (4, 5)}),
    frozenset({(4, 5), (5, 5)}),
    frozenset({(3, 4), (3, 5)}),
    frozenset({(4, 4), (4, 5)}),
    frozenset({(2, 4), (3, 4)}),
    frozenset({(3, 4), (4, 4)}),
    frozenset({(1, 3), (2, 4)}),  # diagonal: the apprentices' path
    frozenset({(4, 4), (5, 3)}),  # diagonal: the pilgrims' slope
    frozenset({(1, 3), (2, 3)}),
    frozenset({(2, 3), (3, 3)}),
    frozenset({(3, 3), (4, 3)}),
    frozenset({(4, 3), (5, 3)}),
    frozenset({(5, 3), (6, 3)}),
    frozenset({(2, 2), (2, 3)}),
    frozenset({(3, 2), (3, 3)}),
    frozenset({(2, 2), (3, 2)}),
    frozenset({(4, 3), (4, 4)}),  # the guild square climbs to the cathedral
    frozenset({(1, 1), (2, 1)}),
    frozenset({(2, 1), (3, 1)}),
    frozenset({(3, 1), (4, 1)}),
    frozenset({(4, 1), (5, 1)}),
    frozenset({(2, 1), (2, 2)}),
    frozenset({(3, 1), (3, 2)}),
    frozenset({(3, 1), (3, 0)}),
    frozenset({(3, 3), (3, 4)}),
}

# The two worn shortcuts are load-bearing world-building; assert their exact
# endpoints, not just their count.
EXPECTED_DIAGONALS = {
    frozenset({(1, 3), (2, 4)}),
    frozenset({(4, 4), (5, 3)}),
}


class AltoriaCapitalMapTests(unittest.TestCase):
    def setUp(self):
        self.map = XYMap(dict(XYMAP_DATA), Z="capital_altoria", xyzgrid=None)
        self.map.parse()

    def _links(self):
        edges = set()
        for node in self.map.node_index_map.values():
            for neighbor in node.links.values():
                edges.add(frozenset(((node.X, node.Y), (neighbor.X, neighbor.Y))))
        return edges

    def test_parse_yields_exactly_the_twenty_one_coordinates(self):
        parsed = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertEqual(parsed, EXPECTED_COORDS)

    def test_path_matrix_exists_between_every_pair_of_coordinates(self):
        self.map.calculate_path_matrix(force=True)
        self.assertEqual(self.map.dist_matrix.shape, (21, 21))
        matrix = self.map.dist_matrix
        self.assertFalse((matrix == float("inf")).any())

    def test_twenty_six_links_form_six_cycles_not_a_tree(self):
        # The tree pin was right for scaffolding and wrong for a city: a
        # capital where every route is the only route is a corridor. The
        # replacement is a specific cycle count, so the map stays exactly
        # verifiable (design: six cycles, not "some").
        nodes = self.map.node_index_map
        edges = self._links()
        self.assertEqual(len(nodes), 21)
        self.assertEqual(len(edges), 26)
        self.assertEqual(edges, EXPECTED_LINKS)
        # E - V + 1 == 6 for a connected graph: six more edges than a tree.
        self.assertEqual(len(edges) - len(nodes) + 1, 6)
        diagonals = {
            edge
            for edge in edges
            if len({p[0] for p in edge}) == 2 and len({p[1] for p in edge}) == 2
        }
        self.assertEqual(diagonals, EXPECTED_DIAGONALS)

    def test_some_pair_of_rooms_has_two_distinct_routes(self):
        # A cycle exists iff some pair of rooms has two routes: walk an edge,
        # delete it, and the graph stays connected.
        edges = self._links()
        self.assertTrue(edges)
        for edge in edges:
            (x1, y1), (x2, y2) = tuple(edge)
            adjacency = {coordinate: set() for coordinate in EXPECTED_COORDS}
            for other in edges:
                if other == edge:
                    continue
                (ax, ay), (bx, by) = tuple(other)
                adjacency[(ax, ay)].add((bx, by))
                adjacency[(bx, by)].add((ax, ay))
            seen = {(x1, y1)}
            queue = [(x1, y1)]
            while queue:
                for nxt in adjacency[queue.pop()]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            if seen == EXPECTED_COORDS:
                return  # this edge lies on a cycle: two routes between its ends
        self.fail("the link graph is a tree; no pair of rooms has two routes")

    @covers_requirement("sample-city-altoria::exactly-one-room-is-the-anchorroom-at-the-central-plaza")
    def test_only_central_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                if coordinate == (3, 3):
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
        self.assertEqual(len(self.map.node_index_map), 21)
        self.assertEqual(len(self._links()), 26)

    def test_no_building_interiors_in_descriptions(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                self.assertNotIn("interior", prototype["desc"].lower())
                self.assertNotIn("inside", prototype["desc"].lower())
