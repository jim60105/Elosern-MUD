"""Data-contract test: capital xymap data contract

Pins the capital's approved integer-metre node positions (world-map-scale
design §8), its fixed connected topology, anchor, options, authored exit
octants and physical route durations."""

from math import hypot

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTestCase

from world.maps.altoria_capital import PROTOTYPES, XYMAP_DATA
from world.maps.map_data import SETTLEMENT_GRAPHS

# The approved outdoor positions, keyed by their stable authored identity.
METER_COORDS = {
    "south_gate": (3050, 150),
    "quay": (1250, 760),
    "riverbank_road": (2150, 920),
    "south_avenue": (3140, 1050),
    "inn_lane": (3970, 1120),
    "bath_forecourt": (4830, 970),
    "old_wall_ruins": (2350, 1900),
    "north_avenue": (3350, 1980),
    "craft_alley": (1300, 2600),
    "market_street": (2420, 2700),
    "central_plaza": (3500, 2850),
    "guild_forecourt": (4380, 3000),
    "east_market": (5380, 2850),
    "east_gate": (6500, 3010),
    "training_ground": (2300, 3820),
    "holy_steps": (3480, 3700),
    "great_temple": (4560, 3920),
    "noble_quarter": (3500, 4850),
    "upper_gate": (4690, 5010),
    "academy": (5650, 5200),
    "palace_forecourt": (4500, 6350),
}

EXPECTED_COORDS = set(METER_COORDS.values())

GRID_KEYS = {
    METER_COORDS["south_gate"]: "南門",
    METER_COORDS["quay"]: "碼頭埠",
    METER_COORDS["riverbank_road"]: "河岸道",
    METER_COORDS["south_avenue"]: "南大道",
    METER_COORDS["inn_lane"]: "客棧巷",
    METER_COORDS["bath_forecourt"]: "浴場前",
    METER_COORDS["old_wall_ruins"]: "舊城牆遺跡",
    METER_COORDS["north_avenue"]: "大道北段",
    METER_COORDS["craft_alley"]: "工匠巷",
    METER_COORDS["market_street"]: "市場街",
    METER_COORDS["central_plaza"]: "中央廣場",
    METER_COORDS["guild_forecourt"]: "公會前",
    METER_COORDS["east_market"]: "東市",
    METER_COORDS["east_gate"]: "東門",
    METER_COORDS["training_ground"]: "校場外",
    METER_COORDS["holy_steps"]: "聖階",
    METER_COORDS["great_temple"]: "大神殿前",
    METER_COORDS["noble_quarter"]: "貴族區前",
    METER_COORDS["upper_gate"]: "上城門",
    METER_COORDS["academy"]: "學院前",
    METER_COORDS["palace_forecourt"]: "王宮前庭",
}


def _edge(source, destination):
    return frozenset((METER_COORDS[source], METER_COORDS[destination]))


# The authored undirected edge set. Pinning it is what keeps the teardrop's
# diagonals and terrace links from being silently rewired by a data edit.
EXPECTED_LINKS = {
    _edge("palace_forecourt", "upper_gate"),
    _edge("noble_quarter", "upper_gate"),
    _edge("upper_gate", "academy"),
    _edge("holy_steps", "noble_quarter"),
    _edge("great_temple", "upper_gate"),
    _edge("training_ground", "holy_steps"),
    _edge("holy_steps", "great_temple"),
    _edge("craft_alley", "training_ground"),  # diagonal: the apprentices' path
    _edge("great_temple", "east_market"),  # diagonal: the pilgrims' slope
    _edge("craft_alley", "market_street"),
    _edge("market_street", "central_plaza"),
    _edge("central_plaza", "guild_forecourt"),
    _edge("guild_forecourt", "east_market"),
    _edge("east_market", "east_gate"),
    _edge("old_wall_ruins", "market_street"),
    _edge("north_avenue", "central_plaza"),
    _edge("old_wall_ruins", "north_avenue"),
    _edge("guild_forecourt", "great_temple"),
    _edge("quay", "riverbank_road"),
    _edge("riverbank_road", "south_avenue"),
    _edge("south_avenue", "inn_lane"),
    _edge("inn_lane", "bath_forecourt"),
    _edge("riverbank_road", "old_wall_ruins"),
    _edge("south_avenue", "north_avenue"),
    _edge("south_gate", "south_avenue"),
    _edge("central_plaza", "holy_steps"),
}

EXPECTED_DIAGONALS = {
    _edge("craft_alley", "training_ground"),
    _edge("great_temple", "east_market"),
}


class AltoriaCapitalMapTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.graph = SETTLEMENT_GRAPHS["capital_altoria"]

    def _links(self):
        return {
            frozenset((edge.source.coordinate, edge.destination.coordinate))
            for edge in self.graph.edges
        }

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_declaration_yields_exactly_the_twenty_one_meter_coordinates(self):
        self.assertEqual(
            {node.coordinate for node in self.graph.nodes.values()}, EXPECTED_COORDS
        )
        for identity, coordinate in METER_COORDS.items():
            self.assertEqual(self.graph.node(identity).coordinate, coordinate)

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
    def test_twenty_six_links_form_six_cycles_not_a_tree(self):
        edges = self._links()
        self.assertEqual(len(self.graph.nodes), 21)
        self.assertEqual(len(edges), 26)
        self.assertEqual(edges, EXPECTED_LINKS)
        # E - V + 1 == 6 for a connected graph: six more edges than a tree.
        self.assertEqual(len(edges) - len(self.graph.nodes) + 1, 6)
        # Authored diagonals are the four compass-octant directions that
        # change both axes; metre offsets alone make every street oblique.
        diagonal_directions = {"ne", "nw", "se", "sw"}
        diagonals = {
            frozenset((edge.source.coordinate, edge.destination.coordinate))
            for edge in self.graph.edges
            if edge.direction in diagonal_directions
        }
        self.assertEqual(diagonals, EXPECTED_DIAGONALS)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
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

    @covers_requirement(
        "sample-city-altoria::exactly-one-room-is-the-anchorroom-at-the-central-plaza"
    )
    def test_only_central_plaza_is_an_anchor_room(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                if coordinate == METER_COORDS["central_plaza"]:
                    self.assertEqual(prototype["prototype_parent"], "anchor_room")
                    self.assertEqual(prototype["anchor_key"], "capital_altoria")
                else:
                    self.assertEqual(prototype["prototype_parent"], "grid_room")
                self.assertEqual(prototype["key"], GRID_KEYS[coordinate])

    @covers_requirement(
        "sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology"
    )
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
        self.assertEqual(self.graph.options["map_visual_range"], visual_range)
        self.assertEqual(len(self.graph.nodes), 21)
        self.assertEqual(len(self._links()), 26)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-declared-intra-city-exits-spawn-as-costedxyzexit"
    )
    def test_the_declaration_carries_the_costed_exit_override(self):
        wildcard = XYMAP_DATA["prototypes"].get(("*", "*", "*"))
        self.assertIsNotNone(wildcard)
        self.assertEqual(wildcard["prototype_parent"], "xyz_exit")
        self.assertEqual(wildcard["typeclass"], "typeclasses.exits.CostedXYZExit")
        self.assertEqual(self.graph.exit_prototype["typeclass"],
                         "typeclasses.exits.CostedXYZExit")

    def test_no_building_interiors_in_descriptions(self):
        for coordinate, prototype in PROTOTYPES.items():
            with self.subTest(coordinate=coordinate):
                self.assertNotIn("interior", prototype["desc"].lower())
                self.assertNotIn("inside", prototype["desc"].lower())

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
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
        # Unequal segment lengths are real: no uniform lattice step survives.
        self.assertGreater(len({round(edge.length, 6) for edge in self.graph.edges}), 1)

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_healthy_baseline_routes_take_about_thirty_seven_and_ninety_four_minutes(self):
        from world.rules.travel_cost import distance_traversal_cost

        def total(start, end):
            route = self.graph.route(start, end)
            return sum(edge.length for edge in route)

        plaza = distance_traversal_cost(
            total("south_gate", "central_plaza"), "settlement", [_Probe()]
        )
        palace = distance_traversal_cost(
            total("south_gate", "palace_forecourt"), "settlement", [_Probe()]
        )
        self.assertEqual(plaza.seconds, 2193)
        self.assertEqual(palace.seconds, 5618)

    @covers_requirement("movement-cost-charging::physical-gate-approaches-are-charged-exactly-once")
    def test_gate_approach_segments_pin_their_absolute_meter_endpoints(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_destination import gate_approach_distance_m
        from world.rules.travel_cost import distance_traversal_cost

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        # 南門: gate local (3050,150) -> absolute (860050,1077800); approach
        # cell (860,1077) center (860500,1077500): hypot(450, 300).
        south = gate_approach_distance_m(entry, entry.gate_for("n"))
        self.assertAlmostEqual(south, hypot(450, 300), places=6)
        # 東門: gate local (6500,3010) -> absolute (863500,1080660); approach
        # cell (864,1080) center (864500,1080500): hypot(1000, 160).
        east = gate_approach_distance_m(entry, entry.gate_for("w"))
        self.assertAlmostEqual(east, hypot(1000, 160), places=6)
        # One authored segment, charged in either direction at 1.25 m/s.
        self.assertEqual(distance_traversal_cost(south, "settlement", [_Probe()]).seconds, 433)
        self.assertEqual(distance_traversal_cost(east, "settlement", [_Probe()]).seconds, 811)


class _Probe:
    """An uninitialized body: the base speed, no fatigue attributes."""
