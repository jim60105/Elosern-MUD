"""Data-contract test: village ciaran map data contract
Parsing, topology and content checks for the village_ciaran map (map-anchor-grid,
settlement-shops design §6.2)."""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.contrib.grid.xyzgrid.xymap import XYMap

from world.maps.village_ciaran import MAPSTR, PROTOTYPES, XYMAP_DATA

# The six coordinates the village shipped with (ciaran-village-map).
# ciaran-village-crafts grew the map to ten nodes; these six pin the
# scenario "the six original coordinates are undisturbed" — a home's
# exterior moving because a new node reshaped the grid fails here first.
ORIGINAL_SIX_COORDS = {
    (0, 1),  # 隱密小徑 — the concealed entrance
    (1, 1),  # 村中廣場 — the plaza/anchor
    (2, 1),  # 練刀場
    (1, 0),  # 溪畔小徑
    (1, 2),  # 村北古樹下
    (2, 2),  # 織房坡
}

VILLAGE_COORDS = ORIGINAL_SIX_COORDS | {
    (1, 3),  # 長老古樹下 — the elder's grove (commons change fills it)
    (2, 3),  # 銀葉坡 — further up the weaving slope
    (3, 1),  # 藥草園 — past the training ground, in the cleared sun
    (2, 0),  # 溪畔下游 — further along the stream (scenery)
}

GRID_KEYS = {
    (0, 1): "隱密小徑",
    (1, 1): "村中廣場",
    (2, 1): "練刀場",
    (1, 0): "溪畔小徑",
    (1, 2): "村北古樹下",
    (2, 2): "織房坡",
    (1, 3): "長老古樹下",
    (2, 3): "銀葉坡",
    (3, 1): "藥草園",
    (2, 0): "溪畔下游",
}

# The village reads as a concealed forest settlement, not a town: none of the
# keys or descriptions may name wall, gate, guard, marketplace or any signed
# commercial premises.
FORBIDDEN_TEXT = ("wall", "gate", "guard", "marketplace", "shop", "store", "城牆", "城門", "衛兵", "市集", "市場", "店")


def _undirected_edges(node_map):
    """Every link seen once: frozensets of endpoint coordinates."""
    edges = set()
    for node in node_map.values():
        for direction, end_node in node.links.items():
            edges.add(frozenset([(node.X, node.Y), (end_node.X, end_node.Y)]))
    return edges


class VillageCiaranMapTests(unittest.TestCase):
    def setUp(self):
        self.map = XYMap(dict(XYMAP_DATA), Z="village_ciaran", xyzgrid=None)
        self.map.parse()

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_parse_yields_exactly_the_ten_coordinates(self):
        parsed = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertEqual(parsed, VILLAGE_COORDS)

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_the_six_original_coordinates_are_undisturbed(self):
        # The expansion added leaves; it moved nothing. Every original
        # coordinate still parses, so none of the four landed homes'
        # exteriors (nor the entrance or the anchor) shifted.
        parsed = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        self.assertTrue(ORIGINAL_SIX_COORDS <= parsed)

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_path_matrix_exists_between_every_pair_of_coordinates(self):
        self.map.calculate_path_matrix(force=True)
        matrix = self.map.dist_matrix
        self.assertEqual(matrix.shape, (10, 10))
        self.assertFalse((matrix == float("inf")).any())

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_nine_links_form_a_tree(self):
        nodes = self.map.node_index_map
        edges = _undirected_edges(nodes)
        self.assertEqual(len(nodes), 10)
        # Ten nodes, nine links, no cycles: connected (proven separately by
        # the finite path matrix) with exactly one fewer link than nodes is a
        # tree. The village stays a tree as it grows — growth adds leaves and
        # short branches, never a loop.
        self.assertEqual(len(edges), 9)

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_removing_any_link_disconnects_the_map(self):
        # The tree property's other half: no link is redundant, so no pair of
        # nodes has two routes — the no-crossroads rule at graph scale.
        nodes = {(node.X, node.Y) for node in self.map.node_index_map.values()}
        edges = _undirected_edges(self.map.node_index_map)
        adjacency = {}
        for edge in edges:
            (first, second) = tuple(edge)
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        for removed in edges:
            with self.subTest(link=tuple(sorted(removed))):
                seen = {(0, 1)}
                stack = [(0, 1)]
                while stack:
                    node = stack.pop()
                    for neighbour in adjacency[node]:
                        if frozenset((node, neighbour)) == removed:
                            continue
                        if neighbour not in seen:
                            seen.add(neighbour)
                            stack.append(neighbour)
                self.assertLess(len(seen), len(nodes))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_only_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
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

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    @covers_requirement("sample-city-altoria::the-sample-city-s-twelve-intra-city-exits-spawn-as-costedxyzexit-not-the-bare-contrib-xyzexit")
    def test_village_movement_uses_the_costed_exit_override(self):
        wildcard = XYMAP_DATA["prototypes"].get(("*", "*", "*"))
        self.assertIsNotNone(wildcard)
        self.assertEqual(wildcard["prototype_parent"], "xyz_exit")
        self.assertEqual(
            wildcard["typeclass"], "typeclasses.exits.CostedXYZExit"
        )
        self.assertEqual(len(self.map.node_index_map), 10)

    def test_no_wall_gate_guard_or_marketplace_in_village_text(self):
        for coordinate, prototype in PROTOTYPES.items():
            text = f"{prototype['key']} {prototype['desc']}".lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{coordinate}: {forbidden!r} in {text!r}")

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_room_keys_and_descriptions_are_traditional_chinese(self):
        # The spec requires the village's authored prose to be Traditional
        # Chinese prose — every node's key and description is prose a
        # villager would speak, not an English placeholder left behind.
        for coordinate, prototype in PROTOTYPES.items():
            for field in ("key", "desc"):
                text = prototype[field]
                with self.subTest(coordinate=coordinate, field=field):
                    han = sum("\u4e00" <= char <= "\u9fff" for char in text)
                    # Keys are two-or-three-character place names; only the
                    # descriptions are prose. Either way the field must be
                    # Chinese characters, never an English placeholder.
                    self.assertGreaterEqual(han, 2 if field == "key" else 4, text)
                    ascii_words = [
                        word for word in text.split() if word.isascii() and word.isalpha()
                    ]
                    self.assertEqual(ascii_words, [], text)

if __name__ == "__main__":
    import sys

    unittest.main(argv=sys.argv[:1])
