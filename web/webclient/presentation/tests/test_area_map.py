"""The on-demand ``area_map`` presenter and the ``map.view`` action.

publish-area-map-panel: whole-area fog of war on grid, instance, interior and
wilderness layers, gateway metadata, adjacent-only move descriptors, quest
markers, measured bounds, read-only behaviour, and on-demand publication
(movement and text refreshes never compute or push a map).

Settlement and wilderness cases run against the shipped synced maps through
the runtime probes in ``test_local_map._support`` (no catalog literal); room
graphs and the pure fog function use synthetic fixtures.
"""

from collections import deque
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.area_map import (
    UNEXPLORED_LABEL,
    area_map_presenter,
    bearing_and_distance,
    fog_of_war,
)

from world.tests.interior_fixture import (
    interior_document,
    interior_exterior,
    interior_room,
    published_interiors,
)
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.map_panels import (
    AREA_MAX_BYTES,
    AREA_MAX_EDGES,
    AREA_MAX_NODES,
    AREA_MAX_QUEST_MARKERS,
    WILDERNESS_WINDOW,
    validate_area_map,
)
from web.webclient.presentation.map_parts import decode_map_parts, encode_map_parts
from web.webclient.presentation.map_quest_destinations import DestinationFamily, QuestDestination
from web.webclient.presentation.protocol import ProtocolValidationError, json_byte_size
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    PresentationRegistry,
    PresenterSpec,
    build_production_registry,
)
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import encode_grid, encode_room, parse_knowledge, record_arrival

from .test_local_map._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _T_PLAZA_XYZ,
    _context,
    _live,
    _t_anchor_display,
    _t_grid_id,
    _t_region_display_for,
    _t_wild_id,
)

ROOT = Path(__file__).resolve().parents[4]
NODE_TEST = "web/static/webclient/js/tests/protocol_area_map.test.js"



def _render(actor):
    return area_map_presenter(_context(actor))


def _by_id(payload):
    return {node["id"]: node for node in payload["nodes"]}


def _edge_set(payload):
    return {frozenset((edge["source"], edge["destination"])) for edge in payload["edges"]}


def _js_accepts(payload) -> bool:
    script = (
        "const fs=require('node:fs');"
        "const P=require('./web/static/webclient/js/elosern/protocol.js');"
        "try{P.validateMapPanel('area_map',JSON.parse(fs.readFileSync(0,'utf8')));"
        "process.stdout.write('ok')}catch(e){process.stdout.write('no:'+e.message)}"
    )
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout == "ok"


# ---------------------------------------------------------------------------
# Pure fog of war.
# ---------------------------------------------------------------------------


def _undirected(pairs):
    adjacency = {}
    for a, b in pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    return adjacency


class FogOfWarTests(unittest.TestCase):
    """known = visited ∪ adjacent(visited); roads need a visited end."""

    # A line a-b-c-d-e-f with a side branch c-x-y.
    GRAPH = _undirected(
        [("t_a", "t_b"), ("t_b", "t_c"), ("t_c", "t_d"), ("t_d", "t_e"), ("t_e", "t_f"), ("t_c", "t_x"), ("t_x", "t_y")]
    )

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_whole_visited_graph_and_one_step_frontier(self):
        # Visited far beyond two hops from the current node.
        known, visited, edges = fog_of_war(self.GRAPH, {"t_a", "t_b", "t_c", "t_d", "t_e"}, "t_a")
        self.assertEqual(set(known), {"t_a", "t_b", "t_c", "t_d", "t_e", "t_f", "t_x"})
        self.assertEqual(visited, {"t_a", "t_b", "t_c", "t_d", "t_e"})
        self.assertNotIn("t_y", known, "an unseen deeper branch is never emitted")
        self.assertIn(("t_c", "t_x"), edges)
        self.assertIn(("t_e", "t_f"), edges)

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_seen_to_seen_roads_are_never_emitted(self):
        graph = _undirected([("t_a", "t_b"), ("t_a", "t_c"), ("t_b", "t_c")])
        known, _, edges = fog_of_war(graph, set(), "t_a")
        self.assertEqual(set(known), {"t_a", "t_b", "t_c"})
        self.assertEqual(set(edges), {("t_a", "t_b"), ("t_a", "t_c")})

    def test_current_counts_as_visited_and_foreign_visits_are_ignored(self):
        known, visited, _ = fog_of_war(self.GRAPH, {"t_elsewhere"}, "t_f")
        self.assertEqual(visited, {"t_f"})
        self.assertEqual(set(known), {"t_e", "t_f"})

    def test_edges_are_unique_unordered_pairs(self):
        _, _, edges = fog_of_war(self.GRAPH, set(self.GRAPH), "t_a")
        self.assertEqual(len(edges), len({frozenset(edge) for edge in edges}))
        self.assertEqual(len(edges), 7)


class BearingTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere"
    )
    def test_bearing_is_clockwise_from_north_and_wraps_after_rounding(self):
        self.assertEqual(bearing_and_distance((10, 10), (10, 20), 1), (0.0, 10.0))
        self.assertEqual(bearing_and_distance((10, 10), (20, 10), 1), (90.0, 10.0))
        self.assertEqual(bearing_and_distance((10, 10), (10, 0), 2), (180.0, 20.0))
        self.assertEqual(bearing_and_distance((10, 10), (0, 10), 1), (270.0, 10.0))
        # 359.97 degrees rounds to 360.0 and must wrap to 0.0.
        bearing, _ = bearing_and_distance((0, 0), (-1, 2000), 1)
        self.assertEqual(bearing, 0.0)
        self.assertEqual(bearing_and_distance((5, 5), (5, 5), 1), (0.0, 0.0))


# ---------------------------------------------------------------------------
# Grid layer (shipped settlement through runtime probes).
# ---------------------------------------------------------------------------


class GridAreaTests(EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()

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
            QuestDestination("t_q1", "t_def", DestinationFamily.GRID, (0, 0), _T_MAP_KEY, hidden),
            QuestDestination("t_q2", "t_def", DestinationFamily.MONSTER_SITE, (900, 900), "t_other", "wild:t:1:1"),
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


# ---------------------------------------------------------------------------
# Room graphs (synthetic rooms).
# ---------------------------------------------------------------------------


class RoomGraphAreaTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.rooms = {name: create_object(Room, key=f"合成{name}") for name in ("a", "b", "c", "d", "x", "y")}
        self.char = create_object(PlayerCharacter, key="t_char", location=self.rooms["a"])
        self.exits = {}
        for a, b in (("a", "b"), ("b", "c"), ("c", "d"), ("b", "x"), ("x", "y")):
            self._link(a, b)

    def _link(self, a, b, *, both=True):
        self.exits[(a, b)] = create_object(Exit, key=f"往{b}", location=self.rooms[a], destination=self.rooms[b])
        if both:
            self.exits[(b, a)] = create_object(Exit, key=f"往{a}", location=self.rooms[b], destination=self.rooms[a])

    def _visit(self, *names):
        for name in names:
            self.char.location = self.rooms[name]
            record_arrival(self.char)

    def _id(self, name):
        return encode_room(int(self.rooms[name].id))

    @covers_requirement("webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere")
    def test_registered_service_and_instance_keep_external_commission_bearings(self):
        from typeclasses.rooms import InstanceRoom
        from web.webclient.presentation.tests.test_map_quest_destinations import (
            _patch_geography, _record, _DEFINITIONS, _GEOGRAPHY,
        )
        from world.quests.runtime import to_storage

        _patch_geography(self)
        self.rooms["a"].tags.add("t_service")
        instance = create_object(InstanceRoom, key="Synthetic instance")
        instance.attributes.add("origin_room", self.rooms["a"])
        self.char.db.quest_log = [to_storage(_record(name)) for name in ("anchor", "grid", "site", "hunt")]
        with mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", _DEFINITIONS), \
             published_interiors(
                 interior_document(
                     "t_service",
                     {"t_service": interior_room("合成服務", "A synthetic service room.")},
                     exterior=interior_exterior(
                         "service", "service_node", "t_service", "合成門"
                     ),
                 ),
                 replace_existing=True,
             ), \
             mock.patch.dict(_GEOGRAPHY, {"service": SimpleNamespace(cell=(0, 0))}):
            for room in (self.rooms["a"], instance):
                self.char.location = room
                record_arrival(self.char)
                before = (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                          repr(self.char.attributes.get("quest_log")),
                          sorted((a.key, repr(a.value)) for a in room.attributes.all()))
                payload = _render(self.char)
                markers = {m["id"]: m["destination"] for m in payload["quest_markers"]}
                self.assertEqual(markers, {
                    "q_anchor": {"kind": "bearing", "bearing_deg": 36.9, "distance_km": 500.0},
                    "q_grid": {"kind": "bearing", "bearing_deg": 36.9, "distance_km": 500.0},
                    "q_site": {"kind": "bearing", "bearing_deg": 42.7, "distance_km": 176.9},
                    "q_hunt": {"kind": "bearing", "bearing_deg": 90.0, "distance_km": 40.0},
                })
                self.assertTrue(all("x" not in n and "y" not in n for n in payload["nodes"]))
                self.assertEqual(before, (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                                 repr(self.char.attributes.get("quest_log")),
                                 sorted((a.key, repr(a.value)) for a in room.attributes.all())))

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_interior_fog_stops_at_the_frontier_without_coordinates(self):
        self._visit("a", "b")
        payload = _render(self.char)
        nodes = _by_id(payload)
        self.assertEqual(payload["layer"], "interior")
        self.assertEqual(set(nodes), {self._id(n) for n in ("a", "b", "c", "x")})
        for node in payload["nodes"]:
            self.assertNotIn("x", node)
            self.assertNotIn("y", node)
            self.assertIsNone(node["gateway"])
        self.assertEqual(nodes[self._id("b")]["visibility"], "current")
        self.assertEqual(nodes[self._id("a")]["label"], "合成a")
        # A seen room never leaks its name or its own exits.
        self.assertEqual(nodes[self._id("c")]["label"], UNEXPLORED_LABEL)
        self.assertEqual(nodes[self._id("c")]["visibility"], "seen")
        self.assertNotIn(frozenset((self._id("c"), self._id("d"))), _edge_set(payload))
        # Moves are the current room's own traversable exits.
        actionable = {n["id"]: n["action"] for n in payload["nodes"] if n["action"]}
        self.assertEqual(set(actionable), {self._id("a"), self._id("c"), self._id("x")})
        self.assertEqual(actionable[self._id("c")]["exit_ref"], str(int(self.exits[("b", "c")].id)))
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_identity_is_independent_of_position_and_knowledge(self):
        self._visit("a")
        first = _render(self.char)["map_id"]
        self._visit("b", "c", "d")
        second = _render(self.char)["map_id"]
        self.assertEqual(first, second)
        self.assertEqual(first, f"room:{min(int(room.id) for room in self.rooms.values())}")

    def test_one_way_passages_are_known_but_offer_no_move(self):
        lone = create_object(Room, key="合成單向")
        create_object(Exit, key="落下", location=lone, destination=self.rooms["a"])
        self._visit("a")
        payload = _render(self.char)
        node = _by_id(payload)[encode_room(int(lone.id))]
        self.assertEqual(node["visibility"], "seen")
        self.assertIsNone(node["action"])

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_exits_out_of_the_family_are_gateways_never_traversed(self):
        street = GridRoom.objects.first()
        if street is None:
            sync_grid()
            street = GridRoom.objects.first()
        create_object(Exit, key="出門", location=self.rooms["a"], destination=street)
        beyond = create_object(Room, key="合成鄰屋")
        create_object(Exit, key="鄰屋", location=street, destination=beyond)
        self._visit("a")
        payload = _render(self.char)
        nodes = _by_id(payload)
        door = nodes[encode_room(int(street.id))]
        self.assertEqual(door["gateway"], {"leads_to": street.key})
        self.assertEqual(door["visibility"], "seen")
        self.assertIsNotNone(door["action"])
        self.assertNotIn(encode_room(int(beyond.id)), nodes)
        self.assertEqual(payload["map_id"], f"room:{min(int(room.id) for room in self.rooms.values())}")
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_shared_gateway_keeps_the_current_rooms_move_action(self):
        self._visit("a", "b")
        street = GridRoom.objects.first()
        if street is None:
            sync_grid()
            street = GridRoom.objects.first()
        # The non-current room's exit has the lower dbref and therefore
        # introduces the shared gateway node first.
        create_object(Exit, key="往街", location=self.rooms["a"], destination=street)
        current_exit = create_object(
            Exit, key="往街", location=self.rooms["b"], destination=street
        )
        payload = _render(self.char)
        door = _by_id(payload)[encode_room(int(street.id))]
        self.assertEqual(door["visibility"], "seen")
        self.assertIsNotNone(door["action"], "the current room's door must stay actionable")
        self.assertEqual(door["action"]["exit_ref"], str(int(current_exit.id)))
        self.assertEqual(door["action"]["destination"], encode_room(int(street.id)))
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_instance_graph_is_coordinate_free_and_returns_through_a_gateway(self):
        from world.maps.instance import spawn_instance_room

        cave = spawn_instance_room(
            self.rooms["a"],
            {"prototype_parent": "instance_room", "key": "合成洞窟"},
            exit_key="入洞",
            return_key="出洞",
            ttl_seconds=10,
        )
        self.char.location = cave
        record_arrival(self.char)
        payload = _render(self.char)
        self.assertEqual(payload["layer"], "instance")
        self.assertEqual(payload["map_id"], f"instance:{int(cave.id)}")
        self.assertEqual(payload["frame"]["unit"], "none")
        origin = _by_id(payload)[self._id("a")]
        self.assertEqual(origin["gateway"], {"leads_to": "合成a"})
        self.assertEqual(origin["action"]["destination"], self._id("a"))
        # The origin interior's own rooms are never walked into.
        self.assertNotIn(self._id("b"), _by_id(payload))

    def test_an_over_bound_graph_is_unavailable_not_truncated(self):
        self._visit("a", "b")
        with mock.patch.object(area_map_module, "AREA_MAX_NODES", 3), mock.patch.object(
            area_map_module, "log_warn"
        ) as log:
            with self.assertRaises(PanelUnavailableError):
                _render(self.char)
        self.assertEqual(log.call_args.args[0], "area_map_over_bound")

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_byte_overflow_uses_the_declared_bound_path(self):
        self._visit("a", "b")
        with mock.patch.object(area_map_module, "AREA_MAX_BYTES", 64), mock.patch.object(
            area_map_module, "log_warn"
        ) as log:
            with self.assertRaises(PanelUnavailableError):
                _render(self.char)
        self.assertEqual(log.call_args.args[0], "area_map_over_bound")
        self.assertGreater(log.call_args.kwargs["context"]["bytes"], 64)

    @covers_requirement(
        "webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere"
    )
    def test_bound_commission_marks_a_fogged_instance_room_without_adding_it(self):
        from typeclasses.rooms import InstanceRoom
        from world.quests.definitions import (
            DestinationKind,
            ObjectiveKind,
            QuestDefinition,
            QuestObjective,
            QuestStage,
            QuestType,
            RoomLocator,
        )
        from world.quests.runtime import QuestRecord, QuestState, to_storage

        entrance = create_object(InstanceRoom, key="合成地城入口")
        middle = create_object(InstanceRoom, key="合成地城走廊")
        deep = create_object(InstanceRoom, key="合成地城深處")
        for room in (entrance, middle, deep):
            room.db.origin_room = self.rooms["a"]
        create_object(Exit, key="深入", location=entrance, destination=middle)
        create_object(Exit, key="更深", location=middle, destination=deep)
        self.char.location = entrance
        record_arrival(self.char)

        definition = QuestDefinition(
            key="t_bound_dungeon",
            display_name="合成地城委託",
            quest_type=QuestType.EXPLORE,
            rank="F",
            stages=(
                QuestStage(
                    index=0,
                    objective=QuestObjective(
                        kind=ObjectiveKind.REACH,
                        destination=RoomLocator(DestinationKind.BOUND_INSTANCE),
                    ),
                ),
            ),
        )
        record = QuestRecord(
            quest_id="q_bound_dungeon",
            definition_key=definition.key,
            issuer_key="npc:test_commission",
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=int(deep.id),
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        self.char.db.quest_log = [to_storage(record)]
        with mock.patch.dict(
            "world.quests.definitions.QUEST_DEFINITION_REGISTRY",
            {definition.key: definition},
        ):
            payload = _render(self.char)
        marker = next(marker for marker in payload["quest_markers"] if marker["id"] == record.quest_id)
        # The marker keeps the canonical bound-room identity even though the
        # room is beyond the known frontier.
        self.assertEqual(
            marker["destination"],
            {"kind": "node", "node_id": encode_room(int(deep.id))},
        )
        self.assertNotIn(encode_room(int(deep.id)), _by_id(payload))
        self.assertTrue(_js_accepts(payload))

    def test_markers_without_a_known_position_are_omitted(self):
        self._visit("a")
        destination = QuestDestination("t_q", "t_def", DestinationFamily.GRID, (1, 1), "t_m", "grid:t_m:1:1")
        with mock.patch(
            "web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
            return_value=((destination,), frozenset()),
        ), mock.patch.dict(
            "world.quests.definitions.QUEST_DEFINITION_REGISTRY", {"t_def": SimpleNamespace(display_name="合成")}
        ):
            payload = _render(self.char)
        self.assertEqual(payload["quest_markers"], [])


# ---------------------------------------------------------------------------
# Wilderness window (shipped provider through runtime probes).
# ---------------------------------------------------------------------------


class WildernessAreaTests(EvenniaTest):
    """``EvenniaTest``: ``enter_wilderness`` teleports need the full fixture."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        get_world_clock()

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        name = _live("world.maps.wilderness_provider", "WILDERNESS_NAME")
        self.assertTrue(enter_wilderness(self.char1, coordinates=coordinates, name=name))
        record_arrival(self.char1)

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood"
    )
    def test_window_is_bounded_clipped_and_flags_visits(self):
        ex, ey = EAST_APPROACH
        start = (ex + 9, ey)
        self._at_wild((start[0] - 1, start[1]))
        self._at_wild(start)
        payload = _render(self.char1)
        self.assertEqual(payload["layer"], "wilderness")
        self.assertEqual(payload["frame"]["unit"], "km")
        self.assertLessEqual(len(payload["nodes"]), WILDERNESS_WINDOW * WILDERNESS_WINDOW)
        is_valid = _live("world.maps.wilderness_destination", "is_provider_valid_coordinates")
        km = _live("world.maps.wilderness_provider", "WILDERNESS_KM_PER_CELL")
        half = WILDERNESS_WINDOW // 2
        expected = {
            _t_wild_id(x, y)
            for x in range(start[0] - half, start[0] + half + 1)
            for y in range(start[1] - half, start[1] + half + 1)
            if is_valid((x, y))
        }
        wild = {node["id"] for node in payload["nodes"] if node["id"].startswith("wild:")}
        self.assertEqual(wild, expected)
        nodes = _by_id(payload)
        current = nodes[_t_wild_id(*start)]
        self.assertEqual((current["visibility"], current["visited"]), ("current", True))
        self.assertEqual((current["x"], current["y"]), ((start[0] + 0.5) * km, (start[1] + 0.5) * km))
        west = nodes[_t_wild_id(start[0] - 1, start[1])]
        self.assertEqual((west["visibility"], west["visited"]), ("visited", True))
        far = nodes[_t_wild_id(start[0] + half, start[1])]
        self.assertEqual((far["visibility"], far["visited"], far["action"]), ("seen", False, None))
        district_at = _live("world.maps.district_partition", "district_at")
        districts = _live("world.lore.map_districts", "current")().districts
        self.assertEqual(payload["district_name"], districts[district_at(start)].district_name_zh)
        self.assertEqual(payload["title"], _t_region_display_for(*start))
        self.assertEqual(payload["cell_km"], km)
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood"
    )
    def test_only_legal_immediate_steps_are_actionable(self):
        ex, ey = EAST_APPROACH
        start = (ex + 9, ey)
        self._at_wild(start)
        payload = _render(self.char1)
        neighbor = _live("world.maps.wilderness_destination", "wilderness_neighbor")
        directions = _live("world.maps.wilderness_destination", "DIRECTION_DELTAS")
        legal = {_t_wild_id(*cell) for cell in (neighbor(*start, d) for d in directions) if cell is not None}
        actionable = {node["id"] for node in payload["nodes"] if node["action"] is not None}
        self.assertEqual(actionable, legal)
        self.assertEqual(
            _edge_set(payload), {frozenset((_t_wild_id(*start), node_id)) for node_id in legal}
        )

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood"
    )
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_gateway_step_replaces_its_cell_with_the_gate_room(self):
        self._at_wild(EAST_APPROACH)
        payload = _render(self.char1)
        grid = [node for node in payload["nodes"] if node["id"].startswith("grid:")]
        self.assertEqual([node["id"] for node in grid], [_t_grid_id(*EAST_GATE_XYZ[:2])])
        self.assertEqual(grid[0]["gateway"], {"leads_to": _t_anchor_display(_T_MAP_KEY)})
        self.assertEqual(grid[0]["action"]["destination"], grid[0]["id"])
        positions = [(node["x"], node["y"]) for node in payload["nodes"]]
        self.assertEqual(len(positions), len(set(positions)), "a replaced cell is never doubled")
        for node in payload["nodes"]:
            if node["id"].startswith("wild:"):
                self.assertIsNone(node["gateway"])
        self.assertTrue(_js_accepts(payload))


# ---------------------------------------------------------------------------
# map.view dispatch and on-demand publication.
# ---------------------------------------------------------------------------


class _Session:
    def __init__(self, puppet):
        self.sent = []
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def frames(self, name):
        return [call[name][0][0] for call in self.sent if name in call]


class _Calendar:
    year, season_index, season_name, day_in_season, hour, minute, second = 1, 0, "春", 1, 8, 0, 0


def _status_spec():
    return PresenterSpec("status", 1, ("missing_data", "無法讀取"), lambda ctx: {"schema_version": 1, "available": True})


class MapViewDispatchTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.rooms = [create_object(Room, key=f"合成廳{i}") for i in range(2)]
        create_object(Exit, key="東", location=self.rooms[0], destination=self.rooms[1])
        self.char = create_object(PlayerCharacter, key="t_char", location=self.rooms[0])
        record_arrival(self.char)
        self.calls = []

        def spy(context):
            self.calls.append(context)
            return area_map_presenter(context)

        self.registry = PresentationRegistry("test")
        self.registry.register(_status_spec())
        self.registry.register(
            PresenterSpec("area_map", 1, ("map_unavailable", "區域地圖目前無法顯示"), spy, on_demand=True)
        )
        self.session = _Session(self.char)
        self.coordinator = PresentationCoordinator(
            self.session, self.registry, calendar_provider=lambda: _Calendar(), mode_provider=lambda ctx: "exploration"
        )
        self.session.ndb.elosern_coordinator = self.coordinator
        self.coordinator.full_snapshot(_context(self.char))

    def _envelope(self, action_id, payload, request_id="t_r1"):
        return {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": request_id,
            "base_revision": self.coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    @covers_requirement("webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay")
    def test_area_request_with_missing_instance_origin_never_creates_attributes(self):
        from evennia.typeclasses.attributes import Attribute
        from typeclasses.rooms import InstanceRoom
        from web.webclient.presentation.tests.test_map_quest_destinations import (
            _patch_geography, _record, _DEFINITIONS,
        )
        from world.quests.runtime import to_storage

        _patch_geography(self)
        entrance = create_object(InstanceRoom, key="Synthetic entrance")
        deep = create_object(InstanceRoom, key="Synthetic destination")
        create_object(Exit, key="Deeper", location=entrance, destination=deep)
        self.char.location = entrance
        record_arrival(self.char)
        entrance.attributes.remove("origin_room")
        deep.attributes.remove("origin_room")
        with mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", _DEFINITIONS):
            for index, log in enumerate(([], [
                to_storage(_record("bound", stage_room_id=int(deep.id))),
                to_storage(_record("anchor")), to_storage(_record("hunt")),
            ])):
                self.char.db.quest_log = log
                self.assertFalse(entrance.attributes.has("origin_room"))
                self.assertFalse(deep.attributes.has("origin_room"))
                before = (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                          sorted((a.id, a.db_key, repr(a.value)) for a in Attribute.objects.all()))
                handle_ui_action(self.session, self.char,
                                 self._envelope("map.view", {"scope": "area"}, f"t_orphan{index}"),
                                 build_production_action_registry(), self.registry)
                body = self.session.frames("ui_update")[-1]["panels"]["area_map"]
                self.assertTrue(body["available"])
                self.assertEqual(body["current_node"], encode_room(int(entrance.id)))
                self.assertEqual(body["quest_markers"], [] if not log else [{
                    "id": "q_bound", "title": _DEFINITIONS["map_dest_bound"].display_name,
                    "tracked": False, "destination": {"kind": "node", "node_id": encode_room(int(deep.id))},
                }])
                self.assertEqual(before, (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                                 sorted((a.id, a.db_key, repr(a.value)) for a in Attribute.objects.all())))
                self.assertFalse(entrance.attributes.has("origin_room"))
                self.assertFalse(deep.attributes.has("origin_room"))

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_map_view_is_an_exact_allowlisted_read(self):
        spec = build_production_action_registry().spec("map.view")
        self.assertEqual(spec.affected_panels, ("area_map", "world_map"))
        self.assertEqual(spec.validate_payload({"scope": "area"}), {"scope": "area"})
        self.assertEqual(spec.validate_payload({"scope": "world"}), {"scope": "world"})
        for bad in ({}, {"scope": "galaxy"}, {"scope": "area", "x": 1}, {"scope": 1}, ["area"]):
            with self.subTest(payload=bad), self.assertRaises(ProtocolValidationError):
                spec.validate_payload(bad)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_map_view_publishes_only_the_area_map(self):
        before_location = self.char.location
        before_knowledge = parse_knowledge(self.char)
        before_clock = get_world_clock().tick
        before_quest_log = self.char.attributes.get("quest_log")
        handle_ui_action(
            self.session, self.char, self._envelope("map.view", {"scope": "area"}),
            build_production_action_registry(), self.registry,
        )
        self.assertEqual(len(self.calls), 1)
        updates = self.session.frames("ui_update")
        self.assertEqual(len(updates), 1)
        self.assertEqual(list(updates[0]["panels"]), ["area_map"])
        self.assertTrue(updates[0]["panels"]["area_map"]["available"])
        result = self.session.frames("ui_action_result")[-1]
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["presentation_revision"], updates[0]["revision"])
        self.assertIs(self.char.location, before_location)
        self.assertEqual(parse_knowledge(self.char), before_knowledge)
        self.assertEqual(get_world_clock().tick, before_clock)
        self.assertEqual(self.char.attributes.get("quest_log"), before_quest_log)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_rejected_scope_never_runs_the_presenter(self):
        handle_ui_action(
            self.session, self.char, self._envelope("map.view", {"scope": "galaxy"}),
            build_production_action_registry(), self.registry,
        )
        self.assertEqual(self.calls, [])
        result = self.session.frames("ui_action_result")[-1]
        self.assertEqual(result["code"], "malformed_payload")

    @covers_requirement("webclient-world-map::world-scope-reveals-only-common-geography-and-permitted-district-knowledge")
    def test_world_request_publishes_only_filtered_world_without_gameplay_writes(self):
        from web.webclient.presentation.world_map import world_map_presenter
        from web.webclient.presentation.tests.test_world_map import fixtures, SECRET

        self.registry.register(PresenterSpec("world_map", 1, ("map_unavailable", "地圖無法顯示"),
                                             world_map_presenter, on_demand=True))
        before=(self.char.location,parse_knowledge(self.char),get_world_clock().tick,self.char.db.quest_log)
        with fixtures(), mock.patch("web.webclient.presentation.world_map_geometry.current_point",return_value=(1,2)), \
             mock.patch("web.webclient.presentation.world_map.quest_markers",return_value=[]):
            handle_ui_action(
                self.session,self.char,self._envelope("map.view",{"scope":"world"}),
                build_production_action_registry(),self.registry,
            )
        update=self.session.frames("ui_update")[-1]
        self.assertEqual(set(update["panels"]),{"world_map"})
        self.assertTrue(update["panels"]["world_map"]["available"])
        self.assertNotIn(SECRET,json.dumps(update))
        self.assertEqual(self.calls,[])
        self.assertEqual(before,(self.char.location,parse_knowledge(self.char),get_world_clock().tick,self.char.db.quest_log))

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_movement_and_refresh_never_compute_or_push_a_map(self):
        exit_obj = self.rooms[0].exits[0]
        handle_ui_action(
            self.session,
            self.char,
            self._envelope(
                "explore.move",
                {"exit_ref": str(int(exit_obj.id)), "current_node": encode_room(int(self.rooms[0].id))},
            ),
            build_production_action_registry(),
            self.registry,
        )
        self.assertIs(self.char.location, self.rooms[1], "the move committed")
        self.coordinator.synchronize(_context(self.char))
        self.coordinator.enqueue_publication(
            lambda: _context(self.char), affected_panels={"status"}
        )
        self.assertEqual(self.calls, [])
        for name in ("ui_snapshot", "ui_update"):
            for frame in self.session.frames(name):
                self.assertNotIn("area_map", frame["panels"])

    def test_production_snapshot_omits_the_area_map(self):
        with mock.patch.object(area_map_module, "area_map_presenter") as presenter:
            registry = build_production_registry()
            self.assertIs(registry.spec("area_map").presenter, presenter)
            self.assertIn("area_map", registry.on_demand_panel_names)
            self.assertNotIn("area_map", registry.eager_panel_names)
            session = _Session(self.char)
            coordinator = PresentationCoordinator(session, registry, calendar_provider=lambda: _Calendar())
            coordinator.full_snapshot(_context(self.char))
        presenter.assert_not_called()
        self.assertNotIn("area_map", session.frames("ui_snapshot")[0]["panels"])


# ---------------------------------------------------------------------------
# Measured bounds and the shared part codec.
# ---------------------------------------------------------------------------


def _largest_grid_body(labels: int = 16) -> dict:
    """A schema-valid grid area at the node and edge ceilings."""
    map_key = "t_large"
    width = 32

    def node_id(i):
        return f"grid:{map_key}:{(i % width) * 137}:{(i // width) * 211}"

    nodes = [
        {
            "id": node_id(i),
            "label": "合" * labels,
            "x": (i % width) * 137,
            "y": (i // width) * 211,
            "visibility": "current" if i == 0 else ("visited" if i % 2 else "seen"),
            "gateway": {"leads_to": "合成荒野"} if i % 97 == 0 else None,
            "action": {"kind": "move", "exit_ref": str(100000 + i), "destination": node_id(i)} if 0 < i < 9 else None,
        }
        for i in range(AREA_MAX_NODES)
    ]
    pairs = set()
    step = 1
    while len(pairs) < AREA_MAX_EDGES:
        for i in range(AREA_MAX_NODES):
            j = (i + step) % AREA_MAX_NODES
            pairs.add((min(i, j), max(i, j)))
            if len(pairs) == AREA_MAX_EDGES:
                break
        step += 1
    edges = [{"source": node_id(a), "destination": node_id(b)} for a, b in sorted(pairs)]
    markers = [
        {
            "id": f"t_q{i:061d}",
            "title": "委" * 128,
            "tracked": i == 0,
            "destination": {"kind": "bearing", "bearing_deg": 359.9, "distance_km": 2699.9},
        }
        for i in range(AREA_MAX_QUEST_MARKERS)
    ]
    return {
        "schema_version": 1,
        "available": True,
        "layer": "grid",
        "map_id": map_key,
        "frame": {"key": map_key, "unit": "m"},
        "current_node": node_id(0),
        "title": "合成大城",
        "nodes": nodes,
        "edges": edges,
        "quest_markers": markers,
    }


class AreaBoundsTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_largest_supported_graph_fits_and_travels_in_parts(self):
        body = validate_area_map(_largest_grid_body())
        size = json_byte_size(body)
        self.assertLess(size, AREA_MAX_BYTES)
        parts = encode_map_parts("area_map", body)
        self.assertGreater(len(parts), 1)
        self.assertEqual(decode_map_parts("area_map", parts), body)

    def test_ceilings_reject_rather_than_truncate(self):
        body = _largest_grid_body()
        body["nodes"].append(dict(body["nodes"][-1], id="grid:t_large:1:1", x=1, y=1))
        with self.assertRaises(ProtocolValidationError):
            validate_area_map(body)


class AreaMapNodeEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-fifteen-cell-neighbourhood"
    )
    def test_browser_area_map_validator_suite_passes(self):
        result = subprocess.run(
            ["node", "--test", NODE_TEST], cwd=ROOT, capture_output=True, text=True, timeout=300
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"(?m)^\S* ?fail 0$")


if __name__ == "__main__":
    unittest.main()
