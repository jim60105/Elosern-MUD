"""Data-contract test: village ciaran settlement document contract

Establishes the mechanisms the village's authored settlement document must
satisfy: a connected branching tree in its own metre frame with one anchor, the
costed exit prototype on every directed road, physical lengths from the authored
metres, the concealed entrance slot and Traditional Chinese prose that never
reads as a walled town. Shipped coordinates and route durations are not pinned;
the one-time conversion comparison was the evidence for their preservation.
"""

from math import hypot

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTestCase

from world.maps.map_data import settlement_graph
from world.maps.static_references import settlement_node_xyz
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()

MAP_ID = "village_ciaran"

# The village reads as a concealed forest settlement, not a town: none of the
# keys or descriptions may name wall, gate, guard, marketplace or any signed
# commercial premises.
FORBIDDEN_TEXT = ("wall", "gate", "guard", "marketplace", "shop", "store", "城牆", "城門", "衛兵", "市集", "市場", "店")


def _current_document():
    from world.maps.map_data import current

    return current().settlements[MAP_ID]


def _undirected_edges(graph):
    """Every link seen once: frozensets of endpoint coordinates."""
    return {
        frozenset((edge.source.coordinate, edge.destination.coordinate))
        for edge in graph.edges
    }


class VillageCiaranMapTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.document = _current_document()
        self.graph = settlement_graph(MAP_ID)

    @covers_requirement(
        "village-ciaran-map::ciaran-uses-metric-skylit-underground-geography"
    )
    def test_document_nodes_are_the_graph_nodes_without_omission_or_duplicate(self):
        declared = {node.node_id: node for node in self.document.nodes.values()}
        self.assertEqual(set(declared), set(self.graph.nodes))
        for node_id, declaration in declared.items():
            with self.subTest(node=node_id):
                node = self.graph.node(node_id)
                self.assertEqual(node.coordinate, declaration.coordinate)
                self.assertEqual(
                    node.prototype["prototype_parent"], declaration.prototype_parent
                )
                self.assertEqual(node.prototype["key"], declaration.key)
                self.assertEqual(node.prototype["desc"], declaration.desc)
        self.assertEqual(
            len({node.coordinate for node in declared.values()}), len(declared)
        )

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_path_exists_between_every_pair_of_coordinates(self):
        for start in self.graph.nodes:
            for end in self.graph.nodes:
                with self.subTest(start=start, end=end):
                    self.assertIsNotNone(self.graph.route(start, end))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_the_declared_links_form_a_tree(self):
        edges = _undirected_edges(self.graph)
        # Connected (proven by the finite route matrix) with exactly one fewer
        # link than nodes: no cycle, so the village stays a tree as it grows.
        self.assertEqual(len(edges), len(self.graph.nodes) - 1)
        self.assertEqual(len(edges), len(self.document.roads) // 2)
        # Every authored road appears as exactly one directed edge.
        self.assertEqual(len(self.graph.edges), len(self.document.roads))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_removing_any_link_disconnects_the_map(self):
        # The tree property's other half: no link is redundant, so no pair of
        # nodes has two routes — the no-crossroads rule at graph scale.
        edges = _undirected_edges(self.graph)
        nodes = {node.coordinate for node in self.graph.nodes.values()}
        adjacency = {}
        for edge in edges:
            first, second = tuple(edge)
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        start = next(iter(nodes))
        for removed in edges:
            with self.subTest(link=tuple(sorted(removed))):
                seen = {start}
                stack = [start]
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
    def test_exactly_one_anchor_node_binds_the_location(self):
        anchors = [
            node
            for node in self.document.nodes.values()
            if node.prototype_parent == "anchor_room"
        ]
        self.assertEqual(len(anchors), 1)
        anchor = anchors[0]
        self.assertEqual(anchor.anchor_key, self.document.location_ref)
        # The frame is derived: the unique anchor_room *is* the local anchor.
        self.assertEqual(self.document.local_anchor_m, anchor.coordinate)
        self.assertEqual(
            [node.node_id for node in self.graph.nodes.values() if node.is_anchor],
            [anchor.node_id],
        )
        for node in self.document.nodes.values():
            if node.node_id != anchor.node_id:
                self.assertEqual(node.prototype_parent, "grid_room")
                self.assertIsNone(node.anchor_key)

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_the_village_occupies_a_coordinate_space_of_its_own(self):
        # A coordinate from one settlement's frame never resolves in another:
        # shortest paths stay closed over their own map.
        other = settlement_graph("capital_altoria")
        village_coords = {node.coordinate for node in self.graph.nodes.values()}
        other_coords = {node.coordinate for node in other.nodes.values()}
        self.assertFalse(village_coords & other_coords)
        for coordinate in village_coords:
            self.assertIsNone(other.node_at(coordinate))
        for coordinate in other_coords:
            self.assertIsNone(self.graph.node_at(coordinate))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-declared-intra-city-exits-spawn-as-costedxyzexit"
    )
    def test_village_movement_uses_the_costed_exit_override(self):
        prototype = dict(self.document.exit_prototype)
        self.assertEqual(prototype["prototype_parent"], "xyz_exit")
        self.assertEqual(prototype["typeclass"], "typeclasses.exits.CostedXYZExit")
        self.assertEqual(dict(self.graph.exit_prototype), prototype)

    @covers_requirement(
        "village-ciaran-map::ciaran-uses-metric-skylit-underground-geography"
    )
    def test_route_cost_is_linear_in_the_authored_metres(self):
        from world.rules.travel_cost import distance_traversal_cost

        def cost(metres):
            return distance_traversal_cost(metres, "settlement", [_Probe()]).seconds

        # The village charges at the same baseline speed as capital streets:
        # the charge is linear in distance, not per grid cell.
        self.assertEqual(cost(2000), 2 * cost(1000))

    @covers_requirement(
        "village-ciaran-map::ciaran-uses-metric-skylit-underground-geography"
    )
    def test_every_segment_length_is_its_meter_endpoint_distance(self):
        for edge in self.graph.edges:
            with self.subTest(road=edge.road.road_id):
                self.assertAlmostEqual(
                    edge.length,
                    hypot(
                        edge.destination.x - edge.source.x,
                        edge.destination.y - edge.source.y,
                    ),
                    places=6,
                )
        self.assertGreater(len({round(edge.length, 6) for edge in self.graph.edges}), 1)

    @covers_requirement(
        "village-ciaran-map::the-village-has-exactly-one-concealed-entrance"
    )
    def test_the_entrance_does_not_read_as_a_gate(self):
        entrance = self.document.nodes[
            self.document.city_gate.node
        ]
        text = f"{entrance.key} {entrance.desc}".lower()
        for forbidden in ("wall", "gate", "guard", "城牆", "城門", "衛兵"):
            self.assertNotIn(forbidden, text)

    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    def test_the_declared_entrance_is_the_city_gate_registry_slot(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.city_gates import CITY_GATE_REGISTRY

        row = CITY_GATE_REGISTRY[MAP_ID]
        self.assertEqual(settlement_node_xyz(row.gate)[2], MAP_ID)
        self.assertEqual(
            row.gate,
            WILDERNESS_ENTRY_REGISTRY[self.document.location_ref]
            .gate_for("n")
            .destination,
        )
        self.assertEqual(row.exit_key, self.document.city_gate.exit_key)

    def test_no_wall_gate_guard_or_marketplace_in_village_text(self):
        for node in self.document.nodes.values():
            text = f"{node.key} {node.desc}".lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{node.node_id}: {forbidden!r}")

    def test_room_keys_and_descriptions_are_traditional_chinese(self):
        # The spec requires the village's authored prose to be Traditional
        # Chinese prose — every node's key and description is prose a villager
        # would speak, not an English placeholder left behind.
        for node in self.document.nodes.values():
            for text, minimum in ((node.key, 2), (node.desc, 4)):
                with self.subTest(node=node.node_id):
                    han = sum("\u4e00" <= char <= "\u9fff" for char in text)
                    self.assertGreaterEqual(han, minimum, text)
                    ascii_words = [
                        word for word in text.split() if word.isascii() and word.isalpha()
                    ]
                    self.assertEqual(ascii_words, [], text)


class _Probe:
    """An uninitialized body: the base speed, no fatigue attributes."""
