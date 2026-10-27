"""Data-contract test: capital map document contract

Establishes the mechanisms the capital's authored settlement document must
satisfy: its nodes and directed roads are exactly the validated sparse graph,
the topology is connected with authored cycles and diagonals, one anchor binds
the location, the exit prototype and bounded options are carried, and physical
lengths and route costs come from the authored metres. Shipped prose, coordinate
tables and balance magnitudes are deliberately not pinned here; the one-time
conversion comparison was the evidence for their preservation.
"""

from math import hypot

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTestCase

from elosern_map_core.geometry import cell_center_m, local_to_world_m
from world.maps.map_data import settlement_graph
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()

MAP_ID = "capital_altoria"


def _current_document():
    from world.maps.map_data import current

    return current().settlements[MAP_ID]


class AltoriaCapitalMapTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.document = _current_document()
        self.graph = settlement_graph(MAP_ID)

    def _links(self):
        return {
            frozenset((edge.source.coordinate, edge.destination.coordinate))
            for edge in self.graph.edges
        }

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_document_nodes_are_the_graph_nodes_without_omission_or_duplicate(self):
        declared = {
            node.node_id: node for node in self.document.nodes.values()
        }
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
                    node.prototype.get("anchor_key"), declaration.anchor_key
                )
        self.assertEqual(
            len({node.coordinate for node in declared.values()}), len(declared)
        )

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
    def test_every_declared_road_is_one_directed_edge(self):
        declared = {
            (road.source, road.destination, road.direction)
            for road in self.document.roads
        }
        edges = {
            (edge.source.node_id, edge.destination.node_id, edge.direction)
            for edge in self.graph.edges
        }
        self.assertEqual(edges, declared)
        self.assertEqual(len(self.graph.edges), len(self.document.roads))

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
    def test_path_exists_between_every_pair_of_coordinates(self):
        for start in self.graph.nodes:
            for end in self.graph.nodes:
                with self.subTest(start=start, end=end):
                    self.assertIsNotNone(self.graph.route(start, end))

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
    def test_the_topology_is_not_a_tree(self):
        edges = self._links()
        nodes = {node.coordinate for node in self.graph.nodes.values()}
        # A connected graph with at least one cycle has more edges than V - 1.
        self.assertGreater(len(edges), len(nodes) - 1)
        # Authored diagonals exist as real travel directions, not metre deltas.
        diagonal_directions = {"ne", "nw", "se", "sw"}
        self.assertTrue(
            [edge for edge in self.graph.edges if edge.direction in diagonal_directions]
        )

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
    def test_some_pair_of_rooms_has_two_distinct_routes(self):
        edges = self._links()
        nodes = {node.coordinate for node in self.graph.nodes.values()}
        for edge in edges:
            (x1, y1), (x2, y2) = tuple(edge)
            adjacency = {coordinate: set() for coordinate in nodes}
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
            if seen == nodes:
                return  # this edge lies on a cycle: two routes between its ends
        self.fail("the link graph is a tree; no pair of rooms has two routes")

    @covers_requirement(
        "sample-city-altoria::exactly-one-room-is-the-anchorroom-at-the-central-plaza"
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
        self.assertEqual(self.document.binding.local_anchor_m, anchor.coordinate)
        self.assertEqual(
            [node.node_id for node in self.graph.nodes.values() if node.is_anchor],
            [anchor.node_id],
        )
        from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY

        placement = ANCHOR_PLACEMENT_REGISTRY[self.document.location_ref]
        self.assertEqual(placement.node.object_id, anchor.node_id)
        self.assertEqual(placement.node.map_id, MAP_ID)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
    def test_options_are_the_closed_visual_range_tokens(self):
        options = dict(self.document.options)
        self.assertEqual(set(options), {"map_visual_range", "map_mode"})
        visual_range = options["map_visual_range"]
        self.assertIsInstance(visual_range, int)
        self.assertIsNot(visual_range, True)
        self.assertGreaterEqual(visual_range, 1)
        self.assertLessEqual(visual_range, 8)
        self.assertIn(options["map_mode"], ("nodes", "scan"))
        # The graph the adapter reads carries exactly those options, and adding
        # them changes neither the node set nor the road set.
        self.assertEqual(dict(self.graph.options), options)
        self.assertEqual(
            {node.node_id for node in self.graph.nodes.values()},
            set(self.document.nodes),
        )
        self.assertEqual(len(self.graph.edges), len(self.document.roads))

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-declared-intra-city-exits-spawn-as-costedxyzexit"
    )
    def test_the_document_carries_the_costed_exit_prototype(self):
        prototype = dict(self.document.exit_prototype)
        self.assertEqual(prototype["prototype_parent"], "xyz_exit")
        self.assertEqual(prototype["typeclass"], "typeclasses.exits.CostedXYZExit")
        self.assertEqual(dict(self.graph.exit_prototype), prototype)
        # Coverage is per directed road, diagonals included: every edge spawns
        # through the same prototype, so no cardinal-only rule can exist.
        diagonals = [
            edge
            for edge in self.graph.edges
            if edge.direction in {"ne", "nw", "se", "sw"}
        ]
        self.assertTrue(diagonals)

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_every_segment_length_is_its_metre_endpoint_distance(self):
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
        # Unequal segment lengths are real: no uniform lattice step survives.
        self.assertGreater(len({round(edge.length, 6) for edge in self.graph.edges}), 1)

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_route_cost_is_additive_over_the_authored_metres(self):
        from world.rules.travel_cost import distance_traversal_cost

        def cost(metres):
            return distance_traversal_cost(metres, "settlement", [_Probe()]).seconds

        # Linear in distance at the one declared settlement pace: a doubled
        # length costs exactly twice as much (detects a per-cell or per-edge
        # charge that ignores the authored metres).
        self.assertEqual(cost(2000), 2 * cost(1000))
        # A route's charge is the sum of its own edge charges, up to the
        # integer-second rounding each charge applies.
        route = self.graph.route("south_gate", "central_plaza")
        self.assertTrue(route)
        self.assertLessEqual(
            abs(
                cost(sum(edge.length for edge in route))
                - sum(cost(edge.length) for edge in route)
            ),
            len(route),
        )

    @covers_requirement("movement-cost-charging::physical-gate-approaches-are-charged-exactly-once")
    def test_gate_approach_distance_uses_the_authored_binding(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_destination import gate_approach_distance_m

        entry = WILDERNESS_ENTRY_REGISTRY[self.document.location_ref]
        for gate in entry.gates:
            with self.subTest(direction=gate.return_direction):
                node = self.document.nodes[gate.destination.object_id]
                world = local_to_world_m(
                    self.document.binding.anchor_cell,
                    self.document.binding.local_anchor_m,
                    node.coordinate,
                )
                approach = cell_center_m(entry.approach_cell(gate))
                self.assertAlmostEqual(
                    gate_approach_distance_m(entry, gate),
                    hypot(world[0] - approach[0], world[1] - approach[1]),
                    places=6,
                )


class _Probe:
    """An uninitialized body: the base speed, no fatigue attributes."""
