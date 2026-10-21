"""Data-contract test: village sparse map declaration.

Pins the village's approved integer-metre node positions (world-map-scale
design §9), its ten-node nine-edge tree, sole anchor, authored exit octants,
physical route duration and concealed-path prose."""

from math import hypot

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTestCase

from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.village_ciaran import PROTOTYPES, XYMAP_DATA

# The approved outdoor positions, keyed by their stable authored identity.
METER_COORDS = {
    "hidden_path": (35, 270),
    "village_plaza": (220, 305),
    "stream_path": (245, 135),
    "stream_bend": (430, 85),
    "training_clearing": (405, 335),
    "herb_garden": (590, 300),
    "old_tree_north": (200, 465),
    "elder_tree": (165, 650),
    "weaving_slope": (390, 495),
    "silver_leaf_slope": (440, 665),
}

VILLAGE_COORDS = set(METER_COORDS.values())

GRID_KEYS = {
    METER_COORDS["hidden_path"]: "隱密小徑",
    METER_COORDS["village_plaza"]: "村中廣場",
    METER_COORDS["stream_path"]: "溪畔小徑",
    METER_COORDS["stream_bend"]: "溪畔下游",
    METER_COORDS["training_clearing"]: "練刀場",
    METER_COORDS["herb_garden"]: "藥草園",
    METER_COORDS["old_tree_north"]: "村北古樹下",
    METER_COORDS["elder_tree"]: "長老古樹下",
    METER_COORDS["weaving_slope"]: "織房坡",
    METER_COORDS["silver_leaf_slope"]: "銀葉坡",
}

# The village reads as a concealed forest settlement, not a town: none of the
# keys or descriptions may name wall, gate, guard, marketplace or any signed
# commercial premises.
FORBIDDEN_TEXT = ("wall", "gate", "guard", "marketplace", "shop", "store", "城牆", "城門", "衛兵", "市集", "市場", "店")


def _undirected_edges(graph):
    """Every link seen once: frozensets of endpoint coordinates."""
    return {
        frozenset((edge.source.coordinate, edge.destination.coordinate))
        for edge in graph.edges
    }


class VillageCiaranMapTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.graph = SETTLEMENT_GRAPHS["village_ciaran"]

    @covers_requirement(
        "village-ciaran-map::ciaran-uses-metric-skylit-underground-geography"
    )
    def test_declaration_yields_exactly_the_ten_meter_coordinates(self):
        self.assertEqual(
            {node.coordinate for node in self.graph.nodes.values()}, VILLAGE_COORDS
        )
        for identity, coordinate in METER_COORDS.items():
            self.assertEqual(self.graph.node(identity).coordinate, coordinate)

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_the_six_original_coordinates_are_undisturbed(self):
        # The expansion added leaves; the original identities kept their
        # approved meter bindings, so no landed home's exterior moved.
        original = {
            METER_COORDS[key]
            for key in (
                "hidden_path",
                "village_plaza",
                "training_clearing",
                "stream_path",
                "old_tree_north",
                "weaving_slope",
            )
        }
        self.assertTrue(original <= {node.coordinate for node in self.graph.nodes.values()})

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
    def test_nine_links_form_a_tree(self):
        edges = _undirected_edges(self.graph)
        self.assertEqual(len(self.graph.nodes), 10)
        # Ten nodes, nine links, no cycles: connected (proven separately by
        # the finite route matrix) with exactly one fewer link than nodes.
        self.assertEqual(len(edges), 9)

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_removing_any_link_disconnects_the_map(self):
        # The tree property's other half: no link is redundant, so no pair of
        # nodes has two routes — the no-crossroads rule at graph scale.
        edges = _undirected_edges(self.graph)
        adjacency = {}
        for edge in edges:
            (first, second) = tuple(edge)
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        start = METER_COORDS["hidden_path"]
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
                self.assertLess(len(seen), len(VILLAGE_COORDS))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_only_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                if coordinate == METER_COORDS["village_plaza"]:
                    self.assertEqual(prototype["prototype_parent"], "anchor_room")
                    self.assertEqual(prototype["anchor_key"], "village_ciaran")
                else:
                    self.assertEqual(prototype["prototype_parent"], "grid_room")
                self.assertEqual(prototype["key"], GRID_KEYS[coordinate])

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    def test_the_village_occupies_a_coordinate_space_of_its_own(self):
        # The meter frames are disjoint, and a coordinate from one map never
        # resolves in the other: shortest paths stay closed over their map.
        capital = SETTLEMENT_GRAPHS["capital_altoria"]
        capital_coords = {node.coordinate for node in capital.nodes.values()}
        self.assertFalse(capital_coords & VILLAGE_COORDS)
        for coordinate in VILLAGE_COORDS:
            self.assertIsNone(capital.node_at(coordinate))
        for coordinate in capital_coords:
            self.assertIsNone(self.graph.node_at(coordinate))

    @covers_requirement(
        "village-ciaran-map::the-village-is-a-small-connected-grid-with-one-anchor"
    )
    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-twelve-intra-city-exits-spawn-as-costedxyzexit-not-the-bare-contrib-xyzexit"
    )
    def test_village_movement_uses_the_costed_exit_override(self):
        wildcard = XYMAP_DATA["prototypes"].get(("*", "*", "*"))
        self.assertIsNotNone(wildcard)
        self.assertEqual(wildcard["prototype_parent"], "xyz_exit")
        self.assertEqual(
            wildcard["typeclass"], "typeclasses.exits.CostedXYZExit"
        )
        self.assertEqual(len(self.graph.nodes), 10)

    @covers_requirement(
        "village-ciaran-map::ciaran-uses-metric-skylit-underground-geography"
    )
    def test_entrance_to_elder_route_takes_about_seven_minutes(self):
        from world.rules.travel_cost import distance_traversal_cost

        route = self.graph.route("hidden_path", "elder_tree")
        total = sum(edge.length for edge in route)
        self.assertEqual(
            distance_traversal_cost(total, "settlement", [_Probe()]).seconds, 431
        )

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
        entrance = PROTOTYPES[METER_COORDS["hidden_path"]]
        text = f"{entrance['key']} {entrance['desc']}".lower()
        for forbidden in ("wall", "gate", "guard", "城牆", "城門", "衛兵"):
            self.assertNotIn(forbidden, text)

    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    def test_the_declared_entrance_is_the_city_gate_registry_slot(self):
        from world.maps.city_gates import CITY_GATE_REGISTRY

        row = CITY_GATE_REGISTRY["village_ciaran"]
        self.assertEqual(row.gate_xyz, (*METER_COORDS["hidden_path"], "village_ciaran"))

    def test_no_wall_gate_guard_or_marketplace_in_village_text(self):
        for coordinate, prototype in PROTOTYPES.items():
            text = f"{prototype['key']} {prototype['desc']}".lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{coordinate}: {forbidden!r} in {text!r}")

    def test_room_keys_and_descriptions_are_traditional_chinese(self):
        # The spec requires the village's authored prose to be Traditional
        # Chinese prose — every node's key and description is prose a
        # villager would speak, not an English placeholder left behind.
        for coordinate, prototype in PROTOTYPES.items():
            for field in ("key", "desc"):
                text = prototype[field]
                with self.subTest(coordinate=coordinate, field=field):
                    han = sum("\u4e00" <= char <= "\u9fff" for char in text)
                    self.assertGreaterEqual(han, 2 if field == "key" else 4, text)
                    ascii_words = [
                        word for word in text.split() if word.isascii() and word.isalpha()
                    ]
                    self.assertEqual(ascii_words, [], text)


class _Probe:
    """An uninitialized body: the base speed, no fatigue attributes."""
