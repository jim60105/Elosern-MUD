from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.local_map import LEGEND_LABELS
from web.webclient.presentation.registry import PanelUnavailableError, build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import (
    EAST_APPROACH,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _T_PLAZA_XYZ,
    _context,
    _t_grid_id,
    _t_wild_id,
)



class LocalMapPresenterTests(EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        cls._south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.south_gate = GridRoom.objects.get(id=self._south_gate.id)

    def _registry(self):
        return build_production_registry()

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_grid_room_produces_grid_layer_payload(self):
        actor = self.char1
        actor.location = self.south_gate
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "grid")
        self.assertEqual(payload["current_node"], _t_grid_id(*SOUTH_GATE_XYZ[:2]))
        current = next(node for node in payload["nodes"] if node["current"])
        self.assertEqual(current["visibility"], "current")
        # The payload includes at least one visible unvisited neighbor.
        self.assertTrue(
            any(node["visibility"] in ("visible_unvisited", "visible_visited") for node in payload["nodes"])
        )
        # Canonical game state is unchanged by rendering.
        self.assertIs(actor.location, self.south_gate)
        self.assertIsNone(actor.attributes.get("map_knowledge_rendered"))

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_instance_room_produces_instance_payload(self):
        from world.maps.instance import spawn_instance_room

        room = spawn_instance_room(
            self.room1,
            {"prototype_parent": "instance_room", "key": "cave"},
            exit_key="in",
            return_key="out",
            ttl_seconds=10,
        )
        self.char1.location = room
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "instance")
        self.assertEqual(payload["current_node"], f"room:{room.id}")
        self.assertTrue(
            all(node["id"].startswith("room:") for node in payload["nodes"]),
            "no grid/wild identity may be invented for an instance",
        )

    def test_instance_with_missing_origin_renders_current_node_only(self):
        from typeclasses.rooms import InstanceRoom

        room = create_object(InstanceRoom, key="orphan_cave")
        room.origin_room = None
        self.char1.location = room
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "instance")
        self.assertEqual(payload["current_node"], f"room:{room.id}")

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_interior_room_produces_interior_payload(self):
        interior = create_object(Room, key="阿爾托利亞冒險者公會大廳")
        self.char1.location = interior
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "interior")
        self.assertEqual(payload["current_node"], f"room:{interior.id}")

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_interior_payload_still_remembers_a_previously_entered_room(self):
        # design D7: the coordinate-free layers keep the shipped "previously
        # entered, not currently in view" meaning -- the gateway redefinition
        # is scoped to grid/wilderness only, and _interior_graph is untouched.
        storeroom = create_object(Room, key="倉庫")
        hall = create_object(Room, key="大廳")
        self.char1.location = storeroom
        record_arrival(self.char1)
        self.char1.location = hall
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "interior")
        remembered = {
            node["id"]: node for node in payload["nodes"] if node["visibility"] == "remembered"
        }
        self.assertIn(f"room:{storeroom.id}", remembered)
        self.assertEqual(remembered[f"room:{storeroom.id}"]["label"], storeroom.key)

    def test_remembered_room_without_an_object_is_omitted(self):
        # A remembered room:<dbref> whose object no longer resolves is treated
        # as unavailable and omitted (D4), never labelled 未探索.
        interior = create_object(Room, key="倉庫")
        self.char1.location = interior
        record = {
            "schema_version": 1,
            "visited": {
                f"room:{interior.id}": {"first_seen_tick": 1, "last_seen_tick": 1},
                "room:99999999": {"first_seen_tick": 2, "last_seen_tick": 2},
            },
        }
        self.char1.attributes.add("map_knowledge", record)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        node_ids = [node["id"] for node in payload["nodes"]]
        self.assertIn(f"room:{interior.id}", node_ids)
        self.assertNotIn("room:99999999", node_ids)
        self.assertFalse(
            any(node["label"] == "未探索" for node in payload["nodes"]),
            "an unresolvable remembered room must not surface as 未探索",
        )

    @covers_requirement("webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant")
    def test_non_wilderness_legends_keep_exactly_the_state_labels(self):
        from world.maps.instance import spawn_instance_room

        # grid
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        grid_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(grid_payload["layer"], "grid")
        self.assertEqual(grid_payload["legend"], list(LEGEND_LABELS))

        # instance
        instance = spawn_instance_room(
            self.room1,
            {"prototype_parent": "instance_room", "key": "cave"},
            exit_key="in",
            return_key="out",
            ttl_seconds=10,
        )
        self.char1.location = instance
        record_arrival(self.char1)
        instance_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(instance_payload["layer"], "instance")
        self.assertEqual(instance_payload["legend"], list(LEGEND_LABELS))

        # interior
        interior = create_object(Room, key="_LEGEND_INTEGRITY_HALL_TEST")
        self.char1.location = interior
        record_arrival(self.char1)
        interior_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(interior_payload["layer"], "interior")
        self.assertEqual(interior_payload["legend"], list(LEGEND_LABELS))

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_no_location_is_unavailable_without_fabrication(self):
        actor = self.char1
        actor.location = None
        payload = self._registry().render("local_map", _context(actor))
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], "map_unavailable")
        self.assertNotIn("nodes", payload)

    def test_corrupt_knowledge_is_unavailable(self):
        self.char1.location = self.south_gate
        self.char1.attributes.add(
            "map_knowledge", {"schema_version": 99, "visited": {}}
        )
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertFalse(payload["available"])

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_presenter_failure_is_isolated_from_other_panels(self):
        from web.webclient.presentation.registry import PanelUnavailableError
        from unittest.mock import patch

        actor = self.char1
        actor.race = "human"
        actor.apply_race_baseline()
        actor.location = self.room1
        registry = self._registry()
        with patch(
            "web.webclient.presentation.local_map.local_map_presenter",
            side_effect=PanelUnavailableError,
        ):
            payload = registry.render("local_map", _context(actor))
        self.assertFalse(payload["available"])
        status = registry.render("status", _context(actor))
        self.assertTrue(status["available"])

    @covers_requirement("webclient-local-map::only-currently-traversable-exits-receive-movement-descriptors")
    def test_grid_adjacent_exits_carry_move_descriptors(self):
        actor = self.char1
        actor.location = self.south_gate
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        moves = [
            node for node in payload["nodes"] if node["action"] is not None
        ]
        self.assertTrue(moves)
        for move in moves:
            self.assertEqual(move["action"]["kind"], "move")
            self.assertIn("exit_ref", move["action"])
            self.assertIn("destination", move["action"])

    @covers_requirement("sample-city-altoria::the-sample-city-has-exactly-thirteen-rooms-in-a-fixed-connected-topology")
    def test_invalid_grid_options_fail_closed(self):
        from web.webclient.presentation.registry import PanelUnavailableError
        from unittest.mock import patch

        actor = self.char1
        actor.location = self.south_gate
        registry = self._registry()

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "bogus", "map_visual_range": 2}
            node_index_map = {}

            def get_node_from_coord(self, xy):
                return None

        with patch.object(type(actor.location), "xymap", FakeMap()):
            with self.assertRaises(PanelUnavailableError):
                from web.webclient.presentation.local_map import local_map_presenter

                local_map_presenter(_context(actor))

        class OutOfRangeMap(FakeMap):
            options = {"map_mode": "nodes", "map_visual_range": 99}

        with patch.object(type(actor.location), "xymap", OutOfRangeMap()):
            with self.assertRaises(PanelUnavailableError):
                from web.webclient.presentation.local_map import local_map_presenter

                local_map_presenter(_context(actor))

    @covers_requirement("sample-city-altoria::the-sample-city-has-exactly-thirteen-rooms-in-a-fixed-connected-topology")
    def test_grid_anchor_flag_marks_the_plaza(self):
        actor = self.char1
        plaza = GridRoom.objects.filter_xyz(xyz=_T_PLAZA_XYZ).first()
        actor.location = plaza
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        current = next(node for node in payload["nodes"] if node["current"])
        self.assertTrue(current["anchor"])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_unknown_grid_nodes_are_omitted(self):
        actor = self.char1
        actor.location = self.south_gate
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        # Every node the payload may carry, enumerated from the live map
        # module and the live gate approaches (test-data gate: no authored
        # topology). The set is derived from the SAME source the presenter
        # reads, but membership is what the test guards -- a node id with no
        # registered origin must never be fabricated into the payload.
        from evennia.contrib.grid.xyzgrid.xymap import XYMap
        from world.maps.map_data import XYMAP_DATA_LIST

        capital_map = next(
            data for data in XYMAP_DATA_LIST if data["zcoord"] == _T_MAP_KEY
        )
        parsed = XYMap(dict(capital_map), Z=_T_MAP_KEY, xyzgrid=None)
        parsed.parse()
        valid = {
            _t_grid_id(node.X, node.Y) for node in parsed.node_index_map.values()
        }
        valid |= {_t_wild_id(*EAST_APPROACH), _t_wild_id(*SOUTH_APPROACH)}
        for node in payload["nodes"]:
            self.assertIn(node["id"], valid)

    @covers_requirement("webclient-local-map::only-currently-traversable-exits-receive-movement-descriptors")
    def test_remembered_nodes_carry_no_action(self):
        actor = self.char1
        actor.location = self.south_gate
        record_arrival(actor)
        # Move away and deep into the city so a remembered grid node forms.
        from typeclasses.rooms import GridRoom as _Grid

        north = _Grid.objects.filter_xyz(xyz=(2, 3, _T_MAP_KEY)).first()
        actor.location = north
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        for node in remembered:
            self.assertIsNone(node["action"])


if __name__ == "__main__":
    unittest.main()
