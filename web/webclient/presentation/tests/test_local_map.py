"""Exact ``local_map`` schema, presenter, and layer-adapter tests.

Covers the D10a shared bounds, the version-1 payload validation, the four
layer adapters (grid/anchor, wilderness, instance/interior), the unavailable
and isolated-failure forms, and the worst-case envelope size.
"""

from tools.spec_traceability import covers_requirement

import types
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from unittest.mock import patch

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map import (
    COORD_MAX,
    COORD_MIN,
    LEGEND_LABELS,
    LOCAL_MAP_SCHEMA_VERSION,
    MAX_EDGES,
    MAX_EXIT_REF_CHARS,
    MAX_LEGEND,
    MAX_NODES,
    MAX_NODE_ID_CHARS,
    MAX_STRING_CODE_POINTS,
    MAX_TITLE_CODE_POINTS,
    _GraphBuilder,
    validate_local_map,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _valid_node(**overrides):
    value = {
        "id": "room:5",
        "label": "測試房間",
        "x": 0,
        "y": 0,
        "visibility": "current",
        "current": True,
        "anchor": False,
        "landmark": False,
        "action": None,
    }
    value.update(overrides)
    return value


def _valid_edge(**overrides):
    value = {
        "source": "room:5",
        "destination": "room:6",
        "label": "out",
        "known": True,
        "traversable": True,
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 1,
        "available": True,
        "layer": "interior",
        "current_node": "room:5",
        "title": "測試平面圖",
        "nodes": [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_visited",
                current=False,
            ),
        ],
        "edges": [_valid_edge()],
        "legend": list(LEGEND_LABELS),
    }
    value.update(overrides)
    return value


class LocalMapSchemaTests(unittest.TestCase):
    def test_valid_interior_panel_passes(self):
        normalized = validate_local_map(_valid_panel())
        self.assertEqual(normalized["schema_version"], LOCAL_MAP_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["layer"], "interior")
        self.assertEqual(normalized["current_node"], "room:5")

    def test_rejects_unknown_and_missing_fields(self):
        payload = _valid_panel()
        payload["bogus"] = 1
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

        payload = _valid_panel()
        del payload["nodes"]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_more_than_one_current_node(self):
        payload = _valid_panel()
        payload["nodes"][1]["current"] = True
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_current_node_absent_from_nodes(self):
        payload = _valid_panel()
        payload["current_node"] = "room:999"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_layer_must_match_current_node_prefix(self):
        payload = _valid_panel()
        payload["layer"] = "grid"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)
        payload = _valid_panel(layer="wilderness")
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_unknown_layer_and_visibility(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(layer="dungeon"))
        nodes = [_valid_node(visibility="hidden")]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_edges_must_reference_presented_nodes(self):
        payload = _valid_panel()
        payload["edges"][0]["source"] = "room:999"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_action_descriptor_is_null_or_exact_move(self):
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={
                    "kind": "move",
                    "exit_ref": "42",
                    "destination": "room:6",
                },
            ),
        ]
        self.assertTrue(validate_local_map(_valid_panel(nodes=nodes)))
        bad_kind = list(nodes)
        bad_kind[1] = dict(bad_kind[1])
        bad_kind[1]["action"] = {"kind": "teleport", "exit_ref": "42", "destination": "room:6"}
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=bad_kind))
        bad_ref = list(nodes)
        bad_ref[1] = dict(bad_ref[1])
        bad_ref[1]["action"] = {"kind": "move", "exit_ref": "好".encode().decode(), "destination": "room:6"}
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=bad_ref))

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_every_d10a_bound_is_enforced(self):
        self.assertLessEqual(MAX_NODES, 128)
        self.assertLessEqual(MAX_EDGES, 128)
        # Node/edge/legend strings capped at 256 code points.
        node = _valid_node(label="x" * (MAX_STRING_CODE_POINTS + 1))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[node]))
        # Title capped at 128.
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(title="x" * (MAX_TITLE_CODE_POINTS + 1)))
        # Node ID capped at 128 chars.
        long_id = "grid:capital_altoria:" + "9" * 130
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(current_node=long_id))
        # Coordinates within -1024..1024.
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(x=COORD_MAX + 1)]))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(y=COORD_MIN - 1)]))
        # exit_ref 1..64 ASCII.
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={
                    "kind": "move",
                    "exit_ref": "x" * (MAX_EXIT_REF_CHARS + 1),
                    "destination": "room:6",
                },
            ),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_legend_bounded_at_16(self):
        legend = ["x" * 10] * (MAX_LEGEND + 1)
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(legend=legend))

    def test_schema_version_mismatch_is_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(schema_version=2))

    def test_available_false_is_rejected_by_the_available_validator(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(available=False))

    def test_empty_title_and_empty_labels_are_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(title="   "))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(label="  ")]))

    def test_missing_or_duplicate_current_node_is_rejected(self):
        nodes = [_valid_node(current=False, visibility="visible_unvisited")]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))
        nodes = [
            _valid_node(),
            _valid_node(id="room:6", label="走廊", x=1, y=0, current=False, visibility="visible_unvisited"),
            _valid_node(id="room:6", label="走廊", x=2, y=0, current=False, visibility="remembered"),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_edges_must_be_a_list_and_legend_entries_non_empty(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(edges="nope"))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(legend=["", "x"]))

    def test_action_missing_field_is_rejected(self):
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={"kind": "move", "exit_ref": "42"},
            ),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_worst_case_legal_payload_fits_the_envelope(self):
        from unittest.mock import patch

        # The structural maxima the schema allows -- 64 nodes, 128 edges, 16
        # legend entries -- with realistic bounded content (canonical grid node
        # IDs, room-name labels, direction edge labels, fixed legend text).
        node_ids = [
            f"grid:capital_altoria:{index % 8}:{index // 8}"
            for index in range(MAX_NODES)
        ]
        nodes = []
        for index in range(MAX_NODES):
            nodes.append(
                _valid_node(
                    id=node_ids[index],
                    label="南門街道" * 4,
                    x=-1024 if index % 2 else 1024,
                    y=1024 if index % 2 else -1024,
                    visibility="remembered" if index else "current",
                    current=(index == 0),
                    action=(
                        None
                        if index == 0
                        else {
                            "kind": "move",
                            "exit_ref": f"e{index}",
                            "destination": node_ids[index],
                        }
                    ),
                )
            )
        edges = [
            _valid_edge(
                source=node_ids[index % MAX_NODES],
                destination=node_ids[(index + 1) % MAX_NODES],
                label="n",
            )
            for index in range(MAX_EDGES)
        ]
        payload = _valid_panel(
            layer="grid",
            current_node=node_ids[0],
            title="聖潔王都街道圖",
            nodes=nodes,
            edges=edges,
            legend=["你目前所在的位置", "尚未探索的相鄰位置"] * 8,
        )
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(8, 8),
        ):
            normalized = validate_local_map(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # The per-field ceilings (256-code-point strings on every node/edge)
        # are schema bounds, not a guarantee that any combination fits the
        # envelope. A payload with max-length CJK strings on every node and
        # edge at once serializes far beyond 65,536 bytes, so the validator
        # MUST reject it -- conformance is enforced on serialized size (D10a).
        from unittest.mock import patch

        node_ids = [
            f"grid:capital_altoria:{index % 8}:{index // 8}"
            for index in range(MAX_NODES)
        ]
        nodes = []
        for index in range(MAX_NODES):
            nodes.append(
                _valid_node(
                    id=node_ids[index],
                    label="字" * MAX_STRING_CODE_POINTS,
                    x=COORD_MAX,
                    y=COORD_MIN,
                    visibility="remembered" if index else "current",
                    current=(index == 0),
                    action=(
                        None
                        if index == 0
                        else {
                            "kind": "move",
                            "exit_ref": "e" * MAX_EXIT_REF_CHARS,
                            "destination": node_ids[index],
                        }
                    ),
                )
            )
        edges = [
            _valid_edge(
                source=node_ids[index % MAX_NODES],
                destination=node_ids[(index + 1) % MAX_NODES],
                label="字" * MAX_STRING_CODE_POINTS,
            )
            for index in range(MAX_EDGES)
        ]
        payload = _valid_panel(
            layer="grid",
            current_node=node_ids[0],
            title="字" * MAX_TITLE_CODE_POINTS,
            nodes=nodes,
            edges=edges,
            legend=["字" * MAX_STRING_CODE_POINTS] * MAX_LEGEND,
        )
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(8, 8),
        ):
            with self.assertRaises(ProtocolValidationError):
                validate_local_map(payload)


class LocalMapGridHelperTests(unittest.TestCase):
    """Pure unit tests for the grid adapter helper functions (task 3.2)."""

    def _node(self, x, y, links=None, symbol="#"):
        node = types.SimpleNamespace(
            X=x, Y=y, node_index=x * 100 + y, links=links or {}, symbol=symbol
        )
        return node

    def _map(self, nodes):
        index = {node.node_index: node for node in nodes}
        by_coord = {(node.X, node.Y): node for node in nodes}

        def get_node_from_coord(coord):
            return by_coord.get(coord)

        return types.SimpleNamespace(
            node_index_map=index,
            Z="capital_altoria",
            options={"map_mode": "nodes", "map_visual_range": 2},
            get_node_from_coord=get_node_from_coord,
        )

    def test_scan_mode_selects_a_rectangular_cutout(self):
        from web.webclient.presentation.local_map import _grid_nodes_in_range

        nodes = [
            self._node(0, 0),
            self._node(1, 1),
            self._node(5, 5),
            self._node(2, 2),
        ]
        xymap = self._map(nodes)
        selected = _grid_nodes_in_range(xymap, self._node(0, 0), 2, "scan")
        indices = {node.node_index for node in selected}
        # The 5,5 node is far outside the 2-unit cut-out; the others are in.
        self.assertIn(nodes[0].node_index, indices)
        self.assertIn(nodes[1].node_index, indices)
        self.assertIn(nodes[3].node_index, indices)
        self.assertNotIn(nodes[2].node_index, indices)

    def test_nodes_mode_is_bounded_bfs_over_links(self):
        from web.webclient.presentation.local_map import _grid_nodes_in_range

        a = self._node(0, 0)
        b = self._node(1, 0)
        c = self._node(2, 0)
        d = self._node(3, 0)
        a.links = {"e": b}
        b.links = {"e": c, "w": a}
        c.links = {"e": d, "w": b}
        d.links = {"w": c}
        xymap = self._map([a, b, c, d])
        selected = _grid_nodes_in_range(xymap, a, 2, "nodes")
        indices = {node.node_index for node in selected}
        # Range 2 reaches a, b, c but not d.
        self.assertIn(a.node_index, indices)
        self.assertIn(b.node_index, indices)
        self.assertIn(c.node_index, indices)
        self.assertNotIn(d.node_index, indices)

    def test_grid_node_in_map_handles_foreign_and_missing_nodes(self):
        from web.webclient.presentation.local_map import _grid_node_in_map

        xymap = self._map([self._node(2, 0)])
        from world.rules.map_knowledge import encode_grid

        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(8, 8),
        ):
            self.assertTrue(_grid_node_in_map(xymap, encode_grid("capital_altoria", 2, 0)))
            # A different z-map-key is not in this map.
            self.assertFalse(_grid_node_in_map(xymap, encode_grid("other", 2, 0)))
            # A coordinate with no node at it fails closed.
            self.assertFalse(_grid_node_in_map(xymap, encode_grid("capital_altoria", 5, 5)))

    def test_grid_coord_is_anchor_checks_interrupt_path_or_at_symbol(self):
        from web.webclient.presentation.local_map import _grid_coord_is_anchor

        plain = self._node(2, 0)
        xymap = self._map([plain])
        self.assertFalse(_grid_coord_is_anchor(xymap, (2, 0)))
        interrupt = self._node(2, 0)
        interrupt.interrupt_path = True
        xymap = self._map([interrupt])
        self.assertTrue(_grid_coord_is_anchor(xymap, (2, 0)))
        symbol = self._node(2, 0, symbol="@")
        xymap = self._map([symbol])
        self.assertTrue(_grid_coord_is_anchor(xymap, (2, 0)))

    def test_grid_direction_label_returns_the_link_direction(self):
        from web.webclient.presentation.local_map import _grid_direction_label

        a = self._node(0, 0)
        b = self._node(1, 0)
        a.links = {"e": b}
        self.assertEqual(_grid_direction_label(a, b), "e")
        self.assertEqual(_grid_direction_label(b, a), "")

    def test_grid_exit_action_returns_none_for_missing_destination(self):
        from web.webclient.presentation.local_map import _grid_exit_action

        class EmptyQuery:
            def first(self):
                return None

        with patch(
            "typeclasses.rooms.GridRoom.objects.filter_xyz",
            return_value=EmptyQuery(),
        ):
            self.assertIsNone(_grid_exit_action(object(), object(), (9, 9), "capital_altoria"))

    def test_grid_layer_unrepresentable_rooms_raise_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        actor = types.SimpleNamespace(location=types.SimpleNamespace())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_layer_missing_xymap_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class FakeRoom:
            xyz = (2, 0, "capital_altoria")
            xymap = None
            key = "南門"

        actor = types.SimpleNamespace(location=FakeRoom())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_layer_current_node_outside_map_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class FakeMap:
            Z = "capital_altoria"
            options = {"map_mode": "nodes", "map_visual_range": 2}
            node_index_map = {}

            def get_node_from_coord(self, coord):
                return None

        class FakeRoom:
            xyz = (2, 0, "capital_altoria")
            xymap = FakeMap()
            key = "南門"

        actor = types.SimpleNamespace(location=FakeRoom())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_wilderness_layer_rejects_non_terrain_and_out_of_bounds(self):
        from web.webclient.presentation.local_map import _wilderness_layer

        actor = types.SimpleNamespace(location=types.SimpleNamespace())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _wilderness_layer(actor, [], builder)

        class OutOfBounds:
            coordinates = (999, 999)

        actor = types.SimpleNamespace(location=OutOfBounds())
        with self.assertRaises(PanelUnavailableError):
            _wilderness_layer(actor, [], builder)

    def test_wild_neighbor_returns_none_at_provider_edges(self):
        from web.webclient.presentation.local_map import _wild_neighbor

        self.assertIsNone(_wild_neighbor(0, 0, "sw"))
        self.assertIsNone(_wild_neighbor(0, 0, "s"))
        self.assertIsNone(_wild_neighbor(0, 0, "w"))
        self.assertIsNone(_wild_neighbor(223, 223, "ne"))
        self.assertIsNotNone(_wild_neighbor(5, 5, "n"))

    def test_interior_graph_skips_non_room(self):
        from web.webclient.presentation.local_map import _interior_graph

        actor = types.SimpleNamespace(location=types.SimpleNamespace())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _interior_graph(actor, [], builder, is_instance=False)

    def test_traversable_exception_fails_closed(self):
        from web.webclient.presentation.local_map import _traversable

        class RaisingExit:
            def access(self, actor, locktype):
                raise RuntimeError("boom")

        self.assertFalse(_traversable(RaisingExit(), object()))

    def test_grid_layer_xyz_exception_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class BrokenRoom:
            @property
            def xyz(self):
                raise RuntimeError("no tags")

        actor = types.SimpleNamespace(location=BrokenRoom())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_layer_anchor_missing_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class FakeMap:
            Z = "capital_altoria"
            options = {"map_mode": "nodes", "map_visual_range": 2}
            node_index_map = {}

            def get_node_from_coord(self, coord):
                return None

        class FakeRoom:
            xyz = (2, 0, "capital_altoria")
            xymap = FakeMap()
            key = "南門"

        actor = types.SimpleNamespace(location=FakeRoom())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_exit_action_skips_non_traversable_exit(self):
        from web.webclient.presentation.local_map import _grid_exit_action

        class Destination:
            pass

        destination = Destination()

        def make_exit():
            class ExitObj:
                def __init__(self):
                    self.destination = destination

                def access(self, actor, locktype):
                    return False

            return ExitObj()

        class Room:
            exits = [make_exit()]

        with patch(
            "typeclasses.rooms.GridRoom.objects.filter_xyz",
            return_value=types.SimpleNamespace(first=lambda: destination),
        ):
            self.assertIsNone(_grid_exit_action(object(), Room(), (9, 9), "capital_altoria"))

    def test_wilderness_layer_rejects_missing_coordinates(self):
        from web.webclient.presentation.local_map import _wilderness_layer

        class NoCoords:
            coordinates = None

        actor = types.SimpleNamespace(location=NoCoords())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _wilderness_layer(actor, [], builder)

    def test_graph_builder_remembered_bounds_by_last_seen(self):
        from world.rules.map_knowledge import NodeVisit

        visits = [
            NodeVisit("room:1", 10, 10),
            NodeVisit("room:2", 20, 30),
            NodeVisit("room:3", 20, 20),
        ]
        builder = _GraphBuilder({visit.node_id: visit for visit in visits})
        builder.add_node("room:1", "x", 0, 0, visibility="current", current=True)
        remembered = builder.remembered(2)
        self.assertEqual(
            [visit.node_id for visit in remembered], ["room:2", "room:3"]
        )

    def test_graph_builder_dedups_and_enriches_existing_nodes(self):
        builder = _GraphBuilder({})
        builder.add_node("room:7", "cave", 0, 0, visibility="current", current=True)
        builder.add_node(
            "room:7",
            "cave",
            0,
            0,
            visibility="current",
            current=True,
            action={"kind": "move", "exit_ref": "1", "destination": "room:7"},
        )
        self.assertEqual(len(builder.nodes), 1)
        self.assertEqual(builder.nodes[0]["action"]["exit_ref"], "1")
        # A second node with an action does not downgrade the existing action.
        builder.add_node(
            "room:7",
            "cave",
            0,
            0,
            visibility="current",
            current=True,
            action=None,
        )
        self.assertEqual(builder.nodes[0]["action"]["exit_ref"], "1")


class LocalMapPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()

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
        self.assertEqual(payload["current_node"], "grid:capital_altoria:2:0")
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
            Z = "capital_altoria"
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
        plaza = GridRoom.objects.filter_xyz(xyz=(2, 2, "capital_altoria")).first()
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
        valid = {
            "grid:capital_altoria:2:0",
            "grid:capital_altoria:2:1",
            "grid:capital_altoria:1:1",
            "grid:capital_altoria:3:1",
            "grid:capital_altoria:0:2",
            "grid:capital_altoria:1:2",
            "grid:capital_altoria:2:2",
            "grid:capital_altoria:3:2",
            "grid:capital_altoria:4:2",
            "grid:capital_altoria:2:3",
            "grid:capital_altoria:1:3",
            "grid:capital_altoria:3:3",
            "grid:capital_altoria:2:4",
        }
        for node in payload["nodes"]:
            self.assertIn(node["id"], valid)

    @covers_requirement("webclient-local-map::only-currently-traversable-exits-receive-movement-descriptors")
    def test_remembered_nodes_carry_no_action(self):
        actor = self.char1
        actor.location = self.south_gate
        record_arrival(actor)
        # Move away and deep into the city so a remembered grid node forms.
        from typeclasses.rooms import GridRoom as _Grid

        north = _Grid.objects.filter_xyz(xyz=(2, 3, "capital_altoria")).first()
        actor.location = north
        record_arrival(actor)
        payload = self._registry().render("local_map", _context(actor))
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        for node in remembered:
            self.assertIsNone(node["action"])


class LocalMapWildernessTests(EvenniaTest):
    """Wilderness-layer adapter tests (task 3.3)."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=(2, 4, "capital_altoria")).first()
        self.gate = [e for e in self.north_gate.exits if e.key == "荒野"][0]

    def _registry(self):
        return build_production_registry()

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_wilderness_payload_uses_provider_bounds_and_terrain_labels(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "wilderness")
        x, y = self.char1.location.coordinates
        self.assertEqual(payload["current_node"], f"wild:elosern:{x}:{y}")
        for node in payload["nodes"]:
            self.assertTrue(node["label"].strip())
        # Legal adjacent cells bounded by the provider.
        for node in payload["nodes"]:
            if node["id"] == payload["current_node"]:
                continue
            decoded = node["id"].split(":")
            self.assertLessEqual(int(decoded[2]), 223)
            self.assertLessEqual(int(decoded[3]), 223)

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_visited_cells_beyond_adjacency_become_remembered(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        from world.rules.map_knowledge import parse_knowledge

        current = self.char1.location.coordinates
        # Record a distant visited cell directly.
        far = f"wild:elosern:{current[0] + 5}:{current[1]}"
        visits = {
            visit.node_id: visit
            for visit in parse_knowledge(self.char1)
        }
        visits[far] = type("Visit", (), {"node_id": far, "first_seen_tick": 5, "last_seen_tick": 5})()
        record = {
            "schema_version": 1,
            "visited": {
                node_id: {
                    "first_seen_tick": visit.first_seen_tick,
                    "last_seen_tick": visit.last_seen_tick,
                }
                for node_id, visit in visits.items()
            },
        }
        self.char1.attributes.add("map_knowledge", record)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertIn(far, [node["id"] for node in remembered])


if __name__ == "__main__":
    unittest.main()
