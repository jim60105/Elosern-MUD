"""The on-demand ``area_map`` presenter and the ``map.view`` action (room graph area)."""

from types import SimpleNamespace
from unittest import mock
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.area_map import UNEXPLORED_LABEL
from world.tests.interior_fixture import interior_document, interior_exterior, interior_room, published_interiors
from web.webclient.presentation.map_panels import AREA_MAX_BYTES, AREA_MAX_NODES
from web.webclient.presentation.map_quest_destinations import DestinationEvidence, DestinationFamily, QuestDestination
from web.webclient.presentation.registry import PanelUnavailableError
from world.tests.geography_fixture import sync_test_settlements
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import encode_room, parse_knowledge, record_arrival
from ..test_local_map._support import EAST_GATE_XYZ


from ._support import _render, _by_id, _edge_set, _js_accepts

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
            sync_test_settlements((EAST_GATE_XYZ[2],))
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
            sync_test_settlements((EAST_GATE_XYZ[2],))
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
        destination = QuestDestination(
            "t_q", "t_def", DestinationFamily.GRID, (1, 1), "t_m",
            "grid:t_m:1:1", DestinationEvidence.LOCATION,
        )
        with mock.patch(
            "web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
            return_value=((destination,), frozenset()),
        ), mock.patch.dict(
            "world.quests.definitions.QUEST_DEFINITION_REGISTRY", {"t_def": SimpleNamespace(display_name="合成")}
        ):
            payload = _render(self.char)
        self.assertEqual(payload["quest_markers"], [])
