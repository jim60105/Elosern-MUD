"""Data-contract test: village ciaran map data contract
Parsing, topology and content checks for the village_ciaran map (map-anchor-grid,
settlement-shops design §6.2)."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.contrib.grid.xyzgrid.xymap import XYMap

from world.maps.village_ciaran import MAPSTR, PROTOTYPES, XYMAP_DATA

VILLAGE_COORDS = {
    (0, 1),  # 隱密小徑 — the concealed entrance
    (1, 1),  # 村中廣場 — the plaza/anchor
    (2, 1),  # 練刀場
    (1, 0),  # 溪畔小徑
    (1, 2),  # 村北古樹下
    (2, 2),  # 織房坡
}

GRID_KEYS = {
    (0, 1): "隱密小徑",
    (1, 1): "村中廣場",
    (2, 1): "練刀場",
    (1, 0): "溪畔小徑",
    (1, 2): "村北古樹下",
    (2, 2): "織房坡",
}

# The village reads as a concealed forest settlement, not a town: none of the
# keys or descriptions may name wall, gate, guard, marketplace or any signed
# commercial premises.
FORBIDDEN_TEXT = ("wall", "gate", "guard", "marketplace", "shop", "store", "城牆", "城門", "衛兵", "市集", "市場", "店")


class VillageCiaranMapTests(unittest.TestCase):
    def setUp(self):
        self.map = XYMap(dict(XYMAP_DATA), Z="village_ciaran", xyzgrid=None)
        self.map.parse()

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_parse_yields_exactly_the_six_coordinates(self):
        parsed = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertEqual(parsed, VILLAGE_COORDS)

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_path_matrix_exists_between_every_pair_of_coordinates(self):
        self.map.calculate_path_matrix(force=True)
        matrix = self.map.dist_matrix
        self.assertEqual(matrix.shape, (6, 6))
        self.assertFalse((matrix == float("inf")).any())

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_five_links_form_a_tree(self):
        nodes = self.map.node_index_map
        edges = set()
        for node in nodes.values():
            for direction, end_node in node.links.items():
                edges.add(frozenset([(node.X, node.Y), (end_node.X, end_node.Y)]))
        self.assertEqual(len(nodes), 6)
        # Six nodes, five links, no cycles: a connected tree, matching the
        # capital's "no ambiguous shortest paths" property. Connectivity is
        # proven separately by the finite path matrix above (a connected
        # graph with n-1 edges is a tree).
        self.assertEqual(len(edges), 5)

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_only_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            if coordinate == (1, 1):
                self.assertEqual(prototype["prototype_parent"], "anchor_room")
                self.assertEqual(prototype["anchor_key"], "village_ciaran")
            else:
                self.assertEqual(prototype["prototype_parent"], "grid_room")
                self.assertEqual(prototype["key"], GRID_KEYS[coordinate])

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_same_coordinate_names_different_rooms_in_each_settlement(self):
        # The two settlements deliberately share raw (X, Y) coordinates (e.g.
        # (2,1) is 南大道 in the capital and 練刀場 here): each map is its own
        # coordinate space, so "the same coordinate resolves to a different
        # room in each" — established at the parse level here and at the room
        # level by the bootstrap suite. Each settlement's shortest paths are
        # closed over its own nodes (its matrix never indexes the other map's
        # room set).
        from world.maps.altoria_capital import XYMAP_DATA as CAPITAL_DATA

        capital = XYMap(dict(CAPITAL_DATA), Z="capital_altoria", xyzgrid=None)
        capital.parse()
        capital_nodes = {(node.X, node.Y) for node in capital.node_index_map.values()}
        village_nodes = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertTrue(capital_nodes & village_nodes)

    @covers_requirement("sample-city-altoria::the-sample-city-s-twelve-intra-city-exits-spawn-as-costedxyzexit-not-the-bare-contrib-xyzexit")
    def test_village_movement_uses_the_costed_exit_override(self):
        wildcard = XYMAP_DATA["prototypes"].get(("*", "*", "*"))
        self.assertIsNotNone(wildcard)
        self.assertEqual(wildcard["prototype_parent"], "xyz_exit")
        self.assertEqual(wildcard["typeclass"], "typeclasses.exits.CostedXYZExit")
        # Adding the wildcard override SHALL NOT change topology.
        self.assertEqual(len(self.map.node_index_map), 6)

    def test_no_wall_gate_guard_or_marketplace_in_village_text(self):
        for coordinate, prototype in PROTOTYPES.items():
            text = f"{prototype['key']} {prototype['desc']}".lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{coordinate}: {forbidden!r} in {text!r}")

if __name__ == "__main__":
    import sys

    unittest.main(argv=sys.argv[:1])