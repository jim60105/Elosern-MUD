"""The on-demand ``area_map`` presenter and the ``map.view`` action (grid area)."""

from collections import deque
from types import SimpleNamespace
from unittest import mock
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation.map_quest_destinations import DestinationEvidence, DestinationFamily, QuestDestination
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import encode_grid, parse_knowledge, record_arrival
from ..test_local_map._support import EAST_GATE_XYZ, SOUTH_GATE_XYZ, _T_MAP_KEY, _T_PLAZA_XYZ, _live, _t_grid_id


from ._support import _render, _by_id, _edge_set, _js_accepts

class GridAreaTests(EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        declared = (EAST_GATE_XYZ[2],)
        sync_test_settlements(declared)
        sync_test_wilderness(declared)

    def setUp(self):
        get_world_clock()
        self.start = create_object(Room, key="t_start")
        self.char = create_object(PlayerCharacter, key="t_char", location=self.start)
        self.graph = _live("world.maps.map_data", "settlement_graph")(_T_MAP_KEY)
        projection = self.graph.display_projection()
        self.adjacency = {}
        for node in projection.node_index_map.values():
            node_id = encode_grid(_T_MAP_KEY, node.X, node.Y)
            self.adjacency.setdefault(node_id, set())
            for end in node.links.values():
                other = encode_grid(_T_MAP_KEY, end.X, end.Y)
                self.adjacency[node_id].add(other)
                self.adjacency.setdefault(other, set()).add(node_id)

    def _goto(self, node_id):
        _, _, x, y = node_id.split(":")
        room = GridRoom.objects.filter_xyz(xyz=(int(x), int(y), _T_MAP_KEY)).first()
        self.assertIsNotNone(room, node_id)
        self.char.location = room
        record_arrival(self.char)

    def _path(self, start, hops):
        """A shortest path of exactly ``hops`` steps from ``start``."""
        parents = {start: None}
        queue = deque([(start, 0)])
        while queue:
            node, depth = queue.popleft()
            if depth == hops:
                path = [node]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                return list(reversed(path))
            for other in sorted(self.adjacency[node]):
                if other not in parents:
                    parents[other] = node
                    queue.append((other, depth + 1))
        self.fail(f"no {hops}-hop path in the shipped settlement graph")

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_whole_visited_graph_beyond_the_minimap_window(self):
        plaza = _t_grid_id(*_T_PLAZA_XYZ[:2])
        path = self._path(plaza, 3)
        for node_id in path:
            self._goto(node_id)
        self._goto(plaza)  # stand back at the start, three hops away
        payload = _render(self.char)
        nodes = _by_id(payload)
        visited = set(path)
        expected = visited | {other for node in visited for other in self.adjacency[node]}
        self.assertEqual(set(nodes), expected)
        self.assertEqual(payload["layer"], "grid")
        self.assertEqual(payload["map_id"], _T_MAP_KEY)
        self.assertEqual(payload["frame"], {"key": _T_MAP_KEY, "unit": "m"})
        self.assertEqual(payload["current_node"], plaza)
        self.assertEqual(nodes[plaza]["visibility"], "current")
        self.assertEqual(nodes[path[-1]]["visibility"], "visited")
        for node_id, node in nodes.items():
            with self.subTest(node=node_id):
                sparse = self.graph.node(self.graph.node_at((node["x"], node["y"])).node_id)
                self.assertEqual(encode_grid(_T_MAP_KEY, sparse.x, sparse.y), node_id)
                self.assertIsInstance(node["x"], int)
                if node_id not in visited:
                    self.assertEqual(node["visibility"], "seen")
        for edge in _edge_set(payload):
            with self.subTest(edge=sorted(edge)):
                self.assertTrue(edge & visited, "a road needs at least one visited end")
                a, b = tuple(edge)
                self.assertIn(b, self.adjacency[a])
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_moves_exist_only_on_current_adjacent_exits(self):
        plaza = _t_grid_id(*_T_PLAZA_XYZ[:2])
        path = self._path(plaza, 2)
        for node_id in path:
            self._goto(node_id)
        current = path[-1]
        payload = _render(self.char)
        actionable = {node["id"] for node in payload["nodes"] if node["action"] is not None}
        self.assertTrue(actionable)
        self.assertLessEqual(actionable, self.adjacency[current])
        room = self.char.location
        exit_refs = {str(int(exit_obj.id)) for exit_obj in room.exits}
        for node in payload["nodes"]:
            if node["action"] is not None:
                self.assertEqual(node["action"]["destination"], node["id"])
                self.assertIn(node["action"]["exit_ref"], exit_refs)

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_gate_rooms_carry_the_minimap_gateway_metadata(self):
        gate = _t_grid_id(*SOUTH_GATE_XYZ[:2])
        self._goto(gate)
        payload = _render(self.char)
        nodes = _by_id(payload)
        self.assertIsNotNone(nodes[gate]["gateway"])
        self.assertEqual(set(nodes[gate]["gateway"]), {"leads_to"})
        # Wilderness gate exits never become nodes on the grid layer.
        self.assertTrue(all(node_id.startswith(f"grid:{_T_MAP_KEY}:") for node_id in nodes))
        ordinary = [node for node_id, node in nodes.items() if node_id != gate and node["gateway"] is None]
        self.assertTrue(ordinary)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_reading_the_map_changes_no_gameplay_state(self):
        self._goto(_t_grid_id(*_T_PLAZA_XYZ[:2]))
        clock = get_world_clock()
        before = (self.char.location, parse_knowledge(self.char), clock.tick, self.char.attributes.get("quest_log"))
        _render(self.char)
        _render(self.char)
        after = (self.char.location, parse_knowledge(self.char), get_world_clock().tick, self.char.attributes.get("quest_log"))
        self.assertEqual(before, after)

    @covers_requirement(
        "webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere"
    )
    def test_markers_name_same_map_nodes_and_bear_elsewhere(self):
        plaza = _t_grid_id(*_T_PLAZA_XYZ[:2])
        self._goto(plaza)
        hidden = next(node_id for node_id in self.adjacency if node_id not in _by_id(_render(self.char)))
        destinations = (
            QuestDestination(
                "t_q1", "t_def", DestinationFamily.GRID, (0, 0), _T_MAP_KEY, hidden,
                DestinationEvidence.LOCATION,
            ),
            QuestDestination(
                "t_q2", "t_def", DestinationFamily.MONSTER_SITE, (900, 900),
                "t_other", "wild:t:1:1", DestinationEvidence.LOCATION,
            ),
        )
        definitions = {"t_def": SimpleNamespace(display_name="合成委託")}
        with mock.patch(
            "web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
            return_value=(destinations, frozenset({"t_q2"})),
        ), mock.patch(
            "web.webclient.presentation.map_quest_destinations.actor_world_cell", return_value=(900, 800)
        ), mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", definitions):
            payload = _render(self.char)
        markers = {marker["id"]: marker for marker in payload["quest_markers"]}
        # Tracked first.
        self.assertEqual([marker["id"] for marker in payload["quest_markers"]], ["t_q2", "t_q1"])
        # A fogged same-map destination is identified but stays unpresented.
        self.assertEqual(markers["t_q1"]["destination"], {"kind": "node", "node_id": hidden})
        self.assertNotIn(hidden, _by_id(payload))
        self.assertEqual(
            markers["t_q2"]["destination"], {"kind": "bearing", "bearing_deg": 0.0, "distance_km": 100.0}
        )
        self.assertTrue(markers["t_q2"]["tracked"])

    @covers_requirement(
        "webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere"
    )
    def test_a_habitat_destination_is_guidance_not_an_entity(self):
        plaza = _t_grid_id(*_T_PLAZA_XYZ[:2])
        self._goto(plaza)
        destination = QuestDestination(
            "q_habitat", "t_def", DestinationFamily.SPECIES_HUNT,
            (900, 900), None, None, DestinationEvidence.HABITAT,
        )
        definitions = {"t_def": SimpleNamespace(display_name="合成委託")}
        with mock.patch(
            "web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
            return_value=((destination,), frozenset()),
        ), mock.patch(
            "web.webclient.presentation.map_quest_destinations.actor_world_cell",
            return_value=(900, 800),
        ), mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", definitions):
            payload = _render(self.char)
        marker = next(
            row for row in payload["quest_markers"] if row["id"] == "q_habitat"
        )
        # An empty habitat still points somewhere: the authored region, never a
        # fabricated target or an entity observation.
        self.assertEqual(
            marker["destination"],
            {"kind": "bearing", "bearing_deg": 0.0, "distance_km": 100.0},
        )
        self.assertEqual(
            set(marker), {"id", "title", "tracked", "destination"}
        )
