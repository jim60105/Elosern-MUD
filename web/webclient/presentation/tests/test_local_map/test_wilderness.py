from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.local_map import LEGEND_LABELS, MAX_LEGEND, MAX_STRING_CODE_POINTS
from web.webclient.presentation.local_map import gateways
from web.webclient.presentation.registry import build_production_registry
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.maps.published import SourceMemo
from world.rules.map_knowledge import encode_grid, record_arrival

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _context,
    _live,
    _live_gateway_entry,
    _t_anchor_display,
    _t_grid_id,
    _t_region_display_for,
    _t_wild_id,
)


def _declared_gateway_maps() -> tuple[str, ...]:
    """The settlement maps these gateway checks actually stand on.

    The city entry authoring both gateway faces contributes its east and
    south destination maps; the hidden point entrance contributes its own.
    Gateways of every other settlement are out of scope here, so their maps
    are not materialized.
    """
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    entry = _live_gateway_entry()
    point = next(
        candidate
        for candidate in WILDERNESS_ENTRY_REGISTRY.values()
        if candidate.is_point_shape
    )
    return tuple(
        sorted(
            {
                entry.gate_for("w").destination.map_id,
                entry.gate_for("n").destination.map_id,
                point.gates[0].destination.map_id,
            }
        )
    )


class LocalMapWildernessTests(EvenniaTestCase):
    """Wilderness-layer adapter tests (task 3.3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_test_settlements((EAST_GATE_XYZ[2],))
        sync_test_wilderness((EAST_GATE_XYZ[2],))
        cls._east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        cls._gate = [e for e in cls._east_gate.exits if e.key == "荒野"][0]

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.east_gate = GridRoom.objects.get(id=self._east_gate.id)
        self.gate = [e for e in self.east_gate.exits if e.key == "荒野"][0]

    def _registry(self):
        return build_production_registry()

    def _actionable_directions(self) -> set[str]:
        """The short directions this approach advertises, from its authored entry.

        Ordinary steps are the shared provider-valid geometry's answer for the
        entry's own approach cell, so a footprint edit moves this expectation
        instead of contradicting it. The gateway direction is advertised on
        top of them even though its cell belongs to the mask: that row resolves
        to the grid node.
        """
        from world.lore.wilderness_entry import DIRECTION_DELTAS
        from world.maps.wilderness_destination import wilderness_neighbor

        entry = _live_gateway_entry()
        gate = entry.gate_for("w")
        approach = entry.approach_cell(gate)
        self.assertIsNotNone(approach)
        ordinary = {
            short
            for short in DIRECTION_DELTAS
            if wilderness_neighbor(approach[0], approach[1], short) is not None
        }
        return ordinary | {gate.return_direction}

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_wilderness_payload_uses_provider_bounds_and_terrain_labels(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
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
            # A resolved gateway renders the grid gate node, not a wild cell;
            # provider bounds only constrain wild identities.
            if not node["id"].startswith("wild:"):
                continue
            decoded = node["id"].split(":")
            from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

            self.assertLessEqual(int(decoded[2]), WILDERNESS_MAX_X)
            self.assertLessEqual(int(decoded[3]), WILDERNESS_MAX_Y)
        # Gateway metadata: the resolved grid gate node names the settlement
        # it leads into; the current approach cell and every ordinary wild
        # terrain cell carry null.
        grid_nodes = [node for node in payload["nodes"] if node["id"].startswith("grid:")]
        self.assertEqual(len(grid_nodes), 1)
        self.assertEqual(grid_nodes[0]["gateway"], {"leads_to": _t_anchor_display(_T_MAP_KEY)})
        for node in payload["nodes"]:
            if node["id"].startswith("wild:"):
                with self.subTest(node=node["id"]):
                    self.assertIsNone(node["gateway"])

    @covers_requirement("webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant")
    def test_wilderness_legend_appends_scale_note_after_the_states(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        # The four state labels keep their exact order/positions, and the
        # scale note is the fifth entry (webclient-map-scale-legend D2).
        self.assertEqual(len(payload["legend"]), len(LEGEND_LABELS) + 1)
        self.assertEqual(payload["legend"][: len(LEGEND_LABELS)], list(LEGEND_LABELS))
        from world.maps import wilderness_provider

        scale_note = payload["legend"][len(LEGEND_LABELS)]
        self.assertIn(str(wilderness_provider.WILDERNESS_KM_PER_CELL), scale_note)
        # The extended legend stays inside the shared bounds the validators
        # pin (5 <= 16 entries, the note far below 256 code points); the
        # payload above already passed the exact Python validator in render.
        self.assertLessEqual(len(payload["legend"]), MAX_LEGEND)
        self.assertLessEqual(len(scale_note), MAX_STRING_CODE_POINTS)

    @covers_requirement("webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant")
    def test_scale_note_figure_follows_the_provider_module_attribute(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        with patch("world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL", 42):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        scale_note = payload["legend"][len(LEGEND_LABELS)]
        # The note is derived from the provider module attribute at
        # legend-assembly time -- never a duplicated literal.
        self.assertIn("42", scale_note)
        self.assertNotIn("10", scale_note)

    # test_visited_cells_beyond_adjacency_become_remembered pinned the old
    # "every previously-visited cell becomes remembered" meaning; it is
    # replaced by test_only_stood_on_gateways_are_remembered_in_the_wilderness
    # and its siblings in LocalMapWildernessGatewayTests below (local-map-
    # remembered-are-map-gateways wave 3), which need the full ``EvenniaTest``
    # fixture for ``enter_wilderness`` teleports rather than this class's
    # ``EvenniaTestCase`` base.

    @covers_requirement("webclient-local-map::wilderness-minimap-nodes-are-actionable")
    def test_wilderness_adjacent_nodes_carry_move_actions_with_canonical_destinations(self):
        from world.maps.wilderness_destination import resolve_wilderness_destination

        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        current = payload["current_node"]
        moves = [node for node in payload["nodes"] if node["action"] is not None]
        # At the east gate's approach cell the actionable directions are the
        # gateway row plus every ordinary step the provider-valid geometry
        # allows; the steps into the anchor footprint, and the diagonals whose
        # orthogonal neighbour is one of them, render nothing
        # (wilderness-anchor-footprint).
        expected = self._actionable_directions()
        self.assertEqual(len(moves), len(expected))
        for move in moves:
            self.assertEqual(move["action"]["kind"], "move")
            self.assertTrue(move["action"]["exit_ref"].isascii())
        directions = {
            edge["label"]: edge["destination"]
            for edge in payload["edges"]
            if edge["source"] == current
        }
        self.assertEqual(set(directions), expected)
        for direction, node_id in directions.items():
            node = next(node for node in payload["nodes"] if node["id"] == node_id)
            expected = resolve_wilderness_destination(room, direction)
            self.assertIsNotNone(expected, direction)
            self.assertEqual(node["action"]["destination"], expected, direction)
            edge = next(
                edge for edge in payload["edges"]
                if edge["source"] == current and edge["label"] == direction
            )
            self.assertTrue(edge["traversable"], direction)
        # The gateway west node advertises the grid arrival node, not a wild cell.
        west_node_id = directions["w"]
        west_node = next(node for node in payload["nodes"] if node["id"] == west_node_id)
        self.assertEqual(
            west_node["action"]["destination"], _t_grid_id(*EAST_GATE_XYZ[:2])
        )

    @covers_requirement("webclient-local-map::wilderness-minimap-nodes-are-actionable")
    def test_locked_wilderness_node_stays_inert(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        west_exit = [exit_obj for exit_obj in room.exits if exit_obj.key == "west"][0]
        west_exit.locks.add("traverse:false()")
        payload = self._registry().render("local_map", _context(self.char1))
        current = payload["current_node"]
        edge = next(
            edge for edge in payload["edges"]
            if edge["source"] == current and edge["label"] == "w"
        )
        node = next(node for node in payload["nodes"] if node["id"] == edge["destination"])
        self.assertIsNone(node["action"])
        self.assertFalse(edge["traversable"])
        # Every other actionable direction still carries a move action.
        self.assertEqual(
            len([node for node in payload["nodes"] if node["action"] is not None]),
            len(self._actionable_directions()) - 1,
        )

    def test_aliased_unrelated_exit_does_not_hijack_the_west_action(self):
        from typeclasses.exits import WildernessReturnExit

        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        west_exit = [exit_obj for exit_obj in room.exits if exit_obj.key == "west"][0]
        # An unrelated exit aliased "w" must never replace the real west
        # exit in the move descriptor (direction mapping is key-based only).
        extra = create_object(
            WildernessReturnExit,
            key="密道",
            aliases=["w"],
            location=room,
            destination=room,
        )
        payload = self._registry().render("local_map", _context(self.char1))
        current = payload["current_node"]
        edge = next(
            edge for edge in payload["edges"]
            if edge["source"] == current and edge["label"] == "w"
        )
        node = next(node for node in payload["nodes"] if node["id"] == edge["destination"])
        self.assertEqual(node["action"]["exit_ref"], str(int(west_exit.id)))
        self.assertNotEqual(node["action"]["exit_ref"], str(int(extra.id)))


class _RememberedGatewayFixture:
    """The full-evennia fixture shared by the remembered-gateway journeys.

    ``EvenniaTest`` (not ``EvenniaTestCase``): ``enter_wilderness`` teleports
    need the full-evennia fixture, same as ``LocalMapPerGateFootprintTests``.
    """

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        declared = _declared_gateway_maps()
        sync_test_settlements(declared)
        sync_test_wilderness(declared)
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()

    def _registry(self):
        return build_production_registry()

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(self.char1, coordinates=coordinates, name=WILDERNESS_NAME)
        self.assertTrue(entered, coordinates)
        record_arrival(self.char1)

    def _render_counting_gateway_lookups(self):
        """Render ``local_map`` and count the layer's per-cell approach lookups."""
        with patch(
            "web.webclient.presentation.local_map.wilderness._wilderness_gateway_at",
            wraps=gateways._wilderness_gateway_at,
        ) as lookup:
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        return lookup.call_count


class LocalMapWildernessGatewayTests(_RememberedGatewayFixture, EvenniaTest):
    """Remembered wilderness nodes are stood-on map gateways (waves 3, 5, 6)."""

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_only_stood_on_gateways_are_remembered_in_the_wilderness(self):
        # Stand on the east gate's approach cell (records it honestly, the
        # way arrival recording already works), then walk far enough away
        # that it drops out of the drawn 3x3 field of view.
        ex, ey = EAST_APPROACH
        self._at_wild((ex, ey))
        self._at_wild((ex + 10, ey))
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(len(remembered), 1)
        node = remembered[0]
        self.assertEqual(node["id"], _t_wild_id(ex, ey))
        self.assertEqual((node["x"], node["y"]), (ex, ey))
        self.assertEqual(node["label"], _t_anchor_display(_T_MAP_KEY))
        self.assertTrue(node["landmark"])
        self.assertFalse(node["anchor"])
        self.assertIsNone(node["action"])
        # A remembered approach cell is a wild cell, not a grid gate room.
        self.assertIsNone(node["gateway"])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_a_gateway_the_player_has_never_reached_is_absent(self):
        # The gate room (grid side) was visited, but the approach cell (wild
        # side) never was -- design D4: an honest "you don't know where in
        # the wilds this comes out."
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 10, ey))
        payload = self._registry().render("local_map", _context(self.char1))
        remembered_ids = {node["id"] for node in payload["nodes"] if node["visibility"] == "remembered"}
        self.assertEqual(remembered_ids, set())

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_walked_wilderness_ground_is_not_remembered(self):
        # Eight ordinary cells of one region -- the reported seven-chips
        # defect -- yields zero remembered nodes, not seven+ identical chips.
        ex, ey = EAST_APPROACH
        for i in range(8):
            self._at_wild((ex + 10 + i, ey + 5))
        self._at_wild((ex + 20, ey + 5))
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(remembered, [])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_remembered_nodes_never_cross_coordinate_spaces(self):
        # A completed traversal records both ends (design D4): walking
        # through the gate leaves both the approach cell and the gate room
        # in the knowledge record.
        gate = [
            exit_obj for exit_obj in self.east_gate.exits if exit_obj.key == "荒野"
        ][0]
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        gate.at_traverse(self.char1, self.east_gate)  # now at the approach
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 10, ey))  # walk far away, keeping both memories

        wild_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(wild_payload["layer"], "wilderness")
        remembered_wild = [
            node for node in wild_payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertTrue(remembered_wild)
        for node in remembered_wild:
            self.assertTrue(node["id"].startswith("wild:"))
            _, _, x, y = node["id"].split(":")
            self.assertEqual((node["x"], node["y"]), (int(x), int(y)))
        self.assertNotIn(wild_payload["current_node"], {n["id"] for n in remembered_wild})

        self.char1.location = self.south_gate
        record_arrival(self.char1)
        grid_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(grid_payload["layer"], "grid")
        remembered_grid = [
            node for node in grid_payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertTrue(remembered_grid)
        for node in remembered_grid:
            self.assertTrue(node["id"].startswith("grid:"))
            _, _, x, y = node["id"].split(":")
            self.assertEqual((node["x"], node["y"]), (int(x), int(y)))
        self.assertNotIn(grid_payload["current_node"], {n["id"] for n in remembered_grid})

    @covers_requirement("webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information")
    def test_an_in_view_gate_approach_cell_names_the_place_behind_it(self):
        # FLAGGED/STRIKEABLE wave 6 (design D8a): standing one cell from the
        # east gate's approach cell, that in-view neighbour is named for
        # what it leads to, not the region it stands on -- while its ID,
        # action, and edge stay exactly what they already were.
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 1, ey))
        payload = self._registry().render("local_map", _context(self.char1))
        neighbor = next(
            node for node in payload["nodes"] if node["id"] == _t_wild_id(ex, ey)
        )
        self.assertEqual(neighbor["label"], _t_anchor_display(_T_MAP_KEY))
        self.assertEqual(neighbor["visibility"], "visible_unvisited")
        # Naming the approach cell for its far side adds no gateway metadata:
        # only the resolved grid gate node carries it.
        self.assertIsNone(neighbor["gateway"])
        edge = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"] and edge["destination"] == neighbor["id"]
        )
        self.assertEqual(edge["label"], "w")

    @covers_requirement("webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information")
    def test_a_cell_in_a_different_region_still_says_so(self):
        # An in-view neighbour across a region edge gets its own plain region
        # label (only registered gate approach cells get the far-side name).
        # The live terrain has no region edge near the capital, so the edge is
        # synthetic: one neighbour cell is classified into another region and
        # the presenter must label each cell from its own classification.
        from world.lore.wilderness_regions import regions
        from world.maps import wilderness_provider
        from world.maps.wilderness_provider import WILDERNESS_NAME

        ex, ey = EAST_APPROACH
        here, neighbour = (ex + 1, ey), (ex + 2, ey)
        self.assertTrue(wilderness_provider.is_valid_wilderness_cell(here))
        self.assertTrue(wilderness_provider.is_valid_wilderness_cell(neighbour))
        here_label = _t_region_display_for(*here)
        other_region = next(
            key
            for key, region in regions().items()
            if region.display_name_zh != here_label
        )
        original = wilderness_provider.region_for_coordinates
        wilderness_provider.region_for_coordinates = (
            lambda x, y: other_region if (x, y) == neighbour else original(x, y)
        )
        self.addCleanup(
            setattr, wilderness_provider, "region_for_coordinates", original
        )
        self._at_wild(here)
        payload = self._registry().render("local_map", _context(self.char1))
        current = next(
            node
            for node in payload["nodes"]
            if node["id"] == payload["current_node"]
        )
        self.assertEqual(current["label"], here_label)
        neighbor = next(
            node
            for node in payload["nodes"]
            if node["id"] == f"wild:{WILDERNESS_NAME}:{neighbour[0]}:{neighbour[1]}"
        )
        self.assertEqual(
            neighbor["label"], regions()[other_region].display_name_zh
        )
        self.assertNotEqual(neighbor["label"], current["label"])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_two_wilderness_gateways_of_one_anchor_stay_distinguishable(self):
        # rubber-duck run 2: a single WildernessEntryPoint can register more
        # than one gate (the sample city already has two), so the anchor's
        # display name alone is NOT unique on the wilderness layer -- the
        # same collision-then-qualify rule the grid layer already had must
        # also apply here, or two genuinely different boundaries render the
        # identical anchor-name chip, reproducing this change's own target
        # defect.
        entry = _live_gateway_entry()
        south_approach = entry.approach_cell(entry.gate_for("n"))
        east_approach = entry.approach_cell(entry.gate_for("w"))
        self._at_wild(south_approach)  # the south gate's approach cell
        self._at_wild(east_approach)  # the east gate's approach cell
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 20, ey))  # far from both
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = {
            node["id"]: node["label"]
            for node in payload["nodes"]
            if node["visibility"] == "remembered"
        }
        # Labels qualify by the gate room's own key (the shipped city gate
        # rooms), read from the live rooms -- never authored here.
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.assertEqual(
            remembered,
            {
                _t_wild_id(*south_approach): f"{_t_anchor_display(_T_MAP_KEY)}（{south_gate.key}）",
                _t_wild_id(*east_approach): f"{_t_anchor_display(_T_MAP_KEY)}（{east_gate.key}）",
            },
        )
        self.assertEqual(len(set(remembered.values())), 2)

class LocalMapRememberedGatewayTests(_RememberedGatewayFixture, EvenniaTest):
    """Recency, ceiling and robustness of the remembered gateway nodes."""

    @covers_requirement("webclient-local-map::remembered-wilderness-boundaries-do-not-probe-every-visited-cell")
    def test_gateway_lookups_do_not_grow_with_visited_cells(self):
        ex, ey = EAST_APPROACH
        with patch.object(gateways, "_GATEWAY_TABLE", SourceMemo()), patch.object(
            gateways, "_build_gateway_table", wraps=gateways._build_gateway_table
        ) as builds:
            self._at_wild((ex + 10, ey + 5))
            self._at_wild((ex + 20, ey))
            count_few = self._render_counting_gateway_lookups()
            for i in range(1, 9):
                self._at_wild((ex + 10 + i, ey + 5))
            # Same position again, so the in-view neighbour set is identical.
            self._at_wild((ex + 20, ey))
            count_many = self._render_counting_gateway_lookups()
        self.assertEqual(count_few, count_many)
        # The in-view loop asks once per revealed non-grid neighbour.
        self.assertTrue(1 <= count_many <= 8, count_many)
        self.assertEqual(builds.call_count, 1)

    def _visit_both_approaches_with_distinct_recency(self):
        """Stand on both approach cells, walk away, and pin distinct recency.

        The approach whose node ID sorts LATER as a string gets the larger
        ``last_seen_tick``, so only recency (never ID order) can put it first.
        Returns ``(later_id, earlier_id)`` in the expected payload order.
        """
        from evennia.utils.dbserialize import deserialize
        from world.maps.wilderness_provider import WILDERNESS_NAME
        from world.rules.map_knowledge import CHUNK_CELLS, KNOWLEDGE_ATTR

        entry = _live_gateway_entry()
        south_approach = entry.approach_cell(entry.gate_for("n"))
        east_approach = entry.approach_cell(entry.gate_for("w"))
        self._at_wild(south_approach)
        self._at_wild(east_approach)
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 20, ey))

        record = deserialize(self.char1.attributes.get(KNOWLEDGE_ATTR))
        chunks = record["wilderness"][WILDERNESS_NAME]

        def cell_entry(cell):
            x, y = cell
            chunk = chunks[f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}"]
            return chunk[str((y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS))]

        later, earlier = sorted(
            (south_approach, east_approach), key=lambda cell: _t_wild_id(*cell), reverse=True
        )
        base = max(
            tick
            for cell in (later, earlier)
            for tick in (cell_entry(cell)["first_seen_tick"], cell_entry(cell)["last_seen_tick"])
        )
        cell_entry(later)["last_seen_tick"] = base + 50
        cell_entry(earlier)["last_seen_tick"] = base + 40
        self.char1.attributes.add(KNOWLEDGE_ATTR, record)
        return _t_wild_id(*later), _t_wild_id(*earlier)

    @covers_requirement("webclient-local-map::remembered-wilderness-boundaries-do-not-probe-every-visited-cell")
    def test_remembered_gateways_follow_recency_not_id_order(self):
        later_id, earlier_id = self._visit_both_approaches_with_distinct_recency()
        self.assertGreater(later_id, earlier_id)
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = [
            node["id"] for node in payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertEqual(remembered, [later_id, earlier_id])

    @covers_requirement("webclient-local-map::remembered-wilderness-boundaries-do-not-probe-every-visited-cell")
    def test_the_remembered_ceiling_applies_after_filtering(self):
        later_id, _ = self._visit_both_approaches_with_distinct_recency()
        with patch(
            "web.webclient.presentation.local_map.wilderness.MAX_REMEMBERED_GATEWAYS", 1
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        remembered = [
            node for node in payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertEqual([node["id"] for node in remembered], [later_id])
        # Collision counting runs over the bounded set only: no qualifier.
        self.assertEqual(remembered[0]["label"], _t_anchor_display(_T_MAP_KEY))

    @covers_requirement("webclient-local-map::remembered-wilderness-boundaries-do-not-probe-every-visited-cell")
    def test_an_out_of_bounds_point_gateway_does_not_break_the_layer(self):
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate

        registry = _live("world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY")
        max_x = _live("world.maps.wilderness_provider", "WILDERNESS_MAX_X")
        outside = WildernessEntryPoint(
            anchor_key="t_out_of_bounds",
            shape=("#",),
            origin_xy=(max_x + 5, 0),
            gates=(WildernessGate("n", _live_gateway_entry().gate_for("n").destination),),
        )
        ex, ey = EAST_APPROACH
        with patch(
            "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
            {**dict(registry.items()), "t_out_of_bounds": outside},
        ):
            self._at_wild((ex + 20, ey))
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])

    @covers_requirement("wilderness-gateway::physical-footprints-and-concealed-point-entries-preserve-approaches")
    def test_ciaran_non_entrance_directions_do_not_disclose_the_village(self):
        # Task 2.6: at the hidden point entrance only the authored direction is
        # a gateway; selecting any other direction stays ordinary wilderness
        # movement and the payload never names the concealed settlement.
        from world.maps.wilderness_destination import resolve_wilderness_destination

        entries = _live(
            "world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY"
        ).values()
        point = next(entry for entry in entries if entry.is_point_shape)
        village_label = _t_anchor_display(point.anchor_key)
        authored = point.gates[0].return_direction

        self._at_wild(point.anchor_cell)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["current_node"], _t_wild_id(*point.anchor_cell))
        labels = [node["label"] for node in payload["nodes"]]
        self.assertNotIn(village_label, labels)
        self.assertFalse(
            any(village_label in label for label in labels),
            "the concealed village name leaked into the wilderness payload",
        )

        room = self.char1.location
        for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
            destination = resolve_wilderness_destination(room, direction)
            if direction == authored:
                self.assertTrue(destination.startswith("grid:"), direction)
                continue
            self.assertTrue(
                destination is None or destination.startswith("wild:"),
                f"{direction} hijacked the concealed entrance: {destination}",
            )


class LocalMapWildernessDisclosureTests(EvenniaTest):
    """The wilderness layer publishes only what the observer may know.

    A synthetic schema-2 knowledge record pins the reveal precondition exactly
    (a zero-sight cell, or one cell of ground sight), so each scenario proves
    the disclosure decision rather than the ambient light phase. The hidden
    entry is the shipped point-shape registry row, probed at runtime.
    """

    WHY_NO_EDGES = "an undisclosed direction publishes no edge either"

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        declared = _declared_gateway_maps()
        sync_test_settlements(declared)
        sync_test_wilderness(declared)

    def _registry(self):
        return build_production_registry()

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(
            self.char1, coordinates=coordinates, name=WILDERNESS_NAME
        )
        self.assertTrue(entered, coordinates)
        record_arrival(self.char1)

    def _pin_knowledge(self, sight, visited_grid=()):
        """Replace the record with one synthetic visit carrying ``sight``."""
        from world.maps.wilderness_provider import WILDERNESS_NAME
        from world.rules.map_knowledge import CHUNK_CELLS, KNOWLEDGE_ATTR

        x, y = self.char1.location.coordinates
        offset = (y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS)
        chunk_key = f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}"
        record = {
            "schema_version": 2,
            "visited": {
                node_id: {"first_seen_tick": 1, "last_seen_tick": 1}
                for node_id in visited_grid
            },
            "wilderness": {
                WILDERNESS_NAME: {
                    chunk_key: {
                        str(offset): {
                            "first_seen_tick": 1,
                            "last_seen_tick": 1,
                            "sight": sight,
                        }
                    }
                }
            },
        }
        self.char1.attributes.add(KNOWLEDGE_ATTR, record)

    def _point_entry(self):
        entries = _live(
            "world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY"
        ).values()
        return next(entry for entry in entries if entry.is_point_shape)

    def _away_cell(self):
        ex, ey = EAST_APPROACH
        return (ex + 10, ey + 5)

    @covers_requirement(
        "webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel"
    )
    @covers_requirement(
        "wilderness-map-disclosure::all-wilderness-map-publishers-enforce-reveal-boundaries"
    )
    def test_a_radius_zero_forest_night_publishes_only_the_current_cell(self):
        cell = self._away_cell()
        self._at_wild(cell)
        self._pin_knowledge(0)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        self.assertEqual(payload["current_node"], _t_wild_id(*cell))
        self.assertEqual([node["id"] for node in payload["nodes"]], [_t_wild_id(*cell)])
        self.assertEqual(payload["edges"], [], self.WHY_NO_EDGES)
        # The current cell still names the ground the player stands on.
        self.assertEqual(
            payload["nodes"][0]["label"], _t_region_display_for(*cell)
        )

    @covers_requirement("webclient-local-map::wilderness-minimap-nodes-are-actionable")
    def test_one_revealed_cell_draws_its_neighbour_with_the_canonical_action(self):
        from world.maps.wilderness_destination import (
            DIRECTION_DELTAS,
            resolve_wilderness_destination,
        )
        from world.maps.wilderness_provider import WILDERNESS_NAME

        cell = self._away_cell()
        self._at_wild(cell)
        self._pin_knowledge(1)
        payload = self._registry().render("local_map", _context(self.char1))
        room = self.char1.location
        emitted = {node["id"] for node in payload["nodes"]} - {payload["current_node"]}
        self.assertTrue(emitted, "a revealed neighbourhood must draw its neighbours")
        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            node_id = f"wild:{WILDERNESS_NAME}:{cell[0] + dx}:{cell[1] + dy}"
            if node_id not in emitted:
                continue
            node = next(node for node in payload["nodes"] if node["id"] == node_id)
            expected = resolve_wilderness_destination(room, direction)
            self.assertEqual(expected, node_id, direction)
            self.assertEqual(node["action"]["destination"], node_id, direction)
            self.assertEqual(
                node["label"], _t_region_display_for(cell[0] + dx, cell[1] + dy)
            )

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    @covers_requirement(
        "wilderness-map-disclosure::all-wilderness-map-publishers-enforce-reveal-boundaries"
    )
    def test_a_hidden_gateway_is_omitted_until_its_gate_room_is_visited(self):
        point = self._point_entry()
        hidden_name = _t_anchor_display(point.anchor_key)
        self._at_wild(point.anchor_cell)
        self._pin_knowledge(0)

        payload = self._registry().render("local_map", _context(self.char1))
        self.assertFalse(
            [node for node in payload["nodes"] if node["id"].startswith("grid:")],
            "an unvisited hidden gateway must publish no grid identity",
        )
        self.assertNotIn(hidden_name, [node["label"] for node in payload["nodes"]])

        # Standing in the gate room once is the actual visit that permits the
        # identity; the wilderness view then names the place it leads into.
        gate_direction = point.gates[0].return_direction
        gate_xyz = _live(
            "world.maps." + "static_references", "settlement_node_xyz"
        )(point.gates[0].destination)
        gate_room = GridRoom.objects.filter_xyz(xyz=gate_xyz).first()
        self.assertIsNotNone(gate_room)
        gate_node = encode_grid(gate_xyz[2], gate_xyz[0], gate_xyz[1])
        # The observer stays on the anchor cell; only the stored visit changes.
        self._pin_knowledge(0, visited_grid=(gate_node,))
        payload = self._registry().render("local_map", _context(self.char1))
        gateway_node = next(
            node for node in payload["nodes"] if node["id"] == gate_node
        )
        self.assertEqual(gateway_node["label"], gate_room.key)
        self.assertEqual(gateway_node["gateway"], {"leads_to": hidden_name})
        self.assertEqual(gateway_node["action"]["destination"], gate_node)
        edge = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"]
            and edge["destination"] == gate_node
        )
        self.assertEqual(edge["label"], gate_direction)
        self.assertTrue(edge["traversable"])


if __name__ == "__main__":
    unittest.main()
