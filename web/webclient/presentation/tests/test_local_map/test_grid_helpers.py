import types
import unittest
from unittest.mock import patch
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.local_map import _GraphBuilder
from web.webclient.presentation.registry import PanelUnavailableError

from ._support import _T_MAP_KEY



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
            Z=_T_MAP_KEY,
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
            self.assertTrue(_grid_node_in_map(xymap, encode_grid(_T_MAP_KEY, 2, 0)))
            # A different z-map-key is not in this map.
            self.assertFalse(_grid_node_in_map(xymap, encode_grid("other", 2, 0)))
            # A coordinate with no node at it fails closed.
            self.assertFalse(_grid_node_in_map(xymap, encode_grid(_T_MAP_KEY, 5, 5)))

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
            self.assertIsNone(_grid_exit_action(object(), object(), (9, 9), _T_MAP_KEY))

    def test_grid_layer_unrepresentable_rooms_raise_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        actor = types.SimpleNamespace(location=types.SimpleNamespace())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_layer_missing_xymap_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class FakeRoom:
            xyz = (2, 0, _T_MAP_KEY)
            xymap = None
            key = "南門"

        actor = types.SimpleNamespace(location=FakeRoom())
        builder = _GraphBuilder({})
        with self.assertRaises(PanelUnavailableError):
            _grid_layer(actor, [], builder)

    def test_grid_layer_current_node_outside_map_raises_unavailable(self):
        from web.webclient.presentation.local_map import _grid_layer

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 2}
            node_index_map = {}

            def get_node_from_coord(self, coord):
                return None

        class FakeRoom:
            xyz = (2, 0, _T_MAP_KEY)
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
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 2}
            node_index_map = {}

            def get_node_from_coord(self, coord):
                return None

        class FakeRoom:
            xyz = (2, 0, _T_MAP_KEY)
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
            self.assertIsNone(_grid_exit_action(object(), Room(), (9, 9), _T_MAP_KEY))

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


if __name__ == "__main__":
    unittest.main()
